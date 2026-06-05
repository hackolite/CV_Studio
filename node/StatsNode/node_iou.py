#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node
from node.DLNode.online_training.distillation_loss import compute_set_distillation_loss


# Fixed-width placeholder so the node keeps a constant size before any data
# arrives (must be the same length as the formatted status produced by
# ``_format_status`` below).
_STATUS_PLACEHOLDER = 'diff  --- | loss   ---- | m --- u ---'


def _format_status(diff_score, loss, matched, unmatched):
    """Build a constant-width status line for the IoU node.

    The node auto-sizes to its widest widget, so every numeric field is clamped
    to a bounded range and rendered with a fixed-width format specifier. This
    guarantees the string length never changes, keeping the node a fixed size
    regardless of how variable the underlying detection counts/loss are.
    """
    ds = min(max(float(diff_score), 0.0), 1.0)        # always "0.00".."1.00"
    ls = min(max(float(loss), 0.0), 999.99)            # clamp large losses (6 wide)
    mp = min(max(int(matched), 0), 999)
    un = min(max(int(unmatched), 0), 999)
    return 'diff {:4.2f} | loss {:6.2f} | m {:3d} u {:3d}'.format(ds, ls, mp, un)


def _normalise_bbox(bbox):
    """Return a bbox as (x1, y1, x2, y2) with x1<=x2 and y1<=y2."""
    if bbox is None or len(bbox) < 4:
        return None
    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def compute_iou(box_a, box_b):
    """Compute the Intersection over Union of two [x1, y1, x2, y2] boxes."""
    a = _normalise_bbox(box_a)
    b = _normalise_bbox(box_b)
    if a is None or b is None:
        return 0.0

    inter_x1 = max(a[0], b[0])
    inter_y1 = max(a[1], b[1])
    inter_x2 = min(a[2], b[2])
    inter_y2 = min(a[3], b[3])

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter_area
    if union <= 0.0:
        return 0.0
    return inter_area / union


def match_detections(boxes_a, classes_a, boxes_b, classes_b, match_by_class=False):
    """Greedily match boxes from set A to set B by descending IoU.

    Handles a different number of boxes in each set: every box can be matched
    at most once, leftover boxes stay unmatched. Returns the matched pairs as a
    list of (index_a, index_b, iou) tuples along with the matched index sets.
    """
    candidates = []
    for i, box_a in enumerate(boxes_a):
        for j, box_b in enumerate(boxes_b):
            if match_by_class and classes_a and classes_b:
                if i < len(classes_a) and j < len(classes_b):
                    if classes_a[i] != classes_b[j]:
                        continue
            iou = compute_iou(box_a, box_b)
            if iou > 0.0:
                candidates.append((iou, i, j))

    candidates.sort(key=lambda item: item[0], reverse=True)

    used_a = set()
    used_b = set()
    matched_pairs = []
    for iou, i, j in candidates:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        matched_pairs.append((i, j, iou))

    return matched_pairs, used_a, used_b


def _bbox_geometry(box):
    """Return (cx, cy, w, h) for a [x1, y1, x2, y2] box, or None."""
    b = _normalise_bbox(box)
    if b is None:
        return None
    w = b[2] - b[0]
    h = b[3] - b[1]
    cx = b[0] + w / 2.0
    cy = b[1] + h / 2.0
    return (cx, cy, w, h)


def bbox_pair_difference(box_a, box_b):
    """Per-pair geometric difference between two boxes.

    Returns a dict with:
      - iou_diff: 1 - IoU (0 = identical overlap, 1 = no overlap)
      - center_distance: Euclidean distance between box centers (pixels)
      - size_diff: |w_a - w_b| + |h_a - h_b| (pixels)
    """
    iou = compute_iou(box_a, box_b)
    ga = _bbox_geometry(box_a)
    gb = _bbox_geometry(box_b)
    if ga is None or gb is None:
        return {'iou_diff': 1.0, 'center_distance': 0.0, 'size_diff': 0.0}

    center_distance = ((ga[0] - gb[0]) ** 2 + (ga[1] - gb[1]) ** 2) ** 0.5
    size_diff = abs(ga[2] - gb[2]) + abs(ga[3] - gb[3])
    return {
        'iou_diff': 1.0 - iou,
        'center_distance': center_distance,
        'size_diff': size_diff,
    }


