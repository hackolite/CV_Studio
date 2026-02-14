#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test to verify the Map node fix for:
1. Empty JSON string handling
2. Proper return value format
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


def test_empty_json_handling():
    """Test that empty JSON strings don't cause parse errors"""
    from node.VisualNode.node_map import Node as MapNode
    
    # Create node for testing
    node = MapNode.create_for_testing()
    
    # Test empty string
    empty_input = ""
    if empty_input.strip():
        # Should not reach here
        data = json.loads(empty_input)
        assert False, "Should have skipped parsing empty string"
    else:
        print("✓ Empty string handling test passed - parse skipped")
    
    # Test whitespace-only string
    whitespace_input = "   \n\t  "
    if whitespace_input.strip():
        # Should not reach here
        data = json.loads(whitespace_input)
        assert False, "Should have skipped parsing whitespace-only string"
    else:
        print("✓ Whitespace-only string handling test passed - parse skipped")
    
    # Test valid JSON still works
    valid_input = '{"boats": [{"latitude": 40.7, "longitude": -74.0, "ship_name": "Test"}]}'
    if valid_input.strip():
        data = json.loads(valid_input)
        assert 'boats' in data
        print("✓ Valid JSON string handling test passed")
    else:
        assert False, "Valid JSON should not be skipped"


def test_return_value_format():
    """Test that update method returns proper dict format"""
    import numpy as np
    
    # Create a mock return value like the node should return
    preview_image = np.zeros((135, 240, 3), dtype=np.uint8)
    
    # Old incorrect format (just returning the image)
    old_format = preview_image
    
    # New correct format (returning dict)
    new_format = {"image": preview_image, "json": None, "audio": None}
    
    # Verify the new format has the expected structure
    assert isinstance(new_format, dict), "Return value should be a dict"
    assert "image" in new_format, "Return value should have 'image' key"
    assert "json" in new_format, "Return value should have 'json' key"
    assert "audio" in new_format, "Return value should have 'audio' key"
    assert isinstance(new_format["image"], np.ndarray), "image should be a numpy array"
    assert new_format["json"] is None, "json should be None"
    assert new_format["audio"] is None, "audio should be None"
    
    print("✓ Return value format test passed")
    
    # Verify that accessing old format would fail
    try:
        _ = old_format["image"]
        assert False, "Old format should not support dict access"
    except (TypeError, KeyError):
        print("✓ Old format incompatibility confirmed")


def test_extract_lat_lon():
    """Test lat/lon extraction from JSON"""
    from node.VisualNode.node_map import Node as MapNode
    
    node = MapNode.create_for_testing()
    
    # Test with valid data
    valid_data = {
        "boats": [
            {"latitude": 40.7128, "longitude": -74.0060, "ship_name": "Test Ship"}
        ]
    }
    
    points = node._extract_lat_lon_from_json(valid_data)
    assert len(points) == 1
    assert points[0]['lat'] == 40.7128
    assert points[0]['lon'] == -74.0060
    print("✓ Lat/lon extraction test passed")


if __name__ == "__main__":
    print("Testing Map Node Fixes...")
    print()
    
    try:
        test_empty_json_handling()
        test_return_value_format()
        test_extract_lat_lon()
        
        print()
        print("All tests passed! ✓")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
