#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for video loop frame count synchronization"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_frame_count_reset_on_loop():
    """Test that frame count is reset when video loops back to start"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the line where video position is reset to 0
    found_position_reset = False
    found_frame_count_reset = False
    reset_block_start = -1
    
    for i, line in enumerate(lines):
        if 'video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)' in line:
            found_position_reset = True
            reset_block_start = i
            # Check the next few lines for frame count reset
            for j in range(i, min(i + 5, len(lines))):
                if '_frame_count[str(node_id)] = 0' in lines[j]:
                    found_frame_count_reset = True
                    break
            break
    
    assert found_position_reset, "Should have code to reset video position to frame 0 on loop"
    assert found_frame_count_reset, "Should reset _frame_count to 0 when video position is reset"
    
    print("✓ Frame count is properly reset when video loops")


def test_frame_count_and_position_reset_together():
    """Test that frame count reset happens in the same code block as position reset"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the if loop_flag block
    loop_flag_block_start = -1
    for i, line in enumerate(lines):
        if 'if loop_flag:' in line:
            loop_flag_block_start = i
            break
    
    assert loop_flag_block_start >= 0, "Should have 'if loop_flag:' block"
    
    # Check that within the next 10 lines, both resets happen
    block_content = '\n'.join(lines[loop_flag_block_start:loop_flag_block_start + 10])
    
    assert 'video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)' in block_content, \
        "Should reset video position in loop_flag block"
    assert '_frame_count[str(node_id)] = 0' in block_content, \
        "Should reset frame count in loop_flag block"
    
    print("✓ Frame count and position reset are in the same code block")


if __name__ == '__main__':
    test_frame_count_reset_on_loop()
    test_frame_count_and_position_reset_together()
    print("\n✓ All video loop frame count tests passed successfully!")
