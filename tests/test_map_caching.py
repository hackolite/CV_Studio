#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Map node caching functionality
Tests the cache system without requiring dearpygui
"""
import os
import sys
import tempfile
import hashlib
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mock the cache directory
CACHE_DIR = os.path.join(tempfile.gettempdir(), 'cv_studio_map_cache_test')
os.makedirs(CACHE_DIR, exist_ok=True)


def generate_cache_key(points, zoom_level, size_factor):
    """
    Generate a cache key based on map parameters.
    """
    # Sort points to ensure consistent ordering
    sorted_points = sorted(points, key=lambda p: (p['lat'], p['lon']))
    
    # Build key from essential data
    key_data = {
        'points': [(p['lat'], p['lon']) for p in sorted_points[:100]],
        'zoom': zoom_level,
        'size': round(size_factor, 2),
    }
    
    # Generate hash
    key_str = json.dumps(key_data, sort_keys=True)
    cache_key = hashlib.md5(key_str.encode()).hexdigest()
    
    return cache_key


def test_cache_key_generation():
    """Test that cache keys are generated consistently"""
    points = [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'info': ''},
        {'lat': 51.5074, 'lon': -0.1278, 'name': 'London', 'info': ''},
    ]
    
    key1 = generate_cache_key(points, zoom_level=10, size_factor=1.0)
    key2 = generate_cache_key(points, zoom_level=10, size_factor=1.0)
    
    # Same parameters should produce same key
    assert key1 == key2
    
    # Different zoom should produce different key
    key3 = generate_cache_key(points, zoom_level=12, size_factor=1.0)
    assert key1 != key3
    
    # Different size should produce different key
    key4 = generate_cache_key(points, zoom_level=10, size_factor=2.0)
    assert key1 != key4
    
    print("✓ Cache key generation test passed")


def test_cache_key_order_independence():
    """Test that point order doesn't affect cache key"""
    points1 = [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'info': ''},
        {'lat': 51.5074, 'lon': -0.1278, 'name': 'London', 'info': ''},
    ]
    
    points2 = [
        {'lat': 51.5074, 'lon': -0.1278, 'name': 'London', 'info': ''},
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'info': ''},
    ]
    
    key1 = generate_cache_key(points1, zoom_level=10, size_factor=1.0)
    key2 = generate_cache_key(points2, zoom_level=10, size_factor=1.0)
    
    # Different order should produce same key (sorted internally)
    assert key1 == key2
    
    print("✓ Cache key order independence test passed")


def test_cache_directory_creation():
    """Test that cache directory exists"""
    assert os.path.exists(CACHE_DIR)
    assert os.path.isdir(CACHE_DIR)
    
    print(f"✓ Cache directory creation test passed ({CACHE_DIR})")


def test_cache_file_naming():
    """Test cache file naming convention"""
    points = [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'info': ''},
    ]
    
    cache_key = generate_cache_key(points, zoom_level=10, size_factor=1.0)
    cache_filename = f"map_{cache_key}.html"
    
    # Validate filename format
    assert cache_filename.startswith("map_")
    assert cache_filename.endswith(".html")
    assert len(cache_key) == 32  # MD5 hash length
    
    print("✓ Cache file naming test passed")


def test_cache_with_different_data():
    """Test that different data produces different cache keys"""
    points1 = [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'info': ''},
    ]
    
    points2 = [
        {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York', 'info': ''},
    ]
    
    key1 = generate_cache_key(points1, zoom_level=10, size_factor=1.0)
    key2 = generate_cache_key(points2, zoom_level=10, size_factor=1.0)
    
    assert key1 != key2
    
    print("✓ Cache with different data test passed")


def test_cache_with_many_points():
    """Test cache key generation with many points"""
    # Generate 200 points
    points = []
    for i in range(200):
        points.append({
            'lat': 48.0 + i * 0.01,
            'lon': 2.0 + i * 0.01,
            'name': f'Point-{i}',
            'info': ''
        })
    
    # Should only use first 100 points for key
    key = generate_cache_key(points, zoom_level=10, size_factor=1.0)
    
    assert isinstance(key, str)
    assert len(key) == 32
    
    print("✓ Cache with many points test passed")


def test_cache_simulation_workflow():
    """Test a complete caching workflow simulation"""
    # Simulate GPS movement data
    points = [
        {'lat': 48.8566, 'lon': 2.3522, 'name': 'Vehicle-001', 'info': 'linear - 45.5 km/h'},
        {'lat': 48.8570, 'lon': 2.3530, 'name': 'Vehicle-002', 'info': 'circular - 60.2 km/h'},
        {'lat': 48.8560, 'lon': 2.3515, 'name': 'Vehicle-003', 'info': 'random_walk - 30.8 km/h'},
    ]
    
    # Generate cache key
    cache_key = generate_cache_key(points, zoom_level=12, size_factor=1.5)
    cache_path = os.path.join(CACHE_DIR, f"map_{cache_key}.html")
    
    # Simulate cache creation
    if not os.path.exists(cache_path):
        with open(cache_path, 'w') as f:
            f.write("<html><body>Mock map content</body></html>")
        print(f"  Created cache file: {cache_path}")
    
    # Verify cache file exists
    assert os.path.exists(cache_path)
    
    # Simulate cache retrieval
    with open(cache_path, 'r') as f:
        content = f.read()
    
    assert len(content) > 0
    assert "Mock map content" in content
    
    # Clean up
    os.remove(cache_path)
    
    print("✓ Cache simulation workflow test passed")


if __name__ == "__main__":
    print("Testing Map Caching Functionality...")
    print()
    
    test_cache_key_generation()
    test_cache_key_order_independence()
    test_cache_directory_creation()
    test_cache_file_naming()
    test_cache_with_different_data()
    test_cache_with_many_points()
    test_cache_simulation_workflow()
    
    # Clean up test cache directory
    import shutil
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    
    print()
    print("All map caching tests passed! ✓")
