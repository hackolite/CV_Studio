#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Complete PySide6 Node Editor implementation for CV Studio.
This module provides a full-featured node editor using Qt's QGraphicsView framework.
"""

import json
from collections import OrderedDict
from PySide6.QtWidgets import (
    QGraphicsScene, QGraphicsView, QGraphicsItem, QGraphicsPathItem,
    QGraphicsProxyWidget, QWidget, QVBoxLayout, QLabel, QMenu
)
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, QObject, QTimer
from PySide6.QtGui import (
    QPen, QBrush, QColor, QPainter, QPainterPath, QFont, QAction
)

from src.utils.logging import get_logger

logger = get_logger(__name__)


class NodeSocket(QGraphicsItem):
    """A socket (connection point) on a node"""
    
    def __init__(self, node, socket_type="input", index=0, label=""):
        super().__init__(node)
        self.node = node
        self.socket_type = socket_type  # "input" or "output"
        self.index = index
        self.label = label
        self.radius = 8
        self.connections = []
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges)
        
    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, 2 * self.radius, 2 * self.radius)
    
    def paint(self, painter, option, widget=None):
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        if self.socket_type == "input":
            painter.setBrush(QBrush(QColor(100, 150, 255)))
        else:
            painter.setBrush(QBrush(QColor(255, 150, 100)))
        painter.drawEllipse(self.boundingRect())
        
    def get_center(self):
        """Get the center position in scene coordinates"""
        return self.scenePos()
    
    def add_connection(self, connection):
        """Add a connection to this socket"""
        self.connections.append(connection)
        
    def remove_connection(self, connection):
        """Remove a connection from this socket"""
        if connection in self.connections:
            self.connections.remove(connection)


class NodeConnection(QGraphicsPathItem):
    """A connection between two sockets"""
    
    def __init__(self, source_socket, dest_socket=None, scene=None):
        super().__init__()
        self.source_socket = source_socket
        self.dest_socket = dest_socket
        self.temp_end_pos = None
        
        self.setPen(QPen(QColor(200, 200, 200), 2))
        self.setZValue(-1)
        
        if scene:
            scene.addItem(self)
        
        self.update_path()
        
    def update_path(self):
        """Update the connection path"""
        if not self.source_socket:
            return
            
        start = self.source_socket.get_center()
        
        if self.dest_socket:
            end = self.dest_socket.get_center()
        elif self.temp_end_pos:
            end = self.temp_end_pos
        else:
            return
            
        path = QPainterPath()
        path.moveTo(start)
        
        # Create a curved connection
        ctrl_offset = abs(end.x() - start.x()) * 0.5
        ctrl1 = QPointF(start.x() + ctrl_offset, start.y())
        ctrl2 = QPointF(end.x() - ctrl_offset, end.y())
        
        path.cubicTo(ctrl1, ctrl2, end)
        self.setPath(path)
        
    def set_temp_end(self, pos):
        """Set temporary end position while dragging"""
        self.temp_end_pos = pos
        self.update_path()
        
    def connect_to(self, dest_socket):
        """Complete the connection to a destination socket"""
        self.dest_socket = dest_socket
        self.temp_end_pos = None
        self.update_path()
        
        # Register connection with both sockets
        self.source_socket.add_connection(self)
        self.dest_socket.add_connection(self)


class GraphicsNode(QGraphicsItem):
    """A visual node in the node editor"""
    
    def __init__(self, node_instance, title="Node", width=200, height=150, color=None):
        super().__init__()
        self.node_instance = node_instance
        self.title = title
        self.width = width
        self.height = height
        self.title_height = 30
        self.socket_spacing = 25
        self.socket_margin = 10
        
        # Default color
        if color is None:
            color = QColor(50, 100, 150)
        self.color = color
        self.selected_color = QColor(
            min(255, int(color.red() * 1.2)),
            min(255, int(color.green() * 1.2)),
            min(255, int(color.blue() * 1.2))
        )
        
        self.input_sockets = []
        self.output_sockets = []
        self.content_widget = None
        self.content_proxy = None
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
    def boundingRect(self):
        return QRectF(0, 0, self.width, self.height)
    
    def paint(self, painter, option, widget=None):
        # Draw node body
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        
        if self.isSelected():
            painter.setBrush(QBrush(self.selected_color))
        else:
            painter.setBrush(QBrush(self.color))
            
        painter.drawRect(0, 0, self.width, self.title_height)
        
        # Draw title
        painter.setPen(QPen(QColor(255, 255, 255)))
        font = QFont()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(5, 0, self.width - 10, self.title_height), 
                        Qt.AlignmentFlag.AlignCenter, self.title)
        
        # Draw node content area
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        painter.drawRect(0, self.title_height, self.width, self.height - self.title_height)
        
    def add_input_socket(self, label="Input"):
        """Add an input socket to the node"""
        index = len(self.input_sockets)
        socket = NodeSocket(self, "input", index, label)
        y_pos = self.title_height + self.socket_margin + index * self.socket_spacing
        socket.setPos(0, y_pos)
        self.input_sockets.append(socket)
        return socket
        
    def add_output_socket(self, label="Output"):
        """Add an output socket to the node"""
        index = len(self.output_sockets)
        socket = NodeSocket(self, "output", index, label)
        y_pos = self.title_height + self.socket_margin + index * self.socket_spacing
        socket.setPos(self.width, y_pos)
        self.output_sockets.append(socket)
        return socket
        
    def set_content_widget(self, widget):
        """Set the content widget for this node"""
        if self.content_proxy:
            self.scene().removeItem(self.content_proxy)
            
        self.content_widget = widget
        self.content_proxy = QGraphicsProxyWidget(self)
        self.content_proxy.setWidget(widget)
        self.content_proxy.setPos(10, self.title_height + 10)
        
        # Adjust node height based on content
        content_height = widget.sizeHint().height()
        sockets_height = max(
            len(self.input_sockets) * self.socket_spacing + self.socket_margin * 2,
            len(self.output_sockets) * self.socket_spacing + self.socket_margin * 2
        )
        self.height = max(self.title_height + content_height + 20, sockets_height + self.title_height)
        
    def itemChange(self, change, value):
        """Handle item changes"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Update all connections when node moves
            for socket in self.input_sockets + self.output_sockets:
                for connection in socket.connections:
                    connection.update_path()
        return super().itemChange(change, value)


