#!/usr/bin/env python
# -*- coding: utf-8 -*-
import copy
import os
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value

from node.node_abc import DpgNodeABC
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directory where ONNX ReID model files should be placed
_REID_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'reid_models'
)

# Feature-extraction method names shown in the UI combo box
_METHOD_COLOR_HIST = 'Color Histogram'
_METHOD_OSNET_X0_25 = 'OSNet_x0_25'
_METHOD_OSNET_X0_5 = 'OSNet_x0_5'
_METHOD_OSNET_X1_0 = 'OSNet_x1_0'
_METHODS = [
    _METHOD_COLOR_HIST,
    _METHOD_OSNET_X0_25,
    _METHOD_OSNET_X0_5,
    _METHOD_OSNET_X1_0,
]

# ONNX model file names for each deep method
_OSNET_MODEL_FILES = {
    _METHOD_OSNET_X0_25: 'osnet_x0_25.onnx',
    _METHOD_OSNET_X0_5: 'osnet_x0_5.onnx',
    _METHOD_OSNET_X1_0: 'osnet_x1_0.onnx',
}

# Feature dimensions
_FEAT_DIM_HIST = 48     # 16 bins × 3 channels
_FEAT_DIM_OSNET = 512   # OSNet embedding dimension

# ImageNet normalisation constants used for OSNet pre-processing
_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# Exponential moving-average factor for centroid updates after initialisation.
# Higher = slower adaptation (more stable labels).  Lower = faster adaptation.
_CENTROID_EMA_ALPHA = 0.92


