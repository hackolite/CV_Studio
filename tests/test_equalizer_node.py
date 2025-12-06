#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for the Equalizer node"""

import os
import sys
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_equalizer_node_exists():
    """Test that the equalizer node file exists"""
    equalizer_node_path = os.path.join(
        os.path.dirname(__file__), '..', 
        'node', 'AudioProcessNode', 'node_equalizer.py'
    )
    assert os.path.exists(equalizer_node_path), "node_equalizer.py should exist"
    print("✓ node_equalizer.py exists")


def test_equalizer_import():
    """Test that the equalizer node can be imported"""
    from node.AudioProcessNode.node_equalizer import FactoryNode, Node, apply_equalizer
    
    assert FactoryNode is not None, "FactoryNode should be importable"
    assert Node is not None, "Node should be importable"
    assert apply_equalizer is not None, "apply_equalizer should be importable"
    
    factory = FactoryNode()
    assert factory.node_label == 'Equalizer', "Node label should be 'Equalizer'"
    assert factory.node_tag == 'Equalizer', "Node tag should be 'Equalizer'"
    
    print("✓ Equalizer node can be imported")
    print(f"  - Node label: {factory.node_label}")
    print(f"  - Node tag: {factory.node_tag}")


def test_equalizer_function():
    """Test the equalizer processing function"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    # Create test audio signal (1 second at 22050 Hz)
    sample_rate = 22050
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # Create a signal with multiple frequencies
    # 100 Hz (bass), 400 Hz (mid-bass), 1000 Hz (mid), 4000 Hz (mid-treble), 8000 Hz (treble)
    audio_data = (
        np.sin(2 * np.pi * 100 * t) +
        np.sin(2 * np.pi * 400 * t) +
        np.sin(2 * np.pi * 1000 * t) +
        np.sin(2 * np.pi * 4000 * t) +
        np.sin(2 * np.pi * 8000 * t)
    )
    audio_data = audio_data.astype(np.float32)
    
    # Test 1: Zero gains (no change expected except for filtering/reconstruction)
    gains_zero = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed = apply_equalizer(audio_data, sample_rate, gains_zero)
    assert processed is not None, "Processed audio should not be None"
    assert len(processed) == len(audio_data), "Output length should match input length"
    assert processed.dtype == np.float32, "Output should be float32"
    
    # Check that output is not all zeros
    assert np.max(np.abs(processed)) > 0.01, "Output should contain signal"
    
    print("✓ Equalizer with zero gains works")
    print(f"  - Input length: {len(audio_data)}")
    print(f"  - Output length: {len(processed)}")
    print(f"  - Output max amplitude: {np.max(np.abs(processed)):.4f}")
    
    # Test 2: Boost bass
    gains_bass_boost = {
        'bass': 10.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': 0.0
    }
    
    processed_bass = apply_equalizer(audio_data, sample_rate, gains_bass_boost)
    assert processed_bass is not None, "Processed audio with bass boost should not be None"
    assert len(processed_bass) == len(audio_data), "Output length should match input length"
    
    # Bass boost should increase amplitude (due to gain on bass frequencies)
    print("✓ Equalizer with bass boost works")
    print(f"  - Output max amplitude: {np.max(np.abs(processed_bass)):.4f}")
    
    # Test 3: Cut treble
    gains_treble_cut = {
        'bass': 0.0,
        'mid_bass': 0.0,
        'mid': 0.0,
        'mid_treble': 0.0,
        'treble': -20.0
    }
    
    processed_treble_cut = apply_equalizer(audio_data, sample_rate, gains_treble_cut)
    assert processed_treble_cut is not None, "Processed audio with treble cut should not be None"
    
    print("✓ Equalizer with treble cut works")
    print(f"  - Output max amplitude: {np.max(np.abs(processed_treble_cut)):.4f}")
    
    # Test 4: Normalization prevents clipping
    gains_extreme = {
        'bass': 20.0,
        'mid_bass': 20.0,
        'mid': 20.0,
        'mid_treble': 20.0,
        'treble': 20.0
    }
    
    processed_extreme = apply_equalizer(audio_data, sample_rate, gains_extreme)
    assert np.max(np.abs(processed_extreme)) <= 1.0, "Output should be normalized to prevent clipping"
    
    print("✓ Equalizer normalization prevents clipping")
    print(f"  - Output max amplitude (should be ≤ 1.0): {np.max(np.abs(processed_extreme)):.4f}")


def test_equalizer_edge_cases():
    """Test edge cases for the equalizer"""
    from node.AudioProcessNode.node_equalizer import apply_equalizer
    
    sample_rate = 22050
    
    # Test empty audio
    empty_audio = np.array([], dtype=np.float32)
    gains = {'bass': 0.0, 'mid_bass': 0.0, 'mid': 0.0, 'mid_treble': 0.0, 'treble': 0.0}
    processed = apply_equalizer(empty_audio, sample_rate, gains)
    assert len(processed) == 0, "Empty audio should return empty array"
    print("✓ Equalizer handles empty audio")
    
    # Test None audio
    processed_none = apply_equalizer(None, sample_rate, gains)
    assert processed_none is None, "None audio should return None"
    print("✓ Equalizer handles None audio")


def test_equalizer_node_instantiation():
    """Test that the Node class can be instantiated"""
    from node.AudioProcessNode.node_equalizer import Node
    
    node = Node()
    assert node is not None, "Node should be instantiable"
    assert node.node_label == 'Equalizer', "Node label should be 'Equalizer'"
    assert node.node_tag == 'Equalizer', "Node tag should be 'Equalizer'"
    
    print("✓ Equalizer Node can be instantiated")


# Constants
SEPARATOR_LENGTH = 70


if __name__ == '__main__':
    print("=" * SEPARATOR_LENGTH)
    print("Testing Equalizer Node")
    print("=" * SEPARATOR_LENGTH)
    
    test_equalizer_node_exists()
    print()
    
    test_equalizer_import()
    print()
    
    test_equalizer_function()
    print()
    
    test_equalizer_edge_cases()
    print()
    
    test_equalizer_node_instantiation()
    print()
    
    print("=" * SEPARATOR_LENGTH)
    print("All tests passed! ✓")
    print("=" * SEPARATOR_LENGTH)
