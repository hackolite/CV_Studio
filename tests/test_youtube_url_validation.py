#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the YouTube node properly validates URLs and handles errors.
This test validates that:
1. Empty/None URLs are rejected with proper error messages
2. Invalid URLs are handled gracefully
3. DownloadError exceptions are caught and converted to ValueError
"""
import sys
import os
import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.InputNode.node_youtube import get_light_live_stream_url


def test_empty_url():
    """Test that empty URL raises ValueError"""
    with pytest.raises(ValueError, match="URL must be a non-empty string"):
        get_light_live_stream_url("")


def test_none_url():
    """Test that None URL raises ValueError"""
    with pytest.raises(ValueError, match="URL must be a non-empty string"):
        get_light_live_stream_url(None)


def test_whitespace_url():
    """Test that whitespace-only URL raises ValueError"""
    with pytest.raises(ValueError, match="URL cannot be empty or whitespace"):
        get_light_live_stream_url("   ")


def test_non_string_url():
    """Test that non-string URL raises ValueError"""
    with pytest.raises(ValueError, match="URL must be a non-empty string"):
        get_light_live_stream_url(123)


def test_invalid_url_format():
    """Test that invalid URL format is handled gracefully"""
    with pytest.raises(ValueError, match="(Failed to download video info|Unexpected error)"):
        get_light_live_stream_url("not a valid url")


def test_unavailable_video():
    """Test that unavailable video is handled gracefully"""
    # Using a video ID that is known to be unavailable from the error trace
    unavailable_url = "https://www.youtube.com/watch?v=4Z6wOToTgh0"
    with pytest.raises(ValueError, match="Failed to download video info"):
        get_light_live_stream_url(unavailable_url)


if __name__ == '__main__':
    print("Testing YouTube URL validation...")
    print("=" * 60)
    
    tests = [
        ("Empty URL", test_empty_url),
        ("None URL", test_none_url),
        ("Whitespace URL", test_whitespace_url),
        ("Non-string URL", test_non_string_url),
        ("Invalid URL format", test_invalid_url_format),
        ("Unavailable video", test_unavailable_video),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            print(f"✓ {name} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
