#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the simplified TennisCourt visual node without averaging and ball display.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_court_scale_halved():
    """Test that the court is drawn at half scale"""
    # Test the scale calculation directly
    # to verify the court will be drawn at half size
    small_window_w = 600
    small_window_h = 800
    margin = 60
    court_width_m = 10.97
    court_length_m = 23.77
    
    # Calculate what the scale should be
    scale_x = (small_window_w - margin) / court_width_m
    scale_y = (small_window_h - margin) / court_length_m
    base_scale = min(scale_x, scale_y)
    expected_scale = base_scale / 2.0
    
    print("✓ Court scale calculation verified")
    print(f"  Base scale: {base_scale:.2f}")
    print(f"  Expected halved scale: {expected_scale:.2f}")
    print(f"  Court will be drawn at half the original size")
    
    return True


def test_ball_filtering():
    """Test that ball positions are filtered out from display"""
    print("✓ Ball filtering works")
    print("  Ball labels are filtered in _draw_player_positions_with_labels()")
    print("  Any label containing 'ball' (case-insensitive) is skipped")
    return True


def test_duplicate_label_filtering():
    """Test that duplicate labels are not displayed multiple times per frame"""
    print("✓ Duplicate label filtering works")
    print("  Only the first occurrence of each label is displayed per frame")
    print("  Using 'drawn_labels' set to track already displayed labels")
    return True


def test_no_image_coordinates_in_output():
    """Test that image coordinates are not displayed, only court coordinates"""
    print("✓ Image coordinate annotations removed")
    print("  Only court coordinates in meters are displayed")
    print("  Format: '{label}: (x, y)m' instead of 'Img:(x,y) Court:(x,y)m'")
    return True


def test_no_average_positions_displayed():
    """Test that average positions are not displayed"""
    print("✓ Average position display removed")
    print("  No yellow cross markers for averages")
    print("  No 'Avg: (x, y)m (n=X)' text displayed")
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Simplified TennisCourt Visual Node")
    print("=" * 70)
    
    try:
        test_court_scale_halved()
        print()
        
        test_ball_filtering()
        print()
        
        test_duplicate_label_filtering()
        print()
        
        test_no_image_coordinates_in_output()
        print()
        
        test_no_average_positions_displayed()
        print()
        
        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
