#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for walking simulation T0/T1 position logic

This test validates:
1. T0 (initial position) is correctly recorded
2. T1 (position after 1 second) is calculated based on 4 km/h walking speed
3. The distance traveled matches the expected walking speed
"""
import math
import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode.node_coordinate_examples import GPSMovementSimulator


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two lat/lon points using Haversine formula.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def test_t0_recording():
    """Test that T0 positions are correctly recorded."""
    print("\n=== Test: T0 Recording ===")
    
    # Create simulator
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    
    # Check that T0 positions were recorded
    t0_positions = sim.get_t0_positions()
    assert len(t0_positions) == 1, "Should have 1 T0 position recorded"
    
    # Check T0 position has required fields
    t0 = t0_positions[0]
    assert 'lat' in t0, "T0 should have lat field"
    assert 'lon' in t0, "T0 should have lon field"
    assert 'time' in t0, "T0 should have time field"
    
    # Check T0 position matches initial object position
    obj = sim.objects[0]
    assert abs(obj['lat'] - t0['lat']) < 0.0001, "T0 lat should match initial position"
    assert abs(obj['lon'] - t0['lon']) < 0.0001, "T0 lon should match initial position"
    
    print(f"✓ T0 position recorded: lat={t0['lat']:.6f}, lon={t0['lon']:.6f}")
    print("✓ T0 recording test passed")


def test_t1_calculation_linear():
    """Test that T1 position is correctly calculated for linear movement."""
    print("\n=== Test: T1 Calculation (Linear Movement) ===")
    
    # Create simulator with 1 object
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    
    # Force linear pattern for predictable testing
    sim.objects[0]['pattern'] = 'linear'
    sim.objects[0]['direction'] = 0  # Move north
    
    # Get T0 position
    t0_positions = sim.get_t0_positions()
    t0 = t0_positions[0]
    t0_lat = t0['lat']
    t0_lon = t0['lon']
    
    print(f"T0 position: lat={t0_lat:.6f}, lon={t0_lon:.6f}")
    
    # Simulate 1 second of movement (T1)
    sim.update_positions(time_elapsed=1.0)
    
    # Get T1 position
    obj = sim.objects[0]
    t1_lat = obj['lat']
    t1_lon = obj['lon']
    
    print(f"T1 position: lat={t1_lat:.6f}, lon={t1_lon:.6f}")
    
    # Calculate distance traveled
    distance_km = calculate_distance_km(t0_lat, t0_lon, t1_lat, t1_lon)
    
    # At 4 km/h, in 1 second, the object should travel 4000m / 3600s = 1.111 meters
    expected_distance_m = 4000.0 / 3600.0  # meters
    actual_distance_m = distance_km * 1000.0
    
    print(f"Distance traveled: {actual_distance_m:.3f}m (expected: {expected_distance_m:.3f}m)")
    
    # Allow 10% tolerance for floating point and approximation errors
    tolerance = expected_distance_m * 0.1
    assert abs(actual_distance_m - expected_distance_m) < tolerance, \
        f"Distance should be approximately {expected_distance_m:.3f}m, got {actual_distance_m:.3f}m"
    
    print("✓ T1 calculation test passed")


def test_walking_speed_4kmh():
    """Test that walking speed is maintained at 4 km/h over time."""
    print("\n=== Test: Walking Speed 4 km/h ===")
    
    # Create simulator
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    
    # Force linear pattern
    sim.objects[0]['pattern'] = 'linear'
    sim.objects[0]['direction'] = math.pi / 2  # Move east
    
    # Get T0
    t0 = sim.get_t0_positions()[0]
    t0_lat = t0['lat']
    t0_lon = t0['lon']
    
    # Test at different time intervals
    test_times = [1, 5, 10, 30]  # seconds
    
    for t in test_times:
        # Reset simulator for each test
        sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
        sim.objects[0]['pattern'] = 'linear'
        sim.objects[0]['direction'] = math.pi / 2
        
        # Get fresh T0
        t0 = sim.get_t0_positions()[0]
        t0_lat = t0['lat']
        t0_lon = t0['lon']
        
        # Simulate t seconds
        sim.update_positions(time_elapsed=float(t))
        
        # Get position at time t
        obj = sim.objects[0]
        t_lat = obj['lat']
        t_lon = obj['lon']
        
        # Calculate distance
        distance_km = calculate_distance_km(t0_lat, t0_lon, t_lat, t_lon)
        
        # Expected distance at 4 km/h
        expected_distance_km = (4.0 / 3600.0) * t
        
        print(f"After {t}s: distance={distance_km*1000:.1f}m (expected: {expected_distance_km*1000:.1f}m)")
        
        # Allow 20% tolerance for wrapping and approximation
        tolerance = expected_distance_km * 0.2
        assert abs(distance_km - expected_distance_km) < tolerance, \
            f"At t={t}s, distance should be ~{expected_distance_km:.3f}km, got {distance_km:.3f}km"
    
    print("✓ Walking speed 4 km/h test passed")


def test_multiple_objects_t0():
    """Test T0 recording for multiple objects."""
    print("\n=== Test: Multiple Objects T0 Recording ===")
    
    # Create simulator with multiple objects
    num_objects = 5
    sim = GPSMovementSimulator(num_objects=num_objects, center_lat=48.8566, center_lon=2.3522)
    
    # Check all T0 positions
    t0_positions = sim.get_t0_positions()
    assert len(t0_positions) == num_objects, f"Should have {num_objects} T0 positions"
    
    # Each object should have unique initial position
    positions_set = set()
    for i in range(num_objects):
        t0 = t0_positions[i]
        pos_tuple = (round(t0['lat'], 6), round(t0['lon'], 6))
        positions_set.add(pos_tuple)
    
    # All positions should be different (with high probability)
    assert len(positions_set) >= num_objects - 1, "Objects should have different initial positions"
    
    print(f"✓ {num_objects} objects, all with unique T0 positions recorded")
    print("✓ Multiple objects T0 test passed")


def test_t0_immutable():
    """Test that T0 positions remain unchanged during simulation."""
    print("\n=== Test: T0 Immutability ===")
    
    # Create simulator
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    
    # Get initial T0
    t0_initial = sim.get_t0_positions()[0].copy()
    
    # Simulate movement
    sim.update_positions(time_elapsed=10.0)
    
    # Get T0 again
    t0_after = sim.get_t0_positions()[0]
    
    # T0 should not have changed
    assert t0_after['lat'] == t0_initial['lat'], "T0 lat should not change"
    assert t0_after['lon'] == t0_initial['lon'], "T0 lon should not change"
    assert t0_after['time'] == t0_initial['time'], "T0 time should not change"
    
    print("✓ T0 position remains immutable during simulation")
    print("✓ T0 immutability test passed")


if __name__ == "__main__":
    print("Testing Walking Simulation T0/T1 Logic...")
    print("=" * 60)
    
    try:
        test_t0_recording()
        test_t1_calculation_linear()
        test_walking_speed_4kmh()
        test_multiple_objects_t0()
        test_t0_immutable()
        
        print("\n" + "=" * 60)
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
