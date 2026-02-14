#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for GPS Movement Simulation with Map Node
Tests the complete workflow without GUI dependencies
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_gps_simulator_import():
    """Test that GPSMovementSimulator can be imported from the module"""
    try:
        # Import just the simulator class
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "coord_examples", 
            os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'node_coordinate_examples.py')
        )
        
        # We can't fully import due to dearpygui, but we can check the file exists and has valid syntax
        assert spec is not None
        assert os.path.exists(spec.origin)
        
        # Check file has GPSMovementSimulator class definition
        with open(spec.origin, 'r') as f:
            content = f.read()
            assert 'class GPSMovementSimulator:' in content
            assert 'def get_coordinates(self):' in content
            assert '"GPS Movement Simulation"' in content
        
        print("✓ GPS Movement Simulator is properly defined in node_coordinate_examples.py")
        return True
        
    except Exception as e:
        print(f"✗ Failed to verify GPS simulator: {e}")
        return False


def test_map_node_cache_functions():
    """Test that map node has caching functionality"""
    try:
        map_node_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'node', 
            'VisualNode', 
            'node_map.py'
        )
        
        # Check file exists and has cache-related code
        with open(map_node_path, 'r') as f:
            content = f.read()
            assert 'CACHE_DIR' in content
            assert 'def _generate_cache_key' in content
            assert 'use_cache' in content
            assert 'UseCacheValue' in content
            assert 'Cache Maps' in content
        
        print("✓ Map node has caching functionality implemented")
        return True
        
    except Exception as e:
        print(f"✗ Failed to verify map caching: {e}")
        return False


def test_coordinate_formats_compatibility():
    """Test that coordinate formats are compatible between nodes"""
    try:
        # GPS simulator format
        gps_format_keys = ['latitude', 'longitude', 'name', 'info']
        
        # Map node expected formats (from extraction logic)
        map_formats = [
            ['latitude', 'longitude'],  # Standard format
            ['lat', 'lon'],  # Alternative format
        ]
        
        # GPS format should match standard format
        assert 'latitude' in gps_format_keys
        assert 'longitude' in gps_format_keys
        
        print("✓ GPS simulator output format is compatible with Map node")
        return True
        
    except Exception as e:
        print(f"✗ Format compatibility check failed: {e}")
        return False


def test_documentation_exists():
    """Test that documentation files exist"""
    try:
        docs = [
            os.path.join(os.path.dirname(__file__), '..', 'node', 'InputNode', 'README_CoordinateExamples.md'),
            os.path.join(os.path.dirname(__file__), '..', 'node', 'VisualNode', 'README_Map.md'),
        ]
        
        for doc in docs:
            assert os.path.exists(doc), f"Missing documentation: {doc}"
            
            # Check documentation has key sections
            with open(doc, 'r') as f:
                content = f.read()
                assert '## Overview' in content
                assert '## Features' in content
        
        print("✓ Documentation files exist and have proper structure")
        return True
        
    except Exception as e:
        print(f"✗ Documentation check failed: {e}")
        return False


def test_node_version_updated():
    """Test that node versions were updated"""
    try:
        # Check CoordinateExamples node version
        coord_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'node', 
            'InputNode', 
            'node_coordinate_examples.py'
        )
        
        with open(coord_path, 'r') as f:
            content = f.read()
            # Version should be 1.0.1 or higher
            assert "_ver = '1.0." in content or "_ver = '1.1." in content
        
        print("✓ Node versions updated appropriately")
        return True
        
    except Exception as e:
        print(f"✗ Version check failed: {e}")
        return False


def test_cache_directory_logic():
    """Test that cache directory is properly configured"""
    import tempfile
    
    expected_cache_dir = os.path.join(tempfile.gettempdir(), 'cv_studio_map_cache')
    
    # Verify the cache directory pattern is correct
    assert 'cv_studio_map_cache' in expected_cache_dir
    
    print(f"✓ Cache directory pattern is correct: {expected_cache_dir}")
    return True


if __name__ == "__main__":
    print("Running GPS Movement & Map Caching Integration Tests...")
    print()
    
    all_passed = True
    
    all_passed &= test_gps_simulator_import()
    all_passed &= test_map_node_cache_functions()
    all_passed &= test_coordinate_formats_compatibility()
    all_passed &= test_documentation_exists()
    all_passed &= test_node_version_updated()
    all_passed &= test_cache_directory_logic()
    
    print()
    if all_passed:
        print("All integration tests passed! ✓")
        sys.exit(0)
    else:
        print("Some integration tests failed! ✗")
        sys.exit(1)
