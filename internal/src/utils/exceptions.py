#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Custom exceptions for CV Studio"""


class NodeError(Exception):
    """Base exception for all node-related errors"""
    pass


class NodeExecutionError(NodeError):
    """Exception raised when a node fails during execution"""
    
    def __init__(self, node_id, message, original_exception=None):
        self.node_id = node_id
        self.original_exception = original_exception
        super().__init__(f"Node {node_id} execution failed: {message}")


class NodeConfigurationError(NodeError):
    """Exception raised when a node has invalid configuration"""
    
    def __init__(self, node_id, message):
        self.node_id = node_id
        super().__init__(f"Node {node_id} configuration error: {message}")


class NodeConnectionError(NodeError):
    """Exception raised when node connections are invalid"""
    
    def __init__(self, message):
        super().__init__(f"Node connection error: {message}")


class ResourceError(Exception):
    """Exception raised when resource management fails"""
    pass
