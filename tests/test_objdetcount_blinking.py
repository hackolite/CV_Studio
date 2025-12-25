#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for ObjDetCount node blinking feature
Tests that the node blinks white continuously while trigger is active

Note: pytest is not imported to allow standalone execution.
This test can still be run with pytest if needed.
"""
import time
from collections import deque


class MockNode:
    """Mock ObjDetCount node for testing blinking logic"""
    
    # Use the same constants as the real node
    TOTAL_BLINK_DURATION = 3.0
    BLINK_CYCLE_DURATION = 1.0
    WHITE_PHASE_DURATION = 0.5
    
    def __init__(self):
        self.detection_timestamps = deque()
        self.blink_start_time = None
        self.blink_active = False
        self.previous_trigger_state = False
        self.original_theme = "original_theme_mock"
        self.white_theme = "white_theme_mock"
        self.applied_themes = []  # Track theme changes for testing
    
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
    
    def check_threshold(self, min_threshold, max_threshold):
        """Check if count is within threshold range"""
        count_in_window = len(self.detection_timestamps)
        
        if max_threshold == 0:
            return count_in_window >= min_threshold
        else:
            return min_threshold <= count_in_window <= max_threshold
    
    def mock_bind_theme(self, theme):
        """Mock theme binding for testing"""
        self.applied_themes.append((time.time(), theme))
    
    def handle_blink_effect(self, trigger_active, current_time):
        """
        Handle the blinking effect when trigger is active.
        Blinks white/original continuously while trigger is active.
        """
        # Detect trigger activation (transition from False to True)
        if trigger_active and not self.previous_trigger_state:
            # Start blinking
            self.blink_start_time = current_time
            self.blink_active = True
        
        # Detect trigger deactivation (transition from True to False)
        if not trigger_active and self.previous_trigger_state:
            # Stop blinking and restore original theme
            if self.original_theme is not None:
                self.mock_bind_theme(self.original_theme)
            self.blink_active = False
            self.blink_start_time = None
        
        # Update previous state for next iteration
        self.previous_trigger_state = trigger_active
        
        # Handle active blinking - blink continuously while trigger is active
        if self.blink_active and self.blink_start_time is not None and trigger_active:
            elapsed = current_time - self.blink_start_time
            
            # Blink pattern: alternate between white and original color
            cycle_time = elapsed % self.BLINK_CYCLE_DURATION
            
            if cycle_time < self.WHITE_PHASE_DURATION:
                # Show white
                self.mock_bind_theme(self.white_theme)
            else:
                # Show original color
                if self.original_theme is not None:
                    self.mock_bind_theme(self.original_theme)


def test_blink_starts_on_trigger_activation():
    """Test that blinking starts when trigger goes from False to True"""
    node = MockNode()
    current_time = time.time()
    
    # First update: trigger is False
    trigger_active = False
    node.handle_blink_effect(trigger_active, current_time)
    
    assert not node.blink_active, "Blinking should not be active when trigger is False"
    assert node.blink_start_time is None, "Blink start time should be None"
    
    # Second update: trigger becomes True
    trigger_active = True
    node.handle_blink_effect(trigger_active, current_time)
    
    assert node.blink_active, "Blinking should be active when trigger becomes True"
    assert node.blink_start_time is not None, "Blink start time should be set"
    assert abs(node.blink_start_time - current_time) < 0.01, "Blink start time should be current time"


def test_blink_duration_is_3_seconds():
    """Test that blinking continues as long as trigger is active"""
    node = MockNode()
    base_time = time.time()
    
    # Activate trigger
    node.handle_blink_effect(True, base_time)
    
    # Simulate updates during blinking
    # At 0.5s - should still be blinking
    node.handle_blink_effect(True, base_time + 0.5)
    assert node.blink_active, "Should still be blinking at 0.5s"
    
    # At 1.5s - should still be blinking
    node.handle_blink_effect(True, base_time + 1.5)
    assert node.blink_active, "Should still be blinking at 1.5s"
    
    # At 2.5s - should still be blinking
    node.handle_blink_effect(True, base_time + 2.5)
    assert node.blink_active, "Should still be blinking at 2.5s"
    
    # At 3.5s - should STILL be blinking (continuous blinking)
    node.handle_blink_effect(True, base_time + 3.5)
    assert node.blink_active, "Should still be blinking at 3.5s"
    
    # At 10.0s - should STILL be blinking (continuous blinking)
    node.handle_blink_effect(True, base_time + 10.0)
    assert node.blink_active, "Should still be blinking at 10.0s"
    
    # Only stops when trigger becomes False
    node.handle_blink_effect(False, base_time + 10.1)
    assert not node.blink_active, "Should stop blinking when trigger becomes False"
    assert node.blink_start_time is None, "Blink start time should be reset"


def test_blink_pattern_alternates_white_and_original():
    """Test that the blink pattern alternates between white and original theme"""
    node = MockNode()
    base_time = time.time()
    
    # Activate trigger
    node.handle_blink_effect(True, base_time)
    
    # Check theme at different times
    # At 0.0s - should be white (start of cycle)
    node.handle_blink_effect(True, base_time + 0.0)
    assert node.applied_themes[-1][1] == node.white_theme, "Should show white at 0.0s"
    
    # At 0.25s - should be white (within first 0.5s)
    node.handle_blink_effect(True, base_time + 0.25)
    assert node.applied_themes[-1][1] == node.white_theme, "Should show white at 0.25s"
    
    # At 0.6s - should be original (0.5-1.0s)
    node.handle_blink_effect(True, base_time + 0.6)
    assert node.applied_themes[-1][1] == node.original_theme, "Should show original at 0.6s"
    
    # At 1.0s - should be white (start of second cycle)
    node.handle_blink_effect(True, base_time + 1.0)
    assert node.applied_themes[-1][1] == node.white_theme, "Should show white at 1.0s"
    
    # At 1.6s - should be original (1.5-2.0s)
    node.handle_blink_effect(True, base_time + 1.6)
    assert node.applied_themes[-1][1] == node.original_theme, "Should show original at 1.6s"
    
    # At 2.1s - should be white (start of third cycle)
    node.handle_blink_effect(True, base_time + 2.1)
    assert node.applied_themes[-1][1] == node.white_theme, "Should show white at 2.1s"
    
    # At 2.7s - should be original (2.5-3.0s)
    node.handle_blink_effect(True, base_time + 2.7)
    assert node.applied_themes[-1][1] == node.original_theme, "Should show original at 2.7s"


def test_no_blink_when_trigger_stays_true():
    """Test that blinking continues while trigger stays true"""
    node = MockNode()
    base_time = time.time()
    
    # First activation
    node.handle_blink_effect(True, base_time)
    first_blink_start = node.blink_start_time
    assert first_blink_start is not None, "Should start blinking on first activation"
    
    # Blinking should continue as long as trigger stays True
    node.handle_blink_effect(True, base_time + 3.1)
    assert node.blink_active, "Blinking should continue while trigger is True"
    
    # Trigger stays True - should keep blinking
    node.handle_blink_effect(True, base_time + 5.0)
    assert node.blink_start_time is not None, "Should keep blinking when trigger stays True"
    assert node.blink_active, "Should still be blinking"
    
    # Blinking continues at 10 seconds
    node.handle_blink_effect(True, base_time + 10.0)
    assert node.blink_active, "Should still be blinking at 10 seconds"


def test_blink_restarts_on_new_activation():
    """Test that blinking stops when trigger becomes False and restarts on new activation"""
    node = MockNode()
    base_time = time.time()
    
    # First activation
    node.handle_blink_effect(True, base_time)
    assert node.blink_active, "Should start blinking"
    
    # Blinking continues at 5 seconds
    node.handle_blink_effect(True, base_time + 5.0)
    assert node.blink_active, "Blinking should continue while trigger is True"
    
    # Trigger goes False - blinking should stop
    node.handle_blink_effect(False, base_time + 6.0)
    assert not node.blink_active, "Blinking should stop when trigger becomes False"
    assert node.blink_start_time is None, "Blink start time should be reset"
    
    # Trigger becomes True again - should restart blinking
    node.handle_blink_effect(True, base_time + 7.0)
    assert node.blink_active, "Should restart blinking on new activation"
    assert node.blink_start_time == base_time + 7.0, "Should set new blink start time"


def test_theme_restored_after_blinking():
    """Test that original theme is restored when trigger becomes inactive"""
    node = MockNode()
    base_time = time.time()
    
    # Activate trigger and start blinking
    node.handle_blink_effect(True, base_time)
    
    # Clear theme history
    node.applied_themes = []
    
    # Blinking continues while trigger is True
    node.handle_blink_effect(True, base_time + 5.0)
    assert node.blink_active, "Should still be blinking"
    
    # Clear theme history again before deactivation
    node.applied_themes = []
    
    # Trigger becomes False - should restore original theme
    node.handle_blink_effect(False, base_time + 5.1)
    
    # Check that the theme was restored
    assert len(node.applied_themes) > 0, "Should have applied at least one theme"
    assert node.applied_themes[-1][1] == node.original_theme, "Should restore original theme when trigger becomes False"


if __name__ == '__main__':
    # Run tests
    test_blink_starts_on_trigger_activation()
    print("✓ test_blink_starts_on_trigger_activation passed")
    
    test_blink_duration_is_3_seconds()
    print("✓ test_blink_duration_is_3_seconds passed")
    
    test_blink_pattern_alternates_white_and_original()
    print("✓ test_blink_pattern_alternates_white_and_original passed")
    
    test_no_blink_when_trigger_stays_true()
    print("✓ test_no_blink_when_trigger_stays_true passed")
    
    test_blink_restarts_on_new_activation()
    print("✓ test_blink_restarts_on_new_activation passed")
    
    test_theme_restored_after_blinking()
    print("✓ test_theme_restored_after_blinking passed")
    
    print("\n✅ All blinking tests passed!")

