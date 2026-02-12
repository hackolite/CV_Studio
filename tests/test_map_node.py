#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Map VisualNode
Tests the map visualization node with various JSON structures
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_map import Node as MapNode


def test_extract_coordinates_ais_format():
    """Test coordinate extraction from AIS boat data format"""
    node = MapNode()
    
    # AIS format with boats array
    ais_data = {
        "boats": [
            {"mmsi": "123", "latitude": 40.7128, "longitude": -74.0060, "ship_name": "Ship1"},
            {"mmsi": "456", "latitude": 40.7580, "longitude": -73.9855, "ship_name": "Ship2"},
        ],
        "count": 2
    }
    
    coords = node.extract_coordinates(ais_data)
    
    assert len(coords) == 2, f"Expected 2 coordinates, got {len(coords)}"
    assert coords[0] == (40.7128, -74.0060), f"First coordinate mismatch: {coords[0]}"
    assert coords[1] == (40.7580, -73.9855), f"Second coordinate mismatch: {coords[1]}"
    
    print("✓ AIS format test passed")


def test_extract_coordinates_simple_format():
    """Test coordinate extraction from simple lat/lon format"""
    node = MapNode()
    
    # Simple format
    simple_data = {"latitude": 48.8566, "longitude": 2.3522}
    
    coords = node.extract_coordinates(simple_data)
    
    assert len(coords) == 1, f"Expected 1 coordinate, got {len(coords)}"
    assert coords[0] == (48.8566, 2.3522), f"Coordinate mismatch: {coords[0]}"
    
    print("✓ Simple format test passed")


def test_extract_coordinates_lat_lon_format():
    """Test coordinate extraction from lat/lon format"""
    node = MapNode()
    
    # lat/lon format
    data = {"lat": 51.5074, "lon": -0.1278}
    
    coords = node.extract_coordinates(data)
    
    assert len(coords) == 1, f"Expected 1 coordinate, got {len(coords)}"
    assert coords[0] == (51.5074, -0.1278), f"Coordinate mismatch: {coords[0]}"
    
    print("✓ lat/lon format test passed")


def test_extract_coordinates_list_format():
    """Test coordinate extraction from list of objects"""
    node = MapNode()
    
    # List format
    list_data = [
        {"latitude": 40.7128, "longitude": -74.0060},
        {"latitude": 34.0522, "longitude": -118.2437},
    ]
    
    coords = node.extract_coordinates(list_data)
    
    assert len(coords) == 2, f"Expected 2 coordinates, got {len(coords)}"
    print("✓ List format test passed")


def test_calculate_bounds():
    """Test bounds calculation"""
    node = MapNode()
    
    coords = [
        (40.7128, -74.0060),  # New York
        (34.0522, -118.2437),  # Los Angeles
    ]
    
    min_lat, max_lat, min_lon, max_lon = node.calculate_bounds(coords)
    
    # Check that bounds encompass all points with padding
    assert min_lat < 34.0522, f"min_lat should be less than 34.0522, got {min_lat}"
    assert max_lat > 40.7128, f"max_lat should be greater than 40.7128, got {max_lat}"
    assert min_lon < -118.2437, f"min_lon should be less than -118.2437, got {min_lon}"
    assert max_lon > -74.0060, f"max_lon should be greater than -74.0060, got {max_lon}"
    
    print("✓ Bounds calculation test passed")


def test_calculate_bounds_empty():
    """Test bounds calculation with no coordinates"""
    node = MapNode()
    
    bounds = node.calculate_bounds([])
    
    # Should return world bounds
    assert bounds == (-90, 90, -180, 180), f"Expected world bounds, got {bounds}"
    
    print("✓ Empty bounds test passed")


def test_render_map():
    """Test map rendering"""
    node = MapNode(opencv_setting_dict={'process_width': 640, 'process_height': 480})
    
    coords = [
        (40.7128, -74.0060),  # New York
        (34.0522, -118.2437),  # Los Angeles
    ]
    
    bounds = node.calculate_bounds(coords)
    
    # Render map
    image = node.render_map(
        coordinates=coords,
        bounds=bounds,
        width=640,
        height=480,
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    
    # Check image properties
    assert image.shape == (480, 640, 3), f"Expected shape (480, 640, 3), got {image.shape}"
    assert image.dtype == 'uint8', f"Expected uint8 dtype, got {image.dtype}"
    
    print("✓ Map rendering test passed")


def test_json_string_input():
    """Test that the node can handle JSON as string"""
    node = MapNode()
    
    json_string = json.dumps({
        "boats": [
            {"latitude": 40.7128, "longitude": -74.0060},
        ]
    })
    
    coords = node.extract_coordinates(json_string)
    
    assert len(coords) == 1, f"Expected 1 coordinate, got {len(coords)}"
    print("✓ JSON string input test passed")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Map VisualNode")
    print("=" * 60)
    print()
    
    try:
        test_extract_coordinates_ais_format()
        test_extract_coordinates_simple_format()
        test_extract_coordinates_lat_lon_format()
        test_extract_coordinates_list_format()
        test_calculate_bounds()
        test_calculate_bounds_empty()
        test_render_map()
        test_json_string_input()
        
        print()
        print("=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
