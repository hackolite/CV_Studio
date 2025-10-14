#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test video node fixes for display issues"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_basenode_no_debug_print():
    """Test that basenode.py doesn't have debug print statement"""
    basenode_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'basenode.py'
    )
    
    assert os.path.exists(basenode_path), "basenode.py should exist"
    
    with open(basenode_path, 'r') as f:
        content = f.read()
    
    # Check that the debug print is removed
    assert 'print("node' not in content, "Debug print statement should be removed from basenode.py"
    
    print("✓ Debug print removed from basenode.py")


def test_video_node_consistent_dimensions():
    """Test that node_video.py uses consistent window dimensions"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Find the update method's texture conversion section
    # Should use consistent local variables (small_window_w, small_window_h)
    # not mix instance and local variables
    
    # Check that the convert_cv_to_dpg call uses local variables
    lines = content.split('\n')
    found_convert_call = False
    in_update_method = False
    convert_call_line_idx = -1
    
    for i, line in enumerate(lines):
        if 'def update(' in line:
            in_update_method = True
        elif in_update_method and 'def ' in line and 'def update' not in line:
            in_update_method = False
        
        if in_update_method and 'texture = self.convert_cv_to_dpg(' in line:
            found_convert_call = True
            convert_call_line_idx = i
            # Check next few lines for parameters
            param_lines = '\n'.join(lines[i:i+5])
            
            # Should use small_window_w (local var), not self._small_window_w
            assert 'small_window_w,' in param_lines, "Should use local variable small_window_w"
            assert 'small_window_h,' in param_lines, "Should use local variable small_window_h"
            
            # Should NOT use mixed instance/local vars in same call
            assert 'self._small_window_w,' not in param_lines, "Should not mix instance variables with local variables"
            
            break
    
    assert found_convert_call, "Should find convert_cv_to_dpg call in update method"
    
    print("✓ Consistent dimensions used in node_video.py update method")


def test_video_node_no_problematic_resize():
    """Test that node_video.py doesn't have the problematic frame resize"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # The problematic line that modified the frame after texture creation
    assert 'frame = cv2.resize(frame, (600, 400))' not in content, \
        "Problematic frame resize should be removed"
    
    print("✓ Problematic frame resize removed from node_video.py")


def test_syntax_valid():
    """Test that modified files have valid Python syntax"""
    import py_compile
    
    basenode_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'basenode.py'
    )
    
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    # This will raise SyntaxError if files are invalid
    py_compile.compile(basenode_path, doraise=True)
    py_compile.compile(video_node_path, doraise=True)
    
    print("✓ All modified files have valid Python syntax")


if __name__ == '__main__':
    test_basenode_no_debug_print()
    test_video_node_consistent_dimensions()
    test_video_node_no_problematic_resize()
    test_syntax_valid()
    print("\n✓ All validation tests passed successfully!")
