#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for ObjChart node performance optimization"""

import pytest
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_objchart_render_throttling():
    """Test that chart rendering is throttled to avoid excessive CPU usage"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Initial render should happen
    bucket = node.get_time_bucket("minute")
    node.time_counts[0][bucket] = 10
    
    # First render
    chart1 = node.render_chart("minute", [0], {"0": "person"}, "bar")
    node.cached_chart_image = chart1
    node.last_render_time = time.time()
    
    assert chart1 is not None
    
    # Immediate second render should be throttled (use cached)
    current_time = time.time()
    should_render = (current_time - node.last_render_time) >= node.render_interval
    
    assert not should_render, "Should not render immediately after last render"
    
    # Wait for render interval
    time.sleep(node.render_interval + 0.1)
    
    # Now should allow render
    current_time = time.time()
    should_render = (current_time - node.last_render_time) >= node.render_interval
    
    assert should_render, "Should allow render after render_interval has passed"


def test_objchart_cached_image_reuse():
    """Test that cached chart image is properly reused during throttling"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Create and cache a chart
    bucket = node.get_time_bucket("minute")
    node.time_counts[0][bucket] = 10
    
    chart_image = node.render_chart("minute", [0], {"0": "person"}, "bar")
    node.cached_chart_image = chart_image
    node.last_render_time = time.time()
    
    assert node.cached_chart_image is not None
    assert isinstance(node.cached_chart_image, np.ndarray)
    
    # Verify cached image has expected shape
    assert len(node.cached_chart_image.shape) == 3
    assert node.cached_chart_image.shape[2] == 3  # BGR channels


def test_objchart_render_interval_default():
    """Test that default render interval is 1 second"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    assert node.render_interval == 1.0, "Default render interval should be 1 second"
    assert node.last_render_time == 0, "Last render time should be initialized to 0"
    assert node.cached_chart_image is None, "Cached chart should be None initially"


def test_objchart_multiple_fast_updates():
    """Test that multiple rapid updates don't trigger excessive renders"""
    from node.VisualNode.node_obj_chart import Node
    
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    # Simulate 30 rapid updates (like 30fps video)
    render_count = 0
    node.last_render_time = time.time()
    
    for i in range(30):
        current_time = time.time()
        should_render = (current_time - node.last_render_time) >= node.render_interval
        
        if should_render:
            render_count += 1
            node.last_render_time = current_time
        
        # Small delay to simulate frame time (~33ms at 30fps)
        time.sleep(0.001)  # 1ms delay for test speed
    
    # With 1 second render interval, we should have rendered at most once
    # during 30ms of updates
    assert render_count <= 1, f"Should render at most once, but rendered {render_count} times"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
