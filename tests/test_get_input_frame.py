#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the get_input_frame method in basenode.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_get_input_frame_method_exists():
    """Test that the get_input_frame method exists on Node class"""
    # Mock the dependencies
    import unittest.mock as mock
    
    # Mock numpy and cv2
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    # Test the method exists
    assert hasattr(Node, 'get_input_frame'), "get_input_frame method not found"
    print("✓ get_input_frame method exists on Node class")


def test_get_input_frame_signature():
    """Test that the get_input_frame method has correct signature"""
    import unittest.mock as mock
    import inspect
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    n = Node()
    sig = inspect.signature(n.get_input_frame)
    params = list(sig.parameters.keys())
    
    assert params == ['connection_list', 'node_image_dict', 'node_audio_dict'], \
        f"Wrong parameters: {params}"
    
    # Check default value for node_audio_dict
    assert sig.parameters['node_audio_dict'].default is None, \
        "node_audio_dict should have default value None"
    
    print("✓ get_input_frame has correct signature")


def test_get_input_frame_returns_image():
    """Test that get_input_frame returns image from node_image_dict"""
    import unittest.mock as mock
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    n = Node()
    
    # Create test data
    connection_list = [
        ['1:NodeA:IMAGE:Output01', '2:NodeB:IMAGE:Input01']
    ]
    test_frame = "test_image_data"
    node_image_dict = {
        '1:NodeA': test_frame
    }
    
    # Test getting frame
    result = n.get_input_frame(connection_list, node_image_dict)
    assert result == test_frame, f"Expected {test_frame}, got {result}"
    print("✓ get_input_frame correctly returns image frame")


def test_get_input_frame_returns_audio():
    """Test that get_input_frame returns audio from node_audio_dict when image not found"""
    import unittest.mock as mock
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    n = Node()
    
    # Create test data
    connection_list = [
        ['1:NodeA:AUDIO:Output01', '2:NodeB:AUDIO:Input01']
    ]
    test_audio = "test_audio_data"
    node_image_dict = {}
    node_audio_dict = {
        '1:NodeA': test_audio
    }
    
    # Test getting audio
    result = n.get_input_frame(connection_list, node_image_dict, node_audio_dict)
    assert result == test_audio, f"Expected {test_audio}, got {result}"
    print("✓ get_input_frame correctly returns audio frame")


def test_get_input_frame_returns_none():
    """Test that get_input_frame returns None when no connection found"""
    import unittest.mock as mock
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    n = Node()
    
    # Create test data with no IMAGE or AUDIO connections
    connection_list = [
        ['1:NodeA:INT:Output01', '2:NodeB:INT:Input01']
    ]
    node_image_dict = {}
    
    # Test getting frame
    result = n.get_input_frame(connection_list, node_image_dict)
    assert result is None, f"Expected None, got {result}"
    print("✓ get_input_frame returns None when no IMAGE/AUDIO connection")


def test_get_input_frame_prefers_image():
    """Test that get_input_frame finds IMAGE connection first"""
    import unittest.mock as mock
    
    # Mock the dependencies
    sys.modules['numpy'] = mock.MagicMock()
    sys.modules['cv2'] = mock.MagicMock()
    sys.modules['dearpygui'] = mock.MagicMock()
    sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
    
    from node.basenode import Node
    
    n = Node()
    
    # Create test data with multiple connections
    connection_list = [
        ['1:NodeA:INT:Output01', '2:NodeB:INT:Input01'],
        ['3:NodeC:IMAGE:Output01', '2:NodeB:IMAGE:Input02'],
        ['4:NodeD:FLOAT:Output01', '2:NodeB:FLOAT:Input03']
    ]
    test_frame = "test_image_data"
    node_image_dict = {
        '3:NodeC': test_frame
    }
    
    # Test getting frame
    result = n.get_input_frame(connection_list, node_image_dict)
    assert result == test_frame, f"Expected {test_frame}, got {result}"
    print("✓ get_input_frame correctly finds IMAGE connection among multiple connections")


if __name__ == '__main__':
    print("Running tests for get_input_frame method...\n")
    
    try:
        test_get_input_frame_method_exists()
        test_get_input_frame_signature()
        test_get_input_frame_returns_image()
        test_get_input_frame_returns_audio()
        test_get_input_frame_returns_none()
        test_get_input_frame_prefers_image()
        
        print("\n" + "="*60)
        print("All tests passed! ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
