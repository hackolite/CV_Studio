#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for linking model selection to class rejection dropdown"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.DLNode.object_detection.coco_class_names import coco_class_names


def test_coco_class_names():
    """Test that COCO class name dictionary is properly defined."""
    assert len(coco_class_names) == 80, "COCO should have 80 classes"
    assert 0 in coco_class_names
    assert coco_class_names[0] == 'person'


def test_get_class_rejection_dropdown_items():
    """Test the function that generates dropdown items from class names"""
    import unittest.mock as mock
    for mod in ('dearpygui', 'dearpygui.dearpygui', 'node_editor', 'node_editor.util',
                'src', 'src.utils', 'src.utils.logging', 'src.utils.gpu_utils',
                'node.DLNode.object_detection.CustomONNX',
                'node.DLNode.object_detection.CustomONNX.custom_onnx',
                'node.DLNode.object_detection.custom_models_registry',
                'node.DLNode.object_detection.onnx_inspector'):
        sys.modules.setdefault(mod, mock.MagicMock())

    from node.DLNode.node_object_detection import get_class_rejection_dropdown_items

    # Test with COCO classes
    coco_items = get_class_rejection_dropdown_items(coco_class_names)
    assert len(coco_items) == 80, "Should have 80 items for COCO"
    assert coco_items[0] == "0: person", "First item should be formatted as 'ID: name'"
    assert coco_items[1] == "1: bicycle", "Second item should be '1: bicycle'"

    # Test with a small custom dict
    custom = {0: 'player1', 1: 'player2', 2: 'ball'}
    items = get_class_rejection_dropdown_items(custom)
    assert len(items) == 3
    assert items[0] == "0: player1"
    assert items[1] == "1: player2"
    assert items[2] == "2: ball"

    # Test with person-only
    person_only = {0: 'person'}
    person_items = get_class_rejection_dropdown_items(person_only)
    assert len(person_items) == 1
    assert person_items[0] == "0: person"


def test_get_batch_badge_label():
    """Only true batch-capable models should show the B marker."""
    import unittest.mock as mock
    for mod in ('dearpygui', 'dearpygui.dearpygui', 'node_editor', 'node_editor.util',
                'src', 'src.utils', 'src.utils.logging', 'src.utils.gpu_utils',
                'node.DLNode.object_detection.CustomONNX',
                'node.DLNode.object_detection.CustomONNX.custom_onnx',
                'node.DLNode.object_detection.custom_models_registry',
                'node.DLNode.object_detection.onnx_inspector'):
        sys.modules.setdefault(mod, mock.MagicMock())

    from node.DLNode.node_object_detection import get_batch_badge_label

    assert get_batch_badge_label(True) == "B"
    assert get_batch_badge_label(False) == ""


def _mock_dpg_modules():
    """Helper: install mocks for dpg and related modules."""
    import unittest.mock as mock
    for mod in ('dearpygui', 'dearpygui.dearpygui', 'node_editor', 'node_editor.util',
                'src', 'src.utils', 'src.utils.logging', 'src.utils.gpu_utils',
                'node.DLNode.object_detection.CustomONNX',
                'node.DLNode.object_detection.CustomONNX.custom_onnx',
                'node.DLNode.object_detection.custom_models_registry',
                'node.DLNode.object_detection.onnx_inspector'):
        sys.modules.setdefault(mod, mock.MagicMock())


def test_builtin_models_defined():
    """Test that _BUILTIN_MODELS contains expected entries."""
    _mock_dpg_modules()
    from node.DLNode.node_object_detection import _BUILTIN_MODELS

    names = {m['name'] for m in _BUILTIN_MODELS}
    assert 'YOLOX-Nano(416x416)' in names
    assert 'YOLO11Nano' in names
    assert 'YOLOTENNIS' in names
    assert 'Light-Weight Person Detector' in names

    # Each entry must have required keys
    for m in _BUILTIN_MODELS:
        for key in ('name', 'path', 'output_format', 'input_width', 'input_height',
                    'num_classes', 'class_names'):
            assert key in m, f"Missing key '{key}' in built-in model '{m.get('name')}'"

    # Tennis model should have 3 classes
    tennis = next((m for m in _BUILTIN_MODELS if m['name'] == 'YOLOTENNIS'), None)
    assert tennis is not None, "YOLOTENNIS should be in _BUILTIN_MODELS"
    assert tennis['num_classes'] == 3
    assert tennis['class_names'].get(0) == 'player1'
    assert tennis['class_names'].get(1) == 'player2'
    assert tennis['class_names'].get(2) == 'ball'


def test_callback_function_exists():
    """Test that on_model_change callback and related helpers are present."""
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    with open(file_path, 'r') as f:
        content = f.read()

    assert 'def on_model_change' in content, "Should have on_model_change callback"
    assert 'dpg.configure_item' in content, "Should use dpg.configure_item"
    assert 'get_class_rejection_dropdown_items' in content
    assert 'callback=on_model_change' in content


def test_rejected_classes_cleared_on_model_change():
    """Test that rejected classes are cleared when model changes."""
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    with open(file_path, 'r') as f:
        content = f.read()

    assert 'dpg_set_value(node.tag_node_rejected_classes_value_name, "")' in content, \
        "Should clear rejected classes when model changes"


def test_batch_badge_wiring_present():
    """The node UI should expose and refresh a batch badge next to the model combo."""
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    with open(file_path, 'r') as f:
        content = f.read()

    assert 'tag_node_batch_badge_value_name' in content
    assert 'get_batch_badge_label' in content
    assert 'node._update_batch_badge(selected_model)' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
