#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resource management utilities"""

import os
import sys
import weakref
from typing import Any, Dict, Optional
from .logging import get_logger
from .exceptions import ResourceError

logger = get_logger(__name__)


def resource_path(relative_path):
    """
    Get the absolute path to a resource, works for both development and PyInstaller frozen mode.
    
    When running as a script, returns the path relative to the project root directory.
    When running as a PyInstaller executable (.exe), returns the path relative to
    the temporary directory where PyInstaller extracts files (sys._MEIPASS).
    
    This function should be used for all file access to resources that are bundled
    with the application (models, config files, fonts, images, etc.).
    
    Args:
        relative_path (str): Relative path to the resource from project root
                           (e.g., 'node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx')
    
    Returns:
        str: Absolute path to the resource
        
    Example:
        >>> model_path = resource_path('node/DLNode/YOLOX/model/yolox_nano.onnx')
        >>> with open(resource_path('node_editor/setting/setting.json')) as f:
        ...     config = json.load(f)
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment (script mode)
        # Get the project root (3 levels up from src/utils/resource_manager.py)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    # Normalize path separators for cross-platform compatibility
    return os.path.normpath(os.path.join(base_path, relative_path))


class ResourceManager:
    """Manages lifecycle of resources like video captures, models, etc."""
    
    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._finalizers: Dict[str, Any] = {}
    
    def register(self, resource_id: str, resource: Any, cleanup_func: Optional[callable] = None):
        """
        Register a resource for management
        
        Args:
            resource_id: Unique identifier for the resource
            resource: The resource object
            cleanup_func: Optional cleanup function to call when releasing
        """
        if resource_id in self._resources:
            logger.warning(f"Resource {resource_id} already registered, replacing")
            self.release(resource_id)
        
        self._resources[resource_id] = resource
        
        if cleanup_func:
            # Use weakref to avoid circular references
            self._finalizers[resource_id] = cleanup_func
        
        logger.debug(f"Registered resource: {resource_id}")
    
    def get(self, resource_id: str) -> Optional[Any]:
        """
        Get a registered resource
        
        Args:
            resource_id: Unique identifier for the resource
            
        Returns:
            The resource object or None if not found
        """
        return self._resources.get(resource_id)
    
    def release(self, resource_id: str):
        """
        Release a resource and call its cleanup function
        
        Args:
            resource_id: Unique identifier for the resource
        """
        if resource_id not in self._resources:
            logger.warning(f"Resource {resource_id} not found for release")
            return
        
        resource = self._resources.pop(resource_id)
        cleanup_func = self._finalizers.pop(resource_id, None)
        
        if cleanup_func:
            try:
                cleanup_func(resource)
                logger.debug(f"Released resource: {resource_id}")
            except Exception as e:
                logger.error(f"Error releasing resource {resource_id}: {e}")
                raise ResourceError(f"Failed to release resource {resource_id}: {e}")
    
    def release_all(self):
        """Release all registered resources"""
        resource_ids = list(self._resources.keys())
        for resource_id in resource_ids:
            try:
                self.release(resource_id)
            except Exception as e:
                logger.error(f"Error releasing resource {resource_id}: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.release_all()


# Global resource manager instance
_global_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get the global resource manager instance"""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager()
    return _global_resource_manager
