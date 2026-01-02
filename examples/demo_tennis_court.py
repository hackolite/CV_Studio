#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demonstration script showing the complete TennisCourt node workflow.
This script demonstrates:
1. Court keypoint detection simulation
2. Homography calculation
3. Player position transformation
4. Tennis court visualization with transformed points
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.StatsNode.node_homography import Node as HomographyNode
from node.VisualNode.node_tennis_court import Node as TennisCourtNode


def main():
    print("=" * 70)
    print("TennisCourt Visual Node - Complete Workflow Demonstration")
    print("=" * 70)
    print()
    
    # ========================================================================
    # Step 1: Simulate Court Keypoint Detection
    # ========================================================================
    print("Step 1: Simulating court keypoint detection from TennisKeyPoints model")
    print("-" * 70)
    
    # These are mock detected keypoints as if they came from a pose estimation model
    # In a real scenario, these would come from TennisKeyPoints or TennisKeyPoints_2 model
    detected_keypoints = np.array([
        # Doubles corners
        [100, 500], [700, 500], [700, 50], [100, 50],
        # Singles sidelines
        [200, 500], [600, 500], [600, 50], [200, 50],
        # Service lines
        [200, 400], [600, 400], [200, 150], [600, 150],
        # Center T points
        [400, 400], [400, 150],
    ], dtype=np.float32)
    
    print(f"  ✓ Detected {len(detected_keypoints)} court keypoints")
    print(f"    Example points: {detected_keypoints[:3].tolist()}")
    print()
    
    # ========================================================================
    # Step 2: Calculate Homography Matrix
    # ========================================================================
    print("Step 2: Calculating homography transformation")
    print("-" * 70)
    
    homography_node = HomographyNode()
    homography_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Prepare mock player positions in image coordinates
    player_positions = {
        'keypoints': [
            {'x': 350, 'y': 300, 'label': 'Player 1'},
            {'x': 450, 'y': 200, 'label': 'Player 2'},
            {'x': 380, 'y': 350, 'label': 'Ball'},
        ]
    }
    
    # Create input data structure
    master_json_data = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': detected_keypoints
    }
    
    node_result_dict = {
        '1:PoseEstimation': master_json_data,
        '2:ObjectDetection': player_positions
    }
    
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '3:Homography:JSON:Input01'],
        ['2:ObjectDetection:JSON:Output01', '3:Homography:JSON:Input02']
    ]
    
    # Execute homography calculation
    homography_result = homography_node.update(
        node_id=3,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    print(f"  ✓ Homography matrix calculated successfully")
    print(f"    Matrix shape: {np.array(homography_result['json']['homography_matrix']).shape}")
    print(f"  ✓ Transformed {len(homography_result['json']['transformed_points'])} points to real-world coordinates")
    
    # Display transformed coordinates
    for i, (img_pt, real_pt) in enumerate(zip(
        homography_result['json']['input_points'],
        homography_result['json']['transformed_points']
    )):
        print(f"    Point {i}: Image({img_pt[0]:.0f}, {img_pt[1]:.0f}) → Court({real_pt[0]:.2f}m, {real_pt[1]:.2f}m)")
    print()
    
    # ========================================================================
    # Step 3: Create Tennis Court Visualization
    # ========================================================================
    print("Step 3: Creating tennis court visualization")
    print("-" * 70)
    
    tennis_court_node = TennisCourtNode()
    
    # Extract data for visualization
    template = homography_result['json']['template']
    transformed_points = homography_result['json']['transformed_points']
    
    # Create visualization image
    img_width, img_height = 600, 800
    output_image = np.zeros((img_height, img_width, 3), dtype=np.uint8)
    
    # Calculate scale and offsets
    scale_x = (img_width - 100) / 11.0
    scale_y = (img_height - 100) / 24.0
    scale = min(scale_x, scale_y)
    
    court_width_px = int(10.97 * scale)
    court_length_px = int(23.77 * scale)
    offset_x = (img_width - court_width_px) // 2
    offset_y = (img_height - court_length_px) // 2
    
    # Draw court
    output_image = tennis_court_node._draw_tennis_court(
        output_image, template, scale, offset_x, offset_y
    )
    
    # Draw transformed points
    output_image = tennis_court_node._draw_transformed_points(
        output_image, transformed_points, scale, offset_x, offset_y
    )
    
    print(f"  ✓ Tennis court visualization created")
    print(f"    Image size: {img_width}×{img_height}")
    print(f"    Scale: {scale:.2f} pixels/meter")
    print(f"    Court offset: ({offset_x}, {offset_y})")
    print()
    
    # ========================================================================
    # Step 4: Save and Display Results
    # ========================================================================
    print("Step 4: Saving visualization")
    print("-" * 70)
    
    output_path = '/tmp/tennis_court_demo.png'
    cv2.imwrite(output_path, output_image)
    print(f"  ✓ Visualization saved to: {output_path}")
    
    # Add court information overlay
    info_image = output_image.copy()
    
    # Add title
    cv2.putText(info_image, "Tennis Court Visualization", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Add legend
    legend_y = img_height - 120
    cv2.putText(info_image, "Legend:", (10, legend_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.circle(info_image, (20, legend_y + 20), 6, (255, 255, 255), -1)
    cv2.putText(info_image, "= Court Lines", (35, legend_y + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    cv2.circle(info_image, (20, legend_y + 45), 6, (0, 0, 255), -1)
    cv2.circle(info_image, (20, legend_y + 45), 7, (255, 255, 255), 2)
    cv2.putText(info_image, "= Tracked Points", (35, legend_y + 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    # Add court dimensions
    cv2.putText(info_image, f"Court: {10.97}m x {23.77}m", (10, legend_y + 85),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    output_path_annotated = '/tmp/tennis_court_demo_annotated.png'
    cv2.imwrite(output_path_annotated, info_image)
    print(f"  ✓ Annotated visualization saved to: {output_path_annotated}")
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 70)
    print("Demonstration Complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • Detected {len(detected_keypoints)} court keypoints")
    print(f"  • Calculated homography transformation matrix")
    print(f"  • Transformed {len(transformed_points)} points to real-world coordinates")
    print(f"  • Created tennis court visualization with points")
    print(f"  • Saved outputs to /tmp/")
    print()
    print("Output files:")
    print(f"  1. {output_path}")
    print(f"  2. {output_path_annotated}")
    print()
    print("Next steps:")
    print("  • View the generated images to see the visualization")
    print("  • In the CV Studio GUI, use: Visual → TennisCourt")
    print("  • Connect to Homography node output for real-time visualization")
    print()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
