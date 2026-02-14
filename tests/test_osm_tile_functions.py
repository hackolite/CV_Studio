#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for enhanced OSM tile management functions.

These tests verify the new direct OSM tile downloading and assembly
functions inspired by the DearPyGui OSM implementation.
"""
import sys
import os
import math

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_map import (
    lat_lon_to_tile_float,
    lat_lon_to_pixel_on_map,
    get_osm_tile,
    assemble_osm_map,
    TILE_SIZE
)


def test_lat_lon_to_tile_float():
    """Test fractional tile coordinate calculation."""
    print("Testing lat_lon_to_tile_float...")
    
    # Test Paris coordinates at zoom 10
    lat, lon = 48.8566, 2.3522
    zoom = 10
    fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
    
    # Expected values (calculated from the formula)
    # At zoom 10, Paris should be around tile (518, 352)
    assert 517 < fx < 520, f"Paris X tile at zoom 10 should be ~518, got {fx}"
    assert 351 < fy < 353, f"Paris Y tile at zoom 10 should be ~352, got {fy}"
    
    # Test that fractional part is meaningful
    assert fx != int(fx), "Fractional X should have decimal component"
    assert fy != int(fy), "Fractional Y should have decimal component"
    
    # Test equator/prime meridian at zoom 1
    fx, fy = lat_lon_to_tile_float(0.0, 0.0, 1)
    assert 0.9 < fx < 1.1, f"Equator/Prime meridian X at zoom 1 should be ~1, got {fx}"
    assert 0.9 < fy < 1.1, f"Equator/Prime meridian Y at zoom 1 should be ~1, got {fy}"
    
    print("✓ lat_lon_to_tile_float test passed")


def test_lat_lon_to_pixel_on_map():
    """Test pixel position calculation on assembled map."""
    print("Testing lat_lon_to_pixel_on_map...")
    
    # Test with Paris coordinates
    zoom = 10
    lat, lon = 48.8566, 2.3522  # Paris
    
    # Calculate the fractional tile position for Paris
    fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
    
    # Set origin to be 1.5 tiles left and above Paris
    origin_fx = fx - 1.5
    origin_fy = fy - 1.5
    
    # Calculate pixel position
    px, py = lat_lon_to_pixel_on_map(lat, lon, origin_fx, origin_fy, zoom)
    
    # Paris should be at approximately 1.5 tiles = 384 pixels from origin
    expected_px = 1.5 * TILE_SIZE
    expected_py = 1.5 * TILE_SIZE
    
    assert abs(px - expected_px) < 1.0, f"Pixel X should be ~{expected_px}, got {px}"
    assert abs(py - expected_py) < 1.0, f"Pixel Y should be ~{expected_py}, got {py}"
    
    # Test sub-pixel accuracy with a different point
    lat2, lon2 = 48.8600, 2.3550  # Slightly different point
    px2, py2 = lat_lon_to_pixel_on_map(lat2, lon2, origin_fx, origin_fy, zoom)
    # This point should have sub-pixel precision
    assert px2 != px, "Different coordinates should give different pixel positions"
    
    # Test that origin point is at (0, 0)
    lat_origin, lon_origin = 51.5074, -0.1278  # London
    fx_origin, fy_origin = lat_lon_to_tile_float(lat_origin, lon_origin, zoom)
    px, py = lat_lon_to_pixel_on_map(lat_origin, lon_origin, fx_origin, fy_origin, zoom)
    
    assert abs(px) < 1.0, f"Origin point X should be ~0, got {px}"
    assert abs(py) < 1.0, f"Origin point Y should be ~0, got {py}"
    
    print("✓ lat_lon_to_pixel_on_map test passed")


def test_get_osm_tile():
    """Test OSM tile downloading with fallback."""
    print("Testing get_osm_tile...")
    
    # Note: In sandbox environment, network access is limited
    # so this will test the fallback gray tile functionality
    
    # Test tile download (will likely fail and return gray tile)
    tile = get_osm_tile(10, 500, 350, use_cache=False)
    
    assert tile is not None, "Tile should not be None"
    assert tile.size == (TILE_SIZE, TILE_SIZE), f"Tile size should be {TILE_SIZE}x{TILE_SIZE}"
    assert tile.mode == "RGBA", "Tile should be in RGBA mode"
    
    # Test that caching parameter works (no error)
    tile_cached = get_osm_tile(10, 500, 350, use_cache=True)
    assert tile_cached is not None, "Cached tile should not be None"
    
    print("✓ get_osm_tile test passed (fallback gray tiles)")


def test_assemble_osm_map():
    """Test OSM map assembly with sub-pixel accuracy."""
    print("Testing assemble_osm_map...")
    
    # Test Paris map assembly
    center_lat, center_lon = 48.8566, 2.3522
    zoom = 10
    tiles_x, tiles_y = 3, 3
    
    map_img, origin_fx, origin_fy = assemble_osm_map(
        center_lat, center_lon, zoom, tiles_x, tiles_y
    )
    
    # Verify map dimensions
    expected_width = TILE_SIZE * tiles_x
    expected_height = TILE_SIZE * tiles_y
    assert map_img.size == (expected_width, expected_height), \
        f"Map size should be {expected_width}x{expected_height}, got {map_img.size}"
    
    # Verify origin is a fractional tile position
    assert isinstance(origin_fx, float), "Origin FX should be float"
    assert isinstance(origin_fy, float), "Origin FY should be float"
    
    # Verify center point is approximately in the middle of the map
    center_fx, center_fy = lat_lon_to_tile_float(center_lat, center_lon, zoom)
    
    # Origin should be center minus half the grid size
    expected_origin_fx = center_fx - tiles_x / 2.0
    expected_origin_fy = center_fy - tiles_y / 2.0
    
    assert abs(origin_fx - expected_origin_fx) < 0.01, \
        f"Origin FX should be ~{expected_origin_fx}, got {origin_fx}"
    assert abs(origin_fy - expected_origin_fy) < 0.01, \
        f"Origin FY should be ~{expected_origin_fy}, got {origin_fy}"
    
    # Verify center point is at map center (pixel-wise)
    px, py = lat_lon_to_pixel_on_map(center_lat, center_lon, origin_fx, origin_fy, zoom)
    map_center_x = expected_width / 2
    map_center_y = expected_height / 2
    
    # Allow small tolerance for rounding
    assert abs(px - map_center_x) < 2.0, \
        f"Center point X should be ~{map_center_x}, got {px}"
    assert abs(py - map_center_y) < 2.0, \
        f"Center point Y should be ~{map_center_y}, got {py}"
    
    print("✓ assemble_osm_map test passed")


def test_coordinate_consistency():
    """Test that coordinate conversions are consistent."""
    print("Testing coordinate consistency...")
    
    # Test a round trip: lat/lon -> tile -> pixel -> verify
    test_points = [
        (48.8566, 2.3522),   # Paris
        (51.5074, -0.1278),  # London
        (40.7128, -74.0060), # New York
        (35.6762, 139.6503), # Tokyo
    ]
    
    zoom = 12
    
    for lat, lon in test_points:
        # Convert to tile coordinates
        fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
        
        # Use same point as origin
        px, py = lat_lon_to_pixel_on_map(lat, lon, fx, fy, zoom)
        
        # Point should be at origin (0, 0)
        assert abs(px) < 1.0, f"Point ({lat}, {lon}) X should be ~0, got {px}"
        assert abs(py) < 1.0, f"Point ({lat}, {lon}) Y should be ~0, got {py}"
    
    # Test that points maintain relative positions
    lat1, lon1 = 48.8566, 2.3522   # Paris
    lat2, lon2 = 51.5074, -0.1278  # London (north-west of Paris)
    
    fx_origin, fy_origin = lat_lon_to_tile_float(lat1, lon1, zoom)
    
    px1, py1 = lat_lon_to_pixel_on_map(lat1, lon1, fx_origin, fy_origin, zoom)
    px2, py2 = lat_lon_to_pixel_on_map(lat2, lon2, fx_origin, fy_origin, zoom)
    
    # London should be north (lower Y) and west (lower X) of Paris
    assert px2 < px1, "London should be west (lower X) of Paris"
    assert py2 < py1, "London should be north (lower Y) of Paris"
    
    print("✓ Coordinate consistency test passed")


def test_zoom_level_scaling():
    """Test that different zoom levels produce consistent results."""
    print("Testing zoom level scaling...")
    
    lat, lon = 48.8566, 2.3522  # Paris
    
    # Test that tile coordinates scale correctly with zoom
    for zoom in [8, 10, 12, 15]:
        fx, fy = lat_lon_to_tile_float(lat, lon, zoom)
        
        # At each zoom level, tile count is 2^zoom in each direction
        max_tiles = 2 ** zoom
        assert 0 <= fx < max_tiles, f"Tile X at zoom {zoom} should be in [0, {max_tiles})"
        assert 0 <= fy < max_tiles, f"Tile Y at zoom {zoom} should be in [0, {max_tiles})"
        
        # Higher zoom should give higher tile numbers (for positive lat/lon)
        if zoom > 8:
            fx_prev, fy_prev = lat_lon_to_tile_float(lat, lon, zoom - 1)
            # At higher zoom, tiles are subdivided 2x
            assert fx > fx_prev * 2 - 1, f"Higher zoom should increase tile X"
            assert fy > fy_prev * 2 - 1, f"Higher zoom should increase tile Y"
    
    print("✓ Zoom level scaling test passed")


if __name__ == "__main__":
    print("\nTesting Enhanced OSM Tile Management Functions...\n")
    
    try:
        test_lat_lon_to_tile_float()
        test_lat_lon_to_pixel_on_map()
        test_get_osm_tile()
        test_assemble_osm_map()
        test_coordinate_consistency()
        test_zoom_level_scaling()
        
        print("\n" + "="*60)
        print("All OSM tile function tests passed! ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
