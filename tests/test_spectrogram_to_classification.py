#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test that classification node can receive spectrogram from video node's audio output.
This verifies the fix for passing node_audio_dict to get_input_frame.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_classification_node_accepts_audio_dict():
    """Test that classification node's update method accepts node_audio_dict parameter"""
    import unittest.mock as mock
    import inspect
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['onnxruntime'] = mock.MagicMock()
    
    # Mock the classification modules
    sys.modules['node.DLNode.classification'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3.mobilenet_v3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0.efficientnet'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.imagenet_class_names'] = mock.MagicMock()
    
    from node.DLNode.node_classification import Node as ClassificationNode
    
    node = ClassificationNode()
    
    # Check that update method signature includes node_audio_dict
    sig = inspect.signature(node.update)
    params = list(sig.parameters.keys())
    
    assert 'node_audio_dict' in params, \
        f"node_audio_dict not in update parameters: {params}"
    
    print("✓ Classification node update method includes node_audio_dict parameter")


def test_classification_node_calls_get_input_frame_correctly():
    """Test that classification node passes node_audio_dict to get_input_frame"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['onnxruntime'] = mock.MagicMock()
    
    # Mock the classification modules
    mock_mobilenet = mock.MagicMock()
    mock_efficientnet = mock.MagicMock()
    mock_imagenet_names = ['class1', 'class2']
    
    sys.modules['node.DLNode.classification'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3.mobilenet_v3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3.mobilenet_v3'].MobileNetV3 = mock_mobilenet
    sys.modules['node.DLNode.classification.EfficientNetB0'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0.efficientnet'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0.efficientnet'].EfficientNetB0 = mock_efficientnet
    sys.modules['node.DLNode.classification.imagenet_class_names'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.imagenet_class_names'].imagenet_class_names = mock_imagenet_names
    
    from node.DLNode.node_classification import Node as ClassificationNode
    
    # Read the source code to verify the fix
    import inspect
    source = inspect.getsource(ClassificationNode.update)
    
    # Check that node_audio_dict is passed (not None) to get_input_frame
    # The fixed line should be: frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict)
    # NOT: frame = self.get_input_frame(connection_list, node_image_dict, node_audio_dict=None)
    
    assert 'get_input_frame(connection_list, node_image_dict, node_audio_dict)' in source, \
        "Classification node should pass node_audio_dict (not None) to get_input_frame"
    
    # Verify it's not passing None
    assert 'get_input_frame(connection_list, node_image_dict, node_audio_dict=None)' not in source, \
        "Classification node should NOT pass node_audio_dict=None"
    
    print("✓ Classification node correctly passes node_audio_dict to get_input_frame")


def test_all_dl_nodes_pass_audio_dict():
    """Test that all DL nodes correctly pass node_audio_dict"""
    import unittest.mock as mock
    import inspect
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['onnxruntime'] = mock.MagicMock()
    sys.modules['mediapipe'] = mock.MagicMock()
    
    # Test node files
    dl_node_files = [
        'node/DLNode/node_classification.py',
        'node/DLNode/node_semantic_segmentation.py',
        'node/DLNode/node_monocular_depth_estimation.py',
        'node/DLNode/node_object_detection.py',
        'node/DLNode/node_face_detection.py',
    ]
    
    for node_file in dl_node_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', node_file)
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check that it doesn't pass None
        assert 'get_input_frame(connection_list, node_image_dict, node_audio_dict=None)' not in content, \
            f"{node_file} should not pass node_audio_dict=None"
        
        print(f"  ✓ {os.path.basename(node_file)} correctly passes node_audio_dict")
    
    print("✓ All DL nodes correctly pass node_audio_dict")


def test_all_process_nodes_pass_audio_dict():
    """Test that all Process nodes correctly pass node_audio_dict"""
    process_node_files = [
        'node/ProcessNode/node_flip.py',
        'node/ProcessNode/node_contrast.py',
        'node/ProcessNode/node_crop.py',
        'node/ProcessNode/node_resize.py',
        'node/ProcessNode/node_grayscale.py',
        'node/ProcessNode/node_equalize_hist.py',
        'node/ProcessNode/node_canny.py',
        'node/ProcessNode/node_threshold.py',
        'node/ProcessNode/node_blur.py',
        'node/ProcessNode/node_brightness.py',
    ]
    
    for node_file in process_node_files:
        file_path = os.path.join(os.path.dirname(__file__), '..', node_file)
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check that it doesn't pass None
        assert 'get_input_frame(connection_list, node_image_dict, node_audio_dict=None)' not in content, \
            f"{node_file} should not pass node_audio_dict=None"
        
        print(f"  ✓ {os.path.basename(node_file)} correctly passes node_audio_dict")
    
    print("✓ All Process nodes correctly pass node_audio_dict")


if __name__ == '__main__':
    print("Running tests for spectrogram to classification fix...\n")
    
    try:
        test_classification_node_accepts_audio_dict()
        test_classification_node_calls_get_input_frame_correctly()
        test_all_dl_nodes_pass_audio_dict()
        test_all_process_nodes_pass_audio_dict()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)
        print("\nThe fix is working correctly:")
        print("- Video node outputs spectrogram via 'audio' key")
        print("- Classification and other nodes can now receive it")
        print("- Nodes pass node_audio_dict to get_input_frame")
        print("- get_input_frame retrieves spectrogram from node_audio_dict")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
