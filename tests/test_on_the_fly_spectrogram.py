#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for on-the-fly spectrogram generation with LRU cache"""

import pytest
import sys
import os
import numpy as np
from collections import OrderedDict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_ordereddict_import():
    """Test that OrderedDict is imported in node_video.py"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    assert 'from collections import OrderedDict' in content, "Should import OrderedDict"
    print("✓ OrderedDict import verified")


def test_lru_cache_storage_structure():
    """Test that new LRU cache storage attributes are defined"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check new storage attributes
    assert 'self._full_audio = {}' in content, "Should have _full_audio storage"
    assert 'self._spectrogram_cache = {}' in content, "Should have _spectrogram_cache storage"
    assert 'self._cache_max_size = 50' in content, "Should have _cache_max_size attribute"
    
    # Check old attributes are removed
    assert 'self._video_frames = {}' not in content, "Should NOT have _video_frames storage"
    assert 'self._audio_chunks = {}' not in content, "Should NOT have _audio_chunks storage"
    
    print("✓ LRU cache storage structure verified")


def test_preprocess_video_optimized():
    """Test that _preprocess_video is optimized (no frame extraction)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Should NOT extract all frames
    assert 'self._video_frames[node_id] = frames' not in content, "Should NOT store all frames"
    
    # Should store full audio
    assert 'self._full_audio[node_id] = y' in content, "Should store full audio"
    
    # Should initialize empty cache
    assert 'self._spectrogram_cache[node_id] = OrderedDict()' in content, "Should initialize empty cache"
    
    # Should NOT pre-compute spectrograms
    assert 'self._spectrogram_chunks[node_id] = spectrogram_chunks' not in content, "Should NOT pre-compute spectrograms"
    
    print("✓ Optimized _preprocess_video verified")


def test_compute_spectrogram_for_chunk_method():
    """Test that _compute_spectrogram_for_chunk method exists with correct parameters"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check method exists
    assert 'def _compute_spectrogram_for_chunk(self, node_id, chunk_index):' in content, \
        "Should have _compute_spectrogram_for_chunk method"
    
    # Check same rendering parameters
    assert 'binsize = 2**10' in content, "Should use binsize = 2**10"
    assert 'overlapFac=0.5' in content, "Should use overlapFac=0.5"
    assert 'window=np.hanning' in content, "Should use np.hanning window"
    assert 'factor=1.0' in content, "Should use factor=1.0"
    assert '20. * np.log10' in content, "Should use 20*log10 for dB conversion"
    assert 'apply_colormap_to_spectrogram' in content, "Should use apply_colormap_to_spectrogram"
    
    print("✓ _compute_spectrogram_for_chunk method verified")


def test_prefetch_method():
    """Test that _prefetch_next_spectrograms method exists"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    assert 'def _prefetch_next_spectrograms(self, node_id, current_chunk_index):' in content, \
        "Should have _prefetch_next_spectrograms method"
    
    # Check prefetch logic
    assert 'for offset in range(1, 4):' in content, "Should prefetch 3 chunks"
    
    print("✓ _prefetch_next_spectrograms method verified")


def test_get_spectrogram_for_frame_lru_cache():
    """Test that _get_spectrogram_for_frame uses LRU cache"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check cache hit logic
    assert 'self._spectrogram_cache[node_id].move_to_end(cache_key)' in content, \
        "Should update LRU with move_to_end"
    
    # Check cache miss logic
    assert 'self._compute_spectrogram_for_chunk(node_id, chunk_index)' in content, \
        "Should compute on cache miss"
    
    # Check prefetch call
    assert 'self._prefetch_next_spectrograms(node_id, chunk_index)' in content, \
        "Should call prefetch"
    
    # Check condition changed to _full_audio
    assert 'if node_id not in self._chunk_metadata or node_id not in self._full_audio:' in content, \
        "Should check _full_audio instead of _spectrogram_chunks"
    
    print("✓ LRU cache in _get_spectrogram_for_frame verified")


def test_save_audio_as_mp3_method():
    """Test that _save_audio_as_mp3 method is extracted"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    assert 'def _save_audio_as_mp3(self, node_id, movie_path, y, sr):' in content, \
        "Should have _save_audio_as_mp3 method"
    
    print("✓ _save_audio_as_mp3 method verified")


def test_update_method_checks_full_audio():
    """Test that update() method checks _full_audio instead of _spectrogram_chunks"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    assert 'if show_spectrogram and str(node_id) in self._full_audio:' in content, \
        "Should check _full_audio in update()"
    
    print("✓ update() method checks _full_audio verified")


def test_metadata_structure():
    """Test that chunk_metadata has the correct structure"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check metadata includes required fields
    assert "'fps': fps" in content, "Should include fps in metadata"
    assert "'sr': sr" in content, "Should include sr in metadata"
    assert "'chunk_duration': chunk_duration" in content, "Should include chunk_duration in metadata"
    assert "'step_duration': step_duration" in content, "Should include step_duration in metadata"
    assert "'num_frames': num_frames" in content, "Should include num_frames in metadata"
    
    print("✓ Metadata structure verified")


if __name__ == '__main__':
    test_ordereddict_import()
    test_lru_cache_storage_structure()
    test_preprocess_video_optimized()
    test_compute_spectrogram_for_chunk_method()
    test_prefetch_method()
    test_get_spectrogram_for_frame_lru_cache()
    test_save_audio_as_mp3_method()
    test_update_method_checks_full_audio()
    test_metadata_structure()
    print("\n✓ All on-the-fly spectrogram tests passed successfully!")
