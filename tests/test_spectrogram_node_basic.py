#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for Spectrogram Node implementation
"""
import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_spectrogram_node_import():
    """Test that the spectrogram node module can be imported"""
    from node.AudioProcessNode import node_spectrogram_node
    assert hasattr(node_spectrogram_node, 'FactoryNode')
    assert hasattr(node_spectrogram_node, 'SpectrogramNode')
    print("✓ Spectrogram node classes found")


def test_spectrogram_factory_node_attributes():
    """Test that FactoryNode has required attributes"""
    from node.AudioProcessNode.node_spectrogram_node import FactoryNode
    
    factory = FactoryNode()
    assert hasattr(factory, 'node_label')
    assert hasattr(factory, 'node_tag')
    assert factory.node_label == 'Spectrogram'
    assert factory.node_tag == 'Spectrogram'
    assert hasattr(factory, 'add_node')
    print("✓ FactoryNode has correct attributes")


def test_spectrogram_node_instantiation():
    """Test that SpectrogramNode can be instantiated"""
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    node = SpectrogramNode()
    assert node.node_label == 'Spectrogram'
    assert node.node_tag == 'Spectrogram'
    assert hasattr(node, 'update')
    assert hasattr(node, 'close')
    assert hasattr(node, 'get_setting_dict')
    assert hasattr(node, 'set_setting_dict')
    print("✓ SpectrogramNode can be instantiated")


if __name__ == '__main__':
    test_spectrogram_node_import()
    test_spectrogram_factory_node_attributes()
    test_spectrogram_node_instantiation()
    print("\n✓ All spectrogram node tests passed!")
