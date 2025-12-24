#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demonstration of ObjChart download button functionality.
This script creates a sample chart and demonstrates the download feature.
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.VisualNode.node_obj_chart import Node


def demo_download_feature():
    """Demonstrate the download feature with a sample chart"""
    print("=" * 60)
    print("ObjChart Download Button Demo")
    print("=" * 60)
    
    # Create a node instance
    node = Node(opencv_setting_dict={
        'process_height': 400,
        'process_width': 600
    })
    
    print("\n1. Creating sample detection data...")
    
    # Simulate some detection data over time
    current_time = datetime.now()
    for i in range(10):
        time_bucket = current_time - timedelta(minutes=i)
        # Add some counts for different classes
        node.time_counts[0][time_bucket] = 5 + i  # person
        node.time_counts[2][time_bucket] = 3 + i  # car
        node.time_counts["All"][time_bucket] = 8 + 2*i
    
    print(f"   - Added detection data for {len(node.time_counts)} classes")
    print(f"   - Time buckets: {len(node.time_counts[0])}")
    
    # Render a chart
    print("\n2. Rendering chart...")
    selected_classes = ["All", 0, 2]  # All, person, car
    class_names = {
        "0": "person",
        "2": "car"
    }
    chart_image = node.render_chart(
        time_unit="minute",
        selected_classes=selected_classes,
        class_names_dict=class_names,
        chart_type="bar"
    )
    
    # Store the chart in the node (simulating what happens during update)
    node.current_chart_image = chart_image
    print(f"   - Chart rendered: {chart_image.shape}")
    
    # Test the download callback
    print("\n3. Testing download callback...")
    Node.download_chart_callback(None, None, node)
    
    # Check if file was created
    files = [f for f in os.listdir('.') if f.startswith('objchart_') and f.endswith('.png')]
    if files:
        latest_file = sorted(files)[-1]
        file_size = os.path.getsize(latest_file)
        print(f"   - File size: {file_size} bytes")
        
        # Verify the image can be read
        loaded_image = cv2.imread(latest_file)
        if loaded_image is not None:
            print(f"   - Image verified: {loaded_image.shape}")
            print(f"\n✅ Download feature working correctly!")
            print(f"   You can find the chart image at: {os.path.abspath(latest_file)}")
        else:
            print("   ❌ Error: Could not read saved image")
    else:
        print("   ❌ Error: No image file created")
    
    # Test with no image available
    print("\n4. Testing download with no image available...")
    node.current_chart_image = None
    Node.download_chart_callback(None, None, node)
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    demo_download_feature()
