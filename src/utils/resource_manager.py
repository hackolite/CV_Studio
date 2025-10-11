#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Resource management utilities"""

import weakref
from typing import Any, Dict, Optional
from .logging import get_logger
from .exceptions import ResourceError

logger = get_logger(__name__)


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
