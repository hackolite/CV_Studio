#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test audio spectrogram support without importing dependencies."""

import os
import re
import ast


def test_file_syntax(filepath):
    """Test if a Python file has valid syntax."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def check_update_signature(filepath, expected_params):
    """Check if update method has expected parameters."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the update method definition
    pattern = r'def update\([^)]+\):'
    matches = re.findall(pattern, content)
    
    if not matches:
        return False, "No update method found"
    
    # Check if node_audio_dict is in the signature
    for match in matches:
        if 'node_audio_dict' in match:
            return True, None
    
    return False, f"update method doesn't have node_audio_dict parameter. Found: {matches[0]}"


def test_main_py():
    """Test main.py changes."""
    filepath = '/home/runner/work/CV_Studio/CV_Studio/main.py'
    
    # Check syntax
    valid, error = test_file_syntax(filepath)
    if not valid:
        return False, f"Syntax error: {error}"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for node_audio_dict initialization
    if 'node_audio_dict = {}' not in content:
        return False, "node_audio_dict initialization not found"
    
    # Check for node_audio_dict in update_node_info signature
    if 'def update_node_info' not in content:
        return False, "update_node_info function not found"
    
    # Find update_node_info signature
    pattern = r'def update_node_info\([^)]+\):'
    match = re.search(pattern, content)
    if match and 'node_audio_dict' not in match.group():
        return False, "node_audio_dict not in update_node_info signature"
    
    # Check that audio is propagated
    if 'data.get("audio")' not in content and 'data["audio"]' not in content:
        return False, "Audio data propagation not found"
    
    return True, None


def test_basenode_py():
    """Test basenode.py changes."""
    filepath = '/home/runner/work/CV_Studio/CV_Studio/node/basenode.py'
    
    # Check syntax
    valid, error = test_file_syntax(filepath)
    if not valid:
        return False, f"Syntax error: {error}"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for TYPE_AUDIO constant
    if 'TYPE_AUDIO' not in content:
        return False, "TYPE_AUDIO constant not found"
    
    # Check update method signature
    return check_update_signature(filepath, ['node_audio_dict'])


def test_process_nodes():
    """Test ProcessNode files."""
    base_dir = '/home/runner/work/CV_Studio/CV_Studio/node/ProcessNode'
    nodes_to_test = [
        'node_blur.py',
        'node_brightness.py',
        'node_contrast.py',
        'node_resize.py',
        'node_crop.py',
        'node_flip.py',
        'node_canny.py',
        'node_threshold.py',
        'node_grayscale.py',
        'node_equalize_hist.py',
    ]
    
    results = []
    for node_file in nodes_to_test:
        filepath = os.path.join(base_dir, node_file)
        
        # Check syntax
        valid, error = test_file_syntax(filepath)
        if not valid:
            results.append((node_file, False, f"Syntax error: {error}"))
            continue
        
        # Check update signature
        with open(filepath, 'r') as f:
            content = f.read()
        
        if 'node_audio_dict' not in content:
            results.append((node_file, False, "node_audio_dict not found in file"))
            continue
        
        # Check for audio tags
        if 'tag_node_input_audio_name' not in content:
            results.append((node_file, False, "Audio tags not found"))
            continue
        
        # Check for audio processing
        if 'processed_audio' not in content or 'audio_frame' not in content:
            results.append((node_file, False, "Audio processing logic not found"))
            continue
        
        # Check return statement includes audio
        if '"audio"' not in content:
            results.append((node_file, False, "Return statement doesn't include audio"))
            continue
        
        results.append((node_file, True, None))
    
    return results


def test_dl_nodes():
    """Test DLNode files."""
    base_dir = '/home/runner/work/CV_Studio/CV_Studio/node/DLNode'
    nodes_to_test = [
        'node_object_detection.py',
        'node_classification.py',
        'node_face_detection.py',
        'node_pose_estimation.py',
        'node_semantic_segmentation.py',
    ]
    
    results = []
    for node_file in nodes_to_test:
        filepath = os.path.join(base_dir, node_file)
        
        # Check syntax
        valid, error = test_file_syntax(filepath)
        if not valid:
            results.append((node_file, False, f"Syntax error: {error}"))
            continue
        
        # Check update signature has node_audio_dict
        valid, error = check_update_signature(filepath, ['node_audio_dict'])
        if not valid:
            results.append((node_file, False, error))
            continue
        
        results.append((node_file, True, None))
    
    return results


def test_video_node():
    """Test that video node returns audio."""
    filepath = '/home/runner/work/CV_Studio/CV_Studio/node/InputNode/node_video.py'
    
    # Check syntax
    valid, error = test_file_syntax(filepath)
    if not valid:
        return False, f"Syntax error: {error}"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check that the return statement includes audio
    if 'return {"image":frame, "audio": spectrogram_bgr, "json" : None}' not in content:
        return False, "Video node doesn't return audio spectrogram"
    
    return True, None


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Audio Spectrogram Support (Syntax and Structure)")
    print("=" * 70)
    print()
    
    all_passed = True
    
    # Test main.py
    print("--- Testing main.py ---")
    passed, error = test_main_py()
    if passed:
        print("✓ main.py has all required changes")
    else:
        print(f"✗ main.py test failed: {error}")
        all_passed = False
    print()
    
    # Test basenode.py
    print("--- Testing basenode.py ---")
    passed, error = test_basenode_py()
    if passed:
        print("✓ basenode.py has all required changes")
    else:
        print(f"✗ basenode.py test failed: {error}")
        all_passed = False
    print()
    
    # Test ProcessNode files
    print("--- Testing ProcessNode files ---")
    results = test_process_nodes()
    for node_file, passed, error in results:
        if passed:
            print(f"✓ {node_file} has all required changes")
        else:
            print(f"✗ {node_file} test failed: {error}")
            all_passed = False
    print()
    
    # Test DLNode files
    print("--- Testing DLNode files ---")
    results = test_dl_nodes()
    for node_file, passed, error in results:
        if passed:
            print(f"✓ {node_file} has correct update signature")
        else:
            print(f"✗ {node_file} test failed: {error}")
            all_passed = False
    print()
    
    # Test video node
    print("--- Testing video node ---")
    passed, error = test_video_node()
    if passed:
        print("✓ Video node returns audio spectrogram")
    else:
        print(f"✗ Video node test failed: {error}")
        all_passed = False
    print()
    
    print("=" * 70)
    if all_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 70)
    
    exit(0 if all_passed else 1)
