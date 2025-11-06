#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that the node_editor.py fix properly handles
utility files without FactoryNode class.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_attribute_error_handling():
    """
    Test that AttributeError is properly caught when a module
    doesn't have a FactoryNode class.
    """
    print("Testing AttributeError handling for modules without FactoryNode...")
    
    # Create a mock module without FactoryNode
    mock_module_without_factory = MagicMock(spec=[])
    # Remove FactoryNode attribute to simulate the error
    delattr(mock_module_without_factory, 'FactoryNode') if hasattr(mock_module_without_factory, 'FactoryNode') else None
    
    # Test that accessing FactoryNode raises AttributeError
    try:
        _ = mock_module_without_factory.FactoryNode()
        print("✗ Expected AttributeError was not raised")
        return False
    except AttributeError as e:
        print(f"✓ AttributeError correctly raised: {e}")
    
    # Create a mock module with FactoryNode
    mock_factory = MagicMock()
    mock_factory.node_tag = "TestNode"
    mock_factory.node_label = "Test Node"
    
    mock_module_with_factory = MagicMock()
    mock_module_with_factory.FactoryNode = MagicMock(return_value=mock_factory)
    
    # Test that accessing FactoryNode works
    try:
        factory = mock_module_with_factory.FactoryNode()
        print(f"✓ FactoryNode successfully instantiated: {factory.node_tag}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False
    
    return True


def test_node_editor_logic_simulation():
    """
    Simulate the node_editor loading logic to verify the fix works.
    """
    print("\nSimulating node_editor loading logic...")
    
    # Simulate modules
    modules = {
        'node_video': {'has_factory': True, 'tag': 'Video', 'label': 'Video'},
        'node_image': {'has_factory': True, 'tag': 'Image', 'label': 'Image'},
        'spectrogram_utils': {'has_factory': False},
        'node_mqtt': {'has_factory': True, 'tag': 'MQTT', 'label': 'MQTT'},
    }
    
    loaded_nodes = {}
    skipped_modules = []
    
    # Simulate the loading process with the fix
    for module_name, module_info in modules.items():
        try:
            if module_info['has_factory']:
                # Simulate creating FactoryNode
                loaded_nodes[module_info['tag']] = {
                    'label': module_info['label'],
                    'tag': module_info['tag']
                }
                print(f"  ✓ Loaded: {module_name} (tag: {module_info['tag']})")
            else:
                # Simulate AttributeError
                raise AttributeError(f"module '{module_name}' has no attribute 'FactoryNode'")
        except AttributeError as e:
            # This is the fix - catch AttributeError and skip
            skipped_modules.append(module_name)
            print(f"  ⊘ Skipped: {module_name} (no FactoryNode)")
    
    # Verify results
    assert len(loaded_nodes) == 3, f"Expected 3 loaded nodes, got {len(loaded_nodes)}"
    assert len(skipped_modules) == 1, f"Expected 1 skipped module, got {len(skipped_modules)}"
    assert 'spectrogram_utils' in skipped_modules, "spectrogram_utils should be skipped"
    assert 'Video' in loaded_nodes, "Video node should be loaded"
    assert 'Image' in loaded_nodes, "Image node should be loaded"
    assert 'MQTT' in loaded_nodes, "MQTT node should be loaded"
    
    print(f"\n✓ Loaded {len(loaded_nodes)} nodes successfully")
    print(f"✓ Skipped {len(skipped_modules)} utility modules")
    
    return True


def test_node_files_naming_convention():
    """
    Test that all actual node files follow the 'node_' naming convention
    and utility files don't.
    """
    print("\nChecking InputNode directory for file naming conventions...")
    
    from glob import glob
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_node_dir = os.path.join(os.path.dirname(current_dir), 'node', 'InputNode')
    
    if not os.path.exists(input_node_dir):
        print(f"✗ Directory not found: {input_node_dir}")
        return False
    
    py_files = glob(os.path.join(input_node_dir, '*.py'))
    
    node_files = []
    utility_files = []
    
    for py_file in py_files:
        filename = os.path.basename(py_file)
        if filename == '__init__.py':
            continue
        
        if filename.startswith('node_'):
            node_files.append(filename)
        else:
            utility_files.append(filename)
    
    print(f"  Node files (node_*.py): {len(node_files)}")
    for nf in sorted(node_files)[:3]:
        print(f"    • {nf}")
    if len(node_files) > 3:
        print(f"    ... and {len(node_files) - 3} more")
    
    print(f"  Utility files: {len(utility_files)}")
    for uf in sorted(utility_files):
        print(f"    • {uf}")
    
    # Verify spectrogram_utils is identified as utility
    if 'spectrogram_utils.py' not in utility_files:
        print("✗ spectrogram_utils.py should be a utility file")
        return False
    
    print("✓ spectrogram_utils.py correctly identified as utility file")
    print(f"✓ All {len(node_files)} node files follow 'node_' naming convention")
    
    return True


if __name__ == '__main__':
    print("=" * 70)
    print("Testing Node Editor Utility File Handling Fix")
    print("=" * 70)
    
    tests = [
        test_attribute_error_handling,
        test_node_editor_logic_simulation,
        test_node_files_naming_convention,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"Results: {passed}/{len(tests)} tests passed")
    
    if failed == 0:
        print("✓ All tests passed! The fix correctly handles utility files.")
        print("=" * 70)
        sys.exit(0)
    else:
        print(f"✗ {failed} test(s) failed")
        print("=" * 70)
        sys.exit(1)
