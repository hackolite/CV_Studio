#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test audio spectrogram support in the node system."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_main_imports():
    """Test that main.py can be imported without errors."""
    try:
        import main
        print("✓ main.py imports successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import main.py: {e}")
        return False


def test_basenode_imports():
    """Test that basenode.py can be imported without errors."""
    try:
        from node.basenode import Node
        print("✓ basenode.py imports successfully")
        
        # Check that TYPE_AUDIO is defined
        assert hasattr(Node, 'TYPE_AUDIO'), "TYPE_AUDIO not defined in Node"
        assert Node.TYPE_AUDIO == "AUDIO", "TYPE_AUDIO has incorrect value"
        print("✓ TYPE_AUDIO is defined correctly")
        return True
    except Exception as e:
        print(f"✗ Failed to import/test basenode.py: {e}")
        return False


def test_basenode_update_signature():
    """Test that the update method signature includes node_audio_dict."""
    try:
        from node.basenode import Node
        import inspect
        
        # Get the update method signature
        sig = inspect.signature(Node.update)
        params = list(sig.parameters.keys())
        
        assert 'node_audio_dict' in params, "node_audio_dict not in update method signature"
        print("✓ basenode.Node.update() has node_audio_dict parameter")
        return True
    except Exception as e:
        print(f"✗ Failed to test update signature: {e}")
        return False


def test_process_node_imports():
    """Test that ProcessNode files can be imported."""
    process_nodes = [
        'node_blur',
        'node_brightness',
        'node_contrast',
        'node_resize',
        'node_crop',
        'node_flip',
        'node_canny',
        'node_threshold',
        'node_grayscale',
        'node_equalize_hist',
    ]
    
    all_passed = True
    for node_name in process_nodes:
        try:
            module = __import__(f'node.ProcessNode.{node_name}', fromlist=['Node'])
            Node = getattr(module, 'Node')
            
            # Check update signature
            import inspect
            sig = inspect.signature(Node.update)
            params = list(sig.parameters.keys())
            
            assert 'node_audio_dict' in params, f"{node_name} missing node_audio_dict parameter"
            print(f"✓ {node_name}.py imports and has correct signature")
        except Exception as e:
            print(f"✗ Failed to import/test {node_name}.py: {e}")
            all_passed = False
    
    return all_passed


def test_dl_node_imports():
    """Test that DLNode files can be imported."""
    dl_nodes = [
        'node_object_detection',
        'node_classification',
        'node_face_detection',
        'node_pose_estimation',
        'node_semantic_segmentation',
    ]
    
    all_passed = True
    for node_name in dl_nodes:
        try:
            module = __import__(f'node.DLNode.{node_name}', fromlist=['Node'])
            Node = getattr(module, 'Node')
            
            # Check update signature
            import inspect
            sig = inspect.signature(Node.update)
            params = list(sig.parameters.keys())
            
            assert 'node_audio_dict' in params, f"{node_name} missing node_audio_dict parameter"
            print(f"✓ {node_name}.py imports and has correct signature")
        except Exception as e:
            print(f"✗ Failed to import/test {node_name}.py: {e}")
            all_passed = False
    
    return all_passed


def test_update_node_info_signature():
    """Test that update_node_info function has node_audio_dict parameter."""
    try:
        import main
        import inspect
        
        sig = inspect.signature(main.update_node_info)
        params = list(sig.parameters.keys())
        
        assert 'node_audio_dict' in params, "node_audio_dict not in update_node_info signature"
        print("✓ main.update_node_info() has node_audio_dict parameter")
        return True
    except Exception as e:
        print(f"✗ Failed to test update_node_info signature: {e}")
        return False


def test_video_node_audio_output():
    """Test that video node returns audio in its output."""
    try:
        from node.InputNode.node_video import VideoNode
        import inspect
        
        # Check the source code for the return statement
        source = inspect.getsource(VideoNode.update)
        
        # Look for the return statement that includes "audio"
        assert '"audio"' in source or "'audio'" in source, "Video node update method doesn't return audio"
        print("✓ Video node returns audio in update method")
        return True
    except Exception as e:
        print(f"✗ Failed to test video node audio output: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Testing Audio Spectrogram Support")
    print("=" * 60)
    print()
    
    tests = [
        ("Main imports", test_main_imports),
        ("Basenode imports", test_basenode_imports),
        ("Basenode update signature", test_basenode_update_signature),
        ("ProcessNode imports", test_process_node_imports),
        ("DLNode imports", test_dl_node_imports),
        ("update_node_info signature", test_update_node_info_signature),
        ("Video node audio output", test_video_node_audio_output),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test crashed: {e}")
            failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(0 if failed == 0 else 1)
