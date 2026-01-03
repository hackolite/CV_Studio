#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration of the TennisCourt node improvements:
1. Court size reduced by half
2. Player position tracking and averaging by label
3. Display of last and average positions
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_tennis_court import Node as TennisCourtNode


def create_mock_template():
    """Create a mock tennis court template"""
    return {
        "units": "meters",
        "origin": "bottom_left_corner_outside_doubles",
        "keypoints": [
            {"id": 0,  "name": "far_baseline_left_single_corner", "x": 1.37, "y": 23.77},
            {"id": 1,  "name": "far_baseline_right_single_corner", "x": 9.60, "y": 23.77},
            {"id": 2,  "name": "near_baseline_left_double_corner", "x": 0.00, "y": 0.00},
            {"id": 3,  "name": "near_baseline_right_double_corner", "x": 10.97, "y": 0.00},
            {"id": 4,  "name": "far_baseline_left_service_projection", "x": 1.37, "y": 18.285},
            {"id": 5,  "name": "near_baseline_left_single_corner", "x": 1.37, "y": 0.00},
            {"id": 6,  "name": "far_baseline_right_service_projection", "x": 9.60, "y": 18.285},
            {"id": 7,  "name": "near_baseline_right_single_corner", "x": 9.60, "y": 0.00},
            {"id": 8,  "name": "service_box_left_top_corner", "x": 1.37, "y": 5.485},
            {"id": 9,  "name": "service_box_right_top_corner", "x": 9.60, "y": 5.485},
            {"id": 10, "name": "left_singles_sideline_midpoint", "x": 1.37, "y": 11.885},
            {"id": 11, "name": "right_singles_sideline_midpoint", "x": 9.60, "y": 11.885},
            {"id": 12, "name": "center_service_line_top_T", "x": 5.485, "y": 18.285},
            {"id": 13, "name": "center_service_line_bottom_T", "x": 5.485, "y": 5.485}
        ]
    }


def main():
    print("=" * 80)
    print("TennisCourt Node Improvements Demo")
    print("=" * 80)
    print()
    
    # Initialize node
    node = TennisCourtNode()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 600,
        'process_height': 800
    }
    
    # Create template
    template = create_mock_template()
    
    # Simulate player tracking over multiple frames
    print("Simulating player tracking over 5 frames...")
    print("-" * 80)
    
    frames_data = [
        # Frame 1
        {
            'transformed_points': [[5.0, 10.0], [3.0, 15.0], [7.5, 8.0]],
            'labels': ['person', 'person', 'ball'],
        },
        # Frame 2
        {
            'transformed_points': [[5.2, 10.5], [3.2, 15.3], [7.7, 8.2]],
            'labels': ['person', 'person', 'ball'],
        },
        # Frame 3
        {
            'transformed_points': [[5.1, 10.2], [3.3, 15.5], [7.6, 8.5]],
            'labels': ['person', 'person', 'ball'],
        },
        # Frame 4
        {
            'transformed_points': [[5.3, 10.8], [3.1, 15.2], [7.8, 8.3]],
            'labels': ['person', 'person', 'ball'],
        },
        # Frame 5
        {
            'transformed_points': [[5.2, 10.6], [3.4, 15.6], [7.9, 8.6]],
            'labels': ['person', 'person', 'ball'],
        },
    ]
    
    images = []
    
    for i, frame_data in enumerate(frames_data, 1):
        print(f"\nFrame {i}:")
        print(f"  Transformed points: {frame_data['transformed_points']}")
        print(f"  Labels: {frame_data['labels']}")
        
        # Create blank image
        img_width, img_height = 600, 800
        output_image = np.zeros((img_height, img_width, 3), dtype=np.uint8)
        
        # Calculate scale (HALVED)
        scale_x = (img_width - 60) / 10.97
        scale_y = (img_height - 60) / 23.77
        base_scale = min(scale_x, scale_y)
        scale = base_scale / 2.0  # HALVED
        
        print(f"  Scale: {scale:.2f} pixels/meter (HALVED from {base_scale:.2f})")
        
        # Calculate offsets
        court_width_px = int(10.97 * scale)
        court_length_px = int(23.77 * scale)
        offset_x = (img_width - court_width_px) // 2
        offset_y = (img_height - court_length_px) // 2
        
        # Draw court
        output_image = node._draw_tennis_court(output_image, template, scale, offset_x, offset_y)
        
        # Draw player positions with labels (showing averages and last positions)
        output_image = node._draw_player_positions_with_labels(
            output_image,
            frame_data['transformed_points'],
            frame_data['labels'],
            None,
            scale,
            offset_x,
            offset_y
        )
        
        # Add frame number
        cv2.putText(output_image, f"Frame {i}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # Add legend
        legend_y = 60
        cv2.putText(output_image, "White circle = Last position", (10, legend_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(output_image, "Yellow cross = Average position", (10, legend_y + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        images.append(output_image)
    
    print()
    print("-" * 80)
    print("Current averages by label:")
    averages = node._get_average_positions_by_label()
    for label, (avg_x, avg_y) in averages.items():
        count = len(node._player_positions_history[label])
        print(f"  {label}: ({avg_x:.2f}, {avg_y:.2f})m (from {count} positions)")
    
    print()
    print("Last positions by label:")
    for label, (last_x, last_y) in node._last_positions_by_label.items():
        print(f"  {label}: ({last_x:.2f}, {last_y:.2f})m")
    
    # Save images
    print()
    print("-" * 80)
    print("Saving visualization images...")
    
    for i, img in enumerate(images, 1):
        output_path = f'/tmp/tennis_court_demo_frame{i}.png'
        cv2.imwrite(output_path, img)
        print(f"  Frame {i} saved to: {output_path}")
    
    # Create a comparison image showing the first and last frame side by side
    if len(images) >= 2:
        comparison = np.hstack([images[0], images[-1]])
        comparison_path = '/tmp/tennis_court_demo_comparison.png'
        cv2.imwrite(comparison_path, comparison)
        print(f"  Comparison saved to: {comparison_path}")
    
    print()
    print("=" * 80)
    print("Demo Complete!")
    print("=" * 80)
    print()
    print("Summary of improvements:")
    print("  1. ✓ Court size reduced by half (scale divided by 2)")
    print("  2. ✓ Player positions tracked and averaged by label")
    print("  3. ✓ Last position displayed for each player (white circles)")
    print("  4. ✓ Average position displayed for each label (yellow crosses)")
    print()
    print("Key features:")
    print(f"  - Tracked {len(frames_data)} frames")
    print(f"  - {len(averages)} unique labels detected")
    print(f"  - Person label: {len(node._player_positions_history.get('person', []))} positions tracked")
    print(f"  - Ball label: {len(node._player_positions_history.get('ball', []))} positions tracked")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
