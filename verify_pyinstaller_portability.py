#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify PyInstaller portability fixes
This script tests the resource_path function in both normal and simulated frozen modes.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import resource_path


def test_normal_mode():
    """Test resource_path in normal (script) mode"""
    print("=" * 70)
    print("Testing Normal (Development) Mode")
    print("=" * 70)
    
    test_paths = [
        'node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx',
        'node/DLNode/object_detection/YOLOX/model/yolox_nano.onnx',
        'node/DLNode/object_detection/YOLOX/coco_classes.txt',
        'node_editor/setting/setting.json',
        'node/DLNode/semantic_segmentation/deeplab_v3/model/deeplab_v3_1_default_1.onnx',
        'node/DLNode/pose_estimation/movenet/model/movenet_singlepose_lightning_4.onnx',
        'node/DLNode/face_detection/YuNet/model/face_detection_yunet_120x160.onnx',
    ]
    
    all_passed = True
    for path in test_paths:
        result = resource_path(path)
        exists = os.path.exists(result)
        status = "✓" if exists else "✗"
        
        print(f"\n{status} {path}")
        print(f"  -> {result}")
        print(f"  Exists: {exists}")
        
        if not exists:
            all_passed = False
    
    return all_passed


def test_frozen_mode():
    """Test resource_path in simulated frozen (PyInstaller) mode"""
    print("\n" + "=" * 70)
    print("Testing Frozen (PyInstaller) Mode")
    print("=" * 70)
    
    # Simulate PyInstaller's _MEIPASS
    simulated_temp = '/tmp/simulated_pyinstaller_temp'
    sys._MEIPASS = simulated_temp
    
    print(f"\nSimulated _MEIPASS: {simulated_temp}")
    
    test_paths = [
        'node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx',
        'node_editor/setting/setting.json',
    ]
    
    all_passed = True
    for path in test_paths:
        result = resource_path(path)
        expected = os.path.normpath(os.path.join(simulated_temp, path))
        matches = (result == expected)
        status = "✓" if matches else "✗"
        
        print(f"\n{status} {path}")
        print(f"  -> {result}")
        print(f"  Expected: {expected}")
        print(f"  Match: {matches}")
        
        if not matches:
            all_passed = False
    
    # Clean up
    delattr(sys, '_MEIPASS')
    
    return all_passed


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PyInstaller Portability Verification")
    print("=" * 70)
    print("\nThis script verifies that all file access points use the")
    print("resource_path() function for PyInstaller compatibility.\n")
    
    # Test normal mode
    normal_passed = test_normal_mode()
    
    # Test frozen mode
    frozen_passed = test_frozen_mode()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Normal Mode: {'✓ PASSED' if normal_passed else '✗ FAILED'}")
    print(f"Frozen Mode: {'✓ PASSED' if frozen_passed else '✗ FAILED'}")
    
    if normal_passed and frozen_passed:
        print("\n✓ All tests PASSED! PyInstaller portability is ready.")
        return 0
    else:
        print("\n✗ Some tests FAILED. Please check the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
