#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test demonstrating IntValue and FloatValue nodes can be used
to provide inputs to other nodes.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_value_nodes_integration():
    """Test that value nodes can integrate with the node system"""
    from node.InputNode.node_int_value import FactoryNode as IntFactory, Node as IntNode
    from node.InputNode.node_float_value import FactoryNode as FloatFactory, Node as FloatNode
    
    # Create instances
    int_factory = IntFactory()
    int_node = IntNode()
    float_factory = FloatFactory()
    float_node = FloatNode()
    
    # Verify they can be called with standard node interface
    node_image_dict = {}
    node_result_dict = {}
    node_audio_dict = {}
    connection_list = []
    
    # Test update method
    int_result = int_node.update(1, connection_list, node_image_dict, node_result_dict, node_audio_dict)
    float_result = float_node.update(2, connection_list, node_image_dict, node_result_dict, node_audio_dict)
    
    # Verify return format
    assert 'image' in int_result, "IntValue should return dict with 'image' key"
    assert 'json' in int_result, "IntValue should return dict with 'json' key"
    assert 'audio' in int_result, "IntValue should return dict with 'audio' key"
    
    assert 'image' in float_result, "FloatValue should return dict with 'image' key"
    assert 'json' in float_result, "FloatValue should return dict with 'json' key"
    assert 'audio' in float_result, "FloatValue should return dict with 'audio' key"
    
    # Test close method
    int_node.close(1)
    float_node.close(2)
    
    print("✓ IntValue and FloatValue nodes integrate correctly with node system")


def test_value_nodes_in_menu():
    """Test that value nodes are discoverable by the node editor"""
    import os
    from glob import glob
    from importlib import import_module
    
    node_dir = 'node'
    menu_info = ('Input', 'InputNode')
    
    node_sources_path = os.path.join(node_dir, menu_info[1], '*.py')
    node_sources = glob(node_sources_path)
    
    discovered_nodes = []
    for node_source in node_sources:
        basename = os.path.basename(node_source)
        
        # Skip disabled files
        if basename.startswith('_'):
            continue
        
        import_path = os.path.splitext(os.path.normpath(node_source))[0]
        import_path = import_path.replace(os.sep, '.')
        import_path = '.'.join(import_path.split('.')[-3:])
        
        if import_path.endswith('__init__'):
            continue
        
        try:
            module = import_module(import_path)
            if hasattr(module, 'FactoryNode'):
                factorynode = module.FactoryNode()
                discovered_nodes.append(factorynode.node_tag)
        except Exception:
            pass
    
    assert 'IntValue' in discovered_nodes, "IntValue should be discoverable"
    assert 'FloatValue' in discovered_nodes, "FloatValue should be discoverable"
    
    print(f"✓ Both IntValue and FloatValue are discoverable in the node menu")
    print(f"  Total Input nodes discovered: {len(discovered_nodes)}")


def test_style_configuration():
    """Test that value nodes are registered in the style configuration"""
    from node_editor.style import INPUT
    
    assert 'IntValue' in INPUT, "IntValue should be in INPUT style list"
    assert 'FloatValue' in INPUT, "FloatValue should be in INPUT style list"
    
    print("✓ IntValue and FloatValue are registered in style configuration")


if __name__ == '__main__':
    print("Running IntValue and FloatValue integration tests...")
    print("=" * 60)
    
    tests = [
        ("Integration with node system", test_value_nodes_integration),
        ("Node menu discovery", test_value_nodes_in_menu),
        ("Style configuration", test_style_configuration),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {name} test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name} test failed with error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All integration tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
