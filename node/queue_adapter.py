#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backward-compatible adapter for timestamped queue system.

This module provides a dict-like interface that uses the timestamped queue system
internally, allowing existing code to work without modifications while benefiting
from the new queue-based architecture.
"""

from typing import Any, Optional, Dict
from .timestamped_queue import NodeDataQueueManager


class QueueBackedDict:
    """
    Dictionary-like interface backed by timestamped queues.
    
    This class maintains backward compatibility with the existing dict-based
    interface (node_image_dict, node_result_dict, etc.) while using the
    timestamped queue system internally.
    
    When you get an item, it returns the oldest (FIFO) data from the queue.
    When you set an item, it adds the data to the queue with a timestamp.
    """
    
    def __init__(self, queue_manager: NodeDataQueueManager, data_type: str = "default"):
        """
        Initialize the queue-backed dictionary.
        
        Args:
            queue_manager: The NodeDataQueueManager instance to use
            data_type: Type of data this dict manages (e.g., "image", "audio", "json")
        """
        self._queue_manager = queue_manager
        self._data_type = data_type
        # Cache for backward compatibility - stores the latest value
        self._cache: Dict[str, Any] = {}
    
    def __setitem__(self, node_id_name: str, value: Any) -> None:
        """
        Set a value for a node (adds to queue with timestamp).
        
        Args:
            node_id_name: The node identifier
            value: The data value to store
        """
        # Update cache for immediate retrieval
        self._cache[node_id_name] = value
        
        # Also add to queue with timestamp
        if value is not None:
            self._queue_manager.put_data(node_id_name, self._data_type, value)
    
    def __getitem__(self, node_id_name: str) -> Any:
        """
        Get the value for a node (returns oldest from queue, falls back to cache).
        
        Args:
            node_id_name: The node identifier
        
        Returns:
            The oldest data from the queue, or cached value if queue is empty
        """
        # Try to get from queue first (oldest data - FIFO)
        oldest_data = self._queue_manager.get_oldest_data(node_id_name, self._data_type)
        
        if oldest_data is not None:
            return oldest_data
        
        # Fall back to cache for backward compatibility
        return self._cache.get(node_id_name)
    
    def get(self, node_id_name: str, default: Any = None) -> Any:
        """
        Get value with a default fallback.
        
        Args:
            node_id_name: The node identifier
            default: Default value if key not found
        
        Returns:
            The data value or default
        """
        try:
            value = self.__getitem__(node_id_name)
            return value if value is not None else default
        except KeyError:
            return default
    
    def __contains__(self, node_id_name: str) -> bool:
        """
        Check if a node has data.
        
        Args:
            node_id_name: The node identifier
        
        Returns:
            True if node has data (in queue or cache)
        """
        return (node_id_name in self._cache or 
                not self._queue_manager.get_queue(node_id_name, self._data_type).is_empty())
    
    def __delitem__(self, node_id_name: str) -> None:
        """
        Remove data for a node.
        
        Args:
            node_id_name: The node identifier
        """
        if node_id_name in self._cache:
            del self._cache[node_id_name]
        self._queue_manager.clear_node_queues(node_id_name)
    
    def clear(self) -> None:
        """Clear all data."""
        self._cache.clear()
        # Note: We don't clear all queues as they might be shared
    
    def keys(self):
        """Get all node identifiers."""
        return self._cache.keys()
    
    def values(self):
        """Get all cached values."""
        return self._cache.values()
    
    def items(self):
        """Get all cached items."""
        return self._cache.items()
    
    def get_latest(self, node_id_name: str) -> Any:
        """
        Get the most recent data from a node's queue.
        
        Args:
            node_id_name: The node identifier
        
        Returns:
            The most recent data, or None if not available
        """
        return self._queue_manager.get_latest_data(node_id_name, self._data_type)
    
    def get_queue_info(self, node_id_name: str) -> Dict[str, Any]:
        """
        Get information about a node's queue.
        
        Args:
            node_id_name: The node identifier
        
        Returns:
            Dictionary with queue statistics
        """
        return self._queue_manager.get_queue_info(node_id_name, self._data_type)
