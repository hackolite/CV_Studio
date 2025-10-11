#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Node factory for creating node instances"""

from typing import Dict, Type, Optional, Any
from ...utils.logging import get_logger
from ...utils.exceptions import NodeError

logger = get_logger(__name__)


class NodeFactory:
    """
    Factory class for creating and managing node instances
    
    This class provides a centralized registry for all node types
    and handles node instantiation.
    """
    
    _registry: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, node_tag: str, node_class: Type):
        """
        Register a node class in the factory
        
        Args:
            node_tag: Unique tag/identifier for the node type
            node_class: The node class to register
        """
        if node_tag in cls._registry:
            logger.warning(f"Node type {node_tag} already registered, replacing")
        
        cls._registry[node_tag] = node_class
        logger.debug(f"Registered node type: {node_tag}")
    
    @classmethod
    def create(cls, node_tag: str, **kwargs) -> Any:
        """
        Create an instance of a registered node type
        
        Args:
            node_tag: Unique tag/identifier for the node type
            **kwargs: Arguments to pass to the node constructor
            
        Returns:
            Instance of the requested node type
            
        Raises:
            NodeError: If the node type is not registered
        """
        if node_tag not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise NodeError(
                f"Node type '{node_tag}' not registered. "
                f"Available types: {available}"
            )
        
        node_class = cls._registry[node_tag]
        try:
            instance = node_class(**kwargs)
            logger.debug(f"Created instance of node type: {node_tag}")
            return instance
        except Exception as e:
            logger.error(f"Error creating node {node_tag}: {e}")
            raise NodeError(f"Failed to create node {node_tag}: {e}")
    
    @classmethod
    def get_registered_types(cls) -> Dict[str, Type]:
        """
        Get all registered node types
        
        Returns:
            Dictionary mapping node tags to node classes
        """
        return cls._registry.copy()
    
    @classmethod
    def is_registered(cls, node_tag: str) -> bool:
        """
        Check if a node type is registered
        
        Args:
            node_tag: Unique tag/identifier for the node type
            
        Returns:
            True if registered, False otherwise
        """
        return node_tag in cls._registry
    
    @classmethod
    def unregister(cls, node_tag: str):
        """
        Unregister a node type
        
        Args:
            node_tag: Unique tag/identifier for the node type
        """
        if node_tag in cls._registry:
            del cls._registry[node_tag]
            logger.debug(f"Unregistered node type: {node_tag}")
