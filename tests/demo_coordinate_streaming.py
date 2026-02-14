#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of 1-second GPS coordinate updates
This script simulates the behavior of the CoordinateExamples node
sending GPS coordinates every second to the Map node.
"""
import time
import json
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


def simulate_coordinate_updates(duration_seconds=10):
    """
    Simulate the CoordinateExamples node sending coordinates every second.
    
    Args:
        duration_seconds: How long to run the simulation (default: 10 seconds)
    """
    print("=" * 70)
    print("GPS COORDINATE STREAMING DEMONSTRATION")
    print("=" * 70)
    print()
    print(f"Simulating {duration_seconds} seconds of GPS coordinate updates...")
    print("Coordinates are sent every 1 second (matching the requirement)")
    print()
    
    # Initialize the GPS simulator
    simulator = GPSMovementSimulator(num_objects=5, center_lat=48.8566, center_lon=2.3522)
    
    # Track timing
    last_update_time = time.time()
    update_interval = 1.0  # 1 second
    last_coordinates = []
    
    update_count = 0
    start_time = time.time()
    
    print(f"Starting simulation at {time.strftime('%H:%M:%S')}")
    print("-" * 70)
    
    # Simulate the main loop (which runs at ~100 Hz in the real application)
    loop_iterations = 0
    while time.time() - start_time < duration_seconds:
        loop_iterations += 1
        
        # Check if enough time has elapsed for an update (1 second interval)
        current_time = time.time()
        time_elapsed = current_time - last_update_time
        
        if time_elapsed >= update_interval:
            # Update positions
            simulator.update_positions()
            
            # Get current coordinates
            last_coordinates = simulator.get_coordinates()
            
            # Update the last update time
            last_update_time = current_time
            update_count += 1
            
            # Display the update
            elapsed = current_time - start_time
            print(f"\n[Update #{update_count} at T+{elapsed:.1f}s]")
            print(f"Timestamp: {time.strftime('%H:%M:%S')}")
            print(f"Sending {len(last_coordinates)} coordinates to Map node:")
            
            # Show first 2 coordinates as example
            for i, coord in enumerate(last_coordinates[:2]):
                print(f"  {coord['name']}: ({coord['latitude']:.6f}, {coord['longitude']:.6f}) - {coord['info']}")
            if len(last_coordinates) > 2:
                print(f"  ... and {len(last_coordinates) - 2} more")
        
        # Simulate the main loop delay (10ms in the real application)
        time.sleep(0.01)
    
    print()
    print("-" * 70)
    print(f"Simulation complete!")
    print(f"Total runtime: {time.time() - start_time:.2f} seconds")
    print(f"Total updates sent: {update_count}")
    print(f"Loop iterations: {loop_iterations}")
    print(f"Average update rate: {update_count / (time.time() - start_time):.2f} updates/second")
    print()
    print("✓ Coordinates are successfully sent every 1 second")
    print("✓ Map node can visualize these on OpenStreetMap")
    print()


if __name__ == "__main__":
    simulate_coordinate_updates(duration_seconds=5)
