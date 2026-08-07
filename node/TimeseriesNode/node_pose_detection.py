#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PoseDetection Node for CV_Studio (DataModel domain).

Accepts pose estimation results (JSON + image) from a PoseEstimation node and
classifies the pose into a human-readable label.

Body detection types (MoveNet Single/Multi, MediaPipe Pose):
    debout, assis, courbé, allongé, à croupis, à quatre pattes, couché

Hand detection (MediaPipe Hands):
    Ouvert, Fermé, Pointé, V / Paix, Pouce levé, Inconnu
"""

import copy
import math
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Detection type options and mapping to model families
# ---------------------------------------------------------------------------

DETECTION_TYPES = [
    "Corps - SinglePose (MoveNet)",
    "Corps - MultiPose (MoveNet)",
    "Corps - MediaPipe Pose",
    "Main - MediaPipe Hands",
]

_BODY_MOVENET_TYPES = {
    "Corps - SinglePose (MoveNet)",
    "Corps - MultiPose (MoveNet)",
}
_BODY_MEDIAPIPE_TYPES = {"Corps - MediaPipe Pose"}
_HAND_TYPES = {"Main - MediaPipe Hands"}

# ---------------------------------------------------------------------------
# Body posture labels
# ---------------------------------------------------------------------------
BODY_LABELS = [
    "debout",
    "assis",
    "courbé",
    "allongé",
    "à croupis",
    "à quatre pattes",
    "couché",
]

# Label → colour (BGR) used for overlay text
LABEL_COLORS = {
    "debout":           (0, 220, 0),
    "assis":            (0, 180, 255),
    "courbé":           (0, 255, 220),
    "allongé":          (255, 180, 0),
    "à croupis":        (255, 0, 180),
    "à quatre pattes":  (180, 0, 255),
    "couché":           (0, 140, 255),
    # hand
    "Ouvert":           (0, 220, 0),
    "Fermé":            (0, 0, 220),
    "Pointé":           (0, 220, 220),
    "V / Paix":         (220, 220, 0),
    "Pouce levé":       (220, 100, 0),
    "Inconnu":          (150, 150, 150),
}

DEFAULT_COLOR = (200, 200, 200)


# ---------------------------------------------------------------------------
# Helper: angle between three points (radians)
# ---------------------------------------------------------------------------

def _angle_rad(a, b, c):
    """Return the angle at vertex *b* formed by segments b→a and b→c."""
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    dot = ax * cx + ay * cy
    mag_a = math.hypot(ax, ay)
    mag_c = math.hypot(cx, cy)
    if mag_a < 1e-6 or mag_c < 1e-6:
        return math.pi
    cos_val = max(-1.0, min(1.0, dot / (mag_a * mag_c)))
    return math.acos(cos_val)


# ---------------------------------------------------------------------------
# Body posture classifier
# ---------------------------------------------------------------------------

def _classify_body_movenet(results_list, score_th, image_h, image_w):
    """
    Classify body posture from MoveNet keypoints.

    MoveNet keypoint indices (17 total):
      0  nose,  1  left_eye,   2  right_eye,  3  left_ear,   4  right_ear
      5  left_shoulder,        6  right_shoulder
      7  left_elbow,           8  right_elbow
      9  left_wrist,          10  right_wrist
     11  left_hip,            12  right_hip
     13  left_knee,           14  right_knee
     15  left_ankle,          16  right_ankle

    Each keypoint: [x_px, y_px, score]
    """
    labels = []
    for person in results_list:
        label = _classify_movenet_person(person, score_th, image_h, image_w)
        labels.append(label)
    return labels


def _safe_kp(person, idx, score_th):
    """Return (x, y) for MoveNet keypoint idx if score >= score_th, else None."""
    kp = person.get(idx)
    if kp is None:
        return None
    if len(kp) < 3:
        return None
    if kp[2] < score_th:
        return None
    return (int(kp[0]), int(kp[1]))


def _classify_movenet_person(person, score_th, image_h, image_w):
    sh_l = _safe_kp(person, 5, score_th)
    sh_r = _safe_kp(person, 6, score_th)
    hi_l = _safe_kp(person, 11, score_th)
    hi_r = _safe_kp(person, 12, score_th)
    kn_l = _safe_kp(person, 13, score_th)
    kn_r = _safe_kp(person, 14, score_th)
    an_l = _safe_kp(person, 15, score_th)
    an_r = _safe_kp(person, 16, score_th)
    wr_l = _safe_kp(person, 9, score_th)
    wr_r = _safe_kp(person, 10, score_th)

    shoulder = _avg_pt(sh_l, sh_r)
    hip = _avg_pt(hi_l, hi_r)
    knee = _avg_pt(kn_l, kn_r)
    ankle = _avg_pt(an_l, an_r)
    wrist = _avg_pt(wr_l, wr_r)

    return _classify_from_body_points(shoulder, hip, knee, ankle, wrist, image_h, image_w)


def _classify_body_mediapipe(results_list, score_th, image_h, image_w):
    """
    Classify body posture from MediaPipe Pose keypoints.

    MediaPipe Pose indices (33 total):
     11  left_shoulder,  12  right_shoulder
     13  left_elbow,     14  right_elbow
     15  left_wrist,     16  right_wrist
     23  left_hip,       24  right_hip
     25  left_knee,      26  right_knee
     27  left_ankle,     28  right_ankle

    Each keypoint: [x_px, y_px, z, visibility]
    """
    labels = []
    for person in results_list:
        label = _classify_mediapipe_person(person, score_th, image_h, image_w)
        labels.append(label)
    return labels


def _safe_mp(person, idx, score_th):
    """Return (x, y) for MediaPipe keypoint idx if visibility >= score_th, else None."""
    kp = person.get(idx)
    if kp is None:
        return None
    if len(kp) < 4:
        return None
    if kp[3] < score_th:
        return None
    return (int(kp[0]), int(kp[1]))


def _classify_mediapipe_person(person, score_th, image_h, image_w):
    sh_l = _safe_mp(person, 11, score_th)
    sh_r = _safe_mp(person, 12, score_th)
    hi_l = _safe_mp(person, 23, score_th)
    hi_r = _safe_mp(person, 24, score_th)
    kn_l = _safe_mp(person, 25, score_th)
    kn_r = _safe_mp(person, 26, score_th)
    an_l = _safe_mp(person, 27, score_th)
    an_r = _safe_mp(person, 28, score_th)
    wr_l = _safe_mp(person, 15, score_th)
    wr_r = _safe_mp(person, 16, score_th)

    shoulder = _avg_pt(sh_l, sh_r)
    hip = _avg_pt(hi_l, hi_r)
    knee = _avg_pt(kn_l, kn_r)
    ankle = _avg_pt(an_l, an_r)
    wrist = _avg_pt(wr_l, wr_r)

    return _classify_from_body_points(shoulder, hip, knee, ankle, wrist, image_h, image_w)


def _avg_pt(a, b):
    """Return the average point between two (x,y) tuples (either may be None)."""
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)


def _classify_from_body_points(shoulder, hip, knee, ankle, wrist, image_h, image_w):
    """
    Rule-based body posture classification using key body points.

    In image coordinates y increases downward.

    Classification logic:
    1. If vertical body span is tiny → lying (allongé / couché).
    2. Check wrists near ground level → à quatre pattes.
    3. Compute the knee angle (hip–knee–ankle): deeply bent → à croupis,
       moderately bent → assis, straight + torso leaning → courbé, else debout.
    """
    if shoulder is None:
        return "inconnu"

    # --- Lying down detection -------------------------------------------
    pts = [p for p in [shoulder, hip, knee, ankle] if p is not None]
    if len(pts) >= 2:
        ys = [p[1] for p in pts]
        xs = [p[0] for p in pts]
        vert_span = max(ys) - min(ys)
        horiz_span = max(xs) - min(xs)
        if vert_span < image_h * 0.12:
            return "allongé" if horiz_span > image_w * 0.2 else "couché"

    if hip is None:
        return "debout"

    sh_y, sh_x = shoulder[1], shoulder[0]
    hi_y, hi_x = hip[1], hip[0]

    # Torso lean: ratio of horizontal to total displacement shoulder→hip
    torso_len = math.hypot(hi_x - sh_x, hi_y - sh_y)
    torso_lean = abs(hi_x - sh_x) / (torso_len + 1)  # 0=upright, ~0.7=45°

    if knee is not None:
        kn_y, kn_x = knee[1], knee[0]

        if ankle is not None:
            an_y, an_x = ankle[1], ankle[0]

            # Knee angle (at vertex knee, between hip and ankle)
            kn_angle = math.degrees(_angle_rad(
                (hi_x, hi_y), (kn_x, kn_y), (an_x, an_y)
            ))

            if kn_angle < 80:
                # Deep knee bend: à croupis unless wrists are at ankle level
                if wrist is not None and wrist[1] >= an_y - image_h * 0.08:
                    return "à quatre pattes"
                return "à croupis"
            if kn_angle < 135:
                # Moderate bend: check wrists for all-fours, else assis
                if wrist is not None and wrist[1] >= kn_y - image_h * 0.04:
                    return "à quatre pattes"
                return "assis"
            # Straight leg: check torso lean
            if torso_lean > 0.40:
                return "courbé"
            return "debout"
        else:
            # No ankle: use hip-knee proximity
            if kn_y - hi_y < image_h * 0.06:
                return "assis"
            if torso_lean > 0.40:
                return "courbé"
            return "debout"
    else:
        if torso_lean > 0.40:
            return "courbé"
        return "debout"


# ---------------------------------------------------------------------------
# Hand gesture classifier
# ---------------------------------------------------------------------------

def _is_finger_extended(tip, pip):
    """Return True if fingertip is clearly above the PIP joint (y smaller = higher)."""
    if tip is None or pip is None:
        return False
    return tip[1] < pip[1] - 5


def _classify_hand(hand, image_h):
    """
    Classify hand gesture from MediaPipe Hands keypoints.

    Each hand: dict with integer keys 0..20 → [x_px, y_px, z]
    and special keys 'palm_moment', 'label'.

    Landmarks:
      0 wrist
      1-4   thumb   (CMC, MCP, IP, TIP)
      5-8   index   (MCP, PIP, DIP, TIP)
      9-12  middle  (MCP, PIP, DIP, TIP)
     13-16  ring    (MCP, PIP, DIP, TIP)
     17-20  pinky   (MCP, PIP, DIP, TIP)
    """
    def pt(idx):
        kp = hand.get(idx)
        if kp is None:
            return None
        return (int(kp[0]), int(kp[1]))

    wrist = pt(0)

    # Thumb: compare TIP.x vs MCP.x (hand orientation dependent)
    thumb_tip = pt(4)
    thumb_mcp = pt(2)
    thumb_ext = False
    if thumb_tip is not None and thumb_mcp is not None and wrist is not None:
        # Rough check: thumb TIP is far from wrist compared to thumb MCP
        d_tip = math.hypot(thumb_tip[0] - wrist[0], thumb_tip[1] - wrist[1])
        d_mcp = math.hypot(thumb_mcp[0] - wrist[0], thumb_mcp[1] - wrist[1])
        thumb_ext = d_tip > d_mcp * 1.3

    index_ext  = _is_finger_extended(pt(8),  pt(6))
    middle_ext = _is_finger_extended(pt(12), pt(10))
    ring_ext   = _is_finger_extended(pt(16), pt(14))
    pinky_ext  = _is_finger_extended(pt(20), pt(18))

    fingers = [index_ext, middle_ext, ring_ext, pinky_ext]
    n_ext = sum(fingers)

    if n_ext == 4:
        return "Ouvert"
    if n_ext == 0 and not thumb_ext:
        return "Fermé"
    if index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Pointé"
    if index_ext and middle_ext and not ring_ext and not pinky_ext:
        return "V / Paix"
    if thumb_ext and not index_ext and not middle_ext and not ring_ext and not pinky_ext:
        return "Pouce levé"

    return "Inconnu"


def _classify_hands(results_list, image_h, image_w):
    labels = []
    for hand in results_list:
        labels.append(_classify_hand(hand, image_h))
    return labels


# ---------------------------------------------------------------------------
# Overlay drawing
# ---------------------------------------------------------------------------

def _draw_labels(image, labels, detection_type):
    """Overlay detected labels on the image."""
    debug = copy.deepcopy(image)
    h, w = debug.shape[:2]

    header = detection_type
    cv2.putText(
        debug, header,
        (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6,
        (255, 255, 255), 2, cv2.LINE_AA,
    )

    for i, label in enumerate(labels):
        color = LABEL_COLORS.get(label, DEFAULT_COLOR)
        y_pos = 55 + i * 35
        if y_pos + 10 > h:
            break
        # Background rectangle for readability
        text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(
            debug,
            (8, y_pos - text_size[1] - 4),
            (8 + text_size[0] + 8, y_pos + 4),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            debug, label,
            (12, y_pos),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8,
            color, 2, cv2.LINE_AA,
        )

    if not labels:
        cv2.putText(
            debug, "Aucune detection",
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7,
            (120, 120, 120), 2, cv2.LINE_AA,
        )

    return debug


# ---------------------------------------------------------------------------
# FactoryNode
# ---------------------------------------------------------------------------

class FactoryNode:
    """Factory for creating PoseDetection nodes."""

    node_label = 'PoseDetection'
    node_tag = 'PoseDetection'

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        node = Node()
        node.tag_node_name = str(node_id) + ':' + self.node_tag

        # Inputs
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'

        # Static selector
        node.tag_node_input03_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03'
        node.tag_node_input03_value_name = node.tag_node_name + ':' + node.TYPE_TEXT + ':Input03Value'

        # Outputs
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = opencv_setting_dict['process_width']
        small_window_h = opencv_setting_dict['process_height']
        use_pref_counter = opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_w, small_window_h, 3))
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Image input
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Image',
                )

            # Image output (with texture)
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Pose JSON input
            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input Pose Data',
                )

            # Detection type combo
            with dpg.node_attribute(
                tag=node.tag_node_input03_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    DETECTION_TYPES,
                    default_value=DETECTION_TYPES[0],
                    width=small_window_w,
                    tag=node.tag_node_input03_value_name,
                )

            # Elapsed time output
            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='Elapsed time(ms)',
                    )

            # JSON results output
            with dpg.node_attribute(
                tag=node.tag_node_output03_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output03_value_name,
                    default_value='Detection Results',
                )

        return node


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class Node(Node):
    """PoseDetection Node implementation."""

    _ver = '0.0.1'
    node_label = 'PoseDetection'
    node_tag = 'PoseDetection'

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag

        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        output_value03_tag = tag_node_name + ':' + self.TYPE_JSON + ':Output03Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        detection_type = dpg_get_value(input_value03_tag)

        # --- Resolve connections -------------------------------------------
        image_src = ''
        json_src = ''
        for conn in connection_list:
            conn_type = conn[0].split(':')[2]
            src_base = ':'.join(conn[0].split(':')[:2])
            if conn_type == self.TYPE_IMAGE and not image_src:
                image_src = src_base
            elif conn_type == self.TYPE_JSON and not json_src:
                json_src = src_base

        frame = node_image_dict.get(image_src, None)
        pose_result = node_result_dict.get(json_src, {})

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        # --- Classify -------------------------------------------------------
        labels = []
        result = {}

        if frame is not None and pose_result:
            results_list = pose_result.get('results_list', [])
            score_th = pose_result.get('score_th', 0.3)
            h, w = frame.shape[:2]

            if detection_type in _BODY_MOVENET_TYPES:
                labels = _classify_body_movenet(results_list, score_th, h, w)
            elif detection_type in _BODY_MEDIAPIPE_TYPES:
                labels = _classify_body_mediapipe(results_list, score_th, h, w)
            elif detection_type in _HAND_TYPES:
                labels = _classify_hands(results_list, h, w)

            result['detection_type'] = detection_type
            result['labels'] = labels
            result['model_name'] = pose_result.get('model_name', '')

        if frame is not None and use_pref_counter:
            elapsed_time = int((time.monotonic() - start_time) * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # --- Draw and update texture ----------------------------------------
        debug_frame = None
        if frame is not None:
            debug_frame = _draw_labels(frame, labels, detection_type)
            texture = self.convert_cv_to_dpg(debug_frame, small_window_w, small_window_h)
            dpg_set_value(output_value01_tag, texture)

        return {"image": debug_frame if debug_frame is not None else frame, "json": result, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'
        detection_type = dpg_get_value(input_value03_tag)
        pos = dpg.get_item_pos(tag_node_name)
        return {
            'ver': self._ver,
            'pos': pos,
            input_value03_tag: detection_type,
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        input_value03_tag = tag_node_name + ':' + self.TYPE_TEXT + ':Input03Value'
        if input_value03_tag in setting_dict:
            dpg_set_value(input_value03_tag, setting_dict[input_value03_tag])
