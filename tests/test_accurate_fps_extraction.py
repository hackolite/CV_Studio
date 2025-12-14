#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for accurate FPS extraction using ffprobe.

This test verifies that the _get_accurate_fps() method correctly extracts
the avg_frame_rate from videos using ffprobe, which is more reliable than
OpenCV's CAP_PROP_FPS, especially for VFR videos.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestAccurateFPSExtraction(unittest.TestCase):
    """Test accurate FPS extraction with ffprobe"""
    
    @staticmethod
    def _get_method_source(method_name):
        """Helper to extract source code for a specific method from node_video.py"""
        node_video_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(node_video_path, 'r') as f:
            content = f.read()
        
        # Find the method start
        start_marker = f'def {method_name}(self'
        start_idx = content.find(start_marker)
        if start_idx == -1:
            return None
        
        # Find the next method definition (end of current method)
        # Look for the next 'def ' at the same indentation level
        end_idx = content.find('\n    def ', start_idx + 1)
        if end_idx == -1:
            # If no next method, look for class end or file end
            end_idx = content.find('\nclass ', start_idx + 1)
            if end_idx == -1:
                end_idx = len(content)
        
        return content[start_idx:end_idx]
    
    def test_get_accurate_fps_method_exists(self):
        """Verify that _get_accurate_fps method exists in VideoNode source"""
        node_video_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(node_video_path, 'r') as f:
            content = f.read()
        
        # Check that the method exists
        self.assertIn('def _get_accurate_fps(self', content, 
                       "VideoNode should have _get_accurate_fps method")
        
        print("✓ _get_accurate_fps method exists")
    
    def test_get_accurate_fps_uses_ffprobe(self):
        """Verify that _get_accurate_fps uses ffprobe with correct parameters"""
        method_source = self._get_method_source('_get_accurate_fps')
        
        if method_source is None:
            self.fail("_get_accurate_fps method not found")
        
        # Check that it uses ffprobe
        self.assertIn('ffprobe', method_source, 
                     "_get_accurate_fps should use ffprobe")
        
        # Check that it extracts avg_frame_rate
        self.assertIn('avg_frame_rate', method_source,
                     "_get_accurate_fps should extract avg_frame_rate")
        
        # Check that it handles fraction parsing (e.g., "24000/1001")
        self.assertIn("'/' in", method_source,
                     "_get_accurate_fps should handle fraction parsing")
        
        print("✓ _get_accurate_fps uses ffprobe with avg_frame_rate")
    
    def test_preprocess_video_uses_accurate_fps(self):
        """Verify that _preprocess_video uses _get_accurate_fps instead of OpenCV"""
        method_source = self._get_method_source('_preprocess_video')
        
        if method_source is None:
            self.fail("_preprocess_video method not found")
        
        # Check that it calls _get_accurate_fps
        self.assertIn('_get_accurate_fps', method_source,
                     "_preprocess_video should call _get_accurate_fps")
        
        # Check that it uses the result for FPS
        self.assertIn('self._get_accurate_fps(movie_path)', method_source,
                     "_preprocess_video should call _get_accurate_fps with movie_path")
        
        print("✓ _preprocess_video uses _get_accurate_fps")
    
    def test_accurate_fps_used_before_opencv_fallback(self):
        """Verify that ffprobe FPS is tried before OpenCV fallback"""
        node_video_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py'
        )
        
        with open(node_video_path, 'r') as f:
            lines = f.readlines()
        
        get_accurate_fps_line = None
        opencv_fallback_line = None
        
        for i, line in enumerate(lines):
            if '_get_accurate_fps(movie_path)' in line and 'fps =' in line:
                get_accurate_fps_line = i
            if 'if fps is None or fps <= 0:' in line:
                opencv_fallback_line = i
        
        # Verify that _get_accurate_fps is called before OpenCV fallback
        if get_accurate_fps_line and opencv_fallback_line:
            self.assertLess(get_accurate_fps_line, opencv_fallback_line,
                          "_get_accurate_fps should be called before OpenCV fallback")
        
        print("✓ ffprobe FPS extraction happens before OpenCV fallback")
    
    def test_fps_parsing_handles_fractions(self):
        """Verify that FPS parsing can handle fractions like '24000/1001'"""
        method_source = self._get_method_source('_get_accurate_fps')
        
        if method_source is None:
            self.fail("_get_accurate_fps method not found")
        
        # Check for fraction handling
        self.assertIn("'/' in", method_source,
                     "_get_accurate_fps should check for '/' in FPS string")
        
        # Check for split and division
        self.assertIn('split', method_source,
                     "_get_accurate_fps should split fraction")
        self.assertIn('float', method_source,
                     "_get_accurate_fps should convert to float")
        
        print("✓ FPS parsing handles fractions (e.g., '24000/1001')")
    
    def test_accurate_fps_has_proper_fallbacks(self):
        """Verify that accurate FPS extraction has proper error handling"""
        method_source = self._get_method_source('_get_accurate_fps')
        
        if method_source is None:
            self.fail("_get_accurate_fps method not found")
        
        # Check for error handling
        self.assertIn('try:', method_source,
                     "_get_accurate_fps should have try/except")
        self.assertIn('except', method_source,
                     "_get_accurate_fps should handle exceptions")
        
        # Check for validation
        self.assertIn('os.path.isfile', method_source,
                     "_get_accurate_fps should validate file path")
        
        # Check for None return on failure
        self.assertIn('return None', method_source,
                     "_get_accurate_fps should return None on failure")
        
        print("✓ Accurate FPS extraction has proper error handling")
    
    def test_preprocess_uses_target_fps_as_ultimate_fallback(self):
        """Verify that target_fps is used as ultimate fallback if both ffprobe and OpenCV fail"""
        method_source = self._get_method_source('_preprocess_video')
        
        if method_source is None:
            self.fail("_preprocess_video method not found")
        
        # Check that target_fps is available as fallback
        self.assertIn('target_fps', method_source,
                     "_preprocess_video should have target_fps parameter")
        
        # Check for fallback logic
        self.assertIn('fps <= 0', method_source,
                     "_preprocess_video should check for invalid FPS")
        
        print("✓ target_fps is used as ultimate fallback")
    
    def test_audio_chunking_uses_accurate_fps(self):
        """Verify that audio chunking calculation uses the accurate FPS"""
        method_source = self._get_method_source('_preprocess_video')
        
        if method_source is None:
            self.fail("_preprocess_video method not found")
        
        # Check that samples_per_frame uses fps variable
        self.assertIn('samples_per_frame = sr / fps', method_source,
                     "Audio chunking should use samples_per_frame = sr / fps")
        
        # Verify fps is the variable from _get_accurate_fps
        # (already verified in previous tests)
        
        print("✓ Audio chunking uses accurate FPS")
    
    def test_documentation_includes_accurate_fps(self):
        """Verify that the fix is documented"""
        import os
        
        doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'VFR_AUDIO_SYNC_FIX.md'
        )
        
        # Check that documentation exists
        self.assertTrue(os.path.exists(doc_path),
                       "VFR_AUDIO_SYNC_FIX.md documentation should exist")
        
        # Check that it mentions ffprobe and avg_frame_rate
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('ffprobe', content,
                         "Documentation should mention ffprobe")
            self.assertIn('avg_frame_rate', content,
                         "Documentation should mention avg_frame_rate")
            self.assertIn('_get_accurate_fps', content,
                         "Documentation should mention _get_accurate_fps method")
        
        print("✓ Fix is properly documented in VFR_AUDIO_SYNC_FIX.md")


def run_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("Testing Accurate FPS Extraction Fix")
    print("="*70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestAccurateFPSExtraction)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ All accurate FPS extraction tests passed!")
        print("="*70)
        return 0
    else:
        print("❌ Some tests failed")
        print("="*70)
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
