#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple test for walking simulation T0/T1 position logic (no dependencies)

This test validates the core GPSMovementSimulator class without requiring
dearpygui or other node dependencies.
"""
import math
import time
import random


# Simplified GPSMovementSimulator for testing (extracted from the node)
class GPSMovementSimulator:
    """
    Simulates GPS movement for various objects.
    """
    
    def __init__(self, num_objects=5, center_lat=48.8566, center_lon=2.3522):
        self.num_objects = num_objects
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.objects = []
        self.start_time = time.time()
        self.t0_positions = {}
        self._initialize_objects()
    
    def _initialize_objects(self):
        """Initialize objects with random starting positions."""
        random.seed(42)
        
        for i in range(self.num_objects):
            radius_km = random.uniform(0.5, 10)
            angle = random.uniform(0, 2 * math.pi)
            
            lat_offset = (radius_km / 111.0) * math.cos(angle)
            lon_offset = (radius_km / (111.0 * math.cos(math.radians(self.center_lat)))) * math.sin(angle)
            
            initial_lat = self.center_lat + lat_offset
            initial_lon = self.center_lon + lon_offset
            
            obj = {
                'id': i,
                'name': f'Vehicle-{i+1:03d}',
                'lat': initial_lat,
                'lon': initial_lon,
                'speed_kmh': 4,
                'direction': random.uniform(0, 2 * math.pi),
                'pattern': random.choice(['linear', 'circular', 'random_walk']),
            }
            self.objects.append(obj)
            
            self.t0_positions[i] = {
                'lat': initial_lat,
                'lon': initial_lon,
                'time': self.start_time
            }
            print(f"GPS Simulator: Object {i} T0 position recorded - "
                  f"lat={initial_lat:.6f}, lon={initial_lon:.6f} at t={0:.1f}s")
    
    def update_positions(self, time_elapsed=None):
        """Update positions based on elapsed time."""
        if time_elapsed is None:
            time_elapsed = time.time() - self.start_time
        
        for obj in self.objects:
            distance_km = (obj['speed_kmh'] / 3600.0) * time_elapsed
            
            if obj['pattern'] == 'linear':
                self._update_linear(obj, time_elapsed, distance_km)
    
    def _update_linear(self, obj, time_elapsed, distance_km):
        """Update position with linear movement."""
        t0 = self.t0_positions.get(obj['id'])
        if not t0:
            t0 = {'lat': obj['lat'], 'lon': obj['lon']}
        
        lat_change = (distance_km / 111.0) * math.cos(obj['direction'])
        lon_change = (distance_km / (111.0 * math.cos(math.radians(t0['lat'])))) * math.sin(obj['direction'])
        
        new_lat = t0['lat'] + lat_change
        new_lon = t0['lon'] + lon_change
        
        # Only apply wrapping if too far from center
        base_lat = self.center_lat
        base_lon = self.center_lon
        distance_from_center = math.sqrt((new_lat - base_lat)**2 + (new_lon - base_lon)**2)
        
        if distance_from_center > 0.15:
            obj['lat'] = base_lat + ((new_lat - base_lat) % 0.2) - 0.1
            obj['lon'] = base_lon + ((new_lon - base_lon) % 0.2) - 0.1
        else:
            obj['lat'] = new_lat
            obj['lon'] = new_lon
    
    def get_t0_positions(self):
        """Get T0 positions."""
        return self.t0_positions.copy()


def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance using Haversine formula."""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def test_t0_recording():
    """Test T0 recording.
    
    Note: get_t0_positions() returns a dict mapping object ID to T0 position.
    We access it with t0_positions[0] where 0 is the object ID.
    """
    print("\n=== Test: T0 Recording ===")
    
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    t0_positions = sim.get_t0_positions()
    
    assert len(t0_positions) == 1
    t0 = t0_positions[0]  # Access by object ID (0)
    assert 'lat' in t0 and 'lon' in t0 and 'time' in t0
    
    obj = sim.objects[0]
    assert abs(obj['lat'] - t0['lat']) < 0.0001
    assert abs(obj['lon'] - t0['lon']) < 0.0001
    
    print(f"✓ T0 position: lat={t0['lat']:.6f}, lon={t0['lon']:.6f}")
    print("✓ T0 recording test passed")


def test_t1_calculation():
    """Test T1 calculation."""
    print("\n=== Test: T1 Calculation ===")
    
    sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
    sim.objects[0]['pattern'] = 'linear'
    sim.objects[0]['direction'] = 0
    
    t0 = sim.get_t0_positions()[0]
    t0_lat, t0_lon = t0['lat'], t0['lon']
    print(f"T0 position: lat={t0_lat:.6f}, lon={t0_lon:.6f}")
    
    sim.update_positions(time_elapsed=1.0)
    
    obj = sim.objects[0]
    t1_lat, t1_lon = obj['lat'], obj['lon']
    print(f"T1 position: lat={t1_lat:.6f}, lon={t1_lon:.6f}")
    
    distance_km = calculate_distance_km(t0_lat, t0_lon, t1_lat, t1_lon)
    expected_distance_m = 4000.0 / 3600.0
    actual_distance_m = distance_km * 1000.0
    
    print(f"Distance: {actual_distance_m:.3f}m (expected: {expected_distance_m:.3f}m)")
    
    tolerance = expected_distance_m * 0.15
    assert abs(actual_distance_m - expected_distance_m) < tolerance
    
    print("✓ T1 calculation test passed")


def test_walking_speed():
    """Test 4 km/h walking speed."""
    print("\n=== Test: Walking Speed 4 km/h ===")
    
    for t in [1, 5, 10]:
        sim = GPSMovementSimulator(num_objects=1, center_lat=48.8566, center_lon=2.3522)
        sim.objects[0]['pattern'] = 'linear'
        sim.objects[0]['direction'] = math.pi / 2
        
        t0 = sim.get_t0_positions()[0]
        sim.update_positions(time_elapsed=float(t))
        
        obj = sim.objects[0]
        distance_km = calculate_distance_km(t0['lat'], t0['lon'], obj['lat'], obj['lon'])
        expected_km = (4.0 / 3600.0) * t
        
        print(f"After {t}s: {distance_km*1000:.1f}m (expected: {expected_km*1000:.1f}m)")
        
        tolerance = expected_km * 0.2
        assert abs(distance_km - expected_km) < tolerance
    
    print("✓ Walking speed test passed")


if __name__ == "__main__":
    print("Testing Walking Simulation T0/T1 Logic...")
    print("=" * 60)
    
    try:
        test_t0_recording()
        test_t1_calculation()
        test_walking_speed()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
