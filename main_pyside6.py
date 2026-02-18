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
    QMenuBar, QMenu, QFileDialog, QWidget, QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction

from src.utils.logging import setup_logging, get_logger
from src.utils.gpu_utils import log_gpu_info

# Import timestamped queue system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

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


class NodeEditorView(QGraphicsView):
    """Custom QGraphicsView for the node editor"""
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(self.renderHints() | self.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # Zoom Factor
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        # Set Anchors
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)

        # Save the scene pos
        old_pos = self.mapToScene(event.position().toPoint())

        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)

        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())

        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())


class CVStudioMainWindow(QMainWindow):
    """Main window for CV Studio with PySide6"""
    
    def __init__(self, opencv_setting_dict, menu_dict, node_dir):
        super().__init__()
        
        self.opencv_setting_dict = opencv_setting_dict
        self.menu_dict = menu_dict
        self.node_dir = node_dir
        
        # Node editor data structures
        self.node_id = 0
        self.node_factory_list = {}
        self.node_instances_list = {}
        self.node_list = []
        self.node_link_list = []
        self.node_connection_dict = OrderedDict()
        
        self.terminate_flag = False
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("CV_STUDIO (PySide6)")
        
        # Set window size from settings
        width = self.opencv_setting_dict.get('editor_width', 1280)
        height = self.opencv_setting_dict.get('editor_height', 720)
        self.resize(width, height)
        
        # Create central widget with graphics scene
        self.scene = QGraphicsScene()
        self.view = NodeEditorView(self.scene)
        self.setCentralWidget(self.view)
        
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
            # TODO: Populate with actual node types from node directory
            # This would require loading node factories similar to DPG version
            
    def export_graph(self):
        """Export the node graph to JSON"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Graph",
            "",
            "JSON Files (*.json)"
        )
        if filename:
            logger.info(f"Exporting graph to {filename}")
            # TODO: Implement export logic
            
    def import_graph(self):
        """Import a node graph from JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Graph",
            "",
            "JSON Files (*.json)"
        )
        if filename:
            logger.info(f"Importing graph from {filename}")
            # TODO: Implement import logic
            
    def zoom_in(self):
        """Zoom in the view"""
        self.view.scale(1.1, 1.1)
        
    def zoom_out(self):
        """Zoom out the view"""
        self.view.scale(0.9, 0.9)
        
    def zoom_reset(self):
        """Reset zoom to 100%"""
        self.view.resetTransform()
        
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
        node_dir=current_path + "/node"
    )
    main_window.showMaximized()
    
    logger.info("PySide6 application started")
    logger.info("Note: This is a proof-of-concept. Full node editor implementation required.")
    
    # Start Qt event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
