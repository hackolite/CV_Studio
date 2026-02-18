#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PySide6 adapter to replace DearPyGUI functionality.
This module provides compatibility layer for DPG API.
"""

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, 
    QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsPixmapItem,
    QCheckBox, QSlider, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QPushButton, QLabel, QWidget, QVBoxLayout, QHBoxLayout
)
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, QObject, QMutex, QMutexLocker
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QPixmap, QImage
import numpy as np
import threading

# Global Qt application instance
_qt_app = None
_qt_main_window = None
_qt_node_scene = None
_qt_node_view = None
_dpg_lock = threading.Lock()
_item_registry = {}
_texture_registry = {}
_theme_registry = {}
_next_item_id = 1000

# Constants matching DearPyGUI
mvNode_Attr_Input = 0
mvNode_Attr_Output = 1
mvNode_Attr_Static = 2

mvFormat_Float_rgb = 0
mvFormat_Float_rgba = 1

# Theme/Color constants
mvNodeCol_TitleBar = 0
mvNodeCol_TitleBarHovered = 1
mvNodeCol_TitleBarSelected = 2
mvThemeCol_Text = 3
mvThemeCol_FrameBg = 4
mvThemeCol_FrameBgHovered = 5
mvThemeCol_FrameBgActive = 6
mvThemeCol_SliderGrab = 7
mvThemeCol_SliderGrabActive = 8

mvThemeCat_Nodes = 0
mvThemeCat_Core = 1

# Component types
mvNode = "node"
mvCombo = "combo"
mvInputInt = "input_int"
mvInputFloat = "input_float"
mvInputText = "input_text"
mvSliderInt = "slider_int"
mvSliderFloat = "slider_float"
mvButton = "button"
mvCheckbox = "checkbox"


class DPGLock:
    """Thread-safe lock for DPG operations"""
    def __enter__(self):
        _dpg_lock.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        _dpg_lock.release()
        return False


def create_context():
    """Initialize PySide6 application context"""
    global _qt_app
    if _qt_app is None:
        _qt_app = QApplication.instance()
        if _qt_app is None:
            _qt_app = QApplication([])
    return _qt_app


def setup_dearpygui():
    """Setup the GUI - no-op for PySide6"""
    pass


def create_viewport(title="", width=800, height=600):
    """Create main window viewport"""
    global _qt_main_window, _qt_node_scene, _qt_node_view
    
    _qt_main_window = QMainWindow()
    _qt_main_window.setWindowTitle(title)
    _qt_main_window.resize(width, height)
    
    # Create graphics scene and view for node editor
    _qt_node_scene = QGraphicsScene()
    _qt_node_view = QGraphicsView(_qt_node_scene)
    _qt_main_window.setCentralWidget(_qt_node_view)
    
    return _qt_main_window


def show_viewport(maximized=False):
    """Show the main window"""
    if _qt_main_window:
        if maximized:
            _qt_main_window.showMaximized()
        else:
            _qt_main_window.show()


def start_dearpygui():
    """Start the Qt event loop"""
    if _qt_app:
        _qt_app.exec()


def render_dearpygui_frame():
    """Process Qt events (for manual rendering)"""
    if _qt_app:
        _qt_app.processEvents()


def is_dearpygui_running():
    """Check if Qt application is running"""
    return _qt_app is not None and _qt_main_window is not None and _qt_main_window.isVisible()


def destroy_context():
    """Destroy Qt application context"""
    global _qt_app, _qt_main_window
    if _qt_main_window:
        _qt_main_window.close()
    if _qt_app:
        _qt_app.quit()
    _qt_app = None
    _qt_main_window = None


def get_viewport_client_width():
    """Get viewport width"""
    if _qt_main_window:
        return _qt_main_window.width()
    return 800


def get_viewport_client_height():
    """Get viewport height"""
    if _qt_main_window:
        return _qt_main_window.height()
    return 600


def texture_registry(show=False):
    """Context manager for texture registry"""
    class TextureRegistryContext:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    return TextureRegistryContext()


def add_raw_texture(width, height, data, tag=None, format=mvFormat_Float_rgb):
    """Add a raw texture (store as QPixmap)"""
    global _next_item_id
    if tag is None:
        tag = f"texture_{_next_item_id}"
        _next_item_id += 1
    
    # Convert numpy array to QImage
    if isinstance(data, np.ndarray):
        if len(data.shape) == 3:
            height, width, channels = data.shape
        else:
            # 2D grayscale image
            height, width = data.shape
            channels = 1
        if channels == 3:
            qimage = QImage(data.data, width, height, 3 * width, QImage.Format_RGB888)
        elif channels == 4:
            qimage = QImage(data.data, width, height, 4 * width, QImage.Format_RGBA8888)
        else:
            qimage = QImage(data.data, width, height, width, QImage.Format_Grayscale8)
        pixmap = QPixmap.fromImage(qimage)
    else:
        pixmap = QPixmap(width, height)
    
    _texture_registry[tag] = pixmap
    return tag


def node(tag=None, parent=None, label="", pos=[0, 0]):
    """Context manager for creating a node"""
    class NodeContext:
        def __init__(self, tag, parent, label, pos):
            self.tag = tag
            self.label = label
            self.pos = pos
            self.widget = QWidget()
            self.layout = QVBoxLayout()
            self.widget.setLayout(self.layout)
            
        def __enter__(self):
            global _next_item_id
            if self.tag is None:
                self.tag = f"node_{_next_item_id}"
                _next_item_id += 1
            _item_registry[self.tag] = {
                'type': 'node',
                'widget': self.widget,
                'label': self.label,
                'pos': self.pos,
                'attributes': []
            }
            return self
        
        def __exit__(self, *args):
            # Add node to scene as graphics item
            if _qt_node_scene:
                # Create a simple rectangle for the node
                rect_item = _qt_node_scene.addRect(
                    self.pos[0], self.pos[1], 200, 100,
                    QPen(QColor(100, 100, 100)), QBrush(QColor(50, 50, 50))
                )
                text_item = _qt_node_scene.addText(self.label)
                text_item.setPos(self.pos[0] + 5, self.pos[1] + 5)
                _item_registry[self.tag]['graphics_items'] = [rect_item, text_item]
    
    return NodeContext(tag, parent, label, pos)


def node_attribute(tag=None, attribute_type=mvNode_Attr_Static):
    """Context manager for node attributes"""
    class AttributeContext:
        def __init__(self, tag, attr_type):
            self.tag = tag
            self.attr_type = attr_type
            
        def __enter__(self):
            global _next_item_id
            if self.tag is None:
                self.tag = f"attr_{_next_item_id}"
                _next_item_id += 1
            _item_registry[self.tag] = {
                'type': 'attribute',
                'attr_type': self.attr_type,
                'items': []
            }
            return self
        
        def __exit__(self, *args):
            pass
    
    return AttributeContext(tag, attribute_type)


def add_text(tag=None, default_value="", **kwargs):
    """Add text element"""
    global _next_item_id
    if tag is None:
        tag = f"text_{_next_item_id}"
        _next_item_id += 1
    
    label = QLabel(default_value)
    _item_registry[tag] = {
        'type': 'text',
        'widget': label,
        'value': default_value
    }
    return tag


def add_image(texture_tag):
    """Add image element"""
    global _next_item_id
    tag = f"image_{_next_item_id}"
    _next_item_id += 1
    
    label = QLabel()
    if texture_tag in _texture_registry:
        label.setPixmap(_texture_registry[texture_tag])
    
    _item_registry[tag] = {
        'type': 'image',
        'widget': label,
        'texture_tag': texture_tag
    }
    return tag


def add_checkbox(tag=None, label="", default_value=False, **kwargs):
    """Add checkbox"""
    global _next_item_id
    if tag is None:
        tag = f"checkbox_{_next_item_id}"
        _next_item_id += 1
    
    checkbox = QCheckBox(label)
    checkbox.setChecked(default_value)
    _item_registry[tag] = {
        'type': 'checkbox',
        'widget': checkbox,
        'value': default_value
    }
    return tag


def add_slider_int(tag=None, default_value=0, min_value=0, max_value=100, **kwargs):
    """Add integer slider"""
    global _next_item_id
    if tag is None:
        tag = f"slider_int_{_next_item_id}"
        _next_item_id += 1
    
    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(min_value)
    slider.setMaximum(max_value)
    slider.setValue(default_value)
    _item_registry[tag] = {
        'type': 'slider_int',
        'widget': slider,
        'value': default_value
    }
    return tag


def add_slider_float(tag=None, default_value=0.0, min_value=0.0, max_value=1.0, **kwargs):
    """Add float slider"""
    global _next_item_id
    if tag is None:
        tag = f"slider_float_{_next_item_id}"
        _next_item_id += 1
    
    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(int(min_value * 100))
    slider.setMaximum(int(max_value * 100))
    slider.setValue(int(default_value * 100))
    _item_registry[tag] = {
        'type': 'slider_float',
        'widget': slider,
        'value': default_value,
        'scale': 100
    }
    return tag


def add_combo(tag=None, items=[], default_value="", **kwargs):
    """Add combo box"""
    global _next_item_id
    if tag is None:
        tag = f"combo_{_next_item_id}"
        _next_item_id += 1
    
    combo = QComboBox()
    combo.addItems(items)
    if default_value in items:
        combo.setCurrentText(default_value)
    _item_registry[tag] = {
        'type': 'combo',
        'widget': combo,
        'value': default_value
    }
    return tag


def add_input_int(tag=None, default_value=0, **kwargs):
    """Add integer input"""
    global _next_item_id
    if tag is None:
        tag = f"input_int_{_next_item_id}"
        _next_item_id += 1
    
    spinbox = QSpinBox()
    spinbox.setValue(default_value)
    _item_registry[tag] = {
        'type': 'input_int',
        'widget': spinbox,
        'value': default_value
    }
    return tag


def add_input_float(tag=None, default_value=0.0, **kwargs):
    """Add float input"""
    global _next_item_id
    if tag is None:
        tag = f"input_float_{_next_item_id}"
        _next_item_id += 1
    
    spinbox = QDoubleSpinBox()
    spinbox.setValue(default_value)
    _item_registry[tag] = {
        'type': 'input_float',
        'widget': spinbox,
        'value': default_value
    }
    return tag


def add_input_text(tag=None, default_value="", **kwargs):
    """Add text input"""
    global _next_item_id
    if tag is None:
        tag = f"input_text_{_next_item_id}"
        _next_item_id += 1
    
    lineedit = QLineEdit(default_value)
    _item_registry[tag] = {
        'type': 'input_text',
        'widget': lineedit,
        'value': default_value
    }
    return tag


def add_button(tag=None, label="", callback=None, **kwargs):
    """Add button"""
    global _next_item_id
    if tag is None:
        tag = f"button_{_next_item_id}"
        _next_item_id += 1
    
    button = QPushButton(label)
    if callback:
        button.clicked.connect(callback)
    _item_registry[tag] = {
        'type': 'button',
        'widget': button,
        'callback': callback
    }
    return tag


def get_value(tag):
    """Get value of an item"""
    if tag not in _item_registry:
        return None
    
    item = _item_registry[tag]
    item_type = item['type']
    
    if item_type == 'checkbox':
        return item['widget'].isChecked()
    elif item_type == 'slider_int':
        return item['widget'].value()
    elif item_type == 'slider_float':
        return item['widget'].value() / item.get('scale', 100)
    elif item_type == 'combo':
        return item['widget'].currentText()
    elif item_type == 'input_int':
        return item['widget'].value()
    elif item_type == 'input_float':
        return item['widget'].value()
    elif item_type == 'input_text':
        return item['widget'].text()
    elif item_type == 'text':
        return item['value']
    
    return item.get('value')


def set_value(tag, value):
    """Set value of an item"""
    if tag not in _item_registry:
        return
    
    item = _item_registry[tag]
    item_type = item['type']
    
    if item_type == 'checkbox':
        item['widget'].setChecked(value)
    elif item_type == 'slider_int':
        item['widget'].setValue(value)
    elif item_type == 'slider_float':
        item['widget'].setValue(int(value * item.get('scale', 100)))
    elif item_type == 'combo':
        item['widget'].setCurrentText(value)
    elif item_type == 'input_int':
        item['widget'].setValue(value)
    elif item_type == 'input_float':
        item['widget'].setValue(value)
    elif item_type == 'input_text':
        item['widget'].setText(value)
    elif item_type == 'text':
        item['widget'].setText(value)
        item['value'] = value
    elif item_type == 'image':
        if value in _texture_registry:
            item['widget'].setPixmap(_texture_registry[value])
    
    item['value'] = value


def get_item_pos(tag):
    """Get position of an item"""
    if tag in _item_registry:
        item = _item_registry[tag]
        if 'pos' in item:
            return item['pos']
    return [0, 0]


def set_item_pos(tag, pos):
    """Set position of an item"""
    if tag in _item_registry:
        _item_registry[tag]['pos'] = pos
        if 'graphics_items' in _item_registry[tag]:
            for gitem in _item_registry[tag]['graphics_items']:
                if hasattr(gitem, 'setPos'):
                    gitem.setPos(pos[0], pos[1])


def set_item_width(tag, width):
    """Set width of an item"""
    if tag in _item_registry:
        item = _item_registry[tag]
        if 'widget' in item:
            item['widget'].setFixedWidth(width)


def set_item_height(tag, height):
    """Set height of an item"""
    if tag in _item_registry:
        item = _item_registry[tag]
        if 'widget' in item:
            item['widget'].setFixedHeight(height)


def theme():
    """Context manager for themes"""
    class ThemeContext:
        def __init__(self):
            self.theme_id = None
            
        def __enter__(self):
            global _next_item_id
            self.theme_id = f"theme_{_next_item_id}"
            _next_item_id += 1
            _theme_registry[self.theme_id] = {}
            return self.theme_id
        
        def __exit__(self, *args):
            pass
    
    return ThemeContext()


def theme_component(component_type):
    """Context manager for theme components"""
    class ThemeComponentContext:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
    return ThemeComponentContext()


def add_theme_color(color_type, color_value, category=mvThemeCat_Core):
    """Add theme color - no-op for now"""
    pass


def bind_item_theme(item_tag, theme_tag):
    """Bind theme to item - no-op for now"""
    pass
