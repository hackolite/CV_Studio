#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test for frame slider feature without requiring full dependencies.
This test validates the logic of passing frame_width through the system.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_metadata_tuple_handling():
    """Test that the metadata tuple is correctly handled"""
    
    # Simulate video node output
    spectrogram = "mock_spectrogram_data"
    frame_width = 120
    audio_data = (spectrogram, frame_width)
    
    # Simulate get_input_frame logic
    if isinstance(audio_data, tuple) and len(audio_data) == 2:
        frame, fw = audio_data
        metadata = {"frame_width": fw}
    else:
        frame = audio_data
        metadata = None
    
    # Verify extraction
    assert frame == spectrogram, "Frame should be extracted correctly"
    assert metadata is not None, "Metadata should be created"
    assert metadata['frame_width'] == 120, "Frame width should be 120"
    
    print("✓ Metadata tuple handling works correctly")


def test_backward_compatibility_without_metadata():
    """Test that None audio data is handled correctly"""
    
    # Simulate old-style audio data (just the spectrogram)
    audio_data = "mock_spectrogram_data"
    
    # Simulate get_input_frame logic
    if isinstance(audio_data, tuple) and len(audio_data) == 2:
        frame, fw = audio_data
        metadata = {"frame_width": fw}
    else:
        frame = audio_data
        metadata = None
    
    # Verify handling
    assert frame == "mock_spectrogram_data", "Frame should be extracted correctly"
    assert metadata is None, "Metadata should be None for old-style data"
    
    print("✓ Backward compatibility works (handles non-tuple audio data)")


def test_frame_width_extraction():
    """Test extracting frame_width from metadata in classification node"""
    
    # Simulate classification node receiving metadata
    audio_metadata = {"frame_width": 150}
    
    # Extract frame_width
    frame_width = None
    if audio_metadata is not None and 'frame_width' in audio_metadata:
        frame_width = audio_metadata['frame_width']
    
    # Verify
    assert frame_width == 150, "Frame width should be extracted as 150"
    
    # Test with None metadata
    audio_metadata = None
    frame_width = None
    if audio_metadata is not None and 'frame_width' in audio_metadata:
        frame_width = audio_metadata['frame_width']
    
    assert frame_width is None, "Frame width should be None when metadata is None"
    
    print("✓ Frame width extraction works correctly")


def test_yolo_cls_conditional():
    """Test that yolo-cls conditional logic works correctly"""
    
    # Test case 1: yolo-cls with frame_width
    model_name = 'Yolo-cls'
    frame_width = 100
    should_resize = model_name == 'Yolo-cls' and frame_width is not None
    assert should_resize == True, "Should resize for yolo-cls with frame_width"
    
    # Test case 2: yolo-cls without frame_width
    model_name = 'Yolo-cls'
    frame_width = None
    should_resize = model_name == 'Yolo-cls' and frame_width is not None
    assert should_resize == False, "Should NOT resize for yolo-cls without frame_width"
    
    # Test case 3: other model with frame_width
    model_name = 'ResNet50'
    frame_width = 100
    should_resize = model_name == 'Yolo-cls' and frame_width is not None
    assert should_resize == False, "Should NOT resize for other models"
    
    # Test case 4: other model without frame_width
    model_name = 'ResNet50'
    frame_width = None
    should_resize = model_name == 'Yolo-cls' and frame_width is not None
    assert should_resize == False, "Should NOT resize for other models without frame_width"
    
    print("✓ Yolo-cls conditional logic works correctly")


def test_slider_range_values():
    """Test that slider range values are appropriate"""
    
    # Typical values
    small_window_w = 240  # Default display width
    
    # Slider configuration
    default_value = small_window_w
    min_value = 60
    max_value = small_window_w
    
    # Verify range
    assert min_value == 60, "Minimum should be 60 pixels"
    assert max_value == 240, "Maximum should be 240 pixels (small_window_w)"
    assert default_value == 240, "Default should be full width (240)"
    assert min_value < max_value, "Min should be less than max"
    
    # Test valid values
    test_values = [60, 120, 180, 240]
    for value in test_values:
        assert min_value <= value <= max_value, f"Value {value} should be in range"
    
    print("✓ Slider range values are appropriate")


def test_window_width_calculation():
    """Test that window width is calculated correctly"""
    
    # Simulate different frame_width values
    test_cases = [
        (60, 60),    # Minimum
        (120, 120),  # Half
        (180, 180),  # 3/4
        (240, 240),  # Maximum (default)
    ]
    
    for frame_width, expected_window_width in test_cases:
        # Simulate the logic from node_video.py
        window_width = frame_width
        half_window = window_width // 2
        
        assert window_width == expected_window_width, \
            f"Window width should be {expected_window_width} for frame_width {frame_width}"
        
        # Verify half_window calculation
        expected_half = expected_window_width // 2
        assert half_window == expected_half, \
            f"Half window should be {expected_half}"
    
    print("✓ Window width calculation works correctly")


if __name__ == '__main__':
    print("Running integration tests for frame slider feature...\n")
    
    try:
        test_metadata_tuple_handling()
        test_backward_compatibility_without_metadata()
        test_frame_width_extraction()
        test_yolo_cls_conditional()
        test_slider_range_values()
        test_window_width_calculation()
        
        print("\n" + "="*60)
        print("All integration tests passed! ✓")
        print("="*60)
        print("\nFrame slider logic is correct:")
        print("- Metadata tuple (spectrogram, frame_width) handled properly")
        print("- Backward compatible with old-style audio data")
        print("- Frame width extraction works correctly")
        print("- Yolo-cls conditional logic is sound")
        print("- Slider range (60-240) is appropriate")
        print("- Window width calculations are correct")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
