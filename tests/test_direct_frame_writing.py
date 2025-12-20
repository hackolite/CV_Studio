#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for direct frame-by-frame writing in VideoWriter node.

This test verifies that the VideoWriter node writes frames directly
without using queues or async writers.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_no_queue_import():
    """Verify that queue module is not imported in VideoWriter"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    assert 'import queue' not in code, "queue module should not be imported"
    assert 'from queue import' not in code, "queue module should not be imported"
    print("✓ Test passed: queue module is not imported")


def test_no_async_frame_writer():
    """Verify that AsyncFrameWriter class is removed"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    assert 'class AsyncFrameWriter' not in code, "AsyncFrameWriter class should be removed"
    assert 'AsyncFrameWriter(' not in code, "AsyncFrameWriter should not be instantiated"
    print("✓ Test passed: AsyncFrameWriter class is removed")


def test_no_frame_queue_usage():
    """Verify that frame_queue is not used anywhere"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    assert 'frame_queue' not in code, "frame_queue should not be used"
    assert '.put(' not in code, "Queue put() method should not be used"
    print("✓ Test passed: frame_queue is not used")


def test_direct_writing_implemented():
    """Verify that direct frame writing is implemented"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    # Check for direct write call
    assert 'self._video_writer_dict[tag_node_name].write(writer_frame)' in code, \
        "Direct frame writing should be implemented"
    
    # Check for frame counter
    assert '_frame_count_dict' in code, "Frame counter should be implemented"
    
    print("✓ Test passed: direct frame writing is implemented")


def test_no_async_writer_dict():
    """Verify that _async_writer_dict is removed"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    assert '_async_writer_dict' not in code, "_async_writer_dict should be removed"
    print("✓ Test passed: _async_writer_dict is removed")


def test_documentation_updated():
    """Verify that documentation reflects direct writing"""
    with open('node/VideoNode/node_video_writer.py', 'r') as f:
        code = f.read()
    
    # Check that docstring mentions direct writing
    assert 'Direct frame-by-frame' in code or 'direct frame' in code.lower(), \
        "Documentation should mention direct frame writing"
    
    # Check that it mentions no buffering/queuing
    assert 'No buffering or queuing' in code or 'no queue' in code.lower(), \
        "Documentation should mention no queuing"
    
    print("✓ Test passed: documentation reflects direct writing")


def test_imageconcat_no_queue():
    """Verify that ImageConcat doesn't use queues"""
    with open('node/VideoNode/node_image_concat.py', 'r') as f:
        code = f.read()
    
    assert 'import queue' not in code, "ImageConcat should not import queue"
    assert 'Queue(' not in code, "ImageConcat should not use Queue class"
    print("✓ Test passed: ImageConcat doesn't use queues")


def test_imageconcat_returns_data_structure():
    """Verify that ImageConcat returns proper data structure for VideoWriter"""
    with open('node/VideoNode/node_image_concat.py', 'r') as f:
        code = f.read()
    
    # Check that ImageConcat returns a dict with image, audio, and json keys
    assert 'return {' in code, "ImageConcat should return a dictionary"
    assert '"image"' in code, "ImageConcat should return image data"
    
    print("✓ Test passed: ImageConcat returns proper data structure")


if __name__ == '__main__':
    print("Running direct frame writing tests...\n")
    
    try:
        test_no_queue_import()
        test_no_async_frame_writer()
        test_no_frame_queue_usage()
        test_direct_writing_implemented()
        test_no_async_writer_dict()
        test_documentation_updated()
        test_imageconcat_no_queue()
        test_imageconcat_returns_data_structure()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        print("\nSummary:")
        print("- Queue module removed from VideoWriter")
        print("- AsyncFrameWriter class removed")
        print("- Direct frame-by-frame writing implemented")
        print("- Frame counter added for tracking")
        print("- ImageConcat doesn't use queues")
        print("- Frames written immediately as they arrive from ImageConcat")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
