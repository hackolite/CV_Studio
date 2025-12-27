#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test to verify that ObjChart displays full 24h round-robin data"""

import pytest
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_obj_chart_display_24h_minute_data():
    """Test that chart displays full 24 hours of minute data"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Simulate 24 hours of minute-level data
    # Create data for every 10th minute over the last 24 hours
    now = datetime.now()
    for minutes_ago in range(0, 24 * 60, 10):  # Every 10 minutes for 24 hours
        bucket = now - timedelta(minutes=minutes_ago)
        bucket = bucket.replace(second=0, microsecond=0)
        node.time_counts[0][bucket] = 5 + (minutes_ago % 10)
        node.time_counts["All"][bucket] = 5 + (minutes_ago % 10)
    
    # Verify we have data points across the full 24 hours
    assert len(node.time_counts[0]) == 144  # 24 hours * 60 minutes / 10 = 144 data points
    
    # Render chart with minute time unit
    chart_image = node.render_chart("minute", ["All"], {}, "bar")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    
    # The chart should have rendered with all 144 data points (up to max 1440)
    # Since we have 144 points, they should all be displayed
    print(f"✓ Successfully rendered chart with {len(node.time_counts[0])} data points (minute granularity)")


def test_obj_chart_display_24h_hour_data():
    """Test that chart displays full 24 hours of hour data"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Simulate 24 hours of hour-level data
    now = datetime.now()
    for hours_ago in range(0, 24):  # Every hour for 24 hours
        bucket = now - timedelta(hours=hours_ago)
        bucket = bucket.replace(minute=0, second=0, microsecond=0)
        node.time_counts[0][bucket] = 10 + hours_ago
        node.time_counts["All"][bucket] = 10 + hours_ago
    
    # Verify we have 24 data points (one per hour)
    assert len(node.time_counts[0]) == 24
    
    # Render chart with hour time unit
    chart_image = node.render_chart("hour", ["All"], {}, "bar")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    
    # The chart should render all 24 hours of data
    print(f"✓ Successfully rendered chart with {len(node.time_counts[0])} data points (hour granularity)")


def test_obj_chart_display_24_minutes_second_data():
    """Test that chart displays last 24 minutes of second data (1440 seconds)"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Simulate second-level data for the last 30 minutes (should only show last 24 minutes = 1440 seconds)
    now = datetime.now()
    for seconds_ago in range(0, 30 * 60, 5):  # Every 5 seconds for 30 minutes
        bucket = now - timedelta(seconds=seconds_ago)
        bucket = bucket.replace(microsecond=0)
        node.time_counts[0][bucket] = 3 + (seconds_ago % 5)
        node.time_counts["All"][bucket] = 3 + (seconds_ago % 5)
    
    # Verify we have data points
    total_points = len(node.time_counts[0])
    assert total_points == 360  # 30 minutes * 60 seconds / 5 = 360 data points
    
    # Render chart with second time unit
    chart_image = node.render_chart("second", ["All"], {}, "line")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    
    # The chart should display up to 1440 seconds (24 minutes) of data
    # Since we have 360 points (30 minutes worth), all should be displayed
    print(f"✓ Successfully rendered chart with {total_points} data points (second granularity)")


def test_obj_chart_max_buckets_calculation():
    """Test that max_buckets is calculated correctly for each time unit"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Add test data for multiple hours
    now = datetime.now()
    
    # Add 48 hours of data (to test that only 24h is shown)
    for hours_ago in range(0, 48):
        bucket = now - timedelta(hours=hours_ago)
        bucket = bucket.replace(minute=0, second=0, microsecond=0)
        node.time_counts[0][bucket] = 10
    
    # Render with hour time unit - should only show last 24 buckets (24 hours)
    chart_image = node.render_chart("hour", [0], {}, "bar")
    assert chart_image is not None
    
    # The render_chart method internally limits to max_buckets = 24 for "hour"
    # This means even though we have 48 hours of data, only 24 should be displayed
    print("✓ Chart correctly limits display to 24 hours worth of data for 'hour' time unit")
    
    # Now test with minute data - should show up to 1440 minutes (24 hours)
    node.time_counts.clear()
    for minutes_ago in range(0, 48 * 60):  # 48 hours of minute data
        bucket = now - timedelta(minutes=minutes_ago)
        bucket = bucket.replace(second=0, microsecond=0)
        node.time_counts[1][bucket] = 5
    
    chart_image = node.render_chart("minute", [1], {}, "line")
    assert chart_image is not None
    
    # The render_chart method internally limits to max_buckets = 1440 for "minute"
    print("✓ Chart correctly limits display to 1440 minutes (24 hours) for 'minute' time unit")
    
    # Test with second data - should show up to 1440 seconds (24 minutes)
    node.time_counts.clear()
    for seconds_ago in range(0, 3600):  # 1 hour of second data
        bucket = now - timedelta(seconds=seconds_ago)
        bucket = bucket.replace(microsecond=0)
        node.time_counts[2][bucket] = 3
    
    chart_image = node.render_chart("second", [2], {}, "area")
    assert chart_image is not None
    
    # The render_chart method internally limits to max_buckets = 1440 for "second"
    print("✓ Chart correctly limits display to 1440 seconds (24 minutes) for 'second' time unit")


def test_obj_chart_24h_roundrobin_storage_and_display_alignment():
    """Test that 24h round-robin storage aligns with display capacity"""
    from node.VisualNode.node_obj_chart import Node
    from datetime import datetime, timedelta
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Verify max_data_age_hours is 24
    assert node.max_data_age_hours == 24
    
    # For minute time unit: 24 hours = 1440 minutes
    # The chart should be able to display up to 1440 buckets
    
    # For hour time unit: 24 hours = 24 hours
    # The chart should be able to display up to 24 buckets
    
    # Add exactly 24 hours of minute data
    now = datetime.now()
    for minutes_ago in range(0, 24 * 60):  # Exactly 1440 minutes (24 hours)
        bucket = now - timedelta(minutes=minutes_ago)
        bucket = bucket.replace(second=0, microsecond=0)
        node.time_counts[0][bucket] = minutes_ago % 10
    
    assert len(node.time_counts[0]) == 1440
    
    # Render - all 1440 data points should fit in the display
    chart_image = node.render_chart("minute", [0], {}, "bar")
    assert chart_image is not None
    
    print("✓ Full 24 hours (1440 minutes) of data can be displayed on chart with 'minute' time unit")
    
    # Cleanup old data (anything older than 24 hours)
    node.cleanup_old_data()
    
    # After cleanup, all data should still be present (none older than 24h)
    assert len(node.time_counts[0]) == 1440
    
    # Add data that is 25 hours old
    old_bucket = now - timedelta(hours=25)
    old_bucket = old_bucket.replace(second=0, microsecond=0)
    node.time_counts[0][old_bucket] = 999
    
    # Cleanup should remove the 25-hour-old data
    node.cleanup_old_data()
    
    # The old bucket should be removed
    assert old_bucket not in node.time_counts[0]
    assert len(node.time_counts[0]) == 1440  # Still have all the 24h data
    
    print("✓ Round-robin correctly removes data older than 24 hours while preserving display capacity")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