class PySide6NodeEditor(QGraphicsView):
    """Main node editor widget using PySide6"""
    
    node_created = Signal(object)
    connection_created = Signal(object, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self.scene)
        
        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        # Set background
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        
        # Connection creation state
        self.temp_connection = None
        self.connection_start_socket = None
        
        # Store nodes and connections
        self.nodes = []
        self.connections = []
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

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
        
    def mousePressEvent(self, event):
        """Handle mouse press for connection creation"""
        item = self.itemAt(event.pos())
        
        if isinstance(item, NodeSocket) and event.button() == Qt.MouseButton.LeftButton:
            # Start creating a connection
            if item.socket_type == "output":
                self.start_connection(item, event.pos())
                return
        
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        """Handle mouse move for connection dragging"""
        if self.temp_connection:
            scene_pos = self.mapToScene(event.pos())
            self.temp_connection.set_temp_end(scene_pos)
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release for connection completion"""
        if self.temp_connection:
            item = self.itemAt(event.pos())
            
            if isinstance(item, NodeSocket) and item.socket_type == "input":
                # Complete the connection
                self.complete_connection(item)
            else:
                # Cancel the connection
                self.cancel_connection()
        else:
            super().mouseReleaseEvent(event)
            
    def start_connection(self, socket, pos):
        """Start creating a new connection"""
        self.connection_start_socket = socket
        self.temp_connection = NodeConnection(socket, scene=self.scene)
        scene_pos = self.mapToScene(pos)
        self.temp_connection.set_temp_end(scene_pos)
        
    def complete_connection(self, dest_socket):
        """Complete a connection"""
        if self.temp_connection and self.connection_start_socket:
            self.temp_connection.connect_to(dest_socket)
            self.connections.append(self.temp_connection)
            self.connection_created.emit(self.connection_start_socket, dest_socket)
            logger.debug(f"Connection created from {self.connection_start_socket.node.title} to {dest_socket.node.title}")
        
        self.temp_connection = None
        self.connection_start_socket = None
        
    def cancel_connection(self):
        """Cancel connection creation"""
        if self.temp_connection:
            self.scene.removeItem(self.temp_connection)
        self.temp_connection = None
        self.connection_start_socket = None
        
    def add_node(self, node_instance, title, pos=None, width=200, height=150, color=None):
        """Add a node to the editor"""
        graphics_node = GraphicsNode(node_instance, title, width, height, color)
        
        if pos:
            graphics_node.setPos(pos[0], pos[1])
        else:
            # Place at center of view
            graphics_node.setPos(self.mapToScene(self.viewport().rect().center()))
            
        self.scene.addItem(graphics_node)
        self.nodes.append(graphics_node)
        self.node_created.emit(graphics_node)
        
        return graphics_node
        
    def remove_node(self, graphics_node):
        """Remove a node from the editor"""
        # Remove all connections
        all_sockets = graphics_node.input_sockets + graphics_node.output_sockets
        for socket in all_sockets:
            for connection in socket.connections[:]:  # Copy list to avoid modification during iteration
                self.remove_connection(connection)
        
        # Remove node from scene
        self.scene.removeItem(graphics_node)
        if graphics_node in self.nodes:
            self.nodes.remove(graphics_node)
            
    def remove_connection(self, connection):
        """Remove a connection from the editor"""
        # Remove from sockets
        if connection.source_socket:
            connection.source_socket.remove_connection(connection)
        if connection.dest_socket:
            connection.dest_socket.remove_connection(connection)
            
        # Remove from scene
        self.scene.removeItem(connection)
        if connection in self.connections:
            self.connections.remove(connection)
            
    def clear_all(self):
        """Clear all nodes and connections"""
        # Clear connections first
        for connection in self.connections[:]:
            self.remove_connection(connection)
            
        # Clear nodes
        for node in self.nodes[:]:
            self.remove_node(node)
            
    def export_graph(self):
        """Export the current graph to a dictionary"""
        graph_data = {
            "nodes": [],
            "connections": []
        }
        
        # Export nodes
        node_id_map = {}
        for i, node in enumerate(self.nodes):
            node_id = f"node_{i}"
            node_id_map[node] = node_id
            
            node_data = {
                "id": node_id,
                "type": node.title,
                "pos": [node.pos().x(), node.pos().y()],
                "width": node.width,
                "height": node.height
            }
            graph_data["nodes"].append(node_data)
            
        # Export connections
        for connection in self.connections:
            if connection.source_socket and connection.dest_socket:
                conn_data = {
                    "source_node": node_id_map.get(connection.source_socket.node),
                    "source_socket": connection.source_socket.index,
                    "dest_node": node_id_map.get(connection.dest_socket.node),
                    "dest_socket": connection.dest_socket.index
                }
                graph_data["connections"].append(conn_data)
                
        return graph_data
        
    def import_graph(self, graph_data):
        """Import a graph from a dictionary"""
        self.clear_all()
        
        # Import nodes
        node_map = {}
        for node_data in graph_data.get("nodes", []):
            # This is a placeholder - actual implementation would need to
            # instantiate the correct node type based on node_data["type"]
            node = self.add_node(
                None,  # node_instance - would need to be created
                node_data["type"],
                pos=node_data["pos"],
                width=node_data.get("width", 200),
                height=node_data.get("height", 150)
            )
            node_map[node_data["id"]] = node
            
        # Import connections
        for conn_data in graph_data.get("connections", []):
            source_node = node_map.get(conn_data["source_node"])
            dest_node = node_map.get(conn_data["dest_node"])
            
            if source_node and dest_node:
                source_socket = source_node.output_sockets[conn_data["source_socket"]]
                dest_socket = dest_node.input_sockets[conn_data["dest_socket"]]
                
                connection = NodeConnection(source_socket, dest_socket, self.scene)
                self.connections.append(connection)
