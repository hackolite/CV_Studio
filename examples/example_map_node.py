#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Example script demonstrating the Map node visualization.

This example shows how to:
1. Create sample geographical data
2. Use the Map node to visualize it
3. Test different zoom and pan settings

Usage:
    python example_map_node.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_map import Node as MapNode
import cv2


def example_cities():
    """Example with major world cities"""
    print("=" * 60)
    print("Example 1: Major World Cities")
    print("=" * 60)
    
    cities_data = [
        {"name": "New York", "latitude": 40.7128, "longitude": -74.0060},
        {"name": "London", "latitude": 51.5074, "longitude": -0.1278},
        {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
        {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522},
        {"name": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
        {"name": "Dubai", "latitude": 25.2048, "longitude": 55.2708},
    ]
    
    # Create map node
    node = MapNode(opencv_setting_dict={
        'process_width': 800,
        'process_height': 600
    })
    
    # Extract coordinates
    coords = node.extract_coordinates(cities_data)
    print(f"Extracted {len(coords)} coordinates")
    
    # Calculate bounds
    bounds = node.calculate_bounds(coords)
    print(f"Bounds: Lat [{bounds[0]:.2f}, {bounds[1]:.2f}], Lon [{bounds[2]:.2f}, {bounds[3]:.2f}]")
    
    # Render map
    map_image = node.render_map(
        coordinates=coords,
        bounds=bounds,
        width=800,
        height=600,
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    
    # Save image
    output_path = "/tmp/map_cities.png"
    cv2.imwrite(output_path, cv2.cvtColor(map_image, cv2.COLOR_RGB2BGR))
    print(f"✓ Map saved to: {output_path}")
    print()


def example_ais_boats():
    """Example with AIS boat data format"""
    print("=" * 60)
    print("Example 2: AIS Boat Data (Mediterranean)")
    print("=" * 60)
    
    # Sample AIS-like data for Mediterranean boats
    ais_data = {
        "boats": [
            {
                "mmsi": "123456789",
                "ship_name": "Mediterranean Star",
                "latitude": 43.7102,
                "longitude": 7.2620,  # Monaco
                "speed": 12.5,
                "course": 90.0,
            },
            {
                "mmsi": "987654321",
                "ship_name": "Azure Voyager",
                "latitude": 41.9028,
                "longitude": 12.4964,  # Rome/Tyrrhenian Sea
                "speed": 15.0,
                "course": 180.0,
            },
            {
                "mmsi": "555666777",
                "ship_name": "Blue Horizon",
                "latitude": 36.8969,
                "longitude": 30.7133,  # Antalya
                "speed": 8.5,
                "course": 270.0,
            },
        ],
        "count": 3,
        "timestamp": "2026-02-12T12:00:00Z"
    }
    
    # Create map node
    node = MapNode(opencv_setting_dict={
        'process_width': 800,
        'process_height': 600
    })
    
    # Extract coordinates
    coords = node.extract_coordinates(ais_data)
    print(f"Extracted {len(coords)} boat positions")
    
    for i, (boat, coord) in enumerate(zip(ais_data['boats'], coords)):
        print(f"  {i+1}. {boat['ship_name']}: ({coord[0]:.4f}, {coord[1]:.4f})")
    
    # Calculate bounds
    bounds = node.calculate_bounds(coords)
    
    # Render map with default view
    map_image = node.render_map(
        coordinates=coords,
        bounds=bounds,
        width=800,
        height=600,
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    
    # Save default view
    output_path = "/tmp/map_ais_default.png"
    cv2.imwrite(output_path, cv2.cvtColor(map_image, cv2.COLOR_RGB2BGR))
    print(f"✓ Default view saved to: {output_path}")
    
    # Render map with zoom
    map_image_zoom = node.render_map(
        coordinates=coords,
        bounds=bounds,
        width=800,
        height=600,
        zoom=2.0,  # Zoom in 2x
        pan_x=0.0,
        pan_y=0.0,
    )
    
    # Save zoomed view
    output_path = "/tmp/map_ais_zoomed.png"
    cv2.imwrite(output_path, cv2.cvtColor(map_image_zoom, cv2.COLOR_RGB2BGR))
    print(f"✓ Zoomed view (2x) saved to: {output_path}")
    print()


def example_single_location():
    """Example with a single location"""
    print("=" * 60)
    print("Example 3: Single Location (Eiffel Tower)")
    print("=" * 60)
    
    # Single location
    location = {
        "name": "Eiffel Tower",
        "latitude": 48.8584,
        "longitude": 2.2945,
    }
    
    # Create map node
    node = MapNode(opencv_setting_dict={
        'process_width': 600,
        'process_height': 600
    })
    
    # Extract coordinates
    coords = node.extract_coordinates(location)
    print(f"Location: {location['name']}")
    print(f"Coordinates: ({coords[0][0]:.6f}, {coords[0][1]:.6f})")
    
    # Calculate bounds (will add padding around single point)
    bounds = node.calculate_bounds(coords)
    
    # Render map with high zoom
    map_image = node.render_map(
        coordinates=coords,
        bounds=bounds,
        width=600,
        height=600,
        zoom=5.0,  # High zoom for detail
        pan_x=0.0,
        pan_y=0.0,
    )
    
    # Save image
    output_path = "/tmp/map_eiffel_tower.png"
    cv2.imwrite(output_path, cv2.cvtColor(map_image, cv2.COLOR_RGB2BGR))
    print(f"✓ Map saved to: {output_path}")
    print()


def example_pan_controls():
    """Example demonstrating pan controls"""
    print("=" * 60)
    print("Example 4: Pan Controls (US West Coast)")
    print("=" * 60)
    
    # West coast cities
    west_coast = [
        {"name": "Seattle", "latitude": 47.6062, "longitude": -122.3321},
        {"name": "San Francisco", "latitude": 37.7749, "longitude": -122.4194},
        {"name": "Los Angeles", "latitude": 34.0522, "longitude": -118.2437},
        {"name": "San Diego", "latitude": 32.7157, "longitude": -117.1611},
    ]
    
    # Create map node
    node = MapNode(opencv_setting_dict={
        'process_width': 600,
        'process_height': 800
    })
    
    coords = node.extract_coordinates(west_coast)
    bounds = node.calculate_bounds(coords)
    
    print(f"Rendering {len(coords)} locations on US West Coast")
    
    # Default view
    map_default = node.render_map(coords, bounds, 600, 800, zoom=1.0, pan_x=0.0, pan_y=0.0)
    cv2.imwrite("/tmp/map_west_coast_default.png", cv2.cvtColor(map_default, cv2.COLOR_RGB2BGR))
    print("✓ Default view saved")
    
    # Pan north (focus on Seattle)
    map_north = node.render_map(coords, bounds, 600, 800, zoom=2.0, pan_x=0.0, pan_y=0.5)
    cv2.imwrite("/tmp/map_west_coast_north.png", cv2.cvtColor(map_north, cv2.COLOR_RGB2BGR))
    print("✓ Panned north (Seattle focus) saved")
    
    # Pan south (focus on San Diego)
    map_south = node.render_map(coords, bounds, 600, 800, zoom=2.0, pan_x=0.0, pan_y=-0.5)
    cv2.imwrite("/tmp/map_west_coast_south.png", cv2.cvtColor(map_south, cv2.COLOR_RGB2BGR))
    print("✓ Panned south (San Diego focus) saved")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Map Node Examples")
    print("=" * 60)
    print()
    
    try:
        example_cities()
        example_ais_boats()
        example_single_location()
        example_pan_controls()
        
        print("=" * 60)
        print("All examples completed successfully! ✓")
        print("=" * 60)
        print("\nGenerated maps:")
        print("  - /tmp/map_cities.png")
        print("  - /tmp/map_ais_default.png")
        print("  - /tmp/map_ais_zoomed.png")
        print("  - /tmp/map_eiffel_tower.png")
        print("  - /tmp/map_west_coast_default.png")
        print("  - /tmp/map_west_coast_north.png")
        print("  - /tmp/map_west_coast_south.png")
        print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
