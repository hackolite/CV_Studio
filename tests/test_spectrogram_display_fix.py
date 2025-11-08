#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test spectrogram display fixes for node_video.py"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_texture_dimensions_consistency():
    """Test that texture registry uses consistent dimension variables"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # Find the texture_registry section in add_node method
    in_texture_registry = False
    in_add_node = False
    texture_calls = []
    
    for i, line in enumerate(lines):
        if 'def add_node(' in line:
            in_add_node = True
        elif in_add_node and 'def ' in line and 'def add_node' not in line:
            in_add_node = False
            
        if in_add_node and 'with dpg.texture_registry' in line:
            in_texture_registry = True
        elif in_texture_registry and line.strip() and not line.strip().startswith(')') and 'dpg.add_raw_texture(' in line:
            # Found a texture creation, collect next few lines
            texture_block = []
            j = i
            while j < len(lines) and ')' not in ''.join(texture_block):
                texture_block.append(lines[j])
                j += 1
            if j < len(lines):
                texture_block.append(lines[j])
            texture_calls.append('\n'.join(texture_block))
        elif in_texture_registry and line.strip() and not line[0].isspace() and 'dpg.add_raw_texture' not in line:
            # End of texture registry block
            in_texture_registry = False
    
    # Verify we found texture calls
    assert len(texture_calls) >= 2, "Should find at least 2 texture registry calls (main output + spectrogram)"
    
    # Check each texture call for consistency
    for idx, texture_call in enumerate(texture_calls):
        # Should use local variables (small_window_w, small_window_h)
        # Should NOT use instance variables (node._small_window_w, node._small_window_h)
        
        # Check for consistent use of local variables
        if 'small_window_w' in texture_call or 'small_window_h' in texture_call:
            # If using local vars, should not mix with instance vars
            assert 'node._small_window_w' not in texture_call, \
                f"Texture call {idx} should not mix instance variable node._small_window_w with local variables"
            assert 'node._small_window_h' not in texture_call, \
                f"Texture call {idx} should not mix instance variable node._small_window_h with local variables"
            
            # Both dimensions should use the same pattern (both local or both instance)
            has_local_w = 'small_window_w,' in texture_call and 'node._small_window_w' not in texture_call
            has_local_h = 'small_window_h,' in texture_call and 'node._small_window_h' not in texture_call
            
            assert has_local_w, f"Texture call {idx} should use local variable small_window_w"
            assert has_local_h, f"Texture call {idx} should use local variable small_window_h"
    
    print("✓ Texture dimensions are consistent (using local variables)")


def test_immediate_texture_update():
    """Test that spectrogram data is stored for update (new architecture)"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    assert os.path.exists(video_node_path), "node_video.py should exist"
    
    with open(video_node_path, 'r') as f:
        content = f.read()
        lines = content.split('\n')
    
    # In the new architecture, _preprocess_video stores spectrogram chunks
    in_preprocess_video = False
    found_chunks_storage = False
    found_metadata_storage = False
    
    for i, line in enumerate(lines):
        if 'def _preprocess_video(' in line:
            in_preprocess_video = True
        elif in_preprocess_video and 'def ' in line and 'def _preprocess_video' not in line:
            # Reached another method
            in_preprocess_video = False
            
        if in_preprocess_video:
            # Check if spectrogram chunks are stored
            if 'self._spectrogram_chunks[node_id]' in line and '=' in line:
                found_chunks_storage = True
            
            # Check if metadata is stored
            if 'self._chunk_metadata[node_id]' in line and '=' in line:
                found_metadata_storage = True
    
    assert found_chunks_storage, "Should store chunks in self._spectrogram_chunks"
    assert found_metadata_storage, "Should store metadata in self._chunk_metadata"
    
    print("✓ Spectrogram chunks and metadata are stored for later update")


def test_dpg_imports():
    """Test that dpg_set_value is available in the module"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    # Check imports
    assert 'from node_editor.util import' in content, "Should import from node_editor.util"
    assert 'dpg_set_value' in content, "Should import or use dpg_set_value"
    
    print("✓ Required DPG utilities are imported")


def test_syntax_valid():
    """Test that the modified file has valid Python syntax"""
    video_node_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'InputNode', 'node_video.py'
    )
    
    import ast
    with open(video_node_path, 'r') as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✓ Python syntax is valid")
    except SyntaxError as e:
        raise AssertionError(f"Invalid Python syntax: {e}")


if __name__ == '__main__':
    test_texture_dimensions_consistency()
    test_immediate_texture_update()
    test_dpg_imports()
    test_syntax_valid()
    print("\n✓ All spectrogram display fix tests passed successfully!")
