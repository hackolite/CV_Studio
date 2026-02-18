#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Create a screenshot of the PySide6 node editor demo.
"""

import sys
import os

# Add the current directory to Python path
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QSlider, QCheckBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter

from node_editor.pyside6_node_editor import PySide6NodeEditor, NodeConnection


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
    """Create screenshot"""
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create node editor
    editor = PySide6NodeEditor()
    editor.setWindowTitle("CV Studio - PySide6 Node Editor")
    editor.resize(1200, 800)
    
    # Create demo nodes
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
    
    # Create some connections
    conn1 = NodeConnection(input_node.output_sockets[0], process_node_1.input_sockets[0], editor.scene)
    editor.connections.append(conn1)
    
    conn2 = NodeConnection(process_node_1.output_sockets[0], process_node_2.input_sockets[0], editor.scene)
    editor.connections.append(conn2)
    
    conn3 = NodeConnection(process_node_2.output_sockets[0], output_node.input_sockets[0], editor.scene)
    editor.connections.append(conn3)
    
    # Show and take screenshot after a delay
    editor.show()
    
    def take_screenshot():
        # Render the scene to an image
        scene_rect = editor.scene.sceneRect()
        image = QImage(1200, 800, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(image)
        editor.scene.render(painter, source=editor.mapToScene(editor.viewport().rect()).boundingRect())
        painter.end()
        
        # Save the image
        output_path = "/tmp/pyside6_node_editor_screenshot.png"
        image.save(output_path)
        print(f"Screenshot saved to: {output_path}")
        
        # Also save viewport screenshot
        pixmap = editor.grab()
        viewport_path = "/tmp/pyside6_node_editor_viewport.png"
        pixmap.save(viewport_path)
        print(f"Viewport screenshot saved to: {viewport_path}")
        
        app.quit()
    
    # Take screenshot after 1 second
    QTimer.singleShot(1000, take_screenshot)
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
