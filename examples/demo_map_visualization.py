#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example demonstrating the Map visualization node with sample data

This script shows how to use the Map node to visualize geographic data
from different sources like AIS boat data, city locations, etc.
"""
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode.node_map import Node as MapNode


def example_ais_boat_data():
    """Example 1: AIS Boat Data (from WebSocket)"""
    print("=" * 60)
    print("Example 1: AIS Boat Data")
    print("=" * 60)
    
    # Sample AIS data from Mediterranean Sea
    ais_data = {
        "boats": [
            {
                "mmsi": "247123456",
                "ship_name": "Mediterranean Express",
                "latitude": 36.7213,
                "longitude": 3.0875,
                "speed": 18.5,
                "course": 45.0,
                "ship_type": "Cargo",
                "destination": "Barcelona"
            },
            {
                "mmsi": "247234567",
                "ship_name": "Coastal Trader",
                "latitude": 37.9838,
                "longitude": 23.7275,
                "speed": 12.3,
                "course": 180.0,
                "ship_type": "Tanker",
                "destination": "Athens"
            },
            {
                "mmsi": "247345678",
                "ship_name": "Island Ferry",
                "latitude": 38.1157,
                "longitude": 13.3615,
                "speed": 8.0,
                "course": 270.0,
                "ship_type": "Passenger",
                "destination": "Palermo"
            }
        ],
        "count": 3,
        "timestamp": "2024-01-15T12:00:00Z"
    }
    
    # Create node and extract points
    node = MapNode.create_for_testing()
    points = node._extract_lat_lon_from_json(ais_data)
    
    print(f"Extracted {len(points)} boat positions:")
    for point in points:
        print(f"  - {point['name']} at ({point['lat']:.4f}, {point['lon']:.4f})")
    
    # Generate map
    map_path = node._generate_map(points, zoom_level=6, size_factor=1.2)
    if map_path:
        print(f"\n✓ Map generated: {map_path}")
        print("  Open this file in your browser to see the interactive map!")
    else:
        print("\n⚠ Map generation skipped (folium not installed)")
    
    print()


def example_world_cities():
    """Example 2: Major World Cities"""
    print("=" * 60)
    print("Example 2: Major World Cities")
    print("=" * 60)
    
    # Sample city data
    cities_data = [
        {"latitude": 40.7128, "longitude": -74.0060, "name": "New York"},
        {"latitude": 51.5074, "longitude": -0.1278, "name": "London"},
        {"latitude": 48.8566, "longitude": 2.3522, "name": "Paris"},
        {"latitude": 35.6762, "longitude": 139.6503, "name": "Tokyo"},
        {"latitude": -33.8688, "longitude": 151.2093, "name": "Sydney"},
        {"latitude": 19.4326, "longitude": -99.1332, "name": "Mexico City"},
        {"latitude": -23.5505, "longitude": -46.6333, "name": "São Paulo"},
        {"latitude": 55.7558, "longitude": 37.6173, "name": "Moscow"},
    ]
    
    # Create node and extract points
    node = MapNode.create_for_testing()
    points = node._extract_lat_lon_from_json(cities_data)
    
    print(f"Extracted {len(points)} city locations:")
    for point in points:
        print(f"  - {point['name']} at ({point['lat']:.4f}, {point['lon']:.4f})")
    
    # Generate map with lower zoom to see the world
    map_path = node._generate_map(points, zoom_level=2, size_factor=1.0)
    if map_path:
        print(f"\n✓ Map generated: {map_path}")
        print("  Open this file in your browser to see the interactive map!")
    else:
        print("\n⚠ Map generation skipped (folium not installed)")
    
    print()


def example_gps_track():
    """Example 3: GPS Tracking Points"""
    print("=" * 60)
    print("Example 3: GPS Track (Hiking Trail)")
    print("=" * 60)
    
    # Sample GPS track (hiking trail in Alps)
    gps_track = [
        {"lat": 45.8326, "lon": 6.8652, "name": "Trailhead"},
        {"lat": 45.8342, "lon": 6.8668, "name": "Point 1"},
        {"lat": 45.8358, "lon": 6.8685, "name": "Point 2"},
        {"lat": 45.8375, "lon": 6.8701, "name": "Point 3"},
        {"lat": 45.8391, "lon": 6.8718, "name": "Summit"},
    ]
    
    # Create node and extract points
    node = MapNode.create_for_testing()
    points = node._extract_lat_lon_from_json(gps_track)
    
    print(f"Extracted {len(points)} GPS points:")
    for point in points:
        print(f"  - {point['name']} at ({point['lat']:.4f}, {point['lon']:.4f})")
    
    # Generate map with high zoom for detailed view
    map_path = node._generate_map(points, zoom_level=14, size_factor=1.0)
    if map_path:
        print(f"\n✓ Map generated: {map_path}")
        print("  Open this file in your browser to see the interactive map!")
    else:
        print("\n⚠ Map generation skipped (folium not installed)")
    
    print()


def example_preview_image():
    """Example 4: Preview Image Generation"""
    print("=" * 60)
    print("Example 4: Preview Image Generation")
    print("=" * 60)
    
    # Sample data
    data = [
        {"latitude": 40.0, "longitude": -75.0, "name": "Point A"},
        {"latitude": 41.0, "longitude": -74.0, "name": "Point B"},
        {"latitude": 40.5, "longitude": -74.5, "name": "Point C"},
    ]
    
    # Create node and generate preview
    node = MapNode.create_for_testing()
    points = node._extract_lat_lon_from_json(data)
    preview = node._create_preview_image(points, width=240, height=135)
    
    print(f"Preview image generated:")
    print(f"  - Shape: {preview.shape}")
    print(f"  - Points: {len(points)}")
    print(f"  - Non-zero pixels: {(preview > 0).sum()}")
    print("\n✓ Preview generation successful!")
    print()


if __name__ == "__main__":
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "Map Visualization Node Examples" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # Run all examples
    example_ais_boat_data()
    example_world_cities()
    example_gps_track()
    example_preview_image()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print()
    print("Usage in CV Studio:")
    print("  1. Add a data source (WebSocket, File, etc.)")
    print("  2. Add the Map node from Visual menu")
    print("  3. Connect JSON output to Map input")
    print("  4. Adjust zoom and view size")
    print("  5. Click 'Open Map in Browser'")
    print()
