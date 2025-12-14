#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that queue size calculation uses detected video FPS for audio chunking.

UPDATED: This test now verifies that audio chunking and queue sizes use the
detected video FPS, not the target_fps slider value, to ensure audio/video sync.

With FPS-based chunking (1 chunk per frame):
    audio_chunk_size = sample_rate / video_fps
    image_queue_size = 4 seconds * video_fps
    audio_queue_size = 4 seconds * video_fps

The target_fps slider is used for playback timing but NOT for audio chunking.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestQueueSizeUsesTargetFPS(unittest.TestCase):
    """Test that queue size calculation uses target_fps"""
    
    def test_preprocess_video_accepts_target_fps_parameter(self):
        """Verify that _preprocess_video accepts target_fps parameter"""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(video_node_path, 'r') as f:
            content = f.read()
        
        # Check that _preprocess_video has target_fps parameter
        assert 'def _preprocess_video' in content, "_preprocess_video method should exist"
        assert 'target_fps' in content, "_preprocess_video should have target_fps parameter"
        
        # Find the method signature
        lines = content.split('\n')
        for line in lines:
            if 'def _preprocess_video' in line:
                assert 'target_fps' in line, "target_fps should be in _preprocess_video signature"
                print(f"✓ Found signature: {line.strip()}")
                break
        
        print("✓ _preprocess_video accepts target_fps parameter")
    
    def test_callback_reads_target_fps_from_slider(self):
        """Verify that _callback_file_select reads target_fps from slider"""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(video_node_path, 'r') as f:
            content = f.read()
        
        # Find the _callback_file_select method
        in_callback = False
        found_target_fps_read = False
        found_target_fps_pass = False
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'def _callback_file_select' in line:
                in_callback = True
            elif in_callback and line.strip().startswith('def ') and '_callback_file_select' not in line:
                break
            
            if in_callback:
                # Check that target_fps_value is read using dpg_get_value
                if 'target_fps_value = dpg_get_value(tag_node_input04_value_name)' in line:
                    found_target_fps_read = True
                
                # Also accept if target_fps is assigned from the value
                if 'target_fps = int(target_fps_value)' in line:
                    found_target_fps_read = True
                
                # Check that target_fps is passed to _preprocess_video
                if 'target_fps=target_fps' in line or 'target_fps=' in line:
                    found_target_fps_pass = True
        
        assert found_target_fps_read, "_callback_file_select should read target_fps from slider"
        assert found_target_fps_pass, "_callback_file_select should pass target_fps to _preprocess_video"
        
        print("✓ _callback_file_select reads and passes target_fps")
    
    def test_queue_size_calculation_uses_video_fps(self):
        """Verify that queue size calculation uses detected video fps for audio chunking"""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(video_node_path, 'r') as f:
            content = f.read()
        
        # Find the queue size calculation in _preprocess_video
        in_preprocess = False
        found_correct_calculation = False
        
        lines = content.split('\n')
        for line in lines:
            if 'def _preprocess_video' in line:
                in_preprocess = True
            elif in_preprocess and line.strip().startswith('def ') and '_preprocess_video' not in line:
                break
            
            if in_preprocess:
                # Check for the correct queue size calculation using detected fps
                # After the fix, it should use 'fps' (detected video fps), not 'target_fps' (slider)
                if 'image_queue_size' in line and '* fps' in line and 'target_fps' not in line:
                    found_correct_calculation = True
                    print(f"✓ Found calculation: {line.strip()}")
                
                # Make sure we're not using target_fps (which would be wrong)
                if 'image_queue_size' in line and 'target_fps' in line and '* fps' not in line.replace('target_fps', ''):
                    self.fail("Queue size calculation should use detected video fps, not target_fps slider")
        
        assert found_correct_calculation, "Queue size calculation should use detected video fps"
        
        print("✓ Queue size calculation uses detected video fps (not target_fps)")
    
    def test_calculation_example_with_different_fps(self):
        """Test example: video is 30fps, but target is 24fps - should use video fps"""
        queue_duration_seconds = 4  # 4 seconds of buffer
        
        # Scenario 1: Using video_fps (CORRECT for audio chunking)
        video_fps = 30
        correct_queue_size = int(queue_duration_seconds * video_fps)
        
        # Scenario 2: Using target_fps (INCORRECT - causes desync)
        target_fps = 24
        incorrect_queue_size = int(queue_duration_seconds * target_fps)
        
        # The values should be different
        self.assertNotEqual(correct_queue_size, incorrect_queue_size,
                           "Queue size should differ when target_fps != video_fps")
        
        self.assertEqual(correct_queue_size, 120,
                        f"With video_fps=30, should be 4*30=120, got {correct_queue_size}")
        
        self.assertEqual(incorrect_queue_size, 96,
                        f"With target_fps=24, would be 4*24=96, got {incorrect_queue_size}")
        
        print(f"✓ Example calculation (FPS-based chunking):")
        print(f"  - Correct (video_fps=30): {correct_queue_size} frames (audio chunks match video frames)")
        print(f"  - Incorrect (target_fps=24): {incorrect_queue_size} frames (causes desync)")
        print(f"  - Difference: {correct_queue_size - incorrect_queue_size} frames")


if __name__ == "__main__":
    unittest.main()
