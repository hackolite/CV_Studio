#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for ObjDetCount threshold crossing behavior
Tests that the trigger only activates when crossing thresholds (entering or leaving the range)
"""
import time
from collections import deque


class MockNode:
    """Mock ObjDetCount node for testing threshold crossing logic"""
    
    def __init__(self):
        self.detection_timestamps = deque()
        self.previous_within_threshold = False
    
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
                    pass
    
    def clean_old_timestamps(self, current_time, window_duration):
        """Clean up old timestamps outside the sliding window"""
        cutoff_time = current_time - window_duration
        while self.detection_timestamps and self.detection_timestamps[0] < cutoff_time:
            self.detection_timestamps.popleft()
    
    def check_within_threshold(self, min_threshold, max_threshold):
        """Check if count is within threshold range"""
        count_in_window = len(self.detection_timestamps)
        
        if max_threshold == 0:
            return count_in_window >= min_threshold
        else:
            return min_threshold <= count_in_window <= max_threshold
    
    def check_trigger_on_crossing(self, min_threshold, max_threshold):
        """
        Check if trigger should activate based on threshold crossing.
        Trigger activates only when crossing from outside→inside or inside→outside the threshold range.
        """
        within_threshold = self.check_within_threshold(min_threshold, max_threshold)
        
        # Trigger only on edge transitions
        trigger_active = (within_threshold != self.previous_within_threshold)
        
        # Update previous state
        self.previous_within_threshold = within_threshold
        
        return trigger_active, within_threshold, len(self.detection_timestamps)


def test_trigger_on_entering_threshold():
    """Test that trigger activates when entering threshold range"""
    node = MockNode()
    current_time = time.time()
    
    # Start with 0 detections (outside threshold [3, 7])
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert not trigger, "Should not trigger on first call (no state change yet)"
    assert not within, "Should be outside threshold with 0 detections"
    assert count == 0
    
    # Add 3 detections (enters threshold)
    node.process_detections([0, 1, 2], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert trigger, "Should trigger when entering threshold range"
    assert within, "Should be within threshold with 3 detections"
    assert count == 3
    
    # Add 1 more detection (stay within threshold)
    node.process_detections([3], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert not trigger, "Should NOT trigger while staying within threshold"
    assert within, "Should still be within threshold with 4 detections"
    assert count == 4


def test_trigger_on_leaving_threshold():
    """Test that trigger activates when leaving threshold range"""
    node = MockNode()
    current_time = time.time()
    
    # Start with 5 detections (within threshold [3, 7])
    node.process_detections([0, 1, 2, 3, 4], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    # First call will trigger because we go from outside (initial state=False) to inside
    # This is expected behavior - initial crossing into threshold
    assert trigger, "Should trigger on first call when entering threshold"
    assert within, "Should be within threshold"
    
    # Continue with 5 detections (stay within)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert not trigger, "Should NOT trigger while staying within threshold"
    assert within, "Should still be within threshold"
    
    # Go to 2 detections (leave threshold - below minimum)
    node.detection_timestamps.clear()
    node.process_detections([0, 1], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert trigger, "Should trigger when leaving threshold range"
    assert not within, "Should be outside threshold with 2 detections"
    assert count == 2


def test_trigger_on_exceeding_maximum():
    """Test that trigger activates when exceeding maximum threshold"""
    node = MockNode()
    current_time = time.time()
    
    # Start with 5 detections (within threshold [3, 7])
    node.process_detections([0, 1, 2, 3, 4], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    # First call will trigger because we enter threshold from initial state
    assert trigger, "Should trigger on first call when entering threshold"
    assert within, "Should be within threshold"
    
    # Add more detections to exceed maximum (go to 8)
    node.process_detections([5, 6, 7], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert trigger, "Should trigger when exceeding maximum threshold"
    assert not within, "Should be outside threshold with 8 detections"
    assert count == 8


def test_no_trigger_when_staying_outside_threshold():
    """Test that trigger does not activate while staying outside threshold"""
    node = MockNode()
    current_time = time.time()
    
    # Start with 1 detection (outside threshold [3, 7])
    node.process_detections([0], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert not trigger, "Should not trigger on first call"
    assert not within, "Should be outside threshold"
    
    # Continue with 2 detections (still outside)
    node.process_detections([1], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert not trigger, "Should NOT trigger while staying outside threshold"
    assert not within, "Should still be outside threshold"
    assert count == 2


def test_multiple_crossings():
    """Test multiple threshold crossings in sequence"""
    node = MockNode()
    current_time = time.time()
    
    # Start outside threshold
    node.process_detections([0], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert not trigger, "First call should not trigger"
    
    # Cross into threshold (1→3)
    node.process_detections([1, 2], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert trigger, "Should trigger on entering threshold"
    assert within
    
    # Stay within threshold
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert not trigger, "Should not trigger while staying within"
    assert within
    
    # Cross out above maximum (3→6)
    node.process_detections([3, 4, 5], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert trigger, "Should trigger on leaving threshold upward"
    assert not within
    
    # Stay outside
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert not trigger, "Should not trigger while staying outside"
    assert not within
    
    # Cross back into threshold (6→4)
    node.detection_timestamps.clear()
    node.process_detections([0, 1, 2, 3], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(3, 5)
    assert trigger, "Should trigger on re-entering threshold"
    assert within


def test_threshold_with_no_upper_limit():
    """Test threshold crossing with no upper limit (max_threshold = 0)"""
    node = MockNode()
    current_time = time.time()
    
    # Start with 2 detections (outside threshold min=5, max=0)
    node.process_detections([0, 1], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(5, 0)
    # First call: initial state is False, current state is False (outside), so no trigger
    assert not trigger, "Should not trigger when starting outside threshold"
    assert not within, "Should be outside threshold (below minimum)"
    
    # Cross into threshold (2→5)
    node.process_detections([2, 3, 4], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(5, 0)
    assert trigger, "Should trigger when crossing minimum threshold"
    assert within, "Should be within threshold with 5 detections"
    
    # Add more detections (stay within - no upper limit)
    node.process_detections([5, 6, 7], "All", current_time)
    trigger, within, count = node.check_trigger_on_crossing(5, 0)
    assert not trigger, "Should NOT trigger when staying above minimum (no max limit)"
    assert within, "Should still be within threshold"
    assert count == 8


def test_threshold_crossing_with_sliding_window():
    """Test that threshold crossings work correctly with the sliding window"""
    node = MockNode()
    base_time = time.time()
    window_duration = 2.0  # 2 second window
    
    # Add 5 detections at time 0 (within threshold [3, 7])
    for i in range(5):
        node.detection_timestamps.append(base_time)
    
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    # First call will trigger when entering threshold from initial state
    assert trigger, "First call should trigger when entering threshold"
    assert within
    
    # Time passes, some detections expire, count drops to 2
    node.clean_old_timestamps(base_time + 3.0, window_duration)
    # Remove all timestamps to simulate expiration
    node.detection_timestamps.clear()
    node.process_detections([0, 1], "All", base_time + 3.0)
    
    trigger, within, count = node.check_trigger_on_crossing(3, 7)
    assert trigger, "Should trigger when count drops below threshold due to sliding window"
    assert not within, "Should be outside threshold"
    assert count == 2


if __name__ == '__main__':
    # Run tests
    test_trigger_on_entering_threshold()
    print("✓ test_trigger_on_entering_threshold passed")
    
    test_trigger_on_leaving_threshold()
    print("✓ test_trigger_on_leaving_threshold passed")
    
    test_trigger_on_exceeding_maximum()
    print("✓ test_trigger_on_exceeding_maximum passed")
    
    test_no_trigger_when_staying_outside_threshold()
    print("✓ test_no_trigger_when_staying_outside_threshold passed")
    
    test_multiple_crossings()
    print("✓ test_multiple_crossings passed")
    
    test_threshold_with_no_upper_limit()
    print("✓ test_threshold_with_no_upper_limit passed")
    
    test_threshold_crossing_with_sliding_window()
    print("✓ test_threshold_crossing_with_sliding_window passed")
    
    print("\n✅ All threshold crossing tests passed!")
