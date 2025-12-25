#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for ObjDetCount trigger node
Tests the functionality of counting object detections and triggering based on thresholds
"""
import time
from collections import deque


class MockNode:
    """Mock ObjDetCount node for testing the core logic"""
    
    def __init__(self):
        self.detection_timestamps = deque()
        self.current_class_names = {}
    
    def process_detections(self, class_ids, selected_class, current_time):
        """Process detections and add timestamps"""
        if class_ids:
            if selected_class == "All":
                count = len(class_ids)
                for _ in range(count):
                    self.detection_timestamps.append(current_time)
            elif ":" in selected_class:
                try:
                    target_class_id = int(selected_class.split(":")[0].strip())
                    count = sum(1 for cid in class_ids if int(cid) == target_class_id)
                    for _ in range(count):
                        self.detection_timestamps.append(current_time)
                except (ValueError, IndexError, TypeError):
                    # Skip invalid class format - expected when parsing class selection fails
                    pass
    
    def clean_old_timestamps(self, current_time, window_duration):
        """Clean up old timestamps outside the sliding window"""
        cutoff_time = current_time - window_duration
        while self.detection_timestamps and self.detection_timestamps[0] < cutoff_time:
            self.detection_timestamps.popleft()
    
    def check_threshold(self, min_threshold, max_threshold):
        """Check if count is within threshold range"""
        count_in_window = len(self.detection_timestamps)
        
        if max_threshold == 0:
            return count_in_window >= min_threshold
        else:
            return min_threshold <= count_in_window <= max_threshold


def test_detection_counting_all_classes():
    """Test counting all detected objects"""
    node = MockNode()
    current_time = time.time()
    
    # Simulate 5 detections
    class_ids = [0, 1, 2, 3, 4]
    node.process_detections(class_ids, "All", current_time)
    
    assert len(node.detection_timestamps) == 5
    assert node.check_threshold(0, 10) == True
    assert node.check_threshold(5, 10) == True
    assert node.check_threshold(6, 10) == False


def test_detection_counting_specific_class():
    """Test counting detections of a specific class"""
    node = MockNode()
    current_time = time.time()
    
    # Simulate detections: 3 persons (class 0), 2 cars (class 2)
    class_ids = [0, 0, 0, 2, 2]
    
    # Count only persons (class 0)
    node.process_detections(class_ids, "0: person", current_time)
    
    assert len(node.detection_timestamps) == 3
    assert node.check_threshold(3, 5) == True
    assert node.check_threshold(4, 5) == False


def test_sliding_window():
    """Test that old detections are removed from the sliding window"""
    node = MockNode()
    base_time = time.time()
    
    # Add detection at time 0
    node.detection_timestamps.append(base_time)
    
    # Add detection at time 2
    node.detection_timestamps.append(base_time + 2.0)
    
    # Add detection at time 4
    node.detection_timestamps.append(base_time + 4.0)
    
    assert len(node.detection_timestamps) == 3
    
    # Clean up with window of 3 seconds at time 6
    # This should remove detections older than time 3
    node.clean_old_timestamps(base_time + 6.0, 3.0)
    
    # Only the detection at time 4 should remain
    assert len(node.detection_timestamps) == 1


def test_threshold_no_upper_limit():
    """Test threshold checking with no upper limit (max_threshold = 0)"""
    node = MockNode()
    current_time = time.time()
    
    # Simulate 15 detections
    class_ids = list(range(15))
    node.process_detections(class_ids, "All", current_time)
    
    assert len(node.detection_timestamps) == 15
    
    # With max_threshold = 0, only minimum matters
    assert node.check_threshold(10, 0) == True
    assert node.check_threshold(20, 0) == False


def test_threshold_within_range():
    """Test threshold checking within a specific range"""
    node = MockNode()
    current_time = time.time()
    
    # Simulate 5 detections
    class_ids = [0, 1, 2, 3, 4]
    node.process_detections(class_ids, "All", current_time)
    
    assert len(node.detection_timestamps) == 5
    
    # Count should be within range [3, 7]
    assert node.check_threshold(3, 7) == True
    
    # Count should NOT be within range [6, 10]
    assert node.check_threshold(6, 10) == False
    
    # Count should NOT be within range [1, 4]
    assert node.check_threshold(1, 4) == False


def test_empty_detections():
    """Test behavior with no detections"""
    node = MockNode()
    current_time = time.time()
    
    # No detections
    class_ids = []
    node.process_detections(class_ids, "All", current_time)
    
    assert len(node.detection_timestamps) == 0
    
    # Should only trigger if min_threshold is 0
    assert node.check_threshold(0, 10) == True
    assert node.check_threshold(1, 10) == False


def test_accumulation_over_time():
    """Test that detections accumulate correctly over multiple frames"""
    node = MockNode()
    base_time = time.time()
    
    # Frame 1: 2 detections at time 0
    node.process_detections([0, 1], "All", base_time)
    assert len(node.detection_timestamps) == 2
    
    # Frame 2: 3 more detections at time 0.5
    node.process_detections([0, 1, 2], "All", base_time + 0.5)
    assert len(node.detection_timestamps) == 5
    
    # Clean with 5 second window at time 1.0 - all should remain
    node.clean_old_timestamps(base_time + 1.0, 5.0)
    assert len(node.detection_timestamps) == 5
    
    # Clean with 0.3 second window at time 1.0
    # Cutoff = 1.0 - 0.3 = 0.7
    # Timestamps at 0 and 0.5 are all < 0.7, so all will be removed
    node.clean_old_timestamps(base_time + 1.0, 0.3)
    assert len(node.detection_timestamps) == 0


def test_class_filtering():
    """Test filtering by different classes"""
    node = MockNode()
    current_time = time.time()
    
    # Mixed detections: persons, cars, and bicycles
    class_ids = [0, 0, 0, 1, 1, 2, 2, 2, 2]  # 3 persons, 2 bicycles, 4 cars
    
    # Test counting all
    node.process_detections(class_ids, "All", current_time)
    assert len(node.detection_timestamps) == 9
    
    # Reset and test counting only cars (class 2)
    node.detection_timestamps.clear()
    node.process_detections(class_ids, "2: car", current_time)
    assert len(node.detection_timestamps) == 4
    
    # Reset and test counting only bicycles (class 1)
    node.detection_timestamps.clear()
    node.process_detections(class_ids, "1: bicycle", current_time)
    assert len(node.detection_timestamps) == 2


if __name__ == '__main__':
    # Run tests
    test_detection_counting_all_classes()
    print("✓ test_detection_counting_all_classes passed")
    
    test_detection_counting_specific_class()
    print("✓ test_detection_counting_specific_class passed")
    
    test_sliding_window()
    print("✓ test_sliding_window passed")
    
    test_threshold_no_upper_limit()
    print("✓ test_threshold_no_upper_limit passed")
    
    test_threshold_within_range()
    print("✓ test_threshold_within_range passed")
    
    test_empty_detections()
    print("✓ test_empty_detections passed")
    
    test_accumulation_over_time()
    print("✓ test_accumulation_over_time passed")
    
    test_class_filtering()
    print("✓ test_class_filtering passed")
    
    print("\n✅ All tests passed!")