def score_bbox_difference(boxes_a, classes_a, boxes_b, classes_b,
                          match_by_class=False, iou_threshold=0.0):
    """Score the difference between two sets of bounding boxes.

    A normalised difference score in [0, 1] is produced where 0 means the two
    detection outputs are identical and 1 means they are completely different.

    Matched pairs (greedy by IoU) whose IoU is at least ``iou_threshold`` are
    considered to be the same detection and contribute their per-pair IoU
    difference (1 - IoU). Pairs below the threshold are rejected: their two
    boxes are then counted as unmatched. Every unmatched box (present in one
    set but missing from the other) is treated as a maximal difference of 1.0.
    The total is normalised by the union count (num_a + num_b - accepted
    matches), so the score behaves even when the two sets have a different
    number of boxes.
    """
    raw_pairs, _used_a, _used_b = match_detections(
        boxes_a, classes_a, boxes_b, classes_b, match_by_class
    )

    # Apply the IoU acceptance threshold: only pairs at/above the threshold
    # are treated as the same detection.
    matched_pairs = [(i, j, iou) for (i, j, iou) in raw_pairs if iou >= iou_threshold]
    used_a = {i for (i, _j, _iou) in matched_pairs}
    used_b = {j for (_i, j, _iou) in matched_pairs}

    num_a = len(boxes_a)
    num_b = len(boxes_b)
    matched = len(matched_pairs)
    unmatched_a = num_a - len(used_a)
    unmatched_b = num_b - len(used_b)

    iou_diffs = []
    center_distances = []
    size_diffs = []
    for i, j, _iou in matched_pairs:
        diff = bbox_pair_difference(boxes_a[i], boxes_b[j])
        iou_diffs.append(diff['iou_diff'])
        center_distances.append(diff['center_distance'])
        size_diffs.append(diff['size_diff'])

    # Union count: accepted matched pairs counted once + all unmatched boxes.
    union_count = num_a + num_b - matched

    if union_count == 0:
        # Both sets empty -> no difference.
        diff_score = 0.0
    else:
        total_diff = sum(iou_diffs) + float(unmatched_a + unmatched_b)
        diff_score = total_diff / union_count

    mean_matched_diff = (sum(iou_diffs) / matched) if matched > 0 else 0.0
    mean_center_distance = (sum(center_distances) / matched) if matched > 0 else 0.0
    mean_size_diff = (sum(size_diffs) / matched) if matched > 0 else 0.0
    mean_iou = (
        sum(1.0 - d for d in iou_diffs) / matched if matched > 0 else 0.0
    )

    return {
        'diff_score': float(diff_score),
        'mean_matched_diff': float(mean_matched_diff),
        'mean_center_distance': float(mean_center_distance),
        'mean_size_diff': float(mean_size_diff),
        'mean_iou': float(mean_iou),
        'count_diff': int(abs(num_a - num_b)),
        'matched_pairs': int(matched),
        'num_boxes_a': int(num_a),
        'num_boxes_b': int(num_b),
        'unmatched_a': int(unmatched_a),
        'unmatched_b': int(unmatched_b),
    }




