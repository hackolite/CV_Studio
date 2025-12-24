#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that slider cursors are styled with black color for better visibility
"""
import unittest
import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSliderCursorColors(unittest.TestCase):
    """Test that slider cursors (grab handles) are black for better visibility"""
    
    def test_slider_grab_colors_are_black(self):
        """Test that SliderGrab and SliderGrabActive colors are set to TEXT_COLOR_BLACK"""
        
        # Read the node_editor.py file
        node_editor_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node_editor',
            'node_editor.py'
        )
        
        with open(node_editor_path, 'r') as f:
            content = f.read()
        
        # Check for SliderGrab with TEXT_COLOR_BLACK (not tuple_style)
        slider_grab_pattern = r'dpg\.mvThemeCol_SliderGrab,\s*TEXT_COLOR_BLACK'
        slider_grab_matches = re.findall(slider_grab_pattern, content)
        
        # Should find 2 occurrences (one for mvSliderInt, one for mvSliderFloat)
        self.assertEqual(len(slider_grab_matches), 2,
                        "SliderGrab should be set to TEXT_COLOR_BLACK for both int and float sliders")
        
        # Check for SliderGrabActive with TEXT_COLOR_BLACK (not tuple_style)
        slider_grab_active_pattern = r'dpg\.mvThemeCol_SliderGrabActive,\s*TEXT_COLOR_BLACK'
        slider_grab_active_matches = re.findall(slider_grab_active_pattern, content)
        
        # Should find 2 occurrences (one for mvSliderInt, one for mvSliderFloat)
        self.assertEqual(len(slider_grab_active_matches), 2,
                        "SliderGrabActive should be set to TEXT_COLOR_BLACK for both int and float sliders")
    
    def test_slider_background_uses_node_color(self):
        """Test that slider backgrounds still use the node's color (tuple_style)"""
        
        node_editor_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node_editor',
            'node_editor.py'
        )
        
        with open(node_editor_path, 'r') as f:
            content = f.read()
        
        # Check that FrameBg colors still use tuple_style for sliders
        frame_bg_pattern = r'dpg\.mvThemeCol_FrameBg,\s*tuple_style'
        
        # Find all FrameBg with tuple_style
        frame_bg_matches = re.findall(frame_bg_pattern, content)
        
        # Should find multiple (including sliders, inputs, combos, etc.)
        self.assertGreater(len(frame_bg_matches), 0,
                          "Slider backgrounds should still use tuple_style (node color)")


class TestMOTLabelFontScale(unittest.TestCase):
    """Test that MOT node labels have appropriate dynamic font scale"""
    
    def test_basenode_mot_label_dynamic_font_scale(self):
        """Test that basenode.py uses dynamic font scale based on image height"""
        
        basenode_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node',
            'basenode.py'
        )
        
        with open(basenode_path, 'r') as f:
            content = f.read()
        
        # Check that draw_multi_object_tracking_info calculates font_scale dynamically
        # Should find the formula that calculates font scale based on image height
        self.assertIn('image_height = image.shape[0]', content,
                     "Should get image height from image.shape[0]")
        self.assertIn('font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))', content,
                     "Should calculate font_scale dynamically based on image height")
        
        # Check that cv2.putText uses the calculated font_scale variable
        font_scale_usage_pattern = r'cv2\.FONT_HERSHEY_SIMPLEX,\s*font_scale,'
        matches = re.findall(font_scale_usage_pattern, content)
        
        # Should find at least 2 occurrences (TID and CID labels)
        self.assertGreaterEqual(len(matches), 2,
                               "MOT labels should use the dynamically calculated font_scale variable")
    
    def test_draw_util_mot_label_dynamic_font_scale(self):
        """Test that draw_util.py uses dynamic font scale based on image height"""
        
        draw_util_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node',
            'OverlayNode',
            'draw_util',
            'draw_util.py'
        )
        
        with open(draw_util_path, 'r') as f:
            content = f.read()
        
        # Check that draw_multi_object_tracking_info calculates font_scale dynamically
        # Should find the formula that calculates font scale based on image height
        self.assertIn('image_height = image.shape[0]', content,
                     "Should get image height from image.shape[0]")
        self.assertIn('font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))', content,
                     "Should calculate font_scale dynamically based on image height")
        
        # Check that cv2.putText uses the calculated font_scale variable
        font_scale_usage_pattern = r'cv2\.FONT_HERSHEY_SIMPLEX,\s*font_scale,'
        matches = re.findall(font_scale_usage_pattern, content)
        
        # Should find at least 2 occurrences (TID and CID labels)
        self.assertGreaterEqual(len(matches), 2,
                               "MOT labels should use the dynamically calculated font_scale variable")


if __name__ == '__main__':
    unittest.main()
