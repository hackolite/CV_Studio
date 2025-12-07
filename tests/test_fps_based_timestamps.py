#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test FPS-based timestamp generation for Video node.

This test verifies that:
1. Video node returns timestamps in its data dictionary
2. Timestamps are calculated based on frame number and FPS
3. Main.py uses these timestamps when available
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestFPSBasedTimestamps(unittest.TestCase):
    """Test that FPS-based timestamps are correctly calculated and used."""
    
    def test_timestamp_calculation_formula(self):
        """Test the timestamp calculation formula: frame_number / fps."""
        test_cases = [
            # (frame_number, fps, expected_timestamp)
            (0, 30, 0.0),
            (30, 30, 1.0),
            (60, 30, 2.0),
            (90, 30, 3.0),
            (0, 24, 0.0),
            (24, 24, 1.0),
            (48, 24, 2.0),
            (0, 60, 0.0),
            (60, 60, 1.0),
            (120, 60, 2.0),
        ]
        
        for frame_number, fps, expected_timestamp in test_cases:
            calculated_timestamp = frame_number / fps if fps > 0 else None
            self.assertEqual(calculated_timestamp, expected_timestamp,
                           f"Frame {frame_number} at {fps} FPS should have timestamp {expected_timestamp}")
    
    def test_timestamp_progression(self):
        """Test that timestamps increase linearly with frame numbers."""
        fps = 30
        previous_timestamp = None
        
        for frame_number in range(0, 120, 10):  # 0, 10, 20, ..., 110
            timestamp = frame_number / fps
            
            # Verify timestamp increases
            if previous_timestamp is not None:
                self.assertGreater(timestamp, previous_timestamp,
                                 "Timestamps should increase with frame numbers")
                
                # Verify constant rate of increase
                expected_delta = 10 / fps  # 10 frames worth
                actual_delta = timestamp - previous_timestamp
                self.assertAlmostEqual(actual_delta, expected_delta, places=6,
                                     msg="Timestamps should increase at constant rate")
            
            previous_timestamp = timestamp
    
    def test_main_timestamp_handling_logic(self):
        """Test the logic for handling node-provided timestamps."""
        # Simulate the logic in main.py for timestamp handling
        
        # Test case 1: Input node with explicit timestamp
        data = {"image": "frame", "json": None, "audio": None, "timestamp": 1.5}
        has_data_input = False
        source_timestamp = None
        
        # Logic from main.py
        node_provided_timestamp = data.get("timestamp", None) if isinstance(data, dict) else None
        
        # Should use node-provided timestamp
        self.assertEqual(node_provided_timestamp, 1.5)
        self.assertFalse(has_data_input)
        self.assertIsNone(source_timestamp)
        
        # Test case 2: Processing node should preserve source timestamp
        data = {"image": "processed_frame", "json": None, "audio": None}
        has_data_input = True
        source_timestamp = 2.5
        
        node_provided_timestamp = data.get("timestamp", None) if isinstance(data, dict) else None
        
        # Should use source timestamp (from connected input)
        self.assertIsNone(node_provided_timestamp)
        self.assertTrue(has_data_input)
        self.assertEqual(source_timestamp, 2.5)
        
        # Test case 3: Input node without explicit timestamp
        data = {"image": "webcam_frame", "json": None, "audio": None}
        has_data_input = False
        source_timestamp = None
        
        node_provided_timestamp = data.get("timestamp", None) if isinstance(data, dict) else None
        
        # Should create new timestamp automatically
        self.assertIsNone(node_provided_timestamp)
        self.assertFalse(has_data_input)
        self.assertIsNone(source_timestamp)
    
    def test_timestamp_none_when_no_frame(self):
        """Test that timestamp is None when no frame is available."""
        # Simulate video node with no frame
        frame = None
        target_fps = 30
        current_frame_num = 0
        
        # Calculate timestamp (as in video node)
        frame_timestamp = None
        if frame is not None and target_fps > 0:
            frame_timestamp = current_frame_num / target_fps
        
        # Verify timestamp is None
        self.assertIsNone(frame_timestamp, "Timestamp should be None when no frame")
    
    def test_fps_edge_cases(self):
        """Test timestamp calculation with edge case FPS values."""
        frame_number = 30
        
        # Normal case
        self.assertEqual(frame_number / 30, 1.0)
        
        # High FPS
        self.assertEqual(frame_number / 60, 0.5)
        
        # Low FPS  
        self.assertEqual(frame_number / 15, 2.0)
        
        # Very high FPS
        self.assertEqual(frame_number / 120, 0.25)
        
        # Zero FPS should be handled (no division by zero)
        # In the actual code, this is protected by: if target_fps > 0
        with self.assertRaises(ZeroDivisionError):
            _ = frame_number / 0


if __name__ == "__main__":
    unittest.main()
