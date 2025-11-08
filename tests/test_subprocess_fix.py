#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test for subprocess.run fix in _prepare_spectrogram"""

import pytest
import sys
import os
import subprocess
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock, call

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.node_video import VideoNode


def test_subprocess_call_no_error():
    """
    Test that subprocess.run in _prepare_spectrogram doesn't raise ValueError.
    
    This test verifies that the fix for the subprocess.run call is correct.
    Previously, the call used both capture_output=True and stderr=subprocess.DEVNULL,
    which raised ValueError: stdout and stderr arguments may not be used with capture_output.
    
    The fix replaces capture_output=True with explicit stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL.
    """
    # Create a minimal video file for testing
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_video:
        video_path = tmp_video.name
    
    try:
        # Create VideoNode instance
        node = VideoNode()
        node_id = 'test_node_subprocess'
        
        # Mock subprocess.run to verify it's called with correct arguments
        with patch('subprocess.run') as mock_run:
            # Mock the return value
            mock_run.return_value = MagicMock()
            
            # Mock other dependencies to avoid actual processing
            with patch('scipy.io.wavfile.read') as mock_wav_read:
                mock_wav_read.return_value = (22050, np.zeros(22050))  # 1 second of silence
                
                with patch('cv2.imread') as mock_imread:
                    mock_imread.return_value = np.zeros((100, 100, 3), dtype=np.uint8)
                    
                    with patch.object(node, 'convert_cv_to_dpg', return_value=np.zeros(100)):
                        # This should not raise ValueError about capture_output
                        try:
                            node._prepare_spectrogram(node_id, video_path)
                        except Exception as e:
                            # The test should not fail due to subprocess argument error
                            assert 'stdout and stderr arguments may not be used with capture_output' not in str(e), \
                                f"subprocess.run still has argument conflict: {e}"
            
            # Verify subprocess.run was called with correct arguments
            assert mock_run.called, "subprocess.run should be called"
            call_args = mock_run.call_args
            
            # Check that the call does NOT use capture_output=True
            assert 'capture_output' not in call_args.kwargs or call_args.kwargs['capture_output'] is False, \
                "subprocess.run should not use capture_output=True"
            
            # Check that stdout and stderr are set to DEVNULL
            assert call_args.kwargs.get('stdout') == subprocess.DEVNULL, \
                f"subprocess.run should have stdout=subprocess.DEVNULL, got {call_args.kwargs.get('stdout')}"
            assert call_args.kwargs.get('stderr') == subprocess.DEVNULL, \
                f"subprocess.run should have stderr=subprocess.DEVNULL, got {call_args.kwargs.get('stderr')}"
            
        print("✓ test_subprocess_call_no_error passed")
        
    finally:
        # Clean up temporary file
        if os.path.exists(video_path):
            os.unlink(video_path)


if __name__ == '__main__':
    test_subprocess_call_no_error()
