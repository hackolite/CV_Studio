#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the IoU DataProcess node (node/StatsNode/node_iou.py).

The IoU node compares two ObjectDetection JSON outputs, handles a different
number of bounding boxes per input via greedy matching, and produces a flat
numeric JSON dict consumable by the Chart (ObjChart) node.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dearpygui.dearpygui as dpg

from node.StatsNode.node_iou import (
    FactoryNode,
    Node,
    compute_iou,
    match_detections,
    bbox_pair_difference,
    score_bbox_difference,
)


@pytest.fixture(scope="module", autouse=True)
def dpg_context():
    """A DearPyGui context is required so dpg.does_item_exist (used by the
    node's dpg_get_value/dpg_set_value helpers) does not crash in update()."""
    dpg.create_context()
    yield
    dpg.destroy_context()


def test_iou_node_import():
    factory = FactoryNode()
    node = Node()
    assert factory.node_tag == "IoU"
    assert factory.node_label == "IoU"
    assert node.node_tag == "IoU"


def test_compute_iou_identical_boxes():
    assert compute_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_compute_iou_no_overlap():
    assert compute_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_compute_iou_partial_overlap():
    # Two 10x10 boxes overlapping in a 5x5 region.
    # intersection = 25, union = 100 + 100 - 25 = 175
    iou = compute_iou([0, 0, 10, 10], [5, 5, 15, 15])
    assert abs(iou - (25.0 / 175.0)) < 1e-9


def test_compute_iou_handles_unordered_coords():
    # x2<x1 / y2<y1 should be normalised, not produce negative areas.
    assert compute_iou([10, 10, 0, 0], [0, 0, 10, 10]) == 1.0


def test_match_detections_different_counts():
    # 3 boxes in A, 2 in B. Only 2 can be matched.
    boxes_a = [[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]]
    boxes_b = [[0, 0, 10, 10], [20, 20, 30, 30]]
    matched, used_a, used_b = match_detections(boxes_a, [], boxes_b, [])
    assert len(matched) == 2
    # matched is a list of (index_a, index_b, iou) tuples
    assert all(abs(iou - 1.0) < 1e-9 for (_i, _j, iou) in matched)
    assert len(used_a) == 2
    assert len(used_b) == 2


def test_match_detections_by_class():
    boxes_a = [[0, 0, 10, 10]]
    boxes_b = [[0, 0, 10, 10]]
    # Same geometry but different class -> no match when match_by_class=True
    matched, _, _ = match_detections(boxes_a, [1], boxes_b, [2], match_by_class=True)
    assert matched == []
    # Same class -> matched
    matched, _, _ = match_detections(boxes_a, [1], boxes_b, [1], match_by_class=True)
    assert len(matched) == 1


def test_bbox_pair_difference():
    # Identical boxes -> zero difference everywhere.
    diff = bbox_pair_difference([0, 0, 10, 10], [0, 0, 10, 10])
    assert diff['iou_diff'] == 0.0
    assert diff['center_distance'] == 0.0
    assert diff['size_diff'] == 0.0

    # Shifted box -> non-zero center distance, same size.
    diff = bbox_pair_difference([0, 0, 10, 10], [2, 0, 12, 10])
    assert diff['center_distance'] == 2.0
    assert diff['size_diff'] == 0.0
    assert diff['iou_diff'] > 0.0


def test_score_identical_sets_is_zero():
    boxes = [[0, 0, 10, 10], [20, 20, 30, 30]]
    metrics = score_bbox_difference(boxes, [0, 1], boxes, [0, 1])
    assert metrics['diff_score'] == 0.0
    assert metrics['matched_pairs'] == 2
    assert metrics['unmatched_a'] == 0
    assert metrics['unmatched_b'] == 0


def test_score_completely_different_sets_is_one():
    boxes_a = [[0, 0, 10, 10]]
    boxes_b = [[100, 100, 110, 110]]
    metrics = score_bbox_difference(boxes_a, [0], boxes_b, [0])
    # No overlap -> nothing matched, both boxes count as full difference.
    assert metrics['matched_pairs'] == 0
    assert metrics['diff_score'] == 1.0


