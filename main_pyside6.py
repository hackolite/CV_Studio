#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PySide6-based main application for CV Studio.
This is a proof-of-concept showing how the main application would look with PySide6.
"""
import sys
import os

# Add the current directory to Python path
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

import copy
import json
import asyncio
import argparse
from collections import OrderedDict
import time
import multiprocessing
import cv2

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QMenuBar, QMenu, QFileDialog, QWidget, QVBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction, QColor

from src.utils.logging import setup_logging, get_logger
from src.utils.gpu_utils import log_gpu_info

# Import timestamped queue system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Import the PySide6 node editor
from node_editor.pyside6_node_editor import PySide6NodeEditor
from node.node_factory import NodeFactory

# Setup logging
logger = get_logger(__name__)


def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for both development and frozen mode.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        frozen = True
    except AttributeError:
        # Running in normal Python environment (script mode)
        base_path = os.path.dirname(os.path.abspath(__file__))
        frozen = False

    resource_path = os.path.normpath(os.path.join(base_path, relative_path))
    
    logger.debug(
        f"Resource path resolution:\n"
        f"  Frozen mode: {frozen}\n"
        f"  Base path: {base_path}\n"
        f"  Relative path: {relative_path}\n"
        f"  Resolved path: {resource_path}\n"
        f"  Path exists: {os.path.exists(resource_path)}"
    )
    
    return resource_path





class CVStudioMainWindow(QMainWindow):
    """Main window for CV Studio with PySide6"""
    
    def __init__(self, opencv_setting_dict, menu_dict, node_dir, queue_manager):
        super().__init__()
        
        self.opencv_setting_dict = opencv_setting_dict
        self.menu_dict = menu_dict
        self.node_dir = node_dir
        self.queue_manager = queue_manager
        
        # Node editor data structures
        self.node_id = 0
        self.node_factory_list = {}
        self.node_instances_list = {}
        self.node_list = []
        self.node_link_list = []
        self.node_connection_dict = OrderedDict()
        
        self.terminate_flag = False
        
        # Initialize node factories
        self.init_node_factories()
        
        self.init_ui()
        
    def init_node_factories(self):
        """Initialize node factories from node directory"""
        logger.info("Initializing node factories...")
        
        for menu_label, node_type in self.menu_dict.items():
            node_path = os.path.join(self.node_dir, node_type)
            if os.path.exists(node_path):
                try:
                    # Get all node_*.py files
                    node_files = [f for f in os.listdir(node_path) if f.startswith('node_') and f.endswith('.py')]
                    logger.info(f"Found {len(node_files)} nodes in {node_type}")
                    
                    for node_file in node_files:
                        module_name = node_file[:-3]  # Remove .py extension
                        try:
                            # Import the node module
                            module = __import__(f"node.{node_type}.{module_name}", fromlist=[module_name])
                            
                            # Create node factory if the module has a Node class
                            if hasattr(module, 'Node'):
                                factory = NodeFactory(module, node_type)
                                factory_key = f"{node_type}/{module_name}"
                                self.node_factory_list[factory_key] = factory
                                logger.debug(f"Registered node factory: {factory_key}")
                        except Exception as e:
                            logger.warning(f"Failed to import {node_type}/{module_name}: {e}")
                except Exception as e:
                    logger.error(f"Error loading nodes from {node_type}: {e}")
        
        logger.info(f"Initialized {len(self.node_factory_list)} node factories")
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("CV_STUDIO (PySide6)")
        
        # Set window size from settings
        width = self.opencv_setting_dict.get('editor_width', 1280)
        height = self.opencv_setting_dict.get('editor_height', 720)
        self.resize(width, height)
        
        # Create central widget with node editor
        self.node_editor = PySide6NodeEditor()
        self.setCentralWidget(self.node_editor)
        
        # Connect signals
        self.node_editor.node_created.connect(self.on_node_created)
        self.node_editor.connection_created.connect(self.on_connection_created)
        
        # Create menu bar
        self.create_menu_bar()
        
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        export_action = QAction('Export', self)
        export_action.triggered.connect(self.export_graph)
        file_menu.addAction(export_action)
        
        import_action = QAction('Import', self)
        import_action.triggered.connect(self.import_graph)
        file_menu.addAction(import_action)
        
        # View menu
        view_menu = menubar.addMenu('View')
        
        zoom_in_action = QAction('Zoom In (+10%)', self)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom Out (-10%)', self)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        zoom_reset_action = QAction('Reset Zoom (100%)', self)
        zoom_reset_action.triggered.connect(self.zoom_reset)
        view_menu.addAction(zoom_reset_action)
        
        # Add node menus
        for menu_label, node_type in self.menu_dict.items():
            node_menu = menubar.addMenu(menu_label)
            
            # Add actions for each node type
            for factory_key, factory in self.node_factory_list.items():
                if factory_key.startswith(node_type + "/"):
                    node_name = factory_key.split("/")[1].replace("node_", "").replace("_", " ").title()
                    action = QAction(node_name, self)
                    action.triggered.connect(lambda checked=False, fk=factory_key: self.create_node(fk))
                    node_menu.addAction(action)
            
    def create_node(self, factory_key):
        """Create a new node instance"""
        if factory_key not in self.node_factory_list:
            logger.error(f"Node factory not found: {factory_key}")
            return
            
        factory = self.node_factory_list[factory_key]
        node_name = factory_key.split("/")[1].replace("node_", "").replace("_", " ").title()
        
        # Create node instance
        self.node_id += 1
        node_tag = f"{factory_key}_{self.node_id}"
        
        try:
            # Get color for node type
            node_type = factory_key.split("/")[0]
            color = self.get_node_color(node_type)
            
            # Add graphics node to editor
            graphics_node = self.node_editor.add_node(
                None,  # We'll set the node instance later
                node_name,
                pos=None,  # Will be placed at center
                color=color
            )
            
            # Add sockets based on node type (placeholder - should be based on actual node definition)
            graphics_node.add_input_socket("Input")
            graphics_node.add_output_socket("Output")
            
            # Store node instance
            self.node_instances_list[node_tag] = graphics_node
            
            logger.info(f"Created node: {node_name} ({node_tag})")
            
        except Exception as e:
            logger.error(f"Error creating node {factory_key}: {e}")
            QMessageBox.critical(self, "Error", f"Failed to create node: {e}")
    
    def get_node_color(self, node_type):
        """Get color for a node type"""
        colors = {
            "InputNode": QColor(100, 150, 255),
            "ProcessNode": QColor(150, 100, 255),
            "DLNode": QColor(255, 150, 100),
            "AudioProcessNode": QColor(100, 255, 150),
            "AudioModelNode": QColor(150, 255, 100),
            "StatsNode": QColor(255, 255, 100),
            "TimeseriesNode": QColor(255, 200, 100),
            "TriggerNode": QColor(200, 100, 255),
            "RouterNode": QColor(100, 200, 255),
            "ActionNode": QColor(255, 100, 200),
            "OverlayNode": QColor(200, 255, 100),
            "TrackerNode": QColor(100, 255, 200),
            "VisualNode": QColor(255, 100, 150),
            "VideoNode": QColor(150, 255, 200),
            "SystemNode": QColor(200, 150, 255),
        }
        return colors.get(node_type, QColor(100, 100, 100))
    
    def on_node_created(self, graphics_node):
        """Handle node creation"""
        logger.debug(f"Node created event: {graphics_node.title}")
        
    def on_connection_created(self, source_socket, dest_socket):
        """Handle connection creation"""
        logger.debug(f"Connection created: {source_socket.node.title} -> {dest_socket.node.title}")
    
    def export_graph(self):
        """Export the node graph to JSON"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Graph",
            "",
            "JSON Files (*.json)"
        )
        if filename:
            try:
                graph_data = self.node_editor.export_graph()
                with open(filename, 'w') as f:
                    json.dump(graph_data, f, indent=2)
                logger.info(f"Graph exported to {filename}")
                QMessageBox.information(self, "Success", f"Graph exported to {filename}")
            except Exception as e:
                logger.error(f"Error exporting graph: {e}")
                QMessageBox.critical(self, "Error", f"Failed to export graph: {e}")
            
    def import_graph(self):
        """Import a node graph from JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Graph",
            "",
            "JSON Files (*.json)"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    graph_data = json.load(f)
                self.node_editor.import_graph(graph_data)
                logger.info(f"Graph imported from {filename}")
                QMessageBox.information(self, "Success", f"Graph imported from {filename}")
            except Exception as e:
                logger.error(f"Error importing graph: {e}")
                QMessageBox.critical(self, "Error", f"Failed to import graph: {e}")
            
    def zoom_in(self):
        """Zoom in the view"""
        self.node_editor.scale(1.1, 1.1)
        
    def zoom_out(self):
        """Zoom out the view"""
        self.node_editor.scale(0.9, 0.9)
        
    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.node_editor.resetTransform()
        
    def get_terminate_flag(self):
        """Check if termination flag is set"""
        return self.terminate_flag
        
    def set_terminate_flag(self):
        """Set the termination flag"""
        self.terminate_flag = True


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--setting",
        type=str,
        default=get_resource_path("node_editor/setting/setting.json"),
    )
    parser.add_argument("--unuse_async_draw", action="store_true")
    parser.add_argument("--use_debug_print", action="store_true")
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    setting = args.setting
    unuse_async_draw = args.unuse_async_draw
    use_debug_print = args.use_debug_print

    # Setup logging based on debug flag
    log_level = "DEBUG" if use_debug_print else "INFO"
    setup_logging(level=getattr(__import__("logging"), log_level))

    logger.info("=" * 60)
    logger.info("CV_STUDIO (PySide6) Starting")
    logger.info("=" * 60)
    
    # Initialize timestamped buffer system
    logger.info("Initializing timestamped buffer system")
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    logger.info("Buffer system initialized")

    logger.info("Loading configuration")
    logger.debug(f"Configuration file path: {setting}")
    
    # Verify the configuration file exists
    if not os.path.exists(setting):
        logger.error(f"Configuration file not found: {setting}")
        raise FileNotFoundError(f"Configuration file not found: {setting}")
    
    opencv_setting_dict = None
    with open(setting) as fp:
        opencv_setting_dict = json.load(fp)
    logger.info("Configuration loaded successfully")

    # Initialize Qt Application
    app = QApplication(sys.argv)
    
    # Setup menu dictionary
    menu_dict = OrderedDict({
        "Input": "InputNode",
        "VisionProcess": "ProcessNode",
        "VisionModel": "DLNode",
        "AudioProcess": "AudioProcessNode",
        "AudioModel": "AudioModelNode",
        "DataProcess": "StatsNode",
        "DataModel": "TimeseriesNode",
        "Trigger": "TriggerNode",
        "Router": "RouterNode",
        "Action": "ActionNode",
        "Overlay": "OverlayNode",
        "Tracking": "TrackerNode",
        "Visual": "VisualNode",
        "Video": "VideoNode",
        "System": "SystemNode",
    })
    
    current_path = os.path.dirname(os.path.abspath(__file__))
    
    # Create main window
    main_window = CVStudioMainWindow(
        opencv_setting_dict=opencv_setting_dict,
        menu_dict=menu_dict,
        node_dir=current_path + "/node",
        queue_manager=queue_manager
    )
    main_window.showMaximized()
    
    logger.info("=" * 60)
    logger.info("PySide6 application started successfully")
    logger.info("=" * 60)
    logger.info(f"Loaded {len(main_window.node_factory_list)} node types")
    logger.info("Use the menus to add nodes to the canvas")
    
    # Start Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