class FactoryNode:
    node_label = 'ReId'
    node_tag = 'ReId'

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
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'
        node.tag_node_output03_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03'
        node.tag_node_output03_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output03Value'

        # Extra UI tags
        node.tag_method_value = node.tag_node_name + ':MethodValue'
        node.tag_status_text = node.tag_node_name + ':StatusText'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        # Yellow theme for JSON output button
        with dpg.theme() as yellow_button_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (255, 255, 153, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 255, 153, 255))

        # Initialise slot tracking for this node with 2 default slots (A / B)
        if node.tag_node_name not in node._slot_id:
            node._slot_id[node.tag_node_name] = 2
            node._slot_names[node.tag_node_name] = {1: "A", 2: "B"}

        # Seed the method so update() works even before the combo callback fires
        if node.tag_node_name not in node._selected_method:
            node._selected_method[node.tag_node_name] = _METHOD_OSNET_X0_25

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Image',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_input02_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Input JSON (ObjectDetection)',
                )

            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Feature-extraction method selector
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':MethodAttr',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=node.tag_method_value,
                    label='Method',
                    items=_METHODS,
                    default_value=_METHOD_OSNET_X0_25,
                    width=170,
                    callback=node._on_method_change,
                    user_data=node.tag_node_name,
                )

            # Training status text
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':StatusAttr',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_status_text,
                    default_value=f'Waiting: 0/{self._slot_id.get(node.tag_node_name, 2)} players',
                )

            # Slot name fields (A / B by default)
            for slot_num in range(1, 3):
                tag_node_slotXX_name = node.tag_node_name + ':Slot' + str(slot_num).zfill(2)
                tag_node_slotXX_value_name = tag_node_slotXX_name + 'Value'
                default_name = node._slot_names[node.tag_node_name].get(slot_num, f"player{slot_num}")

                with dpg.node_attribute(
                        tag=tag_node_slotXX_name,
                        attribute_type=dpg.mvNode_Attr_Static,
                ):
                    dpg.add_input_text(
                        tag=tag_node_slotXX_value_name,
                        default_value=default_name,
                        label=f"Slot {slot_num}",
                        callback=node._on_slot_name_change,
                        user_data=(node.tag_node_name, slot_num),
                        width=150,
                    )

            # Slot management
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':SlotManagement',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Add Slot',
                    width=int(small_window_w / 2),
                    callback=node._add_slot,
                    user_data=node.tag_node_name,
                )
                dpg.add_button(
                    label='Remove Slot',
                    width=int(small_window_w / 2),
                    callback=node._remove_slot,
                    user_data=node.tag_node_name,
                )

            # KMeans reset
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':KMeansReset',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    label='Reset KMeans',
                    width=small_window_w,
                    callback=node._reset_kmeans,
                    user_data=node.tag_node_name,
                )

            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

            # JSON output button
            with dpg.node_attribute(
                    tag=node.tag_node_output03_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                btn = dpg.add_button(
                    label="JSON",
                    tag=node.tag_node_output03_value_name,
                    width=small_window_w,
                    enabled=False,
                )
                dpg.bind_item_theme(btn, yellow_button_theme)

        return node


class Node(Node):
    _ver = '0.0.4'

    node_label = 'ReId'
    node_tag = 'ReId'

    _opencv_setting_dict = None

    # Slot management (class-level so all instances share them)
    _max_slot_number = 20
    _slot_id = {}
    _slot_names = {}

    # ReID data structures – keyed by tag_node_name
    _centroids = {}              # np.array (n_slots, feat_dim) once initialised
    _centroids_initialized = {}  # bool – True once the first N-player frame is seen
    _onnx_sessions = {}          # onnxruntime InferenceSession per node (or None)
    _selected_method = {}        # selected method string (avoids dpg_get_value in hot path)

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # UI callbacks
    # ------------------------------------------------------------------

    def _on_method_change(self, sender, app_data, user_data):
        """Store the newly selected method and clear the ONNX session cache."""
        tag_node_name = user_data
        self._selected_method[tag_node_name] = app_data
        if tag_node_name in self._onnx_sessions:
            del self._onnx_sessions[tag_node_name]
        logger.info(f"ReID method changed to '{app_data}' for {tag_node_name}")

    def _add_slot(self, sender, data, user_data):
        """Add a new slot with a default name."""
        tag_node_name = user_data

        if self._max_slot_number > self._slot_id[tag_node_name]:
            self._slot_id[tag_node_name] += 1
            slot_number = self._slot_id[tag_node_name]

            default_name = f"player{slot_number}"
            self._slot_names[tag_node_name][slot_number] = default_name

            before_tag = tag_node_name + ':SlotManagement'
            tag_node_slotXX_name = tag_node_name + ':Slot' + str(slot_number).zfill(2)
            tag_node_slotXX_value_name = tag_node_slotXX_name + 'Value'

            with dpg.node_attribute(
                    tag=tag_node_slotXX_name,
                    attribute_type=dpg.mvNode_Attr_Static,
                    parent=tag_node_name,
                    before=before_tag,
            ):
                dpg.add_input_text(
                    tag=tag_node_slotXX_value_name,
                    default_value=default_name,
                    label=f"Slot {slot_number}",
                    callback=self._on_slot_name_change,
                    user_data=(tag_node_name, slot_number),
                    width=150,
                )

    def _remove_slot(self, sender, data, user_data):
        """Remove the last slot."""
        tag_node_name = user_data

        if self._slot_id[tag_node_name] > 1:
            slot_number = self._slot_id[tag_node_name]

            if slot_number in self._slot_names[tag_node_name]:
                del self._slot_names[tag_node_name][slot_number]

            tag_node_slotXX_name = tag_node_name + ':Slot' + str(slot_number).zfill(2)
            if dpg.does_item_exist(tag_node_slotXX_name):
                dpg.delete_item(tag_node_slotXX_name)

            self._slot_id[tag_node_name] -= 1

    def _on_slot_name_change(self, sender, app_data, user_data):
        """Callback when user renames a slot."""
        tag_node_name, slot_number = user_data
        self._slot_names[tag_node_name][slot_number] = app_data
        logger.info(f"Slot {slot_number} renamed to: {app_data}")

    def _reset_kmeans(self, sender, data, user_data):
        """Reset centroid state so the node re-initialises on the next frame."""
        tag_node_name = user_data

        self._centroids.pop(tag_node_name, None)
        self._centroids_initialized[tag_node_name] = False

        logger.info(f"ReID centroids reset for node {tag_node_name}")
        # Status label will refresh on the next update() cycle

    # ------------------------------------------------------------------
    # ONNX session management
    # ------------------------------------------------------------------

    def _get_onnx_session(self, tag_node_name, method):
        """Return a cached onnxruntime session for *method*, or None if unavailable."""
        if tag_node_name in self._onnx_sessions:
            return self._onnx_sessions[tag_node_name]

        model_filename = _OSNET_MODEL_FILES.get(method)
        if not model_filename:
            self._onnx_sessions[tag_node_name] = None
            return None

        model_path = os.path.join(_REID_MODELS_DIR, model_filename)
        if not os.path.isfile(model_path):
            logger.warning(
                f"ReID: ONNX model not found at '{model_path}'. "
                f"Falling back to Color Histogram. "
                f"See node/TrackerNode/reid_models/README.md for setup instructions."
            )
            self._onnx_sessions[tag_node_name] = None
            return None

        try:
            import onnxruntime as ort
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            session = ort.InferenceSession(model_path, providers=providers)
            self._onnx_sessions[tag_node_name] = session
            logger.info(f"ReID: Loaded ONNX session for {method} from '{model_path}'")
            return session
        except Exception as e:
            logger.warning(f"ReID: Failed to load ONNX session for {method}: {e}. Falling back to Color Histogram.")
            self._onnx_sessions[tag_node_name] = None
            return None

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------

    def _crop_bbox(self, frame, bbox):
        """Return the clipped ROI for *bbox*, or None if invalid."""
        x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
        h, w = frame.shape[:2]
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h))
        if x2 <= x1 or y2 <= y1:
            return None
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        return roi

    def _extract_features(self, frame, bbox):
        """Extract color-histogram features (48-dim) from *bbox* in *frame*."""
        roi = self._crop_bbox(frame, bbox)
        if roi is None:
            return np.zeros(_FEAT_DIM_HIST)

        hist_b = np.histogram(roi[:, :, 0], bins=16, range=(0, 256))[0].astype(np.float32)
        hist_g = np.histogram(roi[:, :, 1], bins=16, range=(0, 256))[0].astype(np.float32)
        hist_r = np.histogram(roi[:, :, 2], bins=16, range=(0, 256))[0].astype(np.float32)

        hist_b /= (hist_b.sum() + 1e-6)
        hist_g /= (hist_g.sum() + 1e-6)
        hist_r /= (hist_r.sum() + 1e-6)

        return np.concatenate([hist_b, hist_g, hist_r])

    def _extract_osnet_features(self, frame, bbox, session):
        """Extract OSNet deep embedding (512-dim) from *bbox* using *session*."""
        roi = self._crop_bbox(frame, bbox)
        if roi is None:
            return np.zeros(_FEAT_DIM_OSNET)

        # Pre-process: resize to (W=128, H=256), BGR→RGB, float32 in [0,1]
        roi_resized = cv2.resize(roi, (128, 256))
        roi_rgb = cv2.cvtColor(roi_resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # ImageNet normalisation
        roi_norm = (roi_rgb - _IMAGENET_MEAN) / _IMAGENET_STD

        # HWC → NCHW (batch=1)
        roi_input = roi_norm.transpose(2, 0, 1)[np.newaxis, ...]

        try:
            input_name = session.get_inputs()[0].name
            outputs = session.run(None, {input_name: roi_input})
            feat = outputs[0][0].astype(np.float32)
        except Exception as e:
            logger.warning(f"ReID: OSNet inference failed: {e}. Returning zero vector.")
            return np.zeros(_FEAT_DIM_OSNET)

        # L2 normalise
        norm = np.linalg.norm(feat) + 1e-6
        return feat / norm

    def _get_feature(self, frame, bbox, method, onnx_session):
        """Dispatch feature extraction to the appropriate backend."""
        if method != _METHOD_COLOR_HIST and onnx_session is not None:
            return self._extract_osnet_features(frame, bbox, onnx_session)
        return self._extract_features(frame, bbox)

    # ------------------------------------------------------------------
    # Centroid initialisation and assignment
    # ------------------------------------------------------------------

    def _init_centroids(self, tag_node_name, features, n_slots):
        """Initialise cluster centres from the features of the first N-player frame.

        *features* is a list of arrays (one per detection).  We take the first
        *n_slots* entries so that each slot gets exactly one initial centre.
        When more detections than slots are present we pick the *n_slots* most
        spread-out features (greedy max-distance selection) to avoid seeding
        two centres from the same player.
        """
        n = len(features)
        if n == n_slots:
            chosen = features[:n_slots]
        elif n > n_slots:
            # Greedy furthest-point sampling to maximise inter-centre diversity
            chosen = [features[0]]
            for _ in range(n_slots - 1):
                dists = [
                    min(np.linalg.norm(f - c) for c in chosen)
                    for f in features
                ]
                chosen.append(features[int(np.argmax(dists))])
        else:
            chosen = features  # fewer detections than slots – use what we have

        self._centroids[tag_node_name] = np.array(chosen, dtype=np.float32)
        self._centroids_initialized[tag_node_name] = True
        logger.info(
            f"ReID: centroids initialised for {tag_node_name} "
            f"({len(chosen)} centres from {n} detections)"
        )

    def _assign_to_centroid(self, feature, tag_node_name):
        """Return the 1-indexed slot number of the nearest centroid."""
        centroids = self._centroids.get(tag_node_name)
        if centroids is None:
            return None

        distances = np.linalg.norm(centroids - feature, axis=1)
        min_distance = np.min(distances)

        tied_indices = np.where(np.isclose(distances, min_distance, rtol=1e-3))[0]
        if len(tied_indices) > 1:
            # Deterministic tie-breaking based on the feature sum
            feature_characteristic = int(np.sum(feature) * 1e6)
            nearest_idx = tied_indices[feature_characteristic % len(tied_indices)]
        else:
            nearest_idx = tied_indices[0]

        return int(nearest_idx) + 1  # 1-indexed

    def _update_centroid(self, tag_node_name, slot_idx_0, feature):
        """Update centroid *slot_idx_0* (0-indexed) with an EMA step."""
        c = self._centroids[tag_node_name]
        c[slot_idx_0] = _CENTROID_EMA_ALPHA * c[slot_idx_0] + (1.0 - _CENTROID_EMA_ALPHA) * feature

    # ------------------------------------------------------------------
    # Main update
    # ------------------------------------------------------------------

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'
        status_tag = tag_node_name + ':StatusText'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Identify source nodes
        src_image_node = ''
        src_json_node = ''
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_IMAGE:
                src_image_node = ':'.join(connection_info[0].split(':')[:2])
            elif connection_type == self.TYPE_JSON:
                src_json_node = ':'.join(connection_info[0].split(':')[:2])

        frame = node_image_dict.get(src_image_node, None)
        json_data = node_result_dict.get(src_json_node, {})

        # Per-node state boot
        if tag_node_name not in self._centroids_initialized:
            self._centroids_initialized[tag_node_name] = False

        if frame is not None and use_pref_counter:
            start_time = time.monotonic()

        result = {}
        output_frame = None

        if frame is not None and json_data:
            bboxes = json_data.get('bboxes', [])
            scores = json_data.get('scores', [])

            # Use the method stored by _on_method_change callback (set at UI time)
            method = self._selected_method.get(tag_node_name, _METHOD_OSNET_X0_25)

            # Get (or lazy-load) ONNX session for deep methods
            onnx_session = None
            if method != _METHOD_COLOR_HIST:
                onnx_session = self._get_onnx_session(tag_node_name, method)

            # Use slot names stored by _on_slot_name_change (always up-to-date)
            slot_names = self._slot_names.get(tag_node_name, {1: 'A', 2: 'B'})
            n_slots = self._slot_id.get(tag_node_name, 2)

            # -----------------------------------------------------------
            # Phase 1 – Initialisation
            # Wait for a frame that contains at least n_slots players,
            # then seed the cluster centres from those crops.
            # -----------------------------------------------------------
            if not self._centroids_initialized.get(tag_node_name, False):
                n_det = len(bboxes)
                dpg_set_value(status_tag, f'Waiting: {n_det}/{n_slots} players')

                if n_det >= n_slots:
                    features = [
                        self._get_feature(frame, bbox, method, onnx_session)
                        for bbox in bboxes
                    ]
                    self._init_centroids(tag_node_name, features, n_slots)
                    dpg_set_value(status_tag, 'Initialized ✓')
                    logger.info(f"ReID: initialized for {tag_node_name}")

                # Pass through original detections during this phase
                result = json_data.copy()
                output_frame = copy.deepcopy(frame)

            # -----------------------------------------------------------
            # Phase 2 – Assignment
            # For every detection: extract feature, find nearest centre,
            # assign ReID label, update centre with EMA.
            # -----------------------------------------------------------
            else:
                reid_class_ids = []
                reid_class_names = []

                for bbox in bboxes:
                    feat = self._get_feature(frame, bbox, method, onnx_session)
                    slot_idx = self._assign_to_centroid(feat, tag_node_name)

                    if slot_idx is not None:
                        slot_name = slot_names.get(slot_idx, f"player{slot_idx}")
                        reid_class_ids.append(slot_idx - 1)   # 0-indexed for output
                        reid_class_names.append(slot_name)
                        # Update centroid with EMA so it adapts slowly to appearance changes
                        self._update_centroid(tag_node_name, slot_idx - 1, feat)
                    else:
                        reid_class_ids.append(0)
                        reid_class_names.append(slot_names.get(1, 'A'))

                # class_names dict {0: 'A', 1: 'B'} – matches OD node format
                class_names_dict = {
                    (s - 1): slot_names.get(s, f"player{s}")
                    for s in range(1, n_slots + 1)
                }

                result = {
                    'bboxes': bboxes,
                    'scores': scores,
                    'class_ids': reid_class_ids,
                    'class_names': class_names_dict,
                    'timestamp': json_data.get('timestamp', time.time()),
                }

                output_frame = self._draw_reid_info(
                    copy.deepcopy(frame), bboxes, reid_class_names, scores
                )

        elif frame is not None:
            output_frame = copy.deepcopy(frame)

        if frame is not None and use_pref_counter:
            elapsed_time = int((time.monotonic() - start_time) * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        # Update preview texture
        if output_frame is not None:
            dpg_set_value(
                output_value01_tag,
                self.convert_cv_to_dpg(output_frame, small_window_w, small_window_h),
            )
        else:
            black = np.zeros((small_window_h, small_window_w, 3))
            dpg_set_value(
                output_value01_tag,
                self.convert_cv_to_dpg(black, small_window_w, small_window_h),
            )

        return {"image": output_frame, "json": result, "audio": None}

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------

    def _draw_reid_info(self, image, bboxes, reid_names, scores):
        """Draw bounding boxes and ReID labels on *image*."""
        for bbox, name, score in zip(bboxes, reid_names, scores):
            x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
            color = self._get_color_for_name(name)
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            text = f'{name} ({score:.2f})'
            cv2.putText(
                image, text, (x1, max(y1 - 10, 10)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
            )
        return image

    def _get_color_for_name(self, name):
        """Return a deterministic BGR color for *name*."""
        h = hash(name)
        r = (h & 0xFF0000) >> 16
        g = (h & 0x00FF00) >> 8
        b = (h & 0x0000FF)
        return (b & 0xFF, g & 0xFF, r & 0xFF)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self, node_id):
        """Clean up per-node state."""
        tag_node_name = str(node_id) + ':' + self.node_tag
        for d in (self._centroids, self._centroids_initialized,
                  self._onnx_sessions, self._selected_method):
            d.pop(tag_node_name, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        method = self._selected_method.get(tag_node_name, _METHOD_OSNET_X0_25)

        pos = dpg.get_item_pos(tag_node_name)
        return {
            'ver': self._ver,
            'pos': pos,
            'slot_id': self._slot_id.get(tag_node_name, 2),
            'slot_names': self._slot_names.get(tag_node_name, {1: 'A', 2: 'B'}),
            'method': method,
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag

        slot_number = int(setting_dict.get('slot_id', 2))
        slot_names = setting_dict.get('slot_names', {1: 'A', 2: 'B'})

        if tag_node_name not in self._slot_id:
            self._slot_id[tag_node_name] = 2
            self._slot_names[tag_node_name] = {1: 'A', 2: 'B'}

        self._slot_names[tag_node_name] = {}
        for slot_idx_str, name in slot_names.items():
            slot_idx = int(slot_idx_str) if isinstance(slot_idx_str, str) else slot_idx_str
            self._slot_names[tag_node_name][slot_idx] = name

        for slot_idx in range(2, slot_number + 1):
            self._add_slot(None, None, tag_node_name)
            slot_value_tag = tag_node_name + ':Slot' + str(slot_idx).zfill(2) + 'Value'
            if dpg.does_item_exist(slot_value_tag):
                dpg_set_value(slot_value_tag, self._slot_names[tag_node_name].get(slot_idx, f"player{slot_idx}"))

        method = setting_dict.get('method', _METHOD_OSNET_X0_25)
        self._selected_method[tag_node_name] = method
        method_tag = tag_node_name + ':MethodValue'
        try:
            dpg_set_value(method_tag, method)
        except Exception:
            pass