def test_score_different_counts():
    # 3 boxes vs 2 boxes, 2 overlap exactly -> 1 extra box is a difference.
    boxes_a = [[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]]
    boxes_b = [[0, 0, 10, 10], [20, 20, 30, 30]]
    metrics = score_bbox_difference(boxes_a, [], boxes_b, [])
    assert metrics['matched_pairs'] == 2
    assert metrics['count_diff'] == 1
    assert metrics['unmatched_a'] == 1
    assert metrics['unmatched_b'] == 0
    # union = 3, total diff = 0 (matched) + 1 (unmatched) -> 1/3
    assert abs(metrics['diff_score'] - (1.0 / 3.0)) < 1e-9


def test_score_threshold_rejects_low_iou_pairs():
    # Two boxes overlap a little (IoU below 0.5); with a high threshold they
    # should be treated as different rather than matched.
    boxes_a = [[0, 0, 10, 10]]
    boxes_b = [[8, 0, 18, 10]]
    low = score_bbox_difference(boxes_a, [], boxes_b, [], iou_threshold=0.0)
    high = score_bbox_difference(boxes_a, [], boxes_b, [], iou_threshold=0.9)
    assert low['matched_pairs'] == 1
    assert high['matched_pairs'] == 0
    assert high['diff_score'] > low['diff_score']


def _make_node():
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False, 'process_width': 320}
    return node


def test_update_outputs_flat_numeric_dict():
    node = _make_node()

    json_a = {
        'bboxes': [[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]],
        'class_ids': [0, 1, 2],
    }
    json_b = {
        'bboxes': [[0, 0, 10, 10], [21, 21, 31, 31]],
        'class_ids': [0, 1],
    }

    node_result_dict = {'1:ObjectDetection': json_a, '2:ObjectDetection': json_b}
    connection_list = [
        ['1:ObjectDetection:JSON:Output01', '3:IoU:JSON:Input01'],
        ['2:ObjectDetection:JSON:Output01', '3:IoU:JSON:Input02'],
    ]

    result = node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={},
    )

    payload = result['json']
    assert payload is not None
    # Must be a flat numeric dict (Chart node requirement) without 'class_ids'.
    assert 'class_ids' not in payload
    assert all(isinstance(v, (int, float)) for v in payload.values())

    assert payload['num_boxes_a'] == 3
    assert payload['num_boxes_b'] == 2
    assert payload['matched_pairs'] == 2
    assert payload['unmatched_a'] == 1
    assert payload['unmatched_b'] == 0
    # Difference score is the primary metric and is in [0, 1].
    assert 0.0 <= payload['diff_score'] <= 1.0
    assert payload['diff_score'] > 0.0
    assert abs(payload['diff_score_percent'] - payload['diff_score'] * 100.0) < 1e-9


def test_update_waiting_for_two_inputs_returns_none():
    node = _make_node()
    json_a = {'bboxes': [[0, 0, 10, 10]], 'class_ids': [0]}
    node_result_dict = {'1:ObjectDetection': json_a}
    connection_list = [
        ['1:ObjectDetection:JSON:Output01', '3:IoU:JSON:Input01'],
    ]

    result = node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={},
    )
    assert result['json'] is None


def test_update_empty_detections():
    node = _make_node()
    json_a = {'bboxes': [], 'class_ids': []}
    json_b = {'bboxes': [], 'class_ids': []}
    node_result_dict = {'1:ObjectDetection': json_a, '2:ObjectDetection': json_b}
    connection_list = [
        ['1:ObjectDetection:JSON:Output01', '3:IoU:JSON:Input01'],
        ['2:ObjectDetection:JSON:Output01', '3:IoU:JSON:Input02'],
    ]
    result = node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={},
    )
    payload = result['json']
    assert payload['matched_pairs'] == 0
    assert payload['mean_iou'] == 0.0
    # Two empty sets means no difference at all.
    assert payload['diff_score'] == 0.0
    assert payload['diff_score_percent'] == 0.0


if __name__ == '__main__':
    import pytest

    raise SystemExit(pytest.main([__file__, '-v']))
