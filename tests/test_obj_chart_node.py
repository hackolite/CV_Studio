#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for ObjChart node"""

import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_obj_chart_node_import():
    """Test that ObjChart node can be imported"""
    from node.VisualNode.node_obj_chart import FactoryNode, Node
    
    assert FactoryNode.node_label == 'ObjChart'
    assert FactoryNode.node_tag == 'ObjChart'
    assert Node.node_label == 'ObjChart'
    assert Node.node_tag == 'ObjChart'


def test_obj_chart_time_bucket():
    """Test that time bucket calculation works correctly"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Test minute bucket
    minute_bucket = node.get_time_bucket("minute")
    assert minute_bucket.second == 0
    assert minute_bucket.microsecond == 0
    
    # Test hour bucket
    hour_bucket = node.get_time_bucket("hour")
    assert hour_bucket.minute == 0
    assert hour_bucket.second == 0
    assert hour_bucket.microsecond == 0


def test_obj_chart_render_empty():
    """Test that chart renders even with no data"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Render chart with no data (default bar chart)
    chart_image = node.render_chart("minute", ["All"], {}, "bar")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    assert len(chart_image.shape) == 3  # Should be a color image
    assert chart_image.shape[2] == 3  # Should have 3 channels (BGR)


def test_obj_chart_accumulation():
    """Test that detection counts accumulate correctly"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Simulate some detections
    bucket = node.get_time_bucket("minute")
    
    # Add counts for class 0
    node.time_counts[0][bucket] += 5
    node.time_counts["All"][bucket] += 5
    
    # Add counts for class 1
    node.time_counts[1][bucket] += 3
    node.time_counts["All"][bucket] += 3
    
    # Verify counts
    assert node.time_counts[0][bucket] == 5
    assert node.time_counts[1][bucket] == 3
    assert node.time_counts["All"][bucket] == 8


def test_obj_chart_render_with_data():
    """Test that chart renders correctly with accumulated data"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Add some test data
    bucket = node.get_time_bucket("minute")
    node.time_counts[0][bucket] = 10
    node.time_counts[1][bucket] = 5
    node.time_counts["All"][bucket] = 15
    
    # Render chart with data (bar chart)
    chart_image = node.render_chart("minute", [0, 1], {
        "0": "person",
        "1": "car"
    }, "bar")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    assert len(chart_image.shape) == 3
    assert chart_image.shape[2] == 3


def test_obj_chart_render_line_chart():
    """Test that line chart renders correctly"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Add some test data
    bucket = node.get_time_bucket("minute")
    node.time_counts[0][bucket] = 10
    node.time_counts[1][bucket] = 5
    
    # Render line chart
    chart_image = node.render_chart("minute", [0, 1], {
        "0": "person",
        "1": "car"
    }, "line")
    
    assert chart_image is not None
    assert isinstance(chart_image, np.ndarray)
    assert len(chart_image.shape) == 3
    assert chart_image.shape[2] == 3


def test_obj_chart_24h_cleanup():
    """Test that data older than 24 hours is cleaned up"""
    from node.VisualNode.node_obj_chart import Node
    from datetime import datetime, timedelta
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Add some old data (25 hours ago)
    old_bucket = datetime.now() - timedelta(hours=25)
    old_bucket = old_bucket.replace(second=0, microsecond=0)
    node.time_counts[0][old_bucket] = 100
    node.time_counts["All"][old_bucket] = 100
    
    # Add some recent data
    recent_bucket = node.get_time_bucket("minute")
    node.time_counts[0][recent_bucket] = 10
    node.time_counts["All"][recent_bucket] = 10
    
    # Verify old data exists before cleanup
    assert old_bucket in node.time_counts[0]
    assert old_bucket in node.time_counts["All"]
    
    # Run cleanup
    node.cleanup_old_data()
    
    # Verify old data is removed
    assert old_bucket not in node.time_counts[0]
    
    # Verify recent data still exists
    assert recent_bucket in node.time_counts[0]
    assert node.time_counts[0][recent_bucket] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
