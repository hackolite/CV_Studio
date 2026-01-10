#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for linking model selection to class rejection dropdown"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.DLNode.object_detection.coco_class_names import coco_class_names
from node.DLNode.object_detection.coco_class_names_only_person import coco_class_names_only_person
from node.DLNode.object_detection.coco_class_names_tennis import coco_class_names_tennis


def test_class_name_lists_exist():
    """Test that all class name dictionaries are properly defined"""
    
    # COCO classes should have 80 classes
    assert len(coco_class_names) == 80, "COCO should have 80 classes"
    
    # Person-only model should have 1 class
    assert len(coco_class_names_only_person) == 1, "Person-only model should have 1 class"
    assert 0 in coco_class_names_only_person, "Should have person class with ID 0"
    assert coco_class_names_only_person[0] == 'person', "Class 0 should be 'person'"
    
    # Tennis model should have 3 classes
    assert len(coco_class_names_tennis) == 3, "Tennis model should have 3 classes"
    assert 0 in coco_class_names_tennis, "Should have player1 class"
    assert 1 in coco_class_names_tennis, "Should have player2 class"
    assert 2 in coco_class_names_tennis, "Should have ball class"


def test_get_class_rejection_dropdown_items():
    """Test the function that generates dropdown items from class names"""
    from node.DLNode.node_object_detection import get_class_rejection_dropdown_items
    
    # Test with COCO classes
    coco_items = get_class_rejection_dropdown_items(coco_class_names)
    assert len(coco_items) == 80, "Should have 80 items for COCO"
    assert coco_items[0] == "0: person", "First item should be formatted as 'ID: name'"
    assert coco_items[1] == "1: bicycle", "Second item should be '1: bicycle'"
    
    # Test with person-only classes
    person_items = get_class_rejection_dropdown_items(coco_class_names_only_person)
    assert len(person_items) == 1, "Should have 1 item for person-only model"
    assert person_items[0] == "0: person", "Should be formatted as '0: person'"
    
    # Test with tennis classes
    tennis_items = get_class_rejection_dropdown_items(coco_class_names_tennis)
    assert len(tennis_items) == 3, "Should have 3 items for tennis model"
    assert tennis_items[0] == "0: player1", "First item should be '0: player1'"
    assert tennis_items[1] == "1: player2", "Second item should be '1: player2'"
    assert tennis_items[2] == "2: ball", "Third item should be '2: ball'"


def test_model_class_name_mapping():
    """Test that each model has a corresponding class name dictionary"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that _model_class_name_list dictionary exists and includes all models
    assert '_model_class_name_list' in content, "Should have _model_class_name_list dictionary"
    
    # Check that key models are mapped to their class lists
    assert "'YOLOX-Nano(416x416)': coco_class_names" in content, "YOLOX should map to coco_class_names"
    assert "'Light-Weight Person Detector': coco_class_names_only_person" in content, \
        "Light-Weight Person Detector should map to coco_class_names_only_person"
    assert "'YOLOTENNIS': coco_class_names_tennis" in content, "YOLOTENNIS should map to coco_class_names_tennis"


def test_callback_function_exists():
    """Test that the callback function for model change exists"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that callback function is defined
    assert 'def on_model_change' in content, "Should have on_model_change callback function"
    
    # Check that callback updates the dropdown
    assert 'dpg.configure_item' in content, "Should use dpg.configure_item to update dropdown"
    assert 'get_class_rejection_dropdown_items' in content, "Should call get_class_rejection_dropdown_items"
    
    # Check that callback is attached to the model selection combo
    assert 'callback=on_model_change' in content, "Should attach callback to model selection combo"


def test_rejected_classes_cleared_on_model_change():
    """Test that rejected classes are cleared when model changes"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that the callback clears the rejected classes value
    # This prevents invalid class IDs when switching models
    assert 'dpg_set_value(node.tag_node_rejected_classes_value_name, "")' in content, \
        "Should clear rejected classes when model changes"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
