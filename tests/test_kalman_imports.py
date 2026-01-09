#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify that the Kalman Filter tracker can be imported from the mot module
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing Kalman Filter imports from different paths...")

# Test 1: Import from kalman module
from node.TrackerNode.mot.kalman import MultiClassKalmanFilter
print("✓ Successfully imported from node.TrackerNode.mot.kalman")

# Test 2: Import directly from mc_kalman
from node.TrackerNode.mot.kalman.mc_kalman import MultiClassKalmanFilter as MCK
print("✓ Successfully imported from node.TrackerNode.mot.kalman.mc_kalman")

# Test 3: Verify they're the same class
assert MultiClassKalmanFilter == MCK, "Class mismatch between import paths"
print("✓ Both import paths reference the same class")

# Test 4: Create an instance
tracker = MultiClassKalmanFilter()
print("✓ Successfully instantiated MultiClassKalmanFilter")

# Test 5: Verify callable interface
assert callable(tracker), "Tracker is not callable"
print("✓ Tracker has callable interface")

print("\n" + "="*60)
print("SUCCESS: All Kalman Filter imports working correctly!")
print("="*60)
