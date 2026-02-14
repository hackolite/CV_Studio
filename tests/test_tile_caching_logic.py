#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for tile download logic and caching

This test validates:
1. Tiles are cached on first download
2. Subsequent requests use cached tiles (no re-download)
3. Cache statistics are correctly reported
"""
import os
import shutil
import tempfile
from unittest.mock import patch, Mock
from io import BytesIO
from PIL import Image


# Simulate the tile caching functions
OSM_CACHE_DIR = os.path.join(tempfile.gettempdir(), 'test_osm_cache')
TILE_SIZE = 256


def get_osm_tile_cached(z, x, y, use_cache=True, mock_download=None):
    """
    Simplified version of get_osm_tile for testing.
    """
    cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
    
    # Check cache first
    if use_cache and os.path.exists(cache_path):
        try:
            img = Image.open(cache_path).convert("RGBA")
            print(f"Tile {z}/{x}/{y} loaded from cache (no download needed)")
            return img, True  # True = from cache
        except Exception as e:
            print(f"Cache read error for tile {z}/{x}/{y}: {e}")
            try:
                os.remove(cache_path)
            except:
                pass
    
    # Download tile (simulated)
    print(f"Downloading tile {z}/{x}/{y} from OSM server...")
    
    if mock_download:
        img = mock_download()
    else:
        # Create a simple test tile
        img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (100, 100, 100, 255))
    
    # Save to cache
    if use_cache:
        try:
            os.makedirs(OSM_CACHE_DIR, exist_ok=True)
            img.save(cache_path)
            print(f"Tile {z}/{x}/{y} saved to cache for future use")
        except Exception as e:
            print(f"Cache write error for tile {z}/{x}/{y}: {e}")
    
    return img, False  # False = not from cache


def test_cache_directory_creation():
    """Test that cache directory is created automatically."""
    print("\n=== Test: Cache Directory Creation ===")
    
    # Clean up first
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    
    assert not os.path.exists(OSM_CACHE_DIR), "Cache directory should not exist initially"
    
    # Request a tile
    img, from_cache = get_osm_tile_cached(10, 5, 5, use_cache=True)
    
    # Cache directory should be created
    assert os.path.exists(OSM_CACHE_DIR), "Cache directory should be created"
    
    print(f"✓ Cache directory created at: {OSM_CACHE_DIR}")
    print("✓ Cache directory creation test passed")


def test_first_download_caches_tile():
    """Test that first download saves tile to cache."""
    print("\n=== Test: First Download Caches Tile ===")
    
    # Clean up
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    
    z, x, y = 10, 100, 200
    cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
    
    # Ensure tile is not cached
    assert not os.path.exists(cache_path), "Tile should not be cached initially"
    
    # Download tile
    img, from_cache = get_osm_tile_cached(z, x, y, use_cache=True)
    
    # Check results
    assert not from_cache, "First request should NOT be from cache"
    assert os.path.exists(cache_path), "Tile should be saved to cache"
    
    print(f"✓ Tile {z}/{x}/{y} cached at: {cache_path}")
    print("✓ First download caches tile test passed")


def test_second_request_uses_cache():
    """Test that second request uses cached tile without downloading."""
    print("\n=== Test: Second Request Uses Cache ===")
    
    # Clean up
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    
    z, x, y = 12, 50, 75
    
    # First request (should download and cache)
    print("--- First request ---")
    img1, from_cache1 = get_osm_tile_cached(z, x, y, use_cache=True)
    assert not from_cache1, "First request should download"
    
    # Second request (should use cache)
    print("--- Second request ---")
    img2, from_cache2 = get_osm_tile_cached(z, x, y, use_cache=True)
    assert from_cache2, "Second request should use cache"
    
    print(f"✓ Tile {z}/{x}/{y} reused from cache (no re-download)")
    print("✓ Second request uses cache test passed")


def test_cache_can_be_disabled():
    """Test that caching can be disabled."""
    print("\n=== Test: Cache Can Be Disabled ===")
    
    # Clean up
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    
    z, x, y = 11, 25, 30
    cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
    
    # Request with caching disabled
    img, from_cache = get_osm_tile_cached(z, x, y, use_cache=False)
    
    # Tile should NOT be cached
    assert not from_cache, "Should not be from cache"
    assert not os.path.exists(cache_path), "Tile should NOT be saved when caching disabled"
    
    print(f"✓ Tile {z}/{x}/{y} not cached when use_cache=False")
    print("✓ Cache can be disabled test passed")


def test_cache_statistics():
    """Test cache statistics tracking."""
    print("\n=== Test: Cache Statistics ===")
    
    # Clean up
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    
    # Simulate downloading multiple tiles
    tiles = [
        (10, 0, 0),
        (10, 0, 1),
        (10, 1, 0),
        (10, 1, 1),
    ]
    
    tiles_from_cache = 0
    tiles_downloaded = 0
    
    # First pass - all downloads
    print("--- First pass (all downloads) ---")
    for z, x, y in tiles:
        img, from_cache = get_osm_tile_cached(z, x, y, use_cache=True)
        if from_cache:
            tiles_from_cache += 1
        else:
            tiles_downloaded += 1
    
    assert tiles_downloaded == 4, "Should have 4 downloads in first pass"
    assert tiles_from_cache == 0, "Should have 0 cache hits in first pass"
    print(f"First pass: {tiles_downloaded} downloaded, {tiles_from_cache} from cache")
    
    # Second pass - all from cache
    print("--- Second pass (all from cache) ---")
    tiles_from_cache = 0
    tiles_downloaded = 0
    
    for z, x, y in tiles:
        img, from_cache = get_osm_tile_cached(z, x, y, use_cache=True)
        if from_cache:
            tiles_from_cache += 1
        else:
            tiles_downloaded += 1
    
    assert tiles_downloaded == 0, "Should have 0 downloads in second pass"
    assert tiles_from_cache == 4, "Should have 4 cache hits in second pass"
    print(f"Second pass: {tiles_downloaded} downloaded, {tiles_from_cache} from cache")
    
    print("✓ Cache statistics test passed")


def test_corrupted_cache_recovery():
    """Test that corrupted cache files are handled gracefully."""
    print("\n=== Test: Corrupted Cache Recovery ===")
    
    # Clean up
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
    os.makedirs(OSM_CACHE_DIR, exist_ok=True)
    
    z, x, y = 10, 10, 10
    cache_path = os.path.join(OSM_CACHE_DIR, f"{z}_{x}_{y}.png")
    
    # Create a corrupted cache file
    with open(cache_path, 'w') as f:
        f.write("This is not a valid PNG file!")
    
    assert os.path.exists(cache_path), "Corrupted cache file should exist"
    
    # Try to load the tile
    img, from_cache = get_osm_tile_cached(z, x, y, use_cache=True)
    
    # Should download a new tile and replace the corrupted one
    assert not from_cache, "Should download due to corrupted cache"
    
    # Cache should now contain a valid tile
    img2, from_cache2 = get_osm_tile_cached(z, x, y, use_cache=True)
    assert from_cache2, "Should now load from corrected cache"
    
    print("✓ Corrupted cache file recovered")
    print("✓ Corrupted cache recovery test passed")


def cleanup():
    """Clean up test cache directory."""
    if os.path.exists(OSM_CACHE_DIR):
        shutil.rmtree(OSM_CACHE_DIR)
        print(f"\n✓ Test cache directory cleaned up")


if __name__ == "__main__":
    print("Testing Tile Download Logic and Caching...")
    print("=" * 60)
    
    try:
        test_cache_directory_creation()
        test_first_download_caches_tile()
        test_second_request_uses_cache()
        test_cache_can_be_disabled()
        test_cache_statistics()
        test_corrupted_cache_recovery()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        
        cleanup()
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        exit(1)
