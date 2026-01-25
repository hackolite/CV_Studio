#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test that exclusion dropdown adapts to model changes and settings loading"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_dropdown_items_generation():
    """Test that dropdown items generation function exists and has correct signature"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that the function exists
    assert 'def get_class_rejection_dropdown_items' in content
    assert 'class_name_dict' in content
    assert 'f"{class_id}: {class_name}"' in content
    
    print("✓ Dropdown items generation function test passed")


def test_set_setting_dict_updates_dropdown():
    """Test that set_setting_dict updates dropdown items based on model"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that set_setting_dict updates dropdown items
    assert 'def set_setting_dict' in content
    
    # Verify that it gets the model's class names
    assert 'self._model_class_name_list[model_name]' in content
    
    # Verify that it calls get_class_rejection_dropdown_items
    lines = content.split('\n')
    in_set_setting_dict = False
    found_update = False
    
    for i, line in enumerate(lines):
        if 'def set_setting_dict' in line:
            in_set_setting_dict = True
        elif in_set_setting_dict and 'def ' in line and 'set_setting_dict' not in line:
            # Reached next function
            break
        elif in_set_setting_dict:
            if 'get_class_rejection_dropdown_items' in line:
                found_update = True
                # Check that dpg.configure_item is called after
                for j in range(i, min(i + 5, len(lines))):
                    if 'dpg.configure_item' in lines[j] and 'items=' in lines[j]:
                        print("✓ set_setting_dict updates dropdown items test passed")
                        return
    
    if not found_update:
        raise AssertionError("set_setting_dict should call get_class_rejection_dropdown_items to update dropdown")


def test_on_model_change_callback_exists():
    """Test that on_model_change callback exists and updates dropdown"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check callback exists
    assert 'def on_model_change' in content
    
    # Check it updates dropdown items
    assert 'dpg.configure_item' in content
    assert 'get_class_rejection_dropdown_items' in content
    
    # Check it's attached to the model combo
    assert 'callback=on_model_change' in content
    
    print("✓ on_model_change callback test passed")


def test_model_class_name_list_completeness():
    """Test that all models in _model_class have corresponding class names"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract models from _model_class
    lines = content.split('\n')
    models_in_model_class = []
    models_in_class_name_list = []
    
    in_model_class = False
    in_class_name_list = False
    
    for line in lines:
        if '_model_class = {' in line:
            in_model_class = True
            continue
        elif in_model_class and '}' in line and ':' not in line:
            in_model_class = False
        elif in_model_class and ':' in line:
            # Extract model name
            model = line.split(':')[0].strip().strip("'\"")
            if model:
                models_in_model_class.append(model)
        
        if '_model_class_name_list = {' in line:
            in_class_name_list = True
            continue
        elif in_class_name_list and '}' in line and ':' not in line:
            in_class_name_list = False
        elif in_class_name_list and ':' in line:
            # Extract model name
            model = line.split(':')[0].strip().strip("'\"")
            if model:
                models_in_class_name_list.append(model)
    
    # Check that all models have class names
    for model in models_in_model_class:
        assert model in models_in_class_name_list, \
            f"Model '{model}' is in _model_class but not in _model_class_name_list"
    
    print("✓ Model class name list completeness test passed")


def test_dropdown_initialized_with_default_model():
    """Test that dropdown is initialized with default model's classes"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that default model is used to initialize dropdown
    assert 'default_model = list(node._model_class.keys())[0]' in content
    assert 'default_class_names = node._model_class_name_list[default_model]' in content
    
    # Check that class_items is generated
    lines = content.split('\n')
    found_default_model = False
    found_class_items = False
    found_add_combo_with_items = False
    
    for i, line in enumerate(lines):
        if 'default_model = list(node._model_class.keys())[0]' in line:
            found_default_model = True
            # Check next few lines
            for j in range(i, min(i + 15, len(lines))):
                if 'class_items = get_class_rejection_dropdown_items' in lines[j]:
                    found_class_items = True
                # Check for dpg.add_combo and items parameter (may be on different lines)
                if 'dpg.add_combo' in lines[j]:
                    # Check this line and next few lines for items parameter
                    for k in range(j, min(j + 10, len(lines))):
                        if 'items=class_items' in lines[k]:
                            found_add_combo_with_items = True
                            break
    
    assert found_default_model, "Should get default model"
    assert found_class_items, "Should generate class items for default model"
    assert found_add_combo_with_items, "Should pass class_items to combo"
    
    print("✓ Dropdown initialization with default model test passed")


if __name__ == '__main__':
    print("Running exclusion dropdown model adaptation tests...\n")
    
    try:
        test_dropdown_items_generation()
    except AssertionError as e:
        print(f"✗ test_dropdown_items_generation failed: {e}")
        sys.exit(1)
    
    try:
        test_set_setting_dict_updates_dropdown()
    except AssertionError as e:
        print(f"✗ test_set_setting_dict_updates_dropdown failed: {e}")
        sys.exit(1)
    
    try:
        test_on_model_change_callback_exists()
    except AssertionError as e:
        print(f"✗ test_on_model_change_callback_exists failed: {e}")
        sys.exit(1)
    
    try:
        test_model_class_name_list_completeness()
    except AssertionError as e:
        print(f"✗ test_model_class_name_list_completeness failed: {e}")
        sys.exit(1)
    
    try:
        test_dropdown_initialized_with_default_model()
    except AssertionError as e:
        print(f"✗ test_dropdown_initialized_with_default_model failed: {e}")
        sys.exit(1)
    
    print("\n✅ All exclusion dropdown model adaptation tests passed!")
