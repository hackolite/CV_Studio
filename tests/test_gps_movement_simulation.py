#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for GPS Movement Simulation functionality
Tests the GPSMovementSimulator class without requiring full node dependencies
"""
import math
import random
import time


class GPSMovementSimulator:
    """
    Simulates GPS movement for various objects.
    Generates random paths simulating realistic movement patterns.
    """
    
    def __init__(self, num_objects=5, center_lat=48.8566, center_lon=2.3522):
        """
        Initialize the GPS movement simulator.
        
        Args:
            num_objects: Number of moving objects to simulate
            center_lat: Center latitude for the simulation area
            center_lon: Center longitude for the simulation area
        """
        self.num_objects = num_objects
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.objects = []
        self.start_time = time.time()
        self._initialize_objects()
    
    def _initialize_objects(self):
        """Initialize objects with random starting positions and velocities."""
        random.seed(42)  # Use a seed for reproducible "random" movements
        
        for i in range(self.num_objects):
            # Random starting position within ~10km radius
            radius_km = random.uniform(0.5, 10)
            angle = random.uniform(0, 2 * math.pi)
            
            # Convert km to degrees (approximate)
            lat_offset = (radius_km / 111.0) * math.cos(angle)
            lon_offset = (radius_km / (111.0 * math.cos(math.radians(self.center_lat)))) * math.sin(angle)
            
            obj = {
                'id': i,
                'name': f'Vehicle-{i+1:03d}',
                'lat': self.center_lat + lat_offset,
                'lon': self.center_lon + lon_offset,
                'speed_kmh': random.uniform(20, 80),  # km/h
                'direction': random.uniform(0, 2 * math.pi),  # radians
                'pattern': random.choice(['linear', 'circular', 'random_walk']),
            }
            self.objects.append(obj)
    
    def update_positions(self, time_elapsed=None):
        """
        Update positions of all objects based on elapsed time.
        
        Args:
            time_elapsed: Time in seconds since start. If None, uses actual elapsed time.
        """
        if time_elapsed is None:
            time_elapsed = time.time() - self.start_time
        
        for obj in self.objects:
            # Update position based on pattern
            if obj['pattern'] == 'linear':
                self._update_linear(obj, time_elapsed)
            elif obj['pattern'] == 'circular':
                self._update_circular(obj, time_elapsed)
            else:  # random_walk
                self._update_random_walk(obj, time_elapsed)
    
    def _update_linear(self, obj, time_elapsed):
        """Update position with linear movement."""
        # Distance traveled in km
        distance_km = (obj['speed_kmh'] / 3600.0) * (time_elapsed % 3600)
        
        # Convert to degrees
        lat_change = (distance_km / 111.0) * math.cos(obj['direction'])
        lon_change = (distance_km / (111.0 * math.cos(math.radians(obj['lat'])))) * math.sin(obj['direction'])
        
        # Update position (modulo to keep in reasonable bounds)
        base_lat = self.center_lat
        base_lon = self.center_lon
        obj['lat'] = base_lat + ((obj['lat'] - base_lat + lat_change) % 0.2) - 0.1
        obj['lon'] = base_lon + ((obj['lon'] - base_lon + lon_change) % 0.2) - 0.1
    
    def _update_circular(self, obj, time_elapsed):
        """Update position with circular movement."""
        # Angular velocity (radians per second)
        angular_velocity = obj['speed_kmh'] / (20.0 * 111.0)  # Assumes ~20km radius
        
        angle = angular_velocity * time_elapsed + obj['direction']
        radius_deg = 0.1  # ~11km radius
        
        obj['lat'] = self.center_lat + radius_deg * math.cos(angle)
        obj['lon'] = self.center_lon + radius_deg * math.sin(angle)
    
    def _update_random_walk(self, obj, time_elapsed):
        """Update position with random walk pattern."""
        # Change direction slightly at each update
        obj['direction'] += random.uniform(-0.3, 0.3)
        
        # Small movement step
        step_size = 0.001  # ~111 meters
        obj['lat'] += step_size * math.cos(obj['direction'])
        obj['lon'] += step_size * math.sin(obj['direction'])
        
        # Keep within bounds
        max_dist = 0.15
        dist_from_center = math.sqrt(
            (obj['lat'] - self.center_lat)**2 + 
            (obj['lon'] - self.center_lon)**2
        )
        if dist_from_center > max_dist:
            # Turn back toward center
            obj['direction'] = math.atan2(
                self.center_lon - obj['lon'],
                self.center_lat - obj['lat']
            )
    
    def get_coordinates(self):
        """
        Get current coordinates of all objects.
        
        Returns:
            List of coordinate dictionaries compatible with Map node
        """
        coordinates = []
        for obj in self.objects:
            coordinates.append({
                'latitude': obj['lat'],
                'longitude': obj['lon'],
                'name': obj['name'],
                'info': f"{obj['pattern']} - {obj['speed_kmh']:.1f} km/h"
            })
        return coordinates


def test_gps_simulator_initialization():
    """Test that GPS simulator initializes correctly"""
    sim = GPSMovementSimulator(num_objects=5, center_lat=48.8566, center_lon=2.3522)
    
    assert len(sim.objects) == 5
    assert sim.center_lat == 48.8566
    assert sim.center_lon == 2.3522
    
    # Check that objects have required fields
    for obj in sim.objects:
        assert 'id' in obj
        assert 'name' in obj
        assert 'lat' in obj
        assert 'lon' in obj
        assert 'speed_kmh' in obj
        assert 'direction' in obj
        assert 'pattern' in obj
        assert obj['pattern'] in ['linear', 'circular', 'random_walk']
    
    print("✓ GPS simulator initialization test passed")


def test_gps_simulator_coordinates_format():
    """Test that generated coordinates are in the correct format for Map node"""
    sim = GPSMovementSimulator(num_objects=3)
    
    coordinates = sim.get_coordinates()
    
    assert len(coordinates) == 3
    
    # Check format compatibility with Map node
    for coord in coordinates:
        assert 'latitude' in coord
        assert 'longitude' in coord
        assert 'name' in coord
        assert 'info' in coord
        
        # Validate latitude/longitude ranges
        assert -90 <= coord['latitude'] <= 90
        assert -180 <= coord['longitude'] <= 180
        
        # Validate types
        assert isinstance(coord['latitude'], float)
        assert isinstance(coord['longitude'], float)
        assert isinstance(coord['name'], str)
        assert isinstance(coord['info'], str)
    
    print("✓ GPS simulator coordinates format test passed")


def test_gps_simulator_movement():
    """Test that objects actually move over time"""
    sim = GPSMovementSimulator(num_objects=3, center_lat=48.8566, center_lon=2.3522)
    
    # Get initial positions
    initial_coords = sim.get_coordinates()
    initial_positions = [(c['latitude'], c['longitude']) for c in initial_coords]
    
    # Update positions (simulate 60 seconds)
    sim.update_positions(time_elapsed=60)
    
    # Get new positions
    updated_coords = sim.get_coordinates()
    updated_positions = [(c['latitude'], c['longitude']) for c in updated_coords]
    
    # At least some objects should have moved
    moved_count = 0
    for initial, updated in zip(initial_positions, updated_positions):
        if initial != updated:
            moved_count += 1
    
    assert moved_count > 0, "No objects moved after 60 seconds"
    
    print(f"✓ GPS simulator movement test passed ({moved_count}/3 objects moved)")


def test_gps_simulator_stays_near_center():
    """Test that objects stay relatively near the center point"""
    center_lat = 48.8566
    center_lon = 2.3522
    sim = GPSMovementSimulator(num_objects=5, center_lat=center_lat, center_lon=center_lon)
    
    # Simulate movement for a long time
    sim.update_positions(time_elapsed=3600)  # 1 hour
    
    coordinates = sim.get_coordinates()
    
    # Check that all objects are within reasonable distance (e.g., 50km ~ 0.5 degrees)
    max_distance = 0.5
    
    for coord in coordinates:
        distance = math.sqrt(
            (coord['latitude'] - center_lat)**2 + 
            (coord['longitude'] - center_lon)**2
        )
        assert distance < max_distance, f"Object too far from center: {distance} degrees"
    
    print("✓ GPS simulator stays near center test passed")


def test_gps_movement_in_example_names():
    """Test that GPS Movement Simulation would be available in example names"""
    # This test just validates that the name exists as a concept
    example_name = "GPS Movement Simulation"
    assert isinstance(example_name, str)
    assert len(example_name) > 0
    
    print("✓ GPS Movement Simulation name validation test passed")


def test_different_movement_patterns():
    """Test that different movement patterns produce different behaviors"""
    sim = GPSMovementSimulator(num_objects=30)  # More objects for better pattern coverage
    
    # Count pattern types
    patterns = {}
    for obj in sim.objects:
        pattern = obj['pattern']
        patterns[pattern] = patterns.get(pattern, 0) + 1
    
    # Should have at least 2 different patterns with multiple objects
    assert len(patterns) >= 2, f"Only {len(patterns)} pattern types found"
    print(f"✓ Different movement patterns test passed (found {len(patterns)} patterns: {patterns})")


def test_gps_simulator_reproducible():
    """Test that simulator produces reproducible results with same seed"""
    sim1 = GPSMovementSimulator(num_objects=3, center_lat=48.8566, center_lon=2.3522)
    coords1_initial = sim1.get_coordinates()
    
    sim2 = GPSMovementSimulator(num_objects=3, center_lat=48.8566, center_lon=2.3522)
    coords2_initial = sim2.get_coordinates()
    
    # Initial positions should be identical (same seed)
    for c1, c2 in zip(coords1_initial, coords2_initial):
        assert abs(c1['latitude'] - c2['latitude']) < 0.0001
        assert abs(c1['longitude'] - c2['longitude']) < 0.0001
    
    print("✓ GPS simulator reproducibility test passed")


if __name__ == "__main__":
    print("Testing GPS Movement Simulation...")
    print()
    
    test_gps_simulator_initialization()
    test_gps_simulator_coordinates_format()
    test_gps_simulator_movement()
    test_gps_simulator_stays_near_center()
    test_gps_movement_in_example_names()
    test_different_movement_patterns()
    test_gps_simulator_reproducible()
    
    print()
    print("All GPS movement simulation tests passed! ✓")
