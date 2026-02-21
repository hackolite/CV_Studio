#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Decibel node (AudioProcessNode)"""

import os
import sys
import unittest.mock as mock
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dearpygui and related modules before any node imports
sys.modules.setdefault('dearpygui', mock.MagicMock())
sys.modules.setdefault('dearpygui.dearpygui', mock.MagicMock())
sys.modules.setdefault('node_editor', mock.MagicMock())
sys.modules.setdefault('node_editor.util', mock.MagicMock())
sys.modules.setdefault('node.node_abc', mock.MagicMock())


def test_decibel_node_exists():
    """Test that the decibel node file exists"""
    node_path = os.path.join(
        os.path.dirname(__file__), '..',
        'node', 'AudioProcessNode', 'node_decibel.py'
    )
    assert os.path.exists(node_path), "node_decibel.py should exist"
    print("✓ node_decibel.py exists")


def test_compute_db_sine():
    """Test that compute_db returns correct dBFS for a known signal"""
    from node.AudioProcessNode.node_decibel import compute_db

    # 0.5-amplitude sine: RMS = 0.5/sqrt(2) ≈ 0.3536 → ~-9.03 dBFS
    sine = 0.5 * np.sin(np.linspace(0, 2 * np.pi, 22050)).astype(np.float32)
    db = compute_db(sine)
    assert db is not None, "compute_db should return a value for valid audio"
    assert abs(db - (-9.03)) < 0.1, f"Expected ~-9.03 dBFS, got {db:.2f}"
    print(f"✓ compute_db(0.5 sine) = {db:.2f} dBFS")


def test_compute_db_silence():
    """Test that compute_db handles near-silence (clips to MIN_RMS)"""
    from node.AudioProcessNode.node_decibel import compute_db

    silence = np.zeros(1000, dtype=np.float32)
    db = compute_db(silence)
    assert db is not None, "compute_db should not return None for silence"
    assert db <= -100.0, f"Silence should yield very low dB, got {db:.2f}"
    print(f"✓ compute_db(silence) = {db:.2f} dBFS (very low as expected)")


def test_compute_db_none():
    """Test that compute_db returns None for None input"""
    from node.AudioProcessNode.node_decibel import compute_db

    assert compute_db(None) is None, "compute_db(None) should return None"
    print("✓ compute_db(None) returns None")


def test_compute_db_empty():
    """Test that compute_db returns None for empty array"""
    from node.AudioProcessNode.node_decibel import compute_db

    assert compute_db(np.array([])) is None, "compute_db([]) should return None"
    print("✓ compute_db([]) returns None")


def test_compute_db_full_scale():
    """Test that a full-scale sine (amplitude 1.0) gives ≈ -3 dBFS"""
    from node.AudioProcessNode.node_decibel import compute_db

    full_scale = np.sin(np.linspace(0, 2 * np.pi, 22050)).astype(np.float32)
    db = compute_db(full_scale)
    assert db is not None
    # RMS of sine = 1/sqrt(2) → 20*log10(1/sqrt(2)) ≈ -3.01 dBFS
    assert abs(db - (-3.01)) < 0.1, f"Expected ~-3.01 dBFS, got {db:.2f}"
    print(f"✓ compute_db(full-scale sine) = {db:.2f} dBFS")


def test_decibel_node_instantiation():
    """Test that the Node class can be instantiated without dpg"""
    from node.AudioProcessNode.node_decibel import Node

    node = Node()
    assert node is not None, "Node should be instantiable"
    assert node.node_label == 'Decibel', "Node label should be 'Decibel'"
    assert node.node_tag == 'Decibel', "Node tag should be 'Decibel'"
    assert isinstance(node.db_history, dict), "db_history should be a dict"
    print("✓ Decibel Node can be instantiated")


def test_db_history_round_robin():
    """Test that old data is cleaned up (round-robin over 60 seconds)"""
    from node.AudioProcessNode.node_decibel import Node, WINDOW_SECONDS
    from datetime import datetime, timedelta

    node = Node()
    now = datetime.now().replace(microsecond=0)

    # Insert a bucket that is exactly WINDOW_SECONDS old (should be removed)
    old_bucket = now - timedelta(seconds=WINDOW_SECONDS + 1)
    node.db_history[old_bucket] = -50.0

    # Insert a recent bucket (should be kept)
    recent_bucket = now - timedelta(seconds=5)
    node.db_history[recent_bucket] = -20.0

    node._cleanup_old_data()

    assert old_bucket not in node.db_history, "Old bucket should be removed"
    assert recent_bucket in node.db_history, "Recent bucket should be kept"
    print(f"✓ Round-robin cleanup works (window = {WINDOW_SECONDS}s)")


if __name__ == '__main__':
    SEPARATOR = "=" * 70
    print(SEPARATOR)
    print("Testing Decibel Node")
    print(SEPARATOR)

    test_decibel_node_exists()
    test_compute_db_sine()
    test_compute_db_silence()
    test_compute_db_none()
    test_compute_db_empty()
    test_compute_db_full_scale()
    test_decibel_node_instantiation()
    test_db_history_round_robin()

    print(SEPARATOR)
    print("All tests passed! ✓")
    print(SEPARATOR)
