#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for the Microphone input node.
Verifies that the microphone node can be imported and instantiated correctly.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_microphone_node_import():
    """Test that Microphone node can be imported"""
    from node.InputNode.node_microphone import FactoryNode, MicrophoneNode, SOUNDDEVICE_AVAILABLE
    
    print("✓ Microphone node imported successfully")
    print(f"  sounddevice available: {SOUNDDEVICE_AVAILABLE}")
    return True


def test_microphone_factory_structure():
    """Test that Microphone FactoryNode has correct structure"""
    from node.InputNode.node_microphone import FactoryNode, MicrophoneNode
    
    factory = FactoryNode()
    node = MicrophoneNode()
    
    # Verify FactoryNode attributes
    assert hasattr(factory, 'node_label'), "FactoryNode missing node_label"
    assert hasattr(factory, 'node_tag'), "FactoryNode missing node_tag"
    assert factory.node_label == 'Microphone', f"Expected node_label 'Microphone', got '{factory.node_label}'"
    assert factory.node_tag == 'Microphone', f"Expected node_tag 'Microphone', got '{factory.node_tag}'"
    
    # Verify Node attributes
    assert hasattr(node, 'node_label'), "Node missing node_label"
    assert hasattr(node, 'node_tag'), "Node missing node_tag"
    assert node.node_label == 'Microphone', f"Expected node_label 'Microphone', got '{node.node_label}'"
    assert node.node_tag == 'Microphone', f"Expected node_tag 'Microphone', got '{node.node_tag}'"
    
    # Verify Node has required type constants
    assert hasattr(node, 'TYPE_AUDIO'), "Node missing TYPE_AUDIO"
    assert hasattr(node, 'TYPE_JSON'), "Node missing TYPE_JSON"
    assert hasattr(node, 'TYPE_INT'), "Node missing TYPE_INT"
    assert hasattr(node, 'TYPE_FLOAT'), "Node missing TYPE_FLOAT"
    
    # Verify Node has required methods
    assert hasattr(node, 'update'), "Node missing update method"
    assert hasattr(node, 'close'), "Node missing close method"
    assert hasattr(node, 'get_setting_dict'), "Node missing get_setting_dict method"
    assert hasattr(node, 'set_setting_dict'), "Node missing set_setting_dict method"
    
    print("✓ Microphone FactoryNode structure verified")
    print(f"  Node.node_tag: {node.node_tag}")
    print(f"  FactoryNode.node_tag: {factory.node_tag}")
    
    return True


def test_microphone_node_attributes():
    """Test that Microphone node has correct initial attributes"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Verify internal state attributes
    assert hasattr(node, '_is_recording'), "Node missing _is_recording attribute"
    assert node._is_recording == False, "Node should start with _is_recording = False"
    
    print("✓ Microphone node attributes verified")
    print(f"  _is_recording: {node._is_recording}")
    
    return True


def test_microphone_node_update_signature():
    """Test that Microphone node update method has correct signature"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    node = MicrophoneNode()
    
    # Get the signature of the update method
    sig = inspect.signature(node.update)
    params = list(sig.parameters.keys())
    
    # Verify parameters (excluding 'self')
    expected_params = ['node_id', 'connection_list', 'node_image_dict', 'node_result_dict', 'node_audio_dict']
    assert params == expected_params, f"Expected params {expected_params}, got {params}"
    
    print("✓ Microphone node update method signature verified")
    print(f"  Parameters: {params}")
    
    return True


def test_microphone_node_return_format():
    """Test that Microphone node update returns correct format"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Note: We can't actually call update() without DearPyGUI being initialized
    # as it tries to access dpg_get_value which causes segfault
    # So we just verify the method exists and is callable
    
    import inspect
    assert callable(node.update), "update method should be callable"
    
    # Verify the method would return a dict based on the code
    # (we can't actually call it without dpg initialized)
    
    print("✓ Microphone node update method verified as callable")
    print("  Note: Full update test requires DearPyGUI initialization")
    
    return True


if __name__ == '__main__':
    print("Testing Microphone Node...")
    print("=" * 60)
    
    tests = [
        ("Import", test_microphone_node_import),
        ("Factory Structure", test_microphone_factory_structure),
        ("Node Attributes", test_microphone_node_attributes),
        ("Update Signature", test_microphone_node_update_signature),
        ("Return Format", test_microphone_node_return_format),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
