#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Coordinate Examples node timer functionality
Tests that GPS simulation updates only once per second
"""
import time
import math
import random


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


class MockNode:
    """Mock node class for testing timer functionality"""
    def __init__(self):
        self.gps_simulator = None
        self.last_update_time = None
        self.update_interval = 1.0
        self.last_coordinates = []


def test_gps_update_interval():
    """Test that GPS coordinates are only updated once per second"""
    
    # Create a node instance
    node = MockNode()
    
    # Initialize the GPS simulator
    node.gps_simulator = GPSMovementSimulator(num_objects=5)
    node.last_update_time = time.time()
    node.last_coordinates = node.gps_simulator.get_coordinates()
    
    # Get initial coordinates (deep copy)
    initial_coords = [coord.copy() for coord in node.last_coordinates]
    
    # Simulate rapid updates (like the main loop running at 100 Hz)
    # The coordinates should NOT change for the first second
    start_time = time.time()
    updates_without_change = 0
    
    # Run multiple updates within 1 second
    for i in range(50):  # Simulate 50 updates
        time.sleep(0.01)  # 10ms between updates
        
        current_time = time.time()
        time_elapsed = current_time - node.last_update_time
        
        if time_elapsed >= node.update_interval:
            # Update should happen
            node.gps_simulator.update_positions()
            node.last_coordinates = node.gps_simulator.get_coordinates()
            node.last_update_time = current_time
        
        # Check if coordinates have changed (deep comparison)
        coords_unchanged = True
        for j, (initial, current) in enumerate(zip(initial_coords, node.last_coordinates)):
            if (initial['latitude'] != current['latitude'] or 
                initial['longitude'] != current['longitude']):
                coords_unchanged = False
                break
        
        if coords_unchanged:
            updates_without_change += 1
    
    elapsed_time = time.time() - start_time
    
    # The coordinates should have stayed the same for at least the first several updates
    # (until 1 second elapsed)
    assert updates_without_change > 0, "Coordinates should not change on every update"
    
    # If we ran for less than 1 second, coordinates should not have changed
    if elapsed_time < 1.0:
        coords_unchanged = True
        for initial, current in zip(initial_coords, node.last_coordinates):
            if (initial['latitude'] != current['latitude'] or 
                initial['longitude'] != current['longitude']):
                coords_unchanged = False
                break
        assert coords_unchanged, "Coordinates should not change before 1 second"
    
    print(f"✓ GPS update interval test passed ({updates_without_change}/50 updates without change)")


def test_gps_updates_after_one_second():
    """Test that GPS coordinates DO update after 1 second"""
    
    # Create a node instance
    node = MockNode()
    
    # Initialize the GPS simulator
    node.gps_simulator = GPSMovementSimulator(num_objects=5)
    node.last_update_time = time.time() - 1.5  # Pretend last update was 1.5 seconds ago
    node.last_coordinates = node.gps_simulator.get_coordinates()
    
    # Get initial coordinates
    initial_coords = [coord.copy() for coord in node.last_coordinates]
    
    # Simulate an update after 1 second has passed
    current_time = time.time()
    time_elapsed = current_time - node.last_update_time
    
    assert time_elapsed >= node.update_interval, "Test setup error: should be >= 1 second"
    
    # Perform update
    node.gps_simulator.update_positions()
    node.last_coordinates = node.gps_simulator.get_coordinates()
    node.last_update_time = current_time
    
    # Coordinates should have changed (at least for some objects)
    # Note: With 5 objects and random patterns, at least one should move
    changed = False
    for i in range(len(initial_coords)):
        if (initial_coords[i]['latitude'] != node.last_coordinates[i]['latitude'] or
            initial_coords[i]['longitude'] != node.last_coordinates[i]['longitude']):
            changed = True
            break
    
    assert changed, "Coordinates should change after 1 second update"
    
    print("✓ GPS updates after one second test passed")


def test_multiple_one_second_intervals():
    """Test that GPS coordinates update correctly over multiple 1-second intervals"""
    
    # Create a node instance
    node = MockNode()
    
    # Initialize the GPS simulator
    node.gps_simulator = GPSMovementSimulator(num_objects=3)
    node.last_update_time = time.time()
    node.last_coordinates = node.gps_simulator.get_coordinates()
    
    update_count = 0
    positions_history = [node.last_coordinates.copy()]
    
    # Run for approximately 3 seconds
    start_time = time.time()
    while time.time() - start_time < 3.2:
        time.sleep(0.05)  # Simulate 20 Hz update rate
        
        current_time = time.time()
        time_elapsed = current_time - node.last_update_time
        
        if time_elapsed >= node.update_interval:
            # Update should happen
            node.gps_simulator.update_positions()
            node.last_coordinates = node.gps_simulator.get_coordinates()
            node.last_update_time = current_time
            update_count += 1
            positions_history.append(node.last_coordinates.copy())
    
    # Should have updated approximately 3 times (once per second for 3 seconds)
    assert 2 <= update_count <= 4, f"Expected 2-4 updates, got {update_count}"
    assert len(positions_history) >= 3, f"Expected at least 3 position records, got {len(positions_history)}"
    
    print(f"✓ Multiple one-second intervals test passed ({update_count} updates in ~3 seconds)")


def test_node_initialization():
    """Test that node initializes with correct timer state"""
    
    node = MockNode()
    
    # Check that timer attributes exist
    assert hasattr(node, 'last_update_time'), "Node should have last_update_time attribute"
    assert hasattr(node, 'update_interval'), "Node should have update_interval attribute"
    assert hasattr(node, 'last_coordinates'), "Node should have last_coordinates attribute"
    
    # Check initial values
    assert node.last_update_time is None, "last_update_time should start as None"
    assert node.update_interval == 1.0, "update_interval should be 1.0 second"
    assert node.last_coordinates == [], "last_coordinates should start as empty list"
    
    print("✓ Node initialization test passed")


def test_initial_coordinates_available():
    """Test that initial coordinates are available immediately after initialization"""
    
    node = MockNode()
    
    # Initialize the GPS simulator
    node.gps_simulator = GPSMovementSimulator(num_objects=5)
    node.last_update_time = time.time()
    # Get initial coordinates immediately (simulating the actual node behavior)
    node.last_coordinates = node.gps_simulator.get_coordinates()
    
    # Verify coordinates are available right away
    assert len(node.last_coordinates) == 5, "Should have 5 initial coordinates"
    
    # Verify each coordinate has the required fields
    for coord in node.last_coordinates:
        assert 'latitude' in coord
        assert 'longitude' in coord
        assert 'name' in coord
        assert 'info' in coord
    
    print("✓ Initial coordinates available test passed")


if __name__ == "__main__":
    print("Testing Coordinate Examples Node Timer Functionality...")
    print()
    
    test_node_initialization()
    test_initial_coordinates_available()
    test_gps_update_interval()
    test_gps_updates_after_one_second()
    test_multiple_one_second_intervals()
    
    print()
    print("All timer tests passed! ✓")
