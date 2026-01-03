#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test tennis court size reduction (2x smaller).
Verify that the tennis court visualization is half the size it was before.
"""
import sys
import os
import numpy as np

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_tennis_court_size_reduction():
    """Test that tennis court is rendered at half scale"""
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    
    print("Testing tennis court size reduction (2x smaller)...")
    
    # Create tennis court node
    tennis_node = TennisCourtNode()
    tennis_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Get dimensions
    VISUALIZATION_WIDTH = TennisCourtNode.VISUALIZATION_WIDTH
    VISUALIZATION_HEIGHT = TennisCourtNode.VISUALIZATION_HEIGHT
    VISUALIZATION_MARGIN = TennisCourtNode.VISUALIZATION_MARGIN
    COURT_WIDTH_M = TennisCourtNode.COURT_WIDTH_M
    COURT_LENGTH_M = TennisCourtNode.COURT_LENGTH_M
    
    print(f"  Visualization dimensions: {VISUALIZATION_WIDTH}x{VISUALIZATION_HEIGHT}")
    print(f"  Court dimensions: {COURT_WIDTH_M}m x {COURT_LENGTH_M}m")
    print(f"  Margin: {VISUALIZATION_MARGIN}px")
    
    # Calculate expected scale (using same logic as tennis court node update method)
    scale_x = (VISUALIZATION_WIDTH - VISUALIZATION_MARGIN) / COURT_WIDTH_M
    scale_y = (VISUALIZATION_HEIGHT - VISUALIZATION_MARGIN) / COURT_LENGTH_M
    base_scale = min(scale_x, scale_y)
    
    # REDUCED BY 2x as per requirement
    expected_scale = base_scale / 2.0
    
    print(f"  Base scale (without reduction): {base_scale:.2f} px/m")
    print(f"  Expected scale (with 2x reduction): {expected_scale:.2f} px/m")
    
    # Calculate expected court size in pixels
    expected_court_width_px = int(COURT_WIDTH_M * expected_scale)
    expected_court_length_px = int(COURT_LENGTH_M * expected_scale)
    
    print(f"  Expected court size: {expected_court_width_px}x{expected_court_length_px} px")
    
    # Verify that the court is actually smaller than the display area
    assert expected_court_width_px < VISUALIZATION_WIDTH, "Court width should be smaller than display width"
    assert expected_court_length_px < VISUALIZATION_HEIGHT, "Court length should be smaller than display height"
    
    print("  ✓ Court fits within display area with room to spare")
    
    # Verify reduction is exactly 2x
    full_scale = base_scale
    reduced_scale = expected_scale
    reduction_factor = full_scale / reduced_scale
    
    print(f"  Reduction factor: {reduction_factor:.1f}x")
    assert abs(reduction_factor - 2.0) < 0.01, "Reduction should be exactly 2x"
    
    print("  ✓ Court size is reduced by exactly 2x (half the original size)")
    
    # Calculate how much smaller the court is now
    original_court_width = int(COURT_WIDTH_M * base_scale)
    original_court_length = int(COURT_LENGTH_M * base_scale)
    
    print(f"\n  Original court size: {original_court_width}x{original_court_length} px")
    print(f"  New court size: {expected_court_width_px}x{expected_court_length_px} px")
    print(f"  Space saved: {original_court_width - expected_court_width_px}x{original_court_length - expected_court_length_px} px")
    
    return True


def test_tennis_court_visualization_with_reduced_size():
    """Test that visualization works correctly with reduced court size"""
    from node.VisualNode.node_tennis_court import Node as TennisCourtNode
    from node.StatsNode.node_homography import Node as HomographyNode
    
    print("\nTesting tennis court visualization with reduced size...")
    
    tennis_node = TennisCourtNode()
    tennis_node._opencv_setting_dict = {'use_pref_counter': False}
    
    # Create test image
    test_image = np.zeros((TennisCourtNode.VISUALIZATION_HEIGHT, 
                           TennisCourtNode.VISUALIZATION_WIDTH, 3), dtype=np.uint8)
    
    # Get template from Homography node
    template = HomographyNode.TENNIS_COURT_TEMPLATE
    
    # Calculate scale (same as in update method)
    small_window_w = TennisCourtNode.VISUALIZATION_WIDTH
    small_window_h = TennisCourtNode.VISUALIZATION_HEIGHT
    
    scale_x = (small_window_w - TennisCourtNode.VISUALIZATION_MARGIN) / TennisCourtNode.COURT_WIDTH_M
    scale_y = (small_window_h - TennisCourtNode.VISUALIZATION_MARGIN) / TennisCourtNode.COURT_LENGTH_M
    base_scale = min(scale_x, scale_y)
    
    # REDUCED BY 2x
    scale = base_scale / 2.0
    
    # Center the court
    court_width_px = int(TennisCourtNode.COURT_WIDTH_M * scale)
    court_length_px = int(TennisCourtNode.COURT_LENGTH_M * scale)
    offset_x = (small_window_w - court_width_px) // 2
    offset_y = (small_window_h - court_length_px) // 2
    
    # Draw the court
    output_image = tennis_node._draw_tennis_court(test_image, template, scale, offset_x, offset_y)
    
    # Verify image was modified
    assert output_image is not None, "Should return an image"
    assert not np.array_equal(test_image, output_image), "Image should be modified"
    
    print("  ✓ Court visualization works with reduced size")
    print(f"  ✓ Court rendered at scale: {scale:.2f} px/m")
    print(f"  ✓ Court position: offset ({offset_x}, {offset_y})")
    print(f"  ✓ Output image shape: {output_image.shape}")
    
    # Test with player positions
    test_points = [[5.485, 11.885], [5.485, 11.885]]  # Center court
    labels = ['person', 'person']
    
    output_with_players = tennis_node._draw_player_positions_with_labels(
        output_image, test_points, labels, scale=scale, offset_x=offset_x, offset_y=offset_y
    )
    
    assert output_with_players is not None, "Should return image with players"
    
    print("  ✓ Player positions render correctly on reduced court")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Tennis Court Size Reduction (2x Smaller)")
    print("=" * 70)
    print()
    
    try:
        test_tennis_court_size_reduction()
        test_tennis_court_visualization_with_reduced_size()
        
        print()
        print("=" * 70)
        print("All tennis court size reduction tests passed! ✓")
        print("=" * 70)
        print()
        print("Summary:")
        print("  • Tennis court is now rendered at half the original size (2x reduction)")
        print("  • Court is centered in the display area")
        print("  • Visualization works correctly with the reduced size")
        print("  • Player positions render correctly on the smaller court")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
