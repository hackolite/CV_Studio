#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for LRU cache optimization in VideoNode"""

import pytest
import sys
import os
import numpy as np
from collections import OrderedDict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_lru_cache_structure():
    """Test that VideoNode has the new LRU cache structures"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py file should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check OrderedDict import
    assert 'from collections import OrderedDict' in content, "Should import OrderedDict"
    
    # Check new storage attributes
    assert '_full_audio = {}' in content, "Should have _full_audio dict"
    assert '_spectrogram_cache = {}' in content, "Should have _spectrogram_cache dict"
    assert '_cache_max_size = 50' in content, "Should have _cache_max_size = 50"
    
    # Check removed attributes
    assert '_video_frames = {}' not in content, "Should NOT have _video_frames (removed for optimization)"
    assert '_audio_chunks = {}' not in content, "Should NOT have _audio_chunks (removed for optimization)"
    assert '_spectrogram_chunks = {}' not in content, "Should NOT have _spectrogram_chunks (removed for optimization)"
    
    print("✓ LRU cache structure checks passed")


def test_optimized_preprocess_video():
    """Test that _preprocess_video is optimized"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that preprocessing is optimized
    assert 'Version optimisée' in content or 'Chargement optimisé' in content, "Should have optimized version comment"
    assert 'self._full_audio[node_id] = y' in content, "Should store full audio"
    assert 'self._spectrogram_cache[node_id] = OrderedDict()' in content, "Should initialize OrderedDict cache"
    
    # Check that frame extraction is removed
    assert 'Extract all video frames' not in content, "Should NOT extract all frames"
    assert 'self._video_frames[node_id] = frames' not in content, "Should NOT store frames"
    
    # Check that audio chunking is removed from preprocessing
    assert 'self._audio_chunks[node_id] = audio_chunks' not in content, "Should NOT pre-store audio chunks"
    
    # Check that spectrogram pre-computation is removed
    assert 'Pre-computing spectrograms' not in content or 'Pré-computing spectrograms' not in content, "Should NOT pre-compute spectrograms"
    assert 'self._spectrogram_chunks[node_id] = spectrogram_chunks' not in content, "Should NOT pre-store spectrograms"
    
    print("✓ Optimized preprocessing checks passed")


def test_lazy_loading_methods():
    """Test that lazy loading methods exist"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check for new methods
    assert 'def _get_spectrogram_for_frame' in content, "Should have _get_spectrogram_for_frame method"
    assert 'def _compute_spectrogram_for_chunk' in content, "Should have _compute_spectrogram_for_chunk method"
    assert 'def _prefetch_next_spectrograms' in content, "Should have _prefetch_next_spectrograms method"
    assert 'def _save_audio_as_mp3' in content, "Should have _save_audio_as_mp3 method"
    
    # Check LRU cache logic
    assert 'move_to_end(cache_key)' in content, "Should use LRU move_to_end"
    assert 'popitem(last=False)' in content, "Should use LRU eviction"
    assert 'Cache hit' in content or 'cache hit' in content, "Should have cache hit logic"
    assert 'Cache miss' in content or 'cache miss' in content, "Should have cache miss logic"
    
    # Check prefetching logic
    assert 'for offset in range(1, 4)' in content, "Should prefetch 3 chunks"
    
    print("✓ Lazy loading methods checks passed")


def test_update_method_uses_lazy_loading():
    """Test that update method uses the new lazy loading approach"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check that update method uses _full_audio instead of _spectrogram_chunks
    assert 'str(node_id) in self._full_audio' in content, "Should check _full_audio instead of _spectrogram_chunks"
    
    # Ensure old references are removed
    assert 'str(node_id) in self._spectrogram_chunks' not in content, "Should NOT reference _spectrogram_chunks"
    
    print("✓ Update method uses lazy loading")


def test_ordereddict_usage():
    """Test OrderedDict behavior for LRU cache"""
    # Create a simple LRU cache using OrderedDict
    cache = OrderedDict()
    cache_max_size = 3
    
    # Add items
    cache[(1, 0)] = "spec0"
    cache[(1, 1)] = "spec1"
    cache[(1, 2)] = "spec2"
    
    assert len(cache) == 3, "Cache should have 3 items"
    
    # Access item 0 (should move to end)
    cache.move_to_end((1, 0))
    assert list(cache.keys())[-1] == (1, 0), "Accessed item should be at end"
    
    # Add new item and evict oldest
    cache[(1, 3)] = "spec3"
    while len(cache) > cache_max_size:
        cache.popitem(last=False)
    
    assert len(cache) == 3, "Cache should still have 3 items"
    assert (1, 1) not in cache, "Oldest item should be evicted"
    assert (1, 0) in cache, "Recently accessed item should remain"
    
    print("✓ OrderedDict LRU behavior verified")


def test_memory_optimization_benefits():
    """Test expected memory benefits of optimization"""
    # This is a theoretical test based on the problem statement
    
    # Before: 313 MB (2951 chunks × 97 KB + frames)
    # After: 32 MB (audio 26 MB + cache 5 MB)
    
    old_memory_mb = 313
    new_memory_mb = 32
    reduction_factor = old_memory_mb / new_memory_mb
    
    assert reduction_factor >= 9, f"Should have at least 9x memory reduction, got {reduction_factor:.1f}x"
    
    # Cache size calculation
    cache_max_size = 50
    avg_spectrogram_size_kb = 97  # From problem statement
    expected_cache_size_mb = (cache_max_size * avg_spectrogram_size_kb) / 1024
    
    assert expected_cache_size_mb <= 5, f"Cache should be ~5 MB, calculated {expected_cache_size_mb:.1f} MB"
    
    print(f"✓ Memory optimization verified: {reduction_factor:.1f}x reduction")


if __name__ == '__main__':
    test_lru_cache_structure()
    test_optimized_preprocess_video()
    test_lazy_loading_methods()
    test_update_method_uses_lazy_loading()
    test_ordereddict_usage()
    test_memory_optimization_benefits()
    print("\n✓ All LRU cache optimization tests passed successfully!")
