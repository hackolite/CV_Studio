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
    # Create a minimal node instance by mocking the _opencv_setting_dict
    node = object.__new__(MapNode)
    node._opencv_setting_dict = {}
    node.last_map_path = None
    node.point_data = []
    
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
    """Test map generation with folium"""
    try:
        import folium
    except ImportError:
        print("⚠ Folium not installed, skipping map generation test")
        return
    
    # Create a minimal node instance
    node = object.__new__(MapNode)
    node._opencv_setting_dict = {}
    node.last_map_path = None
    node.point_data = []
    
    points = [
        {"lat": 40.7128, "lon": -74.0060, "name": "New York", "info": "123456"},
        {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles", "info": "789012"}
    ]
    
    map_path = node._generate_map(points, zoom_level=6, size_factor=1.0)
    
    assert map_path is not None
    assert os.path.exists(map_path)
    assert map_path.endswith('.html')
    
    # Check file content
    with open(map_path, 'r') as f:
        content = f.read()
        assert 'leaflet' in content.lower()
        assert 'OpenStreetMap' in content
    
    print(f"✓ Map generation test passed (saved to {map_path})")
    
    # Clean up
    # os.remove(map_path)


def test_map_node_preview_image():
    """Test preview image generation"""
    import numpy as np
    
    # Create a minimal node instance
    node = object.__new__(MapNode)
    node._opencv_setting_dict = {}
    node.last_map_path = None
    node.point_data = []
    
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
    # Create a minimal node instance
    node = object.__new__(MapNode)
    node._opencv_setting_dict = {}
    node.last_map_path = None
    node.point_data = []
    
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


if __name__ == "__main__":
    print("Testing Map Node...")
    print()
    
    test_map_node_extract_lat_lon()
    test_map_node_generate_map()
    test_map_node_preview_image()
    test_map_node_empty_data()
    
    print()
    print("All tests passed! ✓")
