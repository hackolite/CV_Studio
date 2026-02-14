#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo: Enhanced OSM Map Node with Direct Tile Rendering

This demo showcases the new enhanced OSM tile management features:
- Direct tile downloading with caching
- Sub-pixel accurate GPS point positioning
- Fractional tile coordinate system
- Enhanced visual markers with halos

The demo creates a map of European cities with precise positioning.
"""
import sys
import os
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_map import (
    lat_lon_to_tile_float,
    lat_lon_to_pixel_on_map,
    assemble_osm_map,
    TILE_SIZE
)


def demo_tile_coordinate_conversion():
    """Demo 1: Fractional tile coordinate conversion."""
    print("="*70)
    print("Demo 1: Fractional Tile Coordinate Conversion")
    print("="*70)
    
    cities = [
        ("Paris", 48.8566, 2.3522),
        ("London", 51.5074, -0.1278),
        ("Berlin", 52.5200, 13.4050),
        ("Madrid", 40.4168, -3.7038),
    ]
    
    zoom = 10
    print(f"\nConverting cities to tile coordinates at zoom {zoom}:\n")
    
    for name, lat, lon in cities:
        fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
        print(f"{name:12} ({lat:7.4f}, {lon:7.4f}) → Tile ({fx:.2f}, {fy:.2f})")
    
    print("\nNotice the fractional components provide sub-pixel accuracy!")


def demo_map_assembly():
    """Demo 2: Assemble map with sub-pixel accurate center."""
    print("\n" + "="*70)
    print("Demo 2: Map Assembly with Sub-Pixel Accuracy")
    print("="*70)
    
    # Center on Paris
    center_lat, center_lon = 48.8566, 2.3522
    zoom = 12
    
    print(f"\nAssembling map centered on Paris ({center_lat}, {center_lon})")
    print(f"Zoom level: {zoom}")
    print(f"Tile size: {TILE_SIZE}x{TILE_SIZE} pixels")
    
    # Assemble map
    map_img, origin_fx, origin_fy = assemble_osm_map(
        center_lat, center_lon, zoom, tiles_x=3, tiles_y=3
    )
    
    print(f"\nMap assembled:")
    print(f"  Size: {map_img.size[0]}x{map_img.size[1]} pixels")
    print(f"  Origin: ({origin_fx:.4f}, {origin_fy:.4f}) fractional tiles")
    
    # Verify center is at map center
    px, py = lat_lon_to_pixel_on_map(center_lat, center_lon, origin_fx, origin_fy, zoom)
    map_center_x = map_img.size[0] / 2
    map_center_y = map_img.size[1] / 2
    
    print(f"\nCenter verification:")
    print(f"  Expected center: ({map_center_x:.1f}, {map_center_y:.1f})")
    print(f"  Actual position: ({px:.1f}, {py:.1f})")
    print(f"  Difference: ({abs(px - map_center_x):.2f}, {abs(py - map_center_y):.2f}) pixels")
    
    if abs(px - map_center_x) < 1.0 and abs(py - map_center_y) < 1.0:
        print("  ✓ Sub-pixel accurate centering achieved!")
    
    # Save map
    output_path = "/tmp/demo_paris_map.png"
    map_img.save(output_path)
    print(f"\nMap saved to: {output_path}")


def demo_multi_point_positioning():
    """Demo 3: Position multiple GPS points with sub-pixel accuracy."""
    print("\n" + "="*70)
    print("Demo 3: Multi-Point GPS Positioning")
    print("="*70)
    
    # European cities
    cities = [
        ("Paris", 48.8566, 2.3522),
        ("London", 51.5074, -0.1278),
        ("Berlin", 52.5200, 13.4050),
        ("Madrid", 40.4168, -3.7038),
        ("Rome", 41.9028, 12.4964),
    ]
    
    # Calculate center point
    lats = [lat for _, lat, _ in cities]
    lons = [lon for _, _, lon in cities]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)
    
    zoom = 6  # Zoom out to see all cities
    
    print(f"\nPositioning {len(cities)} cities on map")
    print(f"Center: ({center_lat:.4f}, {center_lon:.4f})")
    print(f"Zoom: {zoom}")
    
    # Assemble map
    map_img, origin_fx, origin_fy = assemble_osm_map(
        center_lat, center_lon, zoom, tiles_x=4, tiles_y=4
    )
    
    # Convert to numpy array for drawing
    map_array = np.array(map_img)
    if map_array.shape[2] == 4:  # RGBA
        map_array = cv2.cvtColor(map_array, cv2.COLOR_RGBA2BGR)
    else:
        map_array = cv2.cvtColor(map_array, cv2.COLOR_RGB2BGR)
    
    print(f"\nPositioning cities:")
    
    # Draw each city
    for name, lat, lon in cities:
        px, py = lat_lon_to_pixel_on_map(lat, lon, origin_fx, origin_fy, zoom)
        px, py = int(px), int(py)
        
        print(f"  {name:12} → ({px:4}, {py:4}) pixels")
        
        # Skip if outside map
        if px < 0 or px >= map_array.shape[1] or py < 0 or py >= map_array.shape[0]:
            print(f"    (outside visible area)")
            continue
        
        # Draw enhanced marker
        # Halo (semi-transparent)
        overlay = map_array.copy()
        cv2.circle(overlay, (px, py), 14, (180, 120, 80), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.3, map_array, 0.7, 0, map_array)
        
        # Outer ring
        cv2.circle(map_array, (px, py), 14, (0, 80, 255), 2, cv2.LINE_AA)
        
        # Main dot
        cv2.circle(map_array, (px, py), 6, (0, 30, 220), -1, cv2.LINE_AA)
        cv2.circle(map_array, (px, py), 6, (0, 50, 255), 2, cv2.LINE_AA)
        
        # Label
        (text_w, text_h), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        text_x = px + 16
        text_y = py - 10
        
        # Ensure label stays in bounds
        text_x = max(0, min(text_x, map_array.shape[1] - text_w - 5))
        text_y = max(text_h + 5, min(text_y, map_array.shape[0] - 5))
        
        # Background
        cv2.rectangle(
            map_array,
            (text_x - 2, text_y - text_h - 2),
            (text_x + text_w + 2, text_y + 2),
            (255, 255, 255), -1
        )
        cv2.rectangle(
            map_array,
            (text_x - 2, text_y - text_h - 2),
            (text_x + text_w + 2, text_y + 2),
            (0, 0, 0), 1
        )
        
        # Text
        cv2.putText(
            map_array, name, (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA
        )
    
    # Save result
    output_path = "/tmp/demo_europe_cities.png"
    cv2.imwrite(output_path, map_array)
    print(f"\nMap with markers saved to: {output_path}")


def demo_zoom_comparison():
    """Demo 4: Compare different zoom levels."""
    print("\n" + "="*70)
    print("Demo 4: Zoom Level Comparison")
    print("="*70)
    
    lat, lon = 48.8566, 2.3522  # Paris
    
    print(f"\nShowing Paris at different zoom levels:")
    print(f"Coordinates: ({lat}, {lon})\n")
    
    for zoom in [8, 10, 12, 15]:
        fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
        tile_x = int(fx)
        tile_y = int(fy)
        
        # Calculate how many tiles exist at this zoom
        max_tiles = 2 ** zoom
        
        print(f"Zoom {zoom:2d}: Tile ({tile_x:5}, {tile_y:5}) of {max_tiles:6}x{max_tiles:6} grid")
        print(f"         Fractional: ({fx:.4f}, {fy:.4f})")
        print()


def main():
    """Run all demos."""
    print("\n" + "="*70)
    print("Enhanced OSM Map Node - Feature Demonstration")
    print("="*70)
    print("\nThis demo showcases the new direct OSM tile management features.")
    print("The demos run without network access by using gray fallback tiles.")
    print()
    
    try:
        demo_tile_coordinate_conversion()
        demo_map_assembly()
        demo_multi_point_positioning()
        demo_zoom_comparison()
        
        print("\n" + "="*70)
        print("All demos completed successfully! ✓")
        print("="*70)
        print("\nGenerated files:")
        print("  - /tmp/demo_paris_map.png: Single centered map")
        print("  - /tmp/demo_europe_cities.png: Multi-city map with markers")
        print()
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