class FactoryNode:
    node_label = 'IoU'
    node_tag = 'IoU'

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
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'
        node.tag_node_threshold_name = node.tag_node_name + ':Threshold'
        node.tag_node_threshold_value_name = node.tag_node_name + ':ThresholdValue'
        node.tag_node_match_class_name = node.tag_node_name + ':MatchByClass'
        node.tag_node_match_class_value_name = node.tag_node_name + ':MatchByClassValue'
        node.tag_node_status_name = node.tag_node_name + ':Status'
        node.tag_node_status_value_name = node.tag_node_name + ':StatusValue'
        node.tag_node_output_json_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output_json_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

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
                    default_value='Detection A (JSON)',
                )

            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='Detection B (JSON)',
                )

            with dpg.node_attribute(
                tag=node.tag_node_threshold_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_slider_float(
                    tag=node.tag_node_threshold_value_name,
                    label="IoU match th",
                    width=small_window_w - 80,
                    default_value=0.5,
                    min_value=0.0,
                    max_value=1.0,
                )

            with dpg.node_attribute(
                tag=node.tag_node_match_class_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_checkbox(
                    tag=node.tag_node_match_class_value_name,
                    label="Match by class",
                    default_value=False,
                )

            with dpg.node_attribute(
                tag=node.tag_node_status_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(
                    tag=node.tag_node_status_value_name,
                    default_value=_STATUS_PLACEHOLDER,
                )

            with dpg.node_attribute(
                tag=node.tag_node_output_json_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output_json_value_name,
                    default_value='BBox diff metrics (JSON)',
                )

            if use_pref_counter:
                with dpg.node_attribute(
                    tag=node.tag_node_output02_name,
                    attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='Elapsed time(ms)',
                    )

        return node


class Node(Node):
    _ver = '0.0.1'

    node_label = 'IoU'
    node_tag = 'IoU'

    _opencv_setting_dict = None

    def __init__(self):
        pass

    def _get_source_for_input(self, connection_list, node_result_dict, input_suffix):
        """Return the JSON dict connected to the given input slot (e.g. 'Input01')."""
        for connection_info in connection_list:
            destination = connection_info[1]
            source = connection_info[0]
            connection_type = source.split(':')[2]
            if connection_type.upper() != self.TYPE_JSON.upper():
                continue
            if not destination.endswith(input_suffix):
                continue
            source_key = ':'.join(source.split(':')[:2])
            return node_result_dict.get(source_key, None)
        return None

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        threshold_tag = tag_node_name + ':ThresholdValue'
        match_class_tag = tag_node_name + ':MatchByClassValue'
        status_tag = tag_node_name + ':StatusValue'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        if use_pref_counter:
            start_time = time.monotonic()

        threshold = dpg_get_value(threshold_tag)
        if threshold is None:
            threshold = 0.5
        match_by_class = dpg_get_value(match_class_tag)
        if match_by_class is None:
            match_by_class = False

        json_a = self._get_source_for_input(connection_list, node_result_dict, 'Input01')
        json_b = self._get_source_for_input(connection_list, node_result_dict, 'Input02')

        result = None
        if isinstance(json_a, dict) and isinstance(json_b, dict):
            boxes_a = json_a.get('bboxes', []) or []
            boxes_b = json_b.get('bboxes', []) or []
            classes_a = json_a.get('class_ids', []) or []
            classes_b = json_b.get('class_ids', []) or []

            metrics = score_bbox_difference(
                boxes_a, classes_a, boxes_b, classes_b,
                match_by_class=match_by_class,
                iou_threshold=threshold,
            )

            # Hungarian-matched set-based distillation loss (DETR-style).
            # Detection A is the teacher/reference, Detection B the student.
            set_loss = compute_set_distillation_loss(
                boxes_a, boxes_b,
                teacher_class_ids=classes_a,
                student_class_ids=classes_b,
            )

            diff_score = metrics['diff_score']

            # Flat numeric dict so the Chart (ObjChart) node can plot each metric
            # over time. Do NOT include 'class_ids' or non-numeric values here,
            # otherwise the Chart treats the payload as a raw detection result.
            result = {
                'diff_score': float(diff_score),
                'diff_score_percent': float(diff_score * 100.0),
                'mean_matched_diff': float(metrics['mean_matched_diff']),
                'mean_center_distance': float(metrics['mean_center_distance']),
                'mean_size_diff': float(metrics['mean_size_diff']),
                'mean_iou': float(metrics['mean_iou']),
                'count_diff': int(metrics['count_diff']),
                'matched_pairs': int(metrics['matched_pairs']),
                'num_boxes_a': int(metrics['num_boxes_a']),
                'num_boxes_b': int(metrics['num_boxes_b']),
                'unmatched_a': int(metrics['unmatched_a']),
                'unmatched_b': int(metrics['unmatched_b']),
                # Set-based distillation loss + chart metrics (lower = closer).
                'loss': float(set_loss['loss']),
                'loss_total': float(set_loss['loss_total']),
                'loss_box': float(set_loss['loss_box']),
                'loss_class': float(set_loss['loss_class']),
                'loss_iou': float(set_loss['loss_iou']),
                'loss_cardinality': float(set_loss['loss_cardinality']),
                'loss_fp': float(set_loss['loss_fp']),
                'loss_fn': float(set_loss['loss_fn']),
                'loss_cls_mismatch': float(set_loss['loss_cls_mismatch']),
                'cardinality_error': int(set_loss['cardinality_error']),
                'fp_count': int(set_loss['fp_count']),
                'fn_count': int(set_loss['fn_count']),
                'iou_mean_matched': float(set_loss['iou_mean_matched']),
                'class_mismatch_rate': float(set_loss['class_mismatch_rate']),
                'detection_score': float(set_loss['detection_score']),
            }

            dpg_set_value(
                status_tag,
                _format_status(
                    diff_score,
                    set_loss['loss'],
                    metrics['matched_pairs'],
                    metrics['unmatched_a'] + metrics['unmatched_b'],
                ),
            )
        else:
            dpg_set_value(status_tag, _STATUS_PLACEHOLDER)

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')

        return {"image": None, "json": result, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        threshold_tag = tag_node_name + ':ThresholdValue'
        match_class_tag = tag_node_name + ':MatchByClassValue'
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        setting_dict[threshold_tag] = dpg_get_value(threshold_tag)
        setting_dict[match_class_tag] = dpg_get_value(match_class_tag)

        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        threshold_tag = tag_node_name + ':ThresholdValue'
        match_class_tag = tag_node_name + ':MatchByClassValue'

        if threshold_tag in setting_dict and setting_dict[threshold_tag] is not None:
            dpg_set_value(threshold_tag, setting_dict[threshold_tag])
        if match_class_tag in setting_dict and setting_dict[match_class_tag] is not None:
            dpg_set_value(match_class_tag, setting_dict[match_class_tag])
