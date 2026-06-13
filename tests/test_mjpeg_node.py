#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

sys.modules['cv2'] = mock.MagicMock()
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()

from node.InputNode.node_mjpeg import MjpegNode


def test_update_writes_texture_to_mjpeg_tag():
    node = MjpegNode()
    node.node_tag = "MJPEG"
    node.small_window_w = 240
    node.small_window_h = 135

    frame = object()
    cap = mock.MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, frame)

    node_id = "1"
    node._capture[node_id] = cap
    node._is_streaming[node_id] = True
    node.convert_cv_to_dpg = mock.MagicMock(return_value=[0.0] * (240 * 135 * 3))

    with mock.patch('node.InputNode.node_mjpeg.dpg_get_value', return_value=10), \
         mock.patch('node.InputNode.node_mjpeg.dpg_set_value') as m_set_value:
        out = node.update(1, [], {}, {}, {})

    assert out['image'] is frame
    m_set_value.assert_called_once()
    assert m_set_value.call_args.args[0] == "1:MJPEG:image:Output01Value"


def test_update_reconnect_uses_mjpeg_url_tag():
    node = MjpegNode()
    node.node_tag = "MJPEG"

    cap = mock.MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (False, None)

    node_id = "1"
    node._capture[node_id] = cap
    node._is_streaming[node_id] = True

    with mock.patch('node.InputNode.node_mjpeg.dpg_get_value', side_effect=[10, 'http://cam/stream']) as m_get, \
         mock.patch.object(node, '_open_capture', return_value=None), \
         mock.patch('node.InputNode.node_mjpeg.dpg.set_item_label') as m_set_label, \
         mock.patch('node.InputNode.node_mjpeg.time.sleep', return_value=None):
        node.update(1, [], {}, {}, {})

    assert m_get.call_args_list[0].args[0] == "1:MJPEG:fps"
    assert m_get.call_args_list[1].args[0] == "1:MJPEG:text:Input01Value"
    assert node._is_streaming[node_id] is False
    m_set_label.assert_called_once_with("1:MJPEG:text:ButtonValue", "Start")


def test_button_start_opens_stream_and_sets_stop_label():
    node = MjpegNode()
    node_id = "1"
    tag_node_name = f"{node_id}:MJPEG"
    button_tag = f"{tag_node_name}:text:ButtonValue"

    cap = mock.MagicMock()
    with mock.patch('node.InputNode.node_mjpeg.dpg.get_item_label', return_value='Start'), \
         mock.patch('node.InputNode.node_mjpeg.dpg_get_value', return_value='http://cam/stream'), \
         mock.patch.object(node, '_open_capture', return_value=cap), \
         mock.patch('node.InputNode.node_mjpeg.dpg.set_item_label') as m_set_label:
        node._button(None, None, tag_node_name)

    assert node._is_streaming[node_id] is True
    assert node._capture[node_id] is cap
    m_set_label.assert_called_once_with(button_tag, 'Stop')
