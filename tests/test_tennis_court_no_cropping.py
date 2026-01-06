#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Visual test for tennis court window extension (no cropping).
"""
import sys
import os
import numpy as np
import cv2

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_tennis_court_no_cropping():
    """Test that tennis court visualization shows full image with margins"""
    from node.VisualNode.node_tennis_court import Node
    
    print("Testing tennis court visualization without cropping...")
    
    node = Node()
    node._opencv_setting_dict = {
        'use_pref_counter': False,
        'process_width': 300,
        'process_height': 400
    }
    
    # Tennis court template
    template = {
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
    
    # Create blank BGRA image
    small_window_w = node.VISUALIZATION_WIDTH
    small_window_h = node.VISUALIZATION_HEIGHT
    output_image = np.zeros((small_window_h, small_window_w, 4), dtype=np.uint8)
    
    # Calculate scale (same logic as in the node)
    scale_x = (small_window_w - node.VISUALIZATION_MARGIN) / node.COURT_WIDTH_M
    scale_y = (small_window_h - node.VISUALIZATION_MARGIN) / node.COURT_LENGTH_M
    base_scale = min(scale_x, scale_y)
    scale = base_scale / 1.5  # Court content reduced by 1.5
    
    # Center the court
    court_width_px = int(node.COURT_WIDTH_M * scale)
    court_length_px = int(node.COURT_LENGTH_M * scale)
    offset_x = (small_window_w - court_width_px) // 2
    offset_y = (small_window_h - court_length_px) // 2
    
    # Draw court
    output_image = node._draw_tennis_court(output_image, template, scale, offset_x, offset_y)
    
    print(f"  ✓ Court drawn at scale {scale:.2f} pixels/meter")
    print(f"  ✓ Court dimensions in pixels: {court_width_px}x{court_length_px}")
    print(f"  ✓ Offset (centering): ({offset_x}, {offset_y})")
    print(f"  ✓ Window dimensions: {small_window_w}x{small_window_h}")
    print(f"  ✓ Margin at top: {offset_y} pixels (~{offset_y/small_window_h*100:.1f}% of height)")
    print(f"  ✓ Margin at bottom: {offset_y} pixels (~{offset_y/small_window_h*100:.1f}% of height)")
    
    # Verify that we have margins (offset_y should be approximately 1/6 of height or more)
    # Since court is divided by 1.5 and centered, there should be space around it
    expected_min_margin_ratio = 0.10  # At least 10% margin
    actual_margin_ratio = offset_y / small_window_h
    
    assert actual_margin_ratio >= expected_min_margin_ratio, \
        f"Margin too small: {actual_margin_ratio:.2%} < {expected_min_margin_ratio:.2%}"
    
    print(f"\n  ✓ Verification: Court has adequate margins (top/bottom: {actual_margin_ratio:.1%} of height)")
    
    # Save the image for visual inspection
    output_path = '/tmp/tennis_court_with_margins.png'
    # Convert BGRA to BGR for saving
    bgr_image = cv2.cvtColor(output_image, cv2.COLOR_BGRA2BGR)
    cv2.imwrite(output_path, bgr_image)
    print(f"  ✓ Test image saved to: {output_path}")
    
    return True


def test_tennis_court_update_without_cropping():
    """Test that the update method doesn't crop the image"""
    from node.VisualNode.node_tennis_court import Node
    
    print("\nTesting tennis court update method (no cropping logic)...")
    
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Tennis court template
    template = {
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
    
    # Simulate JSON input from Homography node
    json_data = {
        'template': template,
        'transformed_points': [[5.0, 12.0], [3.0, 8.0]],  # Two points in meters
        'input_points': [[400, 300], [200, 200]],
        'bboxes': [[350, 250, 450, 350], [150, 150, 250, 250]],
        'class_ids': [0, 0],
        'class_names': {0: 'person'}
    }
    
    node_result_dict = {'1:Homography': json_data}
    connection_list = [['1:Homography:JSON:Output01', '2:TennisCourt:JSON:Input01']]
    
    # Call update
    result = node.update(
        node_id=2,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={}
    )
    
    assert 'image' in result
    assert result['image'] is not None
    
    # Check that image has expected dimensions (no cropping)
    expected_h = node.VISUALIZATION_HEIGHT
    expected_w = node.VISUALIZATION_WIDTH
    actual_h, actual_w = result['image'].shape[:2]
    
    assert actual_h == expected_h, f"Height mismatch: {actual_h} != {expected_h}"
    assert actual_w == expected_w, f"Width mismatch: {actual_w} != {expected_w}"
    
    print(f"  ✓ Update method returns full-size image: {actual_w}x{actual_h}")
    print(f"  ✓ No cropping applied - full visualization with margins shown")
    
    # Save the result image
    output_path = '/tmp/tennis_court_update_result.png'
    bgr_image = cv2.cvtColor(result['image'], cv2.COLOR_BGRA2BGR)
    cv2.imwrite(output_path, bgr_image)
    print(f"  ✓ Result image saved to: {output_path}")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Tennis Court Window Extension (No Cropping)")
    print("=" * 70)
    print()
    
    try:
        test_tennis_court_no_cropping()
        test_tennis_court_update_without_cropping()
        
        print()
        print("=" * 70)
        print("All tennis court visualization tests passed! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • Court content is reduced by 1.5x (scale divided by 1.5)")
        print("  • Full window is shown with margins around the court")
        print("  • No cropping is applied - giving ~1/6 extra space at top/bottom")
        print("  • Players/objects positions are drawn with proper scaling")
        
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
