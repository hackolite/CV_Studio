#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Visual test for ObjChart node - generates sample output"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.VisualNode.node_obj_chart import Node
import cv2

def test_visual_output():
    """Generate a sample chart to verify visual output"""
    
    # Create node
    node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640
    })
    
    # Simulate detection data over multiple time buckets
    print("Simulating object detection data over 10 time periods...")
    
    base_time = datetime.now().replace(second=0, microsecond=0)
    
    # Add simulated data for different classes
    for i in range(10):
        bucket = base_time - timedelta(minutes=i)
        
        # Class 0 (person) - varying counts
        node.time_counts[0][bucket] = 5 + (i % 3) * 2
        
        # Class 1 (car) - varying counts
        node.time_counts[1][bucket] = 3 + (i % 4)
        
        # Class 2 (bicycle) - fewer counts
        node.time_counts[2][bucket] = 1 + (i % 2)
        
        # All classes
        node.time_counts["All"][bucket] = node.time_counts[0][bucket] + \
                                          node.time_counts[1][bucket] + \
                                          node.time_counts[2][bucket]
    
    # Define class names
    class_names = {
        "0": "person",
        "1": "car",
        "2": "bicycle"
    }
    
    # Test 1: Chart with all classes
    print("\nTest 1: Rendering chart with 'All' classes...")
    chart_all = node.render_chart("minute", ["All"], class_names)
    print(f"  Chart size: {chart_all.shape}")
    cv2.imwrite("/tmp/obj_chart_all_classes.png", chart_all)
    print("  ✓ Saved to /tmp/obj_chart_all_classes.png")
    
    # Test 2: Chart with specific classes
    print("\nTest 2: Rendering chart with classes 0 and 1...")
    chart_specific = node.render_chart("minute", [0, 1], class_names)
    print(f"  Chart size: {chart_specific.shape}")
    cv2.imwrite("/tmp/obj_chart_specific_classes.png", chart_specific)
    print("  ✓ Saved to /tmp/obj_chart_specific_classes.png")
    
    # Test 3: Chart with hourly aggregation
    print("\nTest 3: Rendering chart with hourly aggregation...")
    
    # Add hourly data
    hour_bucket = datetime.now().replace(minute=0, second=0, microsecond=0)
    node.time_counts[0][hour_bucket] = 50
    node.time_counts[1][hour_bucket] = 30
    node.time_counts["All"][hour_bucket] = 80
    
    chart_hourly = node.render_chart("hour", ["All"], class_names)
    print(f"  Chart size: {chart_hourly.shape}")
    cv2.imwrite("/tmp/obj_chart_hourly.png", chart_hourly)
    print("  ✓ Saved to /tmp/obj_chart_hourly.png")
    
    # Test 4: Empty chart
    print("\nTest 4: Rendering empty chart...")
    empty_node = Node(opencv_setting_dict={
        'process_height': 480,
        'process_width': 640
    })
    chart_empty = empty_node.render_chart("minute", ["All"], {})
    print(f"  Chart size: {chart_empty.shape}")
    cv2.imwrite("/tmp/obj_chart_empty.png", chart_empty)
    print("  ✓ Saved to /tmp/obj_chart_empty.png")
    
    print("\n" + "="*60)
    print("All visual tests completed successfully!")
    print("Generated charts in /tmp/:")
    print("  - obj_chart_all_classes.png")
    print("  - obj_chart_specific_classes.png")
    print("  - obj_chart_hourly.png")
    print("  - obj_chart_empty.png")
    print("="*60)

if __name__ == "__main__":
    test_visual_output()
