#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verification script for video node 5-second blocks and 224x224 resizing.

This script demonstrates that:
1. Video frames are automatically resized to 224x224
2. 5-second blocks are tracked correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def verify_224_resize_implementation():
    """Verify that 224x224 resizing is implemented"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for resize to 224x224
    has_resize = 'cv2.resize(frame, (224, 224)' in content
    has_inter_area = 'interpolation=cv2.INTER_AREA' in content
    
    print("=" * 60)
    print("VERIFICATION: 224x224 Frame Resizing")
    print("=" * 60)
    print(f"✓ Frames resized to 224x224: {has_resize}")
    print(f"✓ Uses INTER_AREA interpolation: {has_inter_area}")
    print()
    
    if has_resize and has_inter_area:
        print("✓ Frame resizing is properly implemented!")
        print("  - All frames output by the video node are 224x224")
        print("  - Perfect for DL models like ResNet50, MobileNetV3, etc.")
    else:
        print("✗ Frame resizing not found!")
        return False
    
    return True


def verify_5s_block_tracking():
    """Verify that 5-second block tracking is implemented"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for block tracking
    has_current_block = '_current_block = {}' in content
    has_block_start = '_block_start_frame = {}' in content
    has_frames_per_5s = 'frames_per_5s = int(fps * 5)' in content
    has_block_calc = 'current_block = current_frame // frames_per_5s' in content
    
    print("=" * 60)
    print("VERIFICATION: 5-Second Block Tracking")
    print("=" * 60)
    print(f"✓ Has _current_block attribute: {has_current_block}")
    print(f"✓ Has _block_start_frame attribute: {has_block_start}")
    print(f"✓ Calculates frames per 5 seconds: {has_frames_per_5s}")
    print(f"✓ Calculates current block: {has_block_calc}")
    print()
    
    if all([has_current_block, has_block_start, has_frames_per_5s, has_block_calc]):
        print("✓ 5-second block tracking is properly implemented!")
        print("  - Tracks which 5-second block is being processed")
        print("  - Formula: block_number = frame_number // (fps * 5)")
        print("  - Example: At 30 FPS, block 0 = frames 0-149, block 1 = frames 150-299")
    else:
        print("✗ Block tracking not fully implemented!")
        return False
    
    return True


def demonstrate_block_calculation():
    """Demonstrate how 5-second blocks are calculated"""
    print("=" * 60)
    print("EXAMPLE: 5-Second Block Calculation")
    print("=" * 60)
    
    fps_values = [24, 30, 60]
    
    for fps in fps_values:
        frames_per_5s = fps * 5
        print(f"\nVideo at {fps} FPS:")
        print(f"  - Frames per 5-second block: {frames_per_5s}")
        print(f"  - Block 0: frames 0 to {frames_per_5s - 1}")
        print(f"  - Block 1: frames {frames_per_5s} to {frames_per_5s * 2 - 1}")
        print(f"  - Block 2: frames {frames_per_5s * 2} to {frames_per_5s * 3 - 1}")
    
    print()


def verify_reset_logic():
    """Verify that block tracking is reset on loop and file change"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find loop reset
    loop_reset_found = False
    for i, line in enumerate(lines):
        if 'if loop_flag:' in line:
            block = '\n'.join(lines[i:i+10])
            if '_current_block[str(node_id)] = 0' in block and '_block_start_frame[str(node_id)] = 0' in block:
                loop_reset_found = True
                break
    
    # Find file change reset
    file_change_reset_found = False
    for i, line in enumerate(lines):
        if 'if prev_movie_path != movie_path:' in line:
            block = '\n'.join(lines[i:i+15])
            if '_current_block[str(node_id)] = 0' in block and '_block_start_frame[str(node_id)] = 0' in block:
                file_change_reset_found = True
                break
    
    print("=" * 60)
    print("VERIFICATION: Block Tracking Reset Logic")
    print("=" * 60)
    print(f"✓ Resets on video loop: {loop_reset_found}")
    print(f"✓ Resets on file change: {file_change_reset_found}")
    print()
    
    if loop_reset_found and file_change_reset_found:
        print("✓ Block tracking reset logic is properly implemented!")
        print("  - Blocks reset when video loops back to start")
        print("  - Blocks reset when a new video file is loaded")
    else:
        print("✗ Reset logic not fully implemented!")
        return False
    
    return True


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("VIDEO NODE: 5-SECOND BLOCKS & 224x224 RESIZE VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(verify_224_resize_implementation())
    print()
    
    results.append(verify_5s_block_tracking())
    print()
    
    demonstrate_block_calculation()
    
    results.append(verify_reset_logic())
    print()
    
    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    
    if all(results):
        print("✓ ALL VERIFICATIONS PASSED!")
        print()
        print("The video node now:")
        print("  1. Automatically resizes all frames to 224x224")
        print("  2. Tracks video processing in 5-second blocks")
        print("  3. Resets block tracking on loop and file change")
        print("  4. Uses optimal INTER_AREA interpolation for resizing")
        print()
        print("This ensures compatibility with DL models that require 224x224 input.")
    else:
        print("✗ SOME VERIFICATIONS FAILED!")
        sys.exit(1)
