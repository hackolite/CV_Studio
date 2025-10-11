#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for custom exceptions"""

import pytest
from src.utils.exceptions import (
    NodeError, 
    NodeExecutionError, 
    NodeConfigurationError,
    NodeConnectionError,
    ResourceError
)


def test_node_error():
    """Test base NodeError exception"""
    error = NodeError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_node_execution_error():
    """Test NodeExecutionError with node_id"""
    node_id = 123
    message = "Execution failed"
    error = NodeExecutionError(node_id, message)
    
    assert error.node_id == node_id
    assert message in str(error)
    assert str(node_id) in str(error)


def test_node_execution_error_with_original():
    """Test NodeExecutionError with original exception"""
    node_id = 123
    message = "Execution failed"
    original = ValueError("Original error")
    error = NodeExecutionError(node_id, message, original)
    
    assert error.node_id == node_id
    assert error.original_exception == original
    assert message in str(error)


def test_node_configuration_error():
    """Test NodeConfigurationError"""
    node_id = 456
    message = "Invalid config"
    error = NodeConfigurationError(node_id, message)
    
    assert error.node_id == node_id
    assert message in str(error)
    assert str(node_id) in str(error)


def test_node_connection_error():
    """Test NodeConnectionError"""
    message = "Invalid connection"
    error = NodeConnectionError(message)
    assert message in str(error)


def test_resource_error():
    """Test ResourceError"""
    error = ResourceError("Resource allocation failed")
    assert str(error) == "Resource allocation failed"


def test_exception_hierarchy():
    """Test exception hierarchy"""
    assert issubclass(NodeExecutionError, NodeError)
    assert issubclass(NodeConfigurationError, NodeError)
    assert issubclass(NodeConnectionError, NodeError)
    assert issubclass(NodeError, Exception)
    assert issubclass(ResourceError, Exception)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
