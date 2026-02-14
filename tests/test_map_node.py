#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Map visualization node
"""
import json
import os
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode.node_map import Node as MapNode


def test_map_node_extract_lat_lon():
    """Test extracting latitude and longitude from various JSON structures"""
    # Use factory method for clean test initialization
    node = MapNode.create_for_testing()
    
    # Test AIS boat data structure
    ais_data = {
        "boats": [
            {
                "mmsi": "123456789",
                "ship_name": "Test Ship",
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            {
                "mmsi": "987654321",
                "ship_name": "Another Ship",
                "latitude": 34.0522,
                "longitude": -118.2437
            }
        ]
    }
    
    points = node._extract_lat_lon_from_json(ais_data)
    assert len(points) == 2
    assert points[0]['lat'] == 40.7128
    assert points[0]['lon'] == -74.0060
    assert points[0]['name'] == "Test Ship"
    assert points[1]['lat'] == 34.0522
    assert points[1]['lon'] == -118.2437
    
    print("✓ AIS data structure extraction test passed")
    
    # Test list of points
    list_data = [
        {"latitude": 51.5074, "longitude": -0.1278, "name": "London"},
        {"latitude": 48.8566, "longitude": 2.3522, "name": "Paris"}
    ]
    
    points = node._extract_lat_lon_from_json(list_data)
    assert len(points) == 2
    assert points[0]['name'] == "London"
    assert points[1]['name'] == "Paris"
    
    print("✓ List data structure extraction test passed")
    
    # Test single point with lat/lon keys
    single_point = [
        {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo"}
    ]
    
    points = node._extract_lat_lon_from_json(single_point)
    assert len(points) == 1
    assert points[0]['lat'] == 35.6762
    assert points[0]['lon'] == 139.6503
    
    print("✓ Single point extraction test passed")


def test_map_node_generate_map():
    """Test map generation with contextily"""
    # This test is updated for contextily-based implementation
    # The old folium-based _generate_map method has been removed
    
    # Use factory method for clean test initialization
    node = MapNode.create_for_testing()
    
    points = [
        {"lat": 40.7128, "lon": -74.0060, "name": "New York", "info": "123456"},
        {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles", "info": "789012"}
    ]
    
    # Test that we can create a preview image (which uses contextily)
    import numpy as np
    preview = node._create_preview_image(points, 320, 240)
    
    assert preview is not None
    assert isinstance(preview, np.ndarray)
    assert preview.shape == (240, 320, 3)
    assert preview.dtype == np.uint8
    
    # Check that image is not completely black
    assert np.any(preview > 0)
    
    print("✓ Map generation test passed (using contextily)")


def test_map_node_preview_image():
    """Test preview image generation"""
    import numpy as np
    
    # Use factory method for clean test initialization
    node = MapNode.create_for_testing()
    
    points = [
        {"lat": 40.7128, "lon": -74.0060, "name": "New York", "info": ""},
        {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles", "info": ""},
        {"lat": 41.8781, "lon": -87.6298, "name": "Chicago", "info": ""}
    ]
    
    preview = node._create_preview_image(points, 240, 135)
    
    assert preview is not None
    assert preview.shape == (135, 240, 3)
    assert preview.dtype == np.uint8
    
    # Check that image is not completely black
    assert np.any(preview > 0)
    
    print("✓ Preview image generation test passed")


def test_map_node_empty_data():
    """Test handling of empty data"""
    # Use factory method for clean test initialization
    node = MapNode.create_for_testing()
    
    # Empty dict
    points = node._extract_lat_lon_from_json({})
    assert len(points) == 0
    
    # Empty list
    points = node._extract_lat_lon_from_json([])
    assert len(points) == 0
    
    # Dict without lat/lon
    points = node._extract_lat_lon_from_json({"name": "test", "value": 123})
    assert len(points) == 0
    
    print("✓ Empty data handling test passed")


def test_map_node_coordinate_conversion():
    """Test Web Mercator coordinate conversion"""
    # Use factory method for clean test initialization
    node = MapNode.create_for_testing()
    
    # Test New York City
    lat, lon = 40.7128, -74.0060
    x, y = node.lat_lon_to_web_mercator(lat, lon)
    
    # Convert back
    lat2, lon2 = node.web_mercator_to_lat_lon(x, y)
    
    # Check accuracy (should be within 0.0001 degrees)
    assert abs(lat - lat2) < 0.0001, f"Latitude conversion error: {lat} != {lat2}"
    assert abs(lon - lon2) < 0.0001, f"Longitude conversion error: {lon} != {lon2}"
    
    print("✓ Coordinate conversion test passed")


if __name__ == "__main__":
    print("Testing Map Node...")
    print()
    
    test_map_node_extract_lat_lon()
    test_map_node_generate_map()
    test_map_node_preview_image()
    test_map_node_empty_data()
    test_map_node_coordinate_conversion()
    
    print()
    print("All tests passed! ✓")
