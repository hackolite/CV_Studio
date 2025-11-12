"""Abstract Base Class for DearPyGUI Node Editor Nodes.

This module defines the abstract interface that all node types must implement
in the CV Studio node editor system.
"""
from abc import ABCMeta, abstractmethod


class DpgNodeABC(metaclass=ABCMeta):
    """Abstract base class for all node types in the CV Studio node editor.
    
    This class defines the interface that all nodes must implement, including
    methods for adding nodes to the GUI, updating node state, and managing
    node settings.
    
    Attributes
    ----------
    _ver : str
        Version string for the node implementation.
    node_label : str
        Human-readable label displayed in the node editor.
    node_tag : str
        Unique tag identifier for the node type.
    TYPE_INT : str
        Constant for integer data type connections.
    TYPE_FLOAT : str
        Constant for float data type connections.
    TYPE_IMAGE : str
        Constant for image data type connections.
    TYPE_TIME_MS : str
        Constant for timestamp data type connections.
    TYPE_JSON : str
        Constant for JSON data type connections.
    TYPE_SOUND : str
        Constant for audio data type connections.
    """
    _ver = '0.0.0'

    node_label = ''
    node_tag = ''

    TYPE_INT = 'Int'
    TYPE_FLOAT = 'Float'
    TYPE_IMAGE = 'Image'
    TYPE_TIME_MS = 'TimeMS'
    TYPE_JSON = 'Json'
    TYPE_SOUND = 'Sound'

    @abstractmethod
    def add_node(
        self,
        parent,
        node_id,
        pos,
        width,
        height,
        opencv_setting_dict,
    ):
        """Add the node to the DearPyGUI interface.
        
        Parameters
        ----------
        parent : int
            DearPyGUI parent widget ID.
        node_id : str
            Unique identifier for this node instance.
        pos : tuple[int, int]
            Initial (x, y) position of the node in the editor.
        width : int
            Width of the node editor window.
        height : int
            Height of the node editor window.
        opencv_setting_dict : dict
            Configuration dictionary containing OpenCV and application settings.
            
        Returns
        -------
        Node
            The node instance that was added.
        """
        pass

    @abstractmethod
    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """Update the node's state and process data.
        
        This method is called every frame to process input data from connected
        nodes and produce output data.
        
        Parameters
        ----------
        node_id : str
            Unique identifier for this node instance.
        connection_list : list
            List of connections to this node from other nodes.
        node_image_dict : dict
            Dictionary mapping node IDs to image data.
        node_result_dict : dict
            Dictionary mapping node IDs to JSON result data.
        node_audio_dict : dict
            Dictionary mapping node IDs to audio data.
            
        Returns
        -------
        dict
            Dictionary containing 'image', 'json', and 'audio' keys with
            the processed output data.
        """
        pass

    @abstractmethod
    def get_setting_dict(self, node_id):
        """Get the current settings for this node.
        
        Parameters
        ----------
        node_id : str
            Unique identifier for this node instance.
            
        Returns
        -------
        dict
            Dictionary containing the node's current settings.
        """
        pass

    @abstractmethod
    def set_setting_dict(self, node_id, setting_dict):
        """Set the settings for this node.
        
        Parameters
        ----------
        node_id : str
            Unique identifier for this node instance.
        setting_dict : dict
            Dictionary containing the settings to apply to the node.
        """
        pass

    @abstractmethod
    def close(self, node_id):
        """Clean up resources when the node is closed.
        
        This method should release any resources held by the node, such as
        file handles, network connections, or GPU memory.
        
        Parameters
        ----------
        node_id : str
            Unique identifier for this node instance.
        """
        pass
