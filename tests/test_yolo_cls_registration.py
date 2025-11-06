#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test that Yolo-cls model is properly registered in the classification node.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def setup_mocks():
    """Setup common mocks for all tests"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['onnxruntime'] = mock.MagicMock()


def test_yolo_cls_is_registered():
    """Test that Yolo-cls is available in the classification node model dictionaries"""
    setup_mocks()
    
    # Import the classification node module
    from node.DLNode import node_classification
    
    # Get the Node class
    Node = node_classification.Node
    
    # Check that Yolo-cls is registered in all three dictionaries
    assert 'Yolo-cls' in Node._model_class, \
        "Yolo-cls should be in _model_class dictionary"
    
    assert 'Yolo-cls' in Node._model_path_setting, \
        "Yolo-cls should be in _model_path_setting dictionary"
    
    assert 'Yolo-cls' in Node._model_class_name_dict, \
        "Yolo-cls should be in _model_class_name_dict dictionary"
    
    print("✓ Yolo-cls is registered in all model dictionaries")


def test_yolo_cls_model_path_exists():
    """Test that the Yolo-cls model file exists at the configured path"""
    setup_mocks()
    
    # Import the classification node module
    from node.DLNode import node_classification
    
    # Get the Node class
    Node = node_classification.Node
    
    # Get the model path for Yolo-cls
    model_path = Node._model_path_setting['Yolo-cls']
    
    # Check that the file exists
    assert os.path.exists(model_path), \
        f"Yolo-cls model file should exist at {model_path}"
    
    # Check that it's the correct file
    assert model_path.endswith('Yolo-cls/model/son.onnx'), \
        f"Yolo-cls model path should end with 'Yolo-cls/model/son.onnx', got {model_path}"
    
    print(f"✓ Yolo-cls model file exists at {model_path}")


def test_yolo_cls_class_is_imported():
    """Test that the YoloCls class is properly imported"""
    setup_mocks()
    
    # Import the classification node module
    from node.DLNode import node_classification
    
    # Get the Node class
    Node = node_classification.Node
    
    # Get the YoloCls class
    YoloClsClass = Node._model_class['Yolo-cls']
    
    # Check that it's a class (not None, not a mock, etc.)
    assert YoloClsClass is not None, "YoloCls class should not be None"
    assert type(YoloClsClass).__name__ == 'type', "YoloCls should be a class"
    
    print(f"✓ YoloCls class is properly imported: {YoloClsClass}")


def test_yolo_cls_uses_imagenet_classes():
    """Test that Yolo-cls uses ImageNet class names"""
    setup_mocks()
    
    # Import the classification node module
    from node.DLNode import node_classification
    
    # Get the Node class
    Node = node_classification.Node
    
    # Check that Yolo-cls uses imagenet_class_names
    # (same as other models like ResNet50, MobileNetV3, etc.)
    assert 'Yolo-cls' in Node._model_class_name_dict, \
        "Yolo-cls should have class names defined"
    
    # Compare with ResNet50 to ensure consistency
    yolo_cls_names = Node._model_class_name_dict['Yolo-cls']
    resnet50_names = Node._model_class_name_dict['ResNet50']
    
    assert yolo_cls_names == resnet50_names, \
        "Yolo-cls should use the same class names as ResNet50 (ImageNet classes)"
    
    print("✓ Yolo-cls uses ImageNet class names")


def test_model_list_includes_yolo_cls():
    """Test that Yolo-cls appears in the model list that will be shown in the UI"""
    setup_mocks()
    
    # Import the classification node module
    from node.DLNode import node_classification
    
    # Get the Node class
    Node = node_classification.Node
    
    # Get the list of models
    model_list = list(Node._model_class.keys())
    
    # Check that Yolo-cls is in the list
    assert 'Yolo-cls' in model_list, \
        f"Yolo-cls should be in the model list, got: {model_list}"
    
    # Verify the complete list includes all expected models
    expected_models = ['MobileNetV3 Small', 'MobileNetV3 Large', 
                      'EfficientNet B0', 'ResNet50', 'Yolo-cls']
    
    for model in expected_models:
        assert model in model_list, f"{model} should be in the model list"
    
    print(f"✓ Model list includes Yolo-cls: {model_list}")


if __name__ == '__main__':
    print("Running tests for Yolo-cls registration in classification node...\n")
    
    try:
        test_yolo_cls_is_registered()
        test_yolo_cls_model_path_exists()
        test_yolo_cls_class_is_imported()
        test_yolo_cls_uses_imagenet_classes()
        test_model_list_includes_yolo_cls()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)
        print("\nYolo-cls is now available in the classification node:")
        print("- Yolo-cls is registered in all model dictionaries")
        print("- Model file exists at the correct path")
        print("- YoloCls class is properly imported")
        print("- Uses ImageNet class names")
        print("- Appears in the UI model dropdown list")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
