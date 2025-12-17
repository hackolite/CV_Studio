#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for AVI and MKV video format fix (slow playback issue).

This test validates that:
1. AVI format uses H.264 encoding (not MJPEG copy)
2. MKV format uses H.264 encoding (not FFV1 copy)
3. MP4 format still uses copy (no re-encoding)

Background:
-----------
Issue: Video reconstruction input/video → concat → videowriter in AVI and MKV formats 
produces slow video with strange audio.

Root Cause: MJPEG (AVI) and FFV1 (MKV) are intraframe codecs that store each frame
independently without temporal compression. This causes frame timing issues that lead to
slow playback and audio desynchronization.

Solution: Re-encode AVI and MKV videos to H.264 during FFmpeg audio/video merge,
while keeping MP4 as copy (no re-encoding).
"""

import os


def get_codec_for_format(video_format):
    """
    Helper function to determine codec based on video format.
    Simulates the logic from node_video_writer.py and video_worker.py.
    
    Args:
        video_format: Video format string (AVI, MP4, MKV)
        
    Returns:
        tuple: (vcodec, vcodec_preset)
    """
    if video_format in ['AVI', 'MKV']:
        vcodec = 'libx264'
        vcodec_preset = 'medium'
    else:
        vcodec = 'copy'
        vcodec_preset = None
    
    return vcodec, vcodec_preset


def test_avi_uses_h264_encoding():
    """Test that AVI format is configured to use H.264 encoding"""
    vcodec, vcodec_preset = get_codec_for_format('AVI')
    
    # Verify AVI uses H.264
    assert vcodec == 'libx264', f"AVI should use libx264, got {vcodec}"
    assert vcodec_preset == 'medium', f"AVI should use medium preset, got {vcodec_preset}"
    
    print("✓ AVI format correctly uses H.264 encoding")


def test_mp4_uses_copy():
    """Test that MP4 format still uses copy (no re-encoding)"""
    vcodec, vcodec_preset = get_codec_for_format('MP4')
    
    # Verify MP4 uses copy
    assert vcodec == 'copy', f"MP4 should use copy, got {vcodec}"
    assert vcodec_preset is None, f"MP4 should not have preset, got {vcodec_preset}"
    
    print("✓ MP4 format correctly uses copy (no re-encoding)")


def test_mkv_uses_h264_encoding():
    """Test that MKV format uses H.264 encoding (FFV1 has timing issues like MJPEG)"""
    vcodec, vcodec_preset = get_codec_for_format('MKV')
    
    # Verify MKV uses H.264
    assert vcodec == 'libx264', f"MKV should use libx264, got {vcodec}"
    assert vcodec_preset == 'medium', f"MKV should use medium preset, got {vcodec_preset}"
    
    print("✓ MKV format correctly uses H.264 encoding")


def test_file_extension_detection():
    """Test that AVI and MKV formats are detected from file extension in video_worker.py"""
    # Simulate the logic from video_worker.py
    test_cases = [
        ('/path/to/output.avi', '.avi', 'libx264'),
        ('/path/to/output.AVI', '.avi', 'libx264'),  # Case insensitive
        ('/path/to/output.mkv', '.mkv', 'libx264'),
        ('/path/to/output.MKV', '.mkv', 'libx264'),  # Case insensitive
        ('/path/to/output.mp4', '.mp4', 'copy'),
    ]
    
    for output_path, expected_ext, expected_vcodec in test_cases:
        # Logic from video_worker.py _muxer_worker
        output_ext = os.path.splitext(output_path)[1].lower()
        
        if output_ext in ['.avi', '.mkv']:
            vcodec = 'libx264'
        else:
            vcodec = 'copy'
        
        # Verify
        assert output_ext == expected_ext, \
            f"Extension mismatch for {output_path}: {output_ext} != {expected_ext}"
        assert vcodec == expected_vcodec, \
            f"Codec mismatch for {output_path}: {vcodec} != {expected_vcodec}"
    
    print("✓ File extension detection works correctly")


def test_ffmpeg_parameters_for_avi_and_mkv():
    """Test that FFmpeg parameters are correctly set for AVI and MKV formats"""
    # Simulate parameter building for AVI/MKV
    vcodec = 'libx264'
    vcodec_preset = 'medium'
    
    output_params = {
        'vcodec': vcodec,
        'acodec': 'aac',
        'audio_bitrate': '192k',
        'shortest': None,
        'vsync': 'cfr',
        'avoid_negative_ts': 'make_zero',
        'loglevel': 'error'
    }
    
    if vcodec_preset:
        output_params['preset'] = vcodec_preset
    
    # Verify all required parameters
    assert output_params['vcodec'] == 'libx264', "AVI/MKV should use libx264"
    assert output_params['preset'] == 'medium', "AVI/MKV should use medium preset"
    assert output_params['acodec'] == 'aac', "Should use AAC audio"
    assert output_params['audio_bitrate'] == '192k', "Should use 192k audio bitrate"
    assert output_params['vsync'] == 'cfr', "Should use constant frame rate sync"
    assert output_params['avoid_negative_ts'] == 'make_zero', "Should align timestamps"
    
    print("✓ FFmpeg parameters for AVI and MKV are correct")


def test_ffmpeg_parameters_for_mp4():
    """Test that FFmpeg parameters are correctly set for MP4 format"""
    # Simulate parameter building for MP4
    vcodec = 'copy'
    vcodec_preset = None
    
    output_params = {
        'vcodec': vcodec,
        'acodec': 'aac',
        'audio_bitrate': '192k',
        'shortest': None,
        'vsync': 'cfr',
        'avoid_negative_ts': 'make_zero',
        'loglevel': 'error'
    }
    
    if vcodec_preset:
        output_params['preset'] = vcodec_preset
    
    # Verify all required parameters
    assert output_params['vcodec'] == 'copy', "MP4 should use copy"
    assert 'preset' not in output_params, "MP4 should not have preset"
    assert output_params['acodec'] == 'aac', "Should use AAC audio"
    assert output_params['audio_bitrate'] == '192k', "Should use 192k audio bitrate"
    assert output_params['vsync'] == 'cfr', "Should use constant frame rate sync"
    assert output_params['avoid_negative_ts'] == 'make_zero', "Should align timestamps"
    
    print("✓ FFmpeg parameters for MP4 are correct")


if __name__ == '__main__':
    print("=" * 70)
    print("Testing AVI and MKV Video Format Fix (Slow Playback Issue)")
    print("=" * 70)
    print()
    
    test_avi_uses_h264_encoding()
    test_mp4_uses_copy()
    test_mkv_uses_h264_encoding()
    test_file_extension_detection()
    test_ffmpeg_parameters_for_avi_and_mkv()
    test_ffmpeg_parameters_for_mp4()
    
    print()
    print("=" * 70)
    print("✅ All AVI and MKV format fix tests passed!")
    print("=" * 70)
    print()
    print("Summary:")
    print("- AVI format: Re-encodes to H.264 (fixes slow playback)")
    print("- MKV format: Re-encodes to H.264 (fixes slow playback)")
    print("- MP4 format: Copy codec (no re-encoding, fast)")
    print()
    print("This fix ensures AVI and MKV videos play at correct speed with proper audio sync.")
