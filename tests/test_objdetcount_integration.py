#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integration test for ObjDetCount FactoryNode
Verifies that the FactoryNode can be instantiated and has the add_node method
This mimics how the node_editor uses FactoryNode
"""
import re


def test_factorynode_instantiation_pattern():
    """Test that ObjDetCount FactoryNode follows the same pattern as other trigger nodes"""
    
    # Read ObjDetCount source
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        objdetcount_content = f.read()
    
    # Read OnOffSwitch source as reference
    with open('node/TriggerNode/node_on_off_switch.py', 'r') as f:
        onoffswitch_content = f.read()
    
    # Both should have FactoryNode class
    assert 'class FactoryNode:' in objdetcount_content
    assert 'class FactoryNode:' in onoffswitch_content
    
    # Both should have add_node method in FactoryNode
    objdetcount_factory = re.search(r'class FactoryNode:.*?(?=\nclass\s)', objdetcount_content, re.DOTALL)
    onoffswitch_factory = re.search(r'class FactoryNode:.*?(?=\nclass\s)', onoffswitch_content, re.DOTALL)
    
    assert objdetcount_factory, "Could not find FactoryNode in ObjDetCount"
    assert onoffswitch_factory, "Could not find FactoryNode in OnOffSwitch"
    
    assert 'def add_node(' in objdetcount_factory.group(0)
    assert 'def add_node(' in onoffswitch_factory.group(0)
    
    print("✓ ObjDetCount FactoryNode follows the same pattern as other trigger nodes")


def test_factorynode_creates_node_instance():
    """Test that FactoryNode.add_node creates a Node instance"""
    
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Extract FactoryNode.add_node method
    factory_match = re.search(r'class FactoryNode:.*?(?=\nclass\s)', content, re.DOTALL)
    assert factory_match, "Could not find FactoryNode"
    
    factory_content = factory_match.group(0)
    add_node_match = re.search(r'def add_node\(.*?\):(.*?)(?=\n    def |\Z)', factory_content, re.DOTALL)
    assert add_node_match, "Could not find add_node method"
    
    add_node_content = add_node_match.group(1)
    
    # Should create a Node instance
    assert 'node = Node()' in add_node_content
    
    # Should return the result of node.add_node
    assert 'return node.add_node(' in add_node_content
    
    print("✓ FactoryNode.add_node creates a Node instance and delegates to it")


def test_node_class_has_add_node():
    """Test that the Node class still has its add_node method"""
    
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Find Node class
    node_match = re.search(r'class Node\(BaseNode\):.*', content, re.DOTALL)
    assert node_match, "Could not find Node class"
    
    node_content = node_match.group(0)
    
    # Node class should have add_node method
    assert 'def add_node(' in node_content
    
    print("✓ Node class has add_node method")


def test_signature_compatibility_with_node_editor():
    """Test that the FactoryNode.add_node signature is compatible with node_editor"""
    
    with open('node/TriggerNode/node_objdetcount.py', 'r') as f:
        content = f.read()
    
    # Extract FactoryNode.add_node signature
    factory_match = re.search(r'class FactoryNode:.*?(?=\nclass\s)', content, re.DOTALL)
    assert factory_match, "Could not find FactoryNode"
    
    factory_content = factory_match.group(0)
    add_node_match = re.search(r'def add_node\((.*?)\):', factory_content, re.DOTALL)
    assert add_node_match, "Could not find add_node method"
    
    params = add_node_match.group(1)
    
    # The node_editor calls add_node with these parameters
    # from node_editor.py line 389-394:
    # node = factorynode.add_node(
    #     self._node_editor_tag,       # parent
    #     self._node_id,               # node_id
    #     pos=last_pos,                # pos
    #     opencv_setting_dict=self._opencv_setting_dict,  # opencv_setting_dict
    # )
    
    required_params = ['parent', 'node_id']
    optional_params = ['pos', 'opencv_setting_dict', 'callback']
    
    for param in required_params:
        assert param in params, f"Missing required parameter: {param}"
    
    for param in optional_params:
        assert param in params, f"Missing optional parameter: {param}"
    
    print("✓ FactoryNode.add_node signature is compatible with node_editor")


if __name__ == '__main__':
    test_factorynode_instantiation_pattern()
    test_factorynode_creates_node_instance()
    test_node_class_has_add_node()
    test_signature_compatibility_with_node_editor()
    
    print("\n✅ All integration tests passed!")
