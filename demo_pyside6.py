#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple demo of the PySide6 node editor.
This creates a few sample nodes to demonstrate the functionality.
"""

import sys
import os

# Add the current directory to Python path
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from node_editor.pyside6_node_editor import PySide6NodeEditor
from src.utils.logging import setup_logging, get_logger

# Setup logging
setup_logging(level="INFO")
logger = get_logger(__name__)


def create_demo_widget():
    """Create a demo widget with some controls"""
    widget = QWidget()
    layout = QVBoxLayout()
    
    # Add some sample controls
    layout.addWidget(QLabel("Threshold:"))
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimum(0)
    slider.setMaximum(255)
    slider.setValue(128)
    layout.addWidget(slider)
    
    checkbox = QCheckBox("Enable Processing")
    checkbox.setChecked(True)
    layout.addWidget(checkbox)
    
    widget.setLayout(layout)
    return widget


def main():
    """Run the demo"""
    logger.info("Starting PySide6 Node Editor Demo")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create node editor
    editor = PySide6NodeEditor()
    editor.setWindowTitle("CV Studio - PySide6 Node Editor Demo")
    editor.resize(1200, 800)
    
    # Create some demo nodes
    logger.info("Creating demo nodes...")
    
    # Input node
    input_node = editor.add_node(
        None,
        "Webcam Input",
        pos=[-300, -100],
        color=QColor(100, 150, 255)
    )
    input_node.add_output_socket("Image")
    input_widget = QWidget()
    input_layout = QVBoxLayout()
    input_layout.addWidget(QLabel("Device: 0"))
    input_layout.addWidget(QLabel("Resolution: 640x480"))
    input_widget.setLayout(input_layout)
    input_node.set_content_widget(input_widget)
    
    # Process node 1
    process_node_1 = editor.add_node(
        None,
        "Grayscale",
        pos=[0, -150],
        color=QColor(150, 100, 255)
    )
    process_node_1.add_input_socket("Input")
    process_node_1.add_output_socket("Output")
    
    # Process node 2
    process_node_2 = editor.add_node(
        None,
        "Threshold",
        pos=[0, 50],
        color=QColor(150, 100, 255)
    )
    process_node_2.add_input_socket("Input")
    process_node_2.add_output_socket("Output")
    process_node_2.set_content_widget(create_demo_widget())
    
    # Output node
    output_node = editor.add_node(
        None,
        "Display",
        pos=[300, -50],
        color=QColor(255, 150, 100)
    )
    output_node.add_input_socket("Image")
    
    logger.info(f"Created {len(editor.nodes)} nodes")
    logger.info("Demo Instructions:")
    logger.info("  - Drag nodes to move them")
    logger.info("  - Click and drag from orange output sockets to blue input sockets to create connections")
    logger.info("  - Use mouse wheel to zoom")
    logger.info("  - Click and drag in empty space to pan")
    
    # Show the editor
    editor.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
