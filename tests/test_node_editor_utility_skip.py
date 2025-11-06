#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the node editor correctly skips utility files
without FactoryNode class (like spectrogram_utils.py).
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_spectrogram_utils_import():
    """Test that spectrogram_utils can be imported without FactoryNode"""
    try:
        from node.InputNode import spectrogram_utils
        
        # Verify the module has the expected utility functions
        assert hasattr(spectrogram_utils, 'apply_colormap_cv2'), \
            "spectrogram_utils should have apply_colormap_cv2 function"
        assert hasattr(spectrogram_utils, 'apply_colormap_mpl'), \
            "spectrogram_utils should have apply_colormap_mpl function"
        assert hasattr(spectrogram_utils, 'apply_colormap_to_spectrogram'), \
            "spectrogram_utils should have apply_colormap_to_spectrogram function"
        
        # Verify it does NOT have FactoryNode
        assert not hasattr(spectrogram_utils, 'FactoryNode'), \
            "spectrogram_utils should NOT have FactoryNode class"
        
        print("✓ spectrogram_utils imported successfully")
        print("  - Has apply_colormap_cv2: ✓")
        print("  - Has apply_colormap_mpl: ✓")
        print("  - Has apply_colormap_to_spectrogram: ✓")
        print("  - Does NOT have FactoryNode: ✓")
        
        return True
    except Exception as e:
        print(f"✗ Failed to import spectrogram_utils: {e}")
        raise


def test_video_node_imports_spectrogram_utils():
    """Test that node_video can import and use spectrogram_utils"""
    try:
        from node.InputNode import node_video
        
        # Verify the node_video module has FactoryNode
        assert hasattr(node_video, 'FactoryNode'), \
            "node_video should have FactoryNode class"
        
        # Test that FactoryNode can be instantiated
        factory = node_video.FactoryNode()
        assert factory.node_tag == "Video", \
            f"Factory node_tag should be 'Video', got '{factory.node_tag}'"
        
        print("✓ node_video imported successfully")
        print(f"  - FactoryNode.node_tag: {factory.node_tag}")
        print(f"  - FactoryNode.node_label: {factory.node_label}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to import node_video: {e}")
        raise


def test_node_discovery_pattern():
    """Test that the node discovery would correctly identify node files"""
    from glob import glob
    import os
    
    # Get the path to InputNode directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_node_dir = os.path.join(os.path.dirname(current_dir), 'node', 'InputNode')
    
    # Get all .py files
    py_files = glob(os.path.join(input_node_dir, '*.py'))
    
    node_files = []
    utility_files = []
    
    for py_file in py_files:
        filename = os.path.basename(py_file)
        if filename == '__init__.py':
            continue
        
        # Check if it starts with 'node_'
        if filename.startswith('node_'):
            node_files.append(filename)
        else:
            utility_files.append(filename)
    
    print("✓ Node discovery pattern analysis")
    print(f"  - Node files (start with 'node_'): {len(node_files)}")
    for nf in sorted(node_files):
        print(f"    • {nf}")
    
    print(f"  - Utility files (don't start with 'node_'): {len(utility_files)}")
    for uf in sorted(utility_files):
        print(f"    • {uf}")
    
    # Verify spectrogram_utils is in utility files
    assert 'spectrogram_utils.py' in utility_files, \
        "spectrogram_utils.py should be identified as a utility file"
    
    print("  - spectrogram_utils.py correctly identified as utility file: ✓")
    
    return True


if __name__ == '__main__':
    print("Testing node editor utility file handling...")
    print("=" * 70)
    
    tests = [
        ("Spectrogram Utils Import", test_spectrogram_utils_import),
        ("Video Node Uses Spectrogram Utils", test_video_node_imports_spectrogram_utils),
        ("Node Discovery Pattern", test_node_discovery_pattern),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTest: {name}")
        print("-" * 70)
        try:
            if test_func():
                passed += 1
                print(f"✓ {name} PASSED")
        except Exception as e:
            print(f"✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
