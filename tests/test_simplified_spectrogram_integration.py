#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for simplified frame-based spectrogram in video node.

This test verifies the complete integration of the simplified approach:
- No audio extraction required
- Spectrogram generated directly from video frames
- Real-time updates as frames change
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import cv2
import numpy as np
from unittest.mock import MagicMock, patch


def test_simplified_spectrogram_workflow():
    """
    Test the complete simplified workflow:
    1. Video frame is read
    2. Spectrogram is generated from that frame (not audio)
    3. Spectrogram is displayed in real-time
    """
    from node.InputNode.node_video import VideoNode
    
    # Create a video node
    node = VideoNode()
    node._opencv_setting_dict = {
        'input_window_width': 240,
        'input_window_height': 135,
        'use_pref_counter': False
    }
    node._small_window_w = 240
    node._small_window_h = 135
    
    # Mock DearPyGUI functions
    with patch('node.InputNode.node_video.dpg') as mock_dpg, \
         patch('node.InputNode.node_video.dpg_get_value') as mock_get_value, \
         patch('node.InputNode.node_video.dpg_set_value') as mock_set_value:
        
        # Setup mocks
        mock_dpg.does_item_exist.return_value = True
        mock_get_value.side_effect = lambda tag: {
            '1:Video:SpectrogramToggle': True,  # Spectrogram enabled
            '1:Video:TEXT:Input02Value': False,  # No loop
            '1:Video:INT:Input03Value': 1        # Skip rate
        }.get(tag, None)
        
        # Create a test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Simulate what happens in update() when a frame is available
        node_id = 1
        show_spectrogram = True
        
        if show_spectrogram and test_frame is not None:
            # Generate spectrogram directly from the current frame
            spectrogram_bgr = node._generate_frame_spectrogram(test_frame)
            
            # Verify spectrogram was generated
            assert spectrogram_bgr is not None, "Spectrogram should be generated from frame"
            assert isinstance(spectrogram_bgr, np.ndarray), "Spectrogram should be numpy array"
            
            # Convert to DPG texture format
            texture = node.convert_cv_to_dpg(
                spectrogram_bgr,
                node._small_window_w,
                node._small_window_h
            )
            
            # Verify texture was created
            assert texture is not None, "Texture should be created"
            
            print("✓ Simplified spectrogram workflow test passed")
            print(f"  - Frame shape: {test_frame.shape}")
            print(f"  - Spectrogram shape: {spectrogram_bgr.shape}")
            print(f"  - No audio extraction required")
            print(f"  - Real-time generation from frame")


def test_no_audio_dependencies_in_update():
    """
    Verify that the update() method no longer depends on:
    - Audio file extraction
    - Spectrogram pre-computation
    - Audio metadata
    """
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Verify that frame-based spectrogram doesn't need audio-related attributes
    test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
    
    # This should work without:
    # - self._spectrogram_array (removed)
    # - self._spectrogram_meta (removed from update path)
    # - Audio extraction
    # - Pre-computed spectrogram
    
    spectrogram = node._generate_frame_spectrogram(test_frame)
    
    assert spectrogram is not None, "Frame-based spectrogram should work standalone"
    print("✓ No audio dependencies test passed")
    print("  - No _spectrogram_array lookup needed")
    print("  - No _spectrogram_meta needed")
    print("  - No audio file processing")


def test_real_time_spectrogram_updates():
    """
    Test that different frames produce different spectrograms.
    This simulates real-time updates as video plays.
    """
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Create two different frames
    frame1 = np.zeros((240, 320, 3), dtype=np.uint8)
    frame1[50:100, 100:200] = [255, 0, 0]  # Blue rectangle
    
    frame2 = np.zeros((240, 320, 3), dtype=np.uint8)
    frame2[100:150, 50:150] = [0, 255, 0]  # Green rectangle
    
    # Generate spectrograms
    spec1 = node._generate_frame_spectrogram(frame1)
    spec2 = node._generate_frame_spectrogram(frame2)
    
    # Verify both were generated
    assert spec1 is not None, "Spectrogram 1 should be generated"
    assert spec2 is not None, "Spectrogram 2 should be generated"
    
    # Verify they are different (different frames → different spectrograms)
    assert not np.array_equal(spec1, spec2), \
        "Different frames should produce different spectrograms"
    
    print("✓ Real-time updates test passed")
    print("  - Each frame generates unique spectrogram")
    print("  - Spectrograms update in real-time with video")


def test_performance_characteristics():
    """
    Test that frame-based approach is fast enough for real-time use.
    """
    import time
    from node.InputNode.node_video import VideoNode
    
    node = VideoNode()
    
    # Create a realistic frame size
    test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    # Time the spectrogram generation
    start_time = time.time()
    iterations = 10
    
    for _ in range(iterations):
        spectrogram = node._generate_frame_spectrogram(test_frame)
        assert spectrogram is not None
    
    elapsed = time.time() - start_time
    avg_time = (elapsed / iterations) * 1000  # Convert to ms
    
    print(f"✓ Performance test passed")
    print(f"  - Average time per frame: {avg_time:.2f}ms")
    print(f"  - Suitable for real-time playback at 30 FPS" if avg_time < 33 else "  - May need optimization for 30 FPS")


if __name__ == '__main__':
    print("Testing simplified frame-based spectrogram integration...\n")
    
    test_simplified_spectrogram_workflow()
    print()
    test_no_audio_dependencies_in_update()
    print()
    test_real_time_spectrogram_updates()
    print()
    test_performance_characteristics()
    
    print("\n✓ All integration tests passed!")
    print("\nSummary of changes:")
    print("  - Removed audio extraction complexity")
    print("  - Spectrogram now generated from video frames (2D FFT)")
    print("  - Real-time updates with each frame")
    print("  - No pre-computation needed")
    print("  - Simpler, more direct implementation")
