#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify the Overlay node functionality
"""
import cv2
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.OverlayNode.node_overlay import OverlayNode


def test_overlay_node():
    """Test the Overlay node with sample data"""
    print("Testing Overlay node...")
    
    # Create a test image
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    # Add some color gradient for visual interest
    for i in range(480):
        test_image[i, :] = [i * 255 // 480, 100, 200]
    
    # Create test JSON data (weather data format)
    test_json = {
        "temperature": 25.5,
        "windspeed": 12.3,
        "winddirection": 180,
        "weathercode": 0,
        "is_day": 1,
        "time": "2024-12-24T13:00"
    }
    
    # Create node instance
    node = OverlayNode()
    
    # Test flattening dictionary
    flat_data = node._flatten_dict(test_json)
    print(f"Flattened data: {flat_data}")
    assert len(flat_data) > 0, "Failed to flatten dictionary"
    
    # Test drawing overlay
    font_scale = 0.7
    text_color = (255, 255, 255, 255)
    bg_color = (0, 0, 0, 180)
    position = "Top Right"
    
    output_image = node._draw_overlay(
        test_image,
        test_json,
        font_scale,
        text_color,
        bg_color,
        position
    )
    
    assert output_image is not None, "Failed to create overlay image"
    assert output_image.shape == test_image.shape, "Output image shape mismatch"
    
    # Verify that the output image is different from input (overlay was applied)
    diff = cv2.absdiff(test_image, output_image)
    assert np.sum(diff) > 0, "Overlay was not applied to image"
    
    print("✓ Overlay node flattening test passed")
    print("✓ Overlay node drawing test passed")
    
    # Test with nested dictionary
    nested_json = {
        "current_weather": {
            "temperature": 25.5,
            "windspeed": 12.3,
        },
        "location": {
            "latitude": 48.8566,
            "longitude": 2.3522
        }
    }
    
    output_image_nested = node._draw_overlay(
        test_image,
        nested_json,
        font_scale,
        text_color,
        bg_color,
        "Bottom Left"
    )
    
    assert output_image_nested is not None, "Failed with nested dictionary"
    print("✓ Overlay node nested dictionary test passed")
    
    # Test different positions
    positions = ['Top Left', 'Top Right', 'Bottom Left', 'Bottom Right', 'Center']
    for pos in positions:
        result = node._draw_overlay(test_image, test_json, font_scale, text_color, bg_color, pos)
        assert result is not None, f"Failed with position: {pos}"
    
    print("✓ Overlay node position test passed")
    
    print("\n✅ All Overlay node tests passed!")
    return True


def test_weather_node():
    """Test the Weather node basic functionality"""
    print("\nTesting Weather node...")
    
    from node.InputNode.node_temperature import FactoryNode, WeatherNode
    
    # Test factory node
    factory = FactoryNode()
    assert factory.node_label == 'Weather', f"Expected 'Weather', got '{factory.node_label}'"
    assert factory.node_tag == 'Weather', f"Expected 'Weather', got '{factory.node_tag}'"
    print("✓ Weather FactoryNode test passed")
    
    # Test node instance
    node = WeatherNode()
    assert node.node_label == 'Weather', f"Expected 'Weather', got '{node.node_label}'"
    print("✓ Weather WeatherNode test passed")
    
    # Test that initial data is None
    assert node._last_weather_data is None, "Initial weather data should be None"
    print("✓ Weather node initialization test passed")
    
    print("\n✅ All Weather node tests passed!")
    return True


if __name__ == '__main__':
    try:
        test_weather_node()
        test_overlay_node()
        print("\n" + "="*50)
        print("ALL TESTS PASSED SUCCESSFULLY!")
        print("="*50)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
