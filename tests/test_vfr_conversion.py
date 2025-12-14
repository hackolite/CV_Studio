#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test VFR to CFR video conversion functionality in VideoNode.
"""
import os
import sys
import tempfile
import subprocess
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.node_video import VideoNode


class TestVFRConversion:
    """Tests for VFR detection and conversion"""
    
    def test_video_node_has_vfr_methods(self):
        """Test that VideoNode has VFR detection and conversion methods"""
        node = VideoNode()
        assert hasattr(node, '_detect_vfr'), "VideoNode should have _detect_vfr method"
        assert hasattr(node, '_convert_vfr_to_cfr'), "VideoNode should have _convert_vfr_to_cfr method"
        assert hasattr(node, '_converted_videos'), "VideoNode should have _converted_videos dict"
    
    def test_detect_vfr_nonexistent_file(self):
        """Test VFR detection with non-existent file"""
        node = VideoNode()
        # Should return False (assume CFR) when file doesn't exist
        is_vfr = node._detect_vfr("/nonexistent/video.mp4")
        assert is_vfr == False, "Non-existent file should be treated as CFR"
    
    def test_convert_vfr_to_cfr_nonexistent_file(self):
        """Test VFR conversion with non-existent file"""
        node = VideoNode()
        # Should return original path when file doesn't exist
        result = node._convert_vfr_to_cfr("/nonexistent/video.mp4")
        assert result == "/nonexistent/video.mp4", "Should return original path for non-existent file"
    
    @pytest.mark.skipif(not os.path.exists("/usr/bin/ffmpeg") and not os.path.exists("/usr/local/bin/ffmpeg"), 
                        reason="ffmpeg not installed")
    def test_create_test_cfr_video(self):
        """Test creating a simple CFR video with ffmpeg"""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            test_video_path = tmp.name
        
        try:
            # Create a simple 1-second test video at 24 fps (CFR)
            cmd = [
                "ffmpeg", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=24",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", test_video_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if result.returncode == 0:
                # Test that the video was created
                assert os.path.exists(test_video_path), "Test video should be created"
                assert os.path.getsize(test_video_path) > 0, "Test video should not be empty"
                
                # Test VFR detection on CFR video
                node = VideoNode()
                is_vfr = node._detect_vfr(test_video_path)
                # CFR video should be detected as CFR (not VFR)
                assert is_vfr == False, "CFR test video should be detected as CFR"
            else:
                pytest.skip(f"Failed to create test video: {result.stderr.decode()}")
        finally:
            # Clean up
            if os.path.exists(test_video_path):
                os.unlink(test_video_path)
    
    def test_cleanup_removes_converted_videos(self):
        """Test that cleanup removes converted video files"""
        node = VideoNode()
        node_id = "test_node_123"
        
        # Create a fake converted video path
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            fake_cfr_path = tmp.name
        
        try:
            # Add to converted videos
            node._converted_videos[node_id] = fake_cfr_path
            
            # Verify it exists
            assert os.path.exists(fake_cfr_path), "Fake CFR video should exist"
            
            # Call cleanup
            node._cleanup_audio_chunks(node_id)
            
            # Verify it was deleted
            assert not os.path.exists(fake_cfr_path), "CFR video should be deleted after cleanup"
            assert node_id not in node._converted_videos, "node_id should be removed from _converted_videos"
        finally:
            # Ensure cleanup even if test fails
            if os.path.exists(fake_cfr_path):
                os.unlink(fake_cfr_path)
    
    def test_preprocess_video_calls_vfr_detection(self, monkeypatch):
        """Test that _preprocess_video calls VFR detection"""
        node = VideoNode()
        node._opencv_setting_dict = {"use_pref_counter": False}
        
        # Track if _detect_vfr was called
        detect_vfr_called = []
        
        def mock_detect_vfr(video_path):
            detect_vfr_called.append(video_path)
            return False  # Return CFR
        
        # Mock the _detect_vfr method
        monkeypatch.setattr(node, '_detect_vfr', mock_detect_vfr)
        
        # Create a dummy video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            test_video = tmp.name
        
        try:
            # Call preprocess (will fail at audio extraction but that's ok)
            try:
                node._preprocess_video("test_node", test_video, target_fps=24)
            except Exception:
                pass  # Expected to fail at audio extraction
            
            # Verify _detect_vfr was called
            assert len(detect_vfr_called) == 1, "_detect_vfr should be called once"
            assert detect_vfr_called[0] == test_video, "_detect_vfr should be called with correct path"
        finally:
            if os.path.exists(test_video):
                os.unlink(test_video)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
