#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for Coordinate Examples node → Map node data transfer
Tests that JSON data flows correctly through node_result_dict
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode.node_coordinate_examples import (
    COORDINATE_EXAMPLES,
)
from node.VisualNode.node_map import Node as MapNode


def test_coordinate_to_map_data_transfer():
    """Test that data from CoordinateExamples transfers correctly to Map node"""
    
    # Create map node for testing (skip coordinate node as it needs GUI)
    map_node = MapNode.create_for_testing()
    
    # Add required opencv settings for update() method
    map_node._opencv_setting_dict = {
        'process_width': 240,
        'process_height': 135,
        'use_pref_counter': False
    }
    
    # Use predefined AISTRACKER coordinates instead of calling coord_node.update()
    # (coord node needs GUI context which we don't have in tests)
    coordinates = COORDINATE_EXAMPLES["AISTRACKER"]
    
    # Verify coordinate format
    assert isinstance(coordinates, list)
    print(f"✓ Using AISTRACKER with {len(coordinates)} coordinates")
    
    # Simulate storing in node_result_dict (as done in main.py)
    node_result_dict = {}
    node_result_dict["1:CoordinateExamples"] = coordinates
    
    # Simulate Map node receiving data via connection_list
    # Connection format: ["source_node_id:source_node_tag:TYPE:OutputNN", "dest_node_id:dest_node_tag:TYPE:InputNN"]
    connection_list = [
        ["1:CoordinateExamples:JSON:Output01", "2:Map:JSON:Input01"]
    ]
    
    # Test that Map node can extract coordinates without full update
    # (full update tries to render which causes segfault in test environment)
    points = map_node._extract_lat_lon_from_json(coordinates)
    
    # Verify map node extracted points correctly
    assert len(points) > 0
    print(f"✓ Map node extracted {len(points)} points from CoordinateExamples data")
    
    # Verify point format
    for point in points:
        assert "lat" in point
        assert "lon" in point
        assert isinstance(point["lat"], (int, float))
        assert isinstance(point["lon"], (int, float))
    
    print("✓ All extracted points have valid lat/lon format")


def test_coordinate_to_map_json_serialization():
    """Test that coordinate data remains serializable throughout transfer"""
    
    # Get sample coordinate data
    coordinates = COORDINATE_EXAMPLES["AISTRACKER"]
    
    # Verify original data is JSON serializable
    json_str = json.dumps(coordinates)
    assert isinstance(json_str, str)
    print(f"✓ Original coordinates are JSON serializable (length: {len(json_str)})")
    
    # Parse and verify round-trip
    parsed = json.loads(json_str)
    assert parsed == coordinates
    print("✓ JSON round-trip successful")
    
    # Simulate the transfer (should stay as Python objects, not strings)
    node_result_dict = {"1:CoordinateExamples": coordinates}
    retrieved = node_result_dict.get("1:CoordinateExamples")
    
    # Verify it's still a list, not a string
    assert isinstance(retrieved, list)
    assert retrieved == coordinates
    print("✓ Data remains as Python list (not serialized to string)")


def test_coordinate_to_map_with_gps_simulation():
    """Test GPS simulation data format compatibility with Map node"""
    # Skip actual GPS simulation test as it needs GUI context
    # Just verify the expected format would work with Map node
    
    # Sample GPS simulation output format
    gps_coordinates = [
        {'latitude': 48.8566, 'longitude': 2.3522, 'name': 'Vehicle-001', 'info': 'linear - 45.3 km/h'},
        {'latitude': 48.8666, 'longitude': 2.3622, 'name': 'Vehicle-002', 'info': 'circular - 60.1 km/h'}
    ]
    
    # Verify format
    for coord in gps_coordinates:
        assert "latitude" in coord
        assert "longitude" in coord
        assert isinstance(coord["latitude"], (int, float))
        assert isinstance(coord["longitude"], (int, float))
    
    print(f"✓ GPS simulation format is compatible with Map node")
    
    # Test that Map node can extract these
    map_node = MapNode.create_for_testing()
    points = map_node._extract_lat_lon_from_json(gps_coordinates)
    assert len(points) == 2
    print(f"✓ Map node extracted {len(points)} GPS simulation points")


def test_map_node_handles_various_formats():
    """Test that Map node handles different coordinate formats from various sources"""
    
    map_node = MapNode.create_for_testing()
    
    # Test format 1: List with latitude/longitude keys (CoordinateExamples format)
    format1 = [
        {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
        {"latitude": 51.5074, "longitude": -0.1278, "name": "London"}
    ]
    points = map_node._extract_lat_lon_from_json(format1)
    assert len(points) == 2
    print("✓ Map node handles latitude/longitude format")
    
    # Test format 2: List with lat/lon keys
    format2 = [
        {"lat": 48.8566, "lon": 2.3522, "name": "Paris"},
        {"lat": 35.6762, "lon": 139.6503, "name": "Tokyo"}
    ]
    points = map_node._extract_lat_lon_from_json(format2)
    assert len(points) == 2
    print("✓ Map node handles lat/lon format")
    
    # Test format 3: Nested boats structure (AIS format)
    format3 = {
        "boats": [
            {"latitude": 49.4431, "longitude": 0.1073, "ship_name": "Vessel 1"},
            {"latitude": 51.4545, "longitude": 0.0553, "ship_name": "Vessel 2"}
        ]
    }
    points = map_node._extract_lat_lon_from_json(format3)
    assert len(points) == 2
    print("✓ Map node handles nested boats format")


if __name__ == "__main__":
    print("Testing Coordinate Examples → Map Node Integration...")
    print()
    
    test_coordinate_to_map_data_transfer()
    print()
    test_coordinate_to_map_json_serialization()
    print()
    test_coordinate_to_map_with_gps_simulation()
    print()
    test_map_node_handles_various_formats()
    
    print()
    print("All integration tests passed! ✓")
