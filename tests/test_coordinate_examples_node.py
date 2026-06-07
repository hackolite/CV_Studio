#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Coordinate Examples node
"""
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode.node_coordinate_examples import (
    Node as CoordinateExamplesNode,
    COORDINATE_EXAMPLES,
    get_example_names
)


def test_coordinate_examples_predefined_data():
    """Test that predefined coordinate examples are properly defined"""
    
    # Check that AISTRACKER example exists
    assert "AISTRACKER" in COORDINATE_EXAMPLES
    assert "None" in COORDINATE_EXAMPLES
    
    # Check AISTRACKER has the expected format
    ais_data = COORDINATE_EXAMPLES["AISTRACKER"]
    assert isinstance(ais_data, list)
    assert len(ais_data) > 0
    
    # Check each coordinate entry has required fields
    for coord in ais_data:
        assert "latitude" in coord
        assert "longitude" in coord
        assert isinstance(coord["latitude"], (int, float))
        assert isinstance(coord["longitude"], (int, float))
    
    print("✓ Predefined data structure test passed")


def test_coordinate_examples_none_option():
    """Test that None option returns empty list"""
    
    none_data = COORDINATE_EXAMPLES["None"]
    assert isinstance(none_data, list)
    assert len(none_data) == 0
    
    print("✓ None option returns empty list test passed")


def test_coordinate_examples_names():
    """Test get_example_names function"""
    
    names = get_example_names()
    assert isinstance(names, list)
    assert "None" in names
    assert "AISTRACKER" in names
    assert len(names) >= 2  # At least None and AISTRACKER
    
    print("✓ Example names list test passed")


def test_coordinate_examples_map_compatibility():
    """Test that coordinate examples are compatible with Map node format"""
    from node.VisualNode.node_map import Node as MapNode
    
    # Create a Map node for testing
    map_node = MapNode.create_for_testing()
    
    # Test each example for Map node compatibility
    for example_name, coordinates in COORDINATE_EXAMPLES.items():
        if example_name == "None":
            continue  # Skip empty data
        
        # The Map node expects data in specific formats
        # Test with list format (which CoordinateExamples outputs)
        points = map_node._extract_lat_lon_from_json(coordinates)
        
        assert len(points) > 0, f"Map node failed to extract points from {example_name}"
        
        # Verify extracted points have expected structure
        for point in points:
            assert "lat" in point
            assert "lon" in point
    
    print("✓ Map node compatibility test passed")


def test_coordinate_examples_aistracker_format():
    """Test AISTRACKER example matches expected JSON format"""
    
    ais_data = COORDINATE_EXAMPLES["AISTRACKER"]
    
    # The format should be a list of coordinate objects
    # compatible with [{"latitude":123, "longitude": 1536}]
    for coord in ais_data:
        # Must have latitude and longitude keys (not lat/lon)
        assert "latitude" in coord
        assert "longitude" in coord
        
    # Output should be JSON serializable
    json_str = json.dumps(ais_data)
    assert isinstance(json_str, str)
    
    # Parse back to verify
    parsed = json.loads(json_str)
    assert parsed == ais_data
    
    print("✓ AISTRACKER format matches [{'latitude':123, 'longitude': 1536}] test passed")


def test_coordinate_examples_all_examples_have_coordinates():
    """Test that all non-None examples have valid coordinates"""
    
    for name, data in COORDINATE_EXAMPLES.items():
        if name == "None":
            assert len(data) == 0
            continue
            
        assert len(data) > 0, f"Example {name} has no coordinates"
        
        for i, coord in enumerate(data):
            # Validate latitude range (-90 to 90)
            assert -90 <= coord["latitude"] <= 90, f"Invalid latitude in {name}[{i}]"
            # Validate longitude range (-180 to 180)
            assert -180 <= coord["longitude"] <= 180, f"Invalid longitude in {name}[{i}]"
    
    print("✓ All examples have valid coordinates test passed")


def test_gps_simulation_requires_start_button(monkeypatch):
    """The GPS Movement Simulation should stay idle until Start is pressed."""
    from node.InputNode import node_coordinate_examples as nce

    node = CoordinateExamplesNode()
    node_id = 999

    # Force the dropdown to report GPS Movement Simulation as selected
    monkeypatch.setattr(nce, "dpg_get_value", lambda tag: nce.GPS_SIMULATION_NAME)

    # Before pressing Start: no coordinates should be emitted and the
    # simulator must not be initialised yet.
    result = node.update(node_id, [], {}, {}, {})
    assert result["json"] == []
    assert node.gps_simulator is None

    # Simulate pressing Start: trip begins, simulator initialised, points emitted.
    node.is_started = True
    result = node.update(node_id, [], {}, {}, {})
    assert isinstance(result["json"], list)
    assert len(result["json"]) > 0
    assert node.gps_simulator is not None

    # Simulate pressing Stop: trip halts again and no coordinates are returned.
    node.is_started = False
    node.gps_simulator = None
    node.last_update_time = None
    node.last_coordinates = []
    result = node.update(node_id, [], {}, {}, {})
    assert result["json"] == []
    print("✓ GPS simulation Start/Stop gating test passed")


if __name__ == "__main__":
    print("Testing Coordinate Examples Node...")
    print()
    
    test_coordinate_examples_predefined_data()
    test_coordinate_examples_none_option()
    test_coordinate_examples_names()
    test_coordinate_examples_map_compatibility()
    test_coordinate_examples_aistracker_format()
    test_coordinate_examples_all_examples_have_coordinates()
    
    print()
    print("All tests passed! ✓")
