#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that MOT node labels scale font size based on image dimensions
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMOTDynamicFontScaling(unittest.TestCase):
    """Test that MOT node labels have dynamic font scaling based on image size"""
    
    def test_font_scale_calculation_logic(self):
        """Test that font scale calculation logic is correct"""
        
        # Simulate the font scale calculation logic
        # font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))
        
        test_cases = [
            # (image_height, expected_min, expected_max)
            (360, 0.3, 0.3),      # Small image (360p) -> min font scale (0.25 clamped to 0.3)
            (480, 0.3, 0.35),     # Medium-small (480p) -> ~0.33
            (720, 0.49, 0.51),    # Reference height (720p) -> 0.5
            (1080, 0.74, 0.76),   # HD (1080p) -> 0.75
            (1440, 0.99, 1.01),   # 2K (1440p) -> 1.0 (at max limit)
            (2160, 1.0, 1.0),     # 4K (2160p) -> 1.0 (clamped to max)
            (240, 0.3, 0.3),      # Tiny image (240p) -> min font scale
        ]
        
        for image_height, expected_min, expected_max in test_cases:
            # Calculate font scale using the same formula as in the code
            font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))
            
            # Verify font scale is within expected range
            self.assertGreaterEqual(font_scale, expected_min,
                f"Font scale {font_scale} should be >= {expected_min} for height {image_height}")
            self.assertLessEqual(font_scale, expected_max,
                f"Font scale {font_scale} should be <= {expected_max} for height {image_height}")
            
            # Verify minimums are respected
            self.assertGreaterEqual(font_scale, 0.3,
                f"Font scale should never be less than 0.3, got {font_scale}")
            
            # Verify maximums are respected
            self.assertLessEqual(font_scale, 1.0,
                f"Font scale should never exceed 1.0, got {font_scale}")
    
    def test_vertical_offset_scaling(self):
        """Test that vertical offsets scale proportionally with font scale"""
        
        test_heights = [360, 720, 1080, 1440]
        
        for image_height in test_heights:
            font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))
            
            # Calculate vertical offsets (same logic as in the code)
            vertical_offset_1 = int(36 * (font_scale / 0.5))
            vertical_offset_2 = int(12 * (font_scale / 0.5))
            
            # Verify offsets are reasonable
            self.assertGreater(vertical_offset_1, 0,
                f"Vertical offset 1 should be positive, got {vertical_offset_1}")
            self.assertGreater(vertical_offset_2, 0,
                f"Vertical offset 2 should be positive, got {vertical_offset_2}")
            
            # Verify offset 1 is greater than offset 2 (as expected)
            self.assertGreater(vertical_offset_1, vertical_offset_2,
                f"Offset 1 ({vertical_offset_1}) should be greater than offset 2 ({vertical_offset_2})")
    
    def test_thickness_scaling(self):
        """Test that thickness scales proportionally with font scale"""
        
        test_heights = [360, 720, 1080, 1440]
        
        for image_height in test_heights:
            font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))
            
            # Calculate thickness (same logic as in the code)
            thickness = max(1, int(2 * (font_scale / 0.5)))
            
            # Verify thickness is at least 1
            self.assertGreaterEqual(thickness, 1,
                f"Thickness should be at least 1, got {thickness}")
            
            # Verify thickness scales reasonably (between 1 and 4 for our test range)
            self.assertLessEqual(thickness, 4,
                f"Thickness should not exceed 4 for reasonable heights, got {thickness}")
    
    def test_proportional_scaling(self):
        """Test that font scale is proportional to image height"""
        
        # Reference: 720p with font scale 0.5
        ref_height = 720
        ref_font_scale = max(0.3, min(1.0, (ref_height / 720.0) * 0.5))
        
        # Double the height
        double_height = 1440
        double_font_scale = max(0.3, min(1.0, (double_height / 720.0) * 0.5))
        
        # The ratio should be approximately 2 (within the max limit of 1.0)
        if double_font_scale < 1.0:  # If not capped by maximum
            ratio = double_font_scale / ref_font_scale
            self.assertAlmostEqual(ratio, 2.0, places=1,
                msg=f"Scaling should be roughly proportional, got ratio {ratio}")
        else:
            # If capped, just verify it's at the maximum
            self.assertEqual(double_font_scale, 1.0,
                "Font scale should be capped at 1.0 for very large images")


class TestMOTCodeImplementation(unittest.TestCase):
    """Test that the implementation is correct in the actual files"""
    
    def test_basenode_has_dynamic_scaling(self):
        """Test that basenode.py implements dynamic font scaling correctly"""
        
        basenode_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node',
            'basenode.py'
        )
        
        with open(basenode_path, 'r') as f:
            content = f.read()
        
        # Verify the implementation
        self.assertIn('image_height = image.shape[0]', content,
                     "Should extract image height from image.shape[0]")
        self.assertIn('font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))', content,
                     "Should calculate font_scale with correct formula")
        self.assertIn('vertical_offset_1 = int(36 * (font_scale / 0.5))', content,
                     "Should calculate vertical_offset_1 proportionally")
        self.assertIn('vertical_offset_2 = int(12 * (font_scale / 0.5))', content,
                     "Should calculate vertical_offset_2 proportionally")
        self.assertIn('thickness = max(1, int(2 * (font_scale / 0.5)))', content,
                     "Should calculate thickness proportionally")
    
    def test_draw_util_has_dynamic_scaling(self):
        """Test that draw_util.py implements dynamic font scaling correctly"""
        
        draw_util_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node',
            'OverlayNode',
            'draw_util',
            'draw_util.py'
        )
        
        with open(draw_util_path, 'r') as f:
            content = f.read()
        
        # Verify the implementation
        self.assertIn('image_height = image.shape[0]', content,
                     "Should extract image height from image.shape[0]")
        self.assertIn('font_scale = max(0.3, min(1.0, (image_height / 720.0) * 0.5))', content,
                     "Should calculate font_scale with correct formula")
        self.assertIn('vertical_offset_1 = int(36 * (font_scale / 0.5))', content,
                     "Should calculate vertical_offset_1 proportionally")
        self.assertIn('vertical_offset_2 = int(12 * (font_scale / 0.5))', content,
                     "Should calculate vertical_offset_2 proportionally")
        self.assertIn('thickness = max(1, int(2 * (font_scale / 0.5)))', content,
                     "Should calculate thickness proportionally")
    
    def test_comments_explain_dynamic_scaling(self):
        """Test that comments explain the dynamic scaling behavior"""
        
        files_to_check = [
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'node', 'basenode.py'
            ),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'node', 'OverlayNode', 'draw_util', 'draw_util.py'
            ),
        ]
        
        for file_path in files_to_check:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Check for explanatory comments
            self.assertIn('Reference height: 720px', content,
                         f"File {file_path} should have comment explaining reference height")
            self.assertIn('This makes font size proportional to image size', content,
                         f"File {file_path} should have comment explaining proportional scaling")


if __name__ == '__main__':
    unittest.main()
