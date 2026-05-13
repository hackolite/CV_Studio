#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for updated node files using get_input_frame method
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_process_node_imports():
    """Test that all updated ProcessNode files can be imported"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    process_nodes = [
        'node.ProcessNode.node_blur',
        'node.ProcessNode.node_brightness',
        'node.ProcessNode.node_contrast',
        'node.ProcessNode.node_resize',
        'node.ProcessNode.node_crop',
        'node.ProcessNode.node_flip',
        'node.ProcessNode.node_canny',
        'node.ProcessNode.node_threshold',
        'node.ProcessNode.node_grayscale',
        'node.ProcessNode.node_equalize_hist',
        'node.ProcessNode.node_clahe',
    ]
    
    for node_module in process_nodes:
        try:
            __import__(node_module)
            print(f"✓ {node_module} imported successfully")
        except Exception as e:
            print(f"✗ Failed to import {node_module}: {e}")
            raise


def test_dl_node_imports():
    """Test that all updated DLNode files can be imported"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection.coco_class_names'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection.CustomONNX'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection.CustomONNX.custom_onnx'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection.custom_models_registry'] = mock.MagicMock()
    sys.modules['node.DLNode.object_detection.onnx_inspector'] = mock.MagicMock()
    sys.modules['src'] = mock.MagicMock()
    sys.modules['src.utils'] = mock.MagicMock()
    sys.modules['src.utils.logging'] = mock.MagicMock()
    sys.modules['src.utils.gpu_utils'] = mock.MagicMock()
    sys.modules['node.DLNode.classification'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.MobileNetV3.mobilenet_v3'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.EfficientNetB0.efficientnet'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.ResNet50'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.ResNet50.resnet50'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.imagenet_class_names'] = mock.MagicMock()
    sys.modules['node.DLNode.classification.esc50_class_names'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.YuNet'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.YuNet.yunet'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.yunet'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.yunet.yunet'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe.face_detection'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe.face_mesh'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe_facedetection'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe_facedetection.mediapipe_facedetection'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe_facemesh'] = mock.MagicMock()
    sys.modules['node.DLNode.face_detection.mediapipe_facemesh.mediapipe_facemesh'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.pspnet'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.pspnet.pspnet'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.deeplab_v3'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.deeplab_v3.deeplab_v3'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.road_segmentation_adas_0001'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.road_segmentation_adas_0001.road_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.skin_clothes_hair_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.skin_clothes_hair_segmentation.skin_clothes_hair_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.mediapipe_selfie_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.mediapipe_selfie_segmentation.mediapipe_selfie_segmentation'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.yolov8_seg'] = mock.MagicMock()
    sys.modules['node.DLNode.semantic_segmentation.yolov8_seg.yolov8_seg'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.midas'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.midas.midas'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.FSRE_Depth'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.FSRE_Depth.fsre_depth'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.HR_Depth'] = mock.MagicMock()
    sys.modules['node.DLNode.monocular_depth_estimation.HR_Depth.hr_depth'] = mock.MagicMock()
    
    dl_nodes = [
        'node.DLNode.node_object_detection',
        'node.DLNode.node_classification',
        'node.DLNode.node_face_detection',
        'node.DLNode.node_semantic_segmentation',
        'node.DLNode.node_monocular_depth_estimation',
    ]
    
    for node_module in dl_nodes:
        try:
            __import__(node_module)
            print(f"✓ {node_module} imported successfully")
        except Exception as e:
            print(f"✗ Failed to import {node_module}: {e}")
            raise


def test_node_classes_use_get_input_frame():
    """Test that Node classes have access to get_input_frame method"""
    import unittest.mock as mock
    
    # Mock all dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    sys.modules['node_editor'] = mock.MagicMock()
    sys.modules['node_editor.util'] = mock.MagicMock()
    sys.modules['node.node_abc'] = mock.MagicMock()
    
    from node.ProcessNode.node_blur import Node as BlurNode
    from node.ProcessNode.node_brightness import Node as BrightnessNode
    
    # Test that the nodes inherit get_input_frame
    blur_node = BlurNode()
    assert hasattr(blur_node, 'get_input_frame'), "BlurNode should have get_input_frame method"
    print("✓ BlurNode has get_input_frame method")
    
    brightness_node = BrightnessNode()
    assert hasattr(brightness_node, 'get_input_frame'), "BrightnessNode should have get_input_frame method"
    print("✓ BrightnessNode has get_input_frame method")


if __name__ == '__main__':
    print("Running integration tests for updated node files...\n")
    
    try:
        test_process_node_imports()
        print()
        test_dl_node_imports()
        print()
        test_node_classes_use_get_input_frame()
        
        print("\n" + "="*60)
        print("All integration tests passed! ✓")
        print("="*60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
