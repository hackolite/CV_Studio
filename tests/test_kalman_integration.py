#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that the Kalman Filter tracker is properly integrated into node_mot.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing node_mot.py integration...")

# Test import from node_mot
from node.TrackerNode.node_mot import Node

# Verify that Kalman Filter is in the model class dictionary
node = Node()
print(f"\nAvailable trackers in MOT node: {list(node._model_class.keys())}")

assert 'Kalman Filter' in node._model_class, "Kalman Filter not found in model class dictionary"
print("✓ Kalman Filter is available in MOT node")

# Test instantiation via the model class
from node.TrackerNode.mot.kalman.mc_kalman import MultiClassKalmanFilter
tracker_class = node._model_class['Kalman Filter']
assert tracker_class == MultiClassKalmanFilter, "Kalman Filter class mismatch"
print("✓ Kalman Filter class is correctly mapped")

# Test that we can instantiate it
tracker = tracker_class()
print("✓ Kalman Filter can be instantiated through model class")

print("\n" + "="*60)
print("SUCCESS: Kalman Filter is properly integrated into node_mot.py!")
print("="*60)
