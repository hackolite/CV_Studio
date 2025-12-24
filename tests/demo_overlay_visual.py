#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual demo script for the Overlay node
Creates example images showing the overlay functionality
"""
import cv2
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.OverlayNode.node_overlay import OverlayNode


def create_demo_image():
    """Create a demo image with some visual content"""
    # Create an image with gradient background
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Create a nice gradient
    for i in range(720):
        color_val = int((i / 720) * 180) + 40
        image[i, :] = [30, color_val, 200]
    
    # Add some geometric shapes for visual interest
    cv2.circle(image, (640, 360), 150, (100, 200, 255), -1)
    cv2.rectangle(image, (200, 200), (400, 400), (255, 200, 100), -1)
    cv2.rectangle(image, (880, 320), (1080, 520), (200, 255, 150), -1)
    
    # Add a title
    cv2.putText(image, "CV Studio - Overlay Node Demo", (350, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
    
    return image


def main():
    """Generate demo images showing different overlay configurations"""
    print("Generating Overlay node demo images...")
    
    # Create base image
    base_image = create_demo_image()
    
    # Create sample weather data (from Weather node)
    weather_data = {
        "current_weather": {
            "temperature": 25.5,
            "windspeed": 12.3,
            "winddirection": 180,
            "weathercode": 0,
            "is_day": 1,
            "time": "2024-12-24T13:00"
        },
        "location": {
            "latitude": 48.8566,
            "longitude": 2.3522,
            "city": "Paris"
        }
    }
    
    # Create node instance
    node = OverlayNode()
    
    # Demo 1: Top Right position (default)
    print("Creating demo 1: Top Right position...")
    demo1 = node._draw_overlay(
        base_image.copy(),
        weather_data,
        font_scale=0.7,
        text_color=(255, 255, 255, 255),
        bg_color=(0, 0, 0, 180),
        position='Top Right'
    )
    cv2.imwrite('/tmp/overlay_demo_top_right.png', demo1)
    print("  ✓ Saved: /tmp/overlay_demo_top_right.png")
    
    # Demo 2: Bottom Left position with different style
    print("Creating demo 2: Bottom Left position with green theme...")
    demo2 = node._draw_overlay(
        base_image.copy(),
        weather_data,
        font_scale=0.8,
        text_color=(100, 255, 100, 255),
        bg_color=(10, 30, 10, 200),
        position='Bottom Left'
    )
    cv2.imwrite('/tmp/overlay_demo_bottom_left.png', demo2)
    print("  ✓ Saved: /tmp/overlay_demo_bottom_left.png")
    
    # Demo 3: Center position with larger text
    print("Creating demo 3: Center position with large text...")
    demo3 = node._draw_overlay(
        base_image.copy(),
        weather_data,
        font_scale=1.0,
        text_color=(255, 255, 100, 255),
        bg_color=(50, 50, 50, 220),
        position='Center'
    )
    cv2.imwrite('/tmp/overlay_demo_center.png', demo3)
    print("  ✓ Saved: /tmp/overlay_demo_center.png")
    
    # Demo 4: Simple flat data
    print("Creating demo 4: Simple data format...")
    simple_data = {
        "temperature": "25.5°C",
        "humidity": "65%",
        "wind": "12.3 km/h",
        "status": "Clear Sky"
    }
    demo4 = node._draw_overlay(
        base_image.copy(),
        simple_data,
        font_scale=0.9,
        text_color=(255, 200, 255, 255),
        bg_color=(20, 0, 40, 190),
        position='Top Left'
    )
    cv2.imwrite('/tmp/overlay_demo_simple.png', demo4)
    print("  ✓ Saved: /tmp/overlay_demo_simple.png")
    
    # Create a comparison image
    print("Creating comparison image...")
    comparison = np.hstack([
        cv2.resize(base_image, (640, 360)),
        cv2.resize(demo1, (640, 360))
    ])
    cv2.putText(comparison, "Original", (180, 330),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(comparison, "With Overlay", (820, 330),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite('/tmp/overlay_demo_comparison.png', comparison)
    print("  ✓ Saved: /tmp/overlay_demo_comparison.png")
    
    print("\n" + "="*60)
    print("✅ Demo images created successfully!")
    print("="*60)
    print("\nGenerated images:")
    print("  - /tmp/overlay_demo_top_right.png")
    print("  - /tmp/overlay_demo_bottom_left.png")
    print("  - /tmp/overlay_demo_center.png")
    print("  - /tmp/overlay_demo_simple.png")
    print("  - /tmp/overlay_demo_comparison.png")
    print("\nThe Overlay node can:")
    print("  • Accept an image input (master image)")
    print("  • Accept JSON data with key-value pairs")
    print("  • Display all data on the image in a stylish way")
    print("  • Support multiple positions and styling options")
    print("  • Handle nested JSON structures automatically")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
