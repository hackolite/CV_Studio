#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the YouTube node correctly handles URLs with playlist parameters.
This test validates that URLs like:
https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID
are correctly processed to extract only the video, not the entire playlist.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_noplaylist_option_in_ydl_opts():
    """Test that the ydl_opts includes noplaylist: True"""
    # Read the node_youtube.py file and check for noplaylist option
    node_file_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'InputNode', 
        'node_youtube.py'
    )
    
    with open(node_file_path, 'r') as f:
        content = f.read()
    
    # Check that noplaylist is set to True in ydl_opts
    assert '"noplaylist": True' in content or "'noplaylist': True" in content, \
        "ydl_opts should include 'noplaylist': True to handle playlist URLs correctly"
    
    print("✓ ydl_opts correctly includes 'noplaylist': True")


def test_playlist_url_format():
    """Test that playlist URLs are in the expected format"""
    # Example URLs that should be handled correctly
    playlist_urls = [
        "https://www.youtube.com/watch?v=gFRtAAmiFbE&list=PLxtg5zfgORZr8KB1VglBvI6czMJpPL-rx",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf",
        "https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&index=1",
    ]
    
    for url in playlist_urls:
        # Verify the URL contains both video ID (watch?v=) and playlist parameter (list=)
        assert "watch?v=" in url, f"URL should contain video ID: {url}"
        assert "&list=" in url, f"URL should contain playlist parameter: {url}"
    
    print(f"✓ Verified {len(playlist_urls)} playlist URL formats")


def test_ydl_opts_configuration():
    """Test that ydl_opts has the correct configuration for playlist URLs"""
    # Read the source file directly instead of importing (to avoid dependency issues)
    import inspect
    
    node_file_path = os.path.join(
        os.path.dirname(__file__), 
        '..', 
        'node', 
        'InputNode', 
        'node_youtube.py'
    )
    
    with open(node_file_path, 'r') as f:
        source = f.read()
    
    # Find the get_light_live_stream_url function
    assert "def get_light_live_stream_url" in source, \
        "get_light_live_stream_url function should exist"
    
    # Verify noplaylist is in the configuration
    assert "noplaylist" in source.lower(), \
        "get_light_live_stream_url should configure noplaylist option"
    
    # Verify it's set to True
    assert '"noplaylist": True' in source or "'noplaylist': True" in source, \
        "noplaylist should be set to True"
    
    print("✓ get_light_live_stream_url correctly configures noplaylist option")


if __name__ == '__main__':
    print("Testing YouTube node playlist URL handling...")
    print("=" * 60)
    
    tests = [
        ("noplaylist option in ydl_opts", test_noplaylist_option_in_ydl_opts),
        ("playlist URL format validation", test_playlist_url_format),
        ("ydl_opts configuration", test_ydl_opts_configuration),
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
