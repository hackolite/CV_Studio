#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Base abstract node class for all node implementations"""

from abc import ABCMeta, abstractmethod
from typing import Dict, Any, Optional, List
import uuid

from src.utils.logging import get_logger
from src.utils.exceptions import NodeExecutionError, NodeConfigurationError

logger = get_logger(__name__)


class BaseNode(metaclass=ABCMeta):
    """
    Abstract base class for all nodes in CV Studio
    
    This class defines the interface that all node implementations must follow.
    It provides common functionality for node identification, configuration,
    and execution lifecycle management.
    """
    
    # Node metadata
    _ver: str = '0.0.0'
    node_label: str = ''
    node_tag: str = ''
    
    # Data type constants
    TYPE_INT = 'Int'
    TYPE_FLOAT = 'Float'
    TYPE_IMAGE = 'Image'
    TYPE_TIME_MS = 'TimeMS'
    TYPE_JSON = 'Json'
    TYPE_SOUND = 'Sound'
    TYPE_TEXT = 'Text'
    TYPE_BOOLEAN = 'Boolean'
    TYPE_AUDIO = 'Audio'
    
    def __init__(self):
        """Initialize base node"""
        self._node_id = str(uuid.uuid4())
        self._config: Dict[str, Any] = {}
        logger.debug(f"Initialized node {self.node_tag} with ID {self._node_id}")
    
    @property
    def node_id(self) -> str:
        """Get the unique node ID"""
        return self._node_id
    
    @abstractmethod
    def add_node(
        self,
        parent: Any,
        node_id: int,
        pos: List[int],
        opencv_setting_dict: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Add the node to the GUI
        
        Args:
            parent: Parent GUI element
            node_id: Numeric ID for the node
            pos: Position [x, y] for the node
            opencv_setting_dict: Configuration dictionary
            
        Returns:
            The created node element
        """
        pass
    
    @abstractmethod
    def update(
        self,
        node_id: int,
        connection_list: List[Any],
        node_image_dict: Dict[str, Any],
        node_result_dict: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update/execute the node's processing logic
        
        Args:
            node_id: Numeric ID of the node
            connection_list: List of connections to this node
            node_image_dict: Dictionary of images from other nodes
            node_result_dict: Dictionary of results from other nodes
            
        Returns:
            Dictionary containing the node's output (image, json, etc.)
        """
        pass
    
    @abstractmethod
    def get_setting_dict(self, node_id: int) -> Dict[str, Any]:
        """
        Get the current settings of the node
        
        Args:
            node_id: Numeric ID of the node
            
        Returns:
            Dictionary of current settings
        """
        pass
    
    @abstractmethod
    def set_setting_dict(self, node_id: int, setting_dict: Dict[str, Any]):
        """
        Set the settings of the node
        
        Args:
            node_id: Numeric ID of the node
            setting_dict: Dictionary of settings to apply
        """
        pass
    
    @abstractmethod
    def close(self, node_id: int):
        """
        Cleanup node resources
        
        Args:
            node_id: Numeric ID of the node
        """
        pass
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate node configuration
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if valid, raises NodeConfigurationError otherwise
        """
        # Default implementation - can be overridden
        return True
    
    def handle_error(self, node_id: int, error: Exception):
        """
        Handle errors during node execution
        
        Args:
            node_id: Numeric ID of the node
            error: The exception that occurred
        """
        logger.error(f"Error in node {self.node_tag} (ID: {node_id}): {error}")
        raise NodeExecutionError(node_id, str(error), error)
