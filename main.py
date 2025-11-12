#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CV Studio - Node-based Computer Vision Application.

This module is the main entry point for CV Studio, a professional node-based
image processing application for computer vision development, verification,
and comparison.

The application provides a visual node editor powered by DearPyGUI that allows
users to create computer vision pipelines through an intuitive drag-and-drop
interface.
"""
import sys
import copy
import json
import asyncio
import argparse
from collections import OrderedDict
import os
import serial
import cv2
import dearpygui.dearpygui as dpg

from src.utils.logging import setup_logging, get_logger
from src.utils.gpu_utils import log_gpu_info

from node_editor.util import check_camera_connection
from node_editor.node_editor import DpgNodeEditor

# Setup logging
logger = get_logger(__name__)


def get_args():
    """Parse and return command line arguments.
    
    Returns
    -------
    argparse.Namespace
        Parsed command line arguments containing:
        - setting: str, path to configuration JSON file
        - unuse_async_draw: bool, disable asynchronous drawing if True
        - use_debug_print: bool, enable debug logging if True
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--setting",
        type=str,
        # get abs
        default=os.path.abspath(
            os.path.join(os.path.dirname(__file__), "node_editor/setting/setting.json")
        ),
    )
    parser.add_argument("--unuse_async_draw", action="store_true")
    parser.add_argument("--use_debug_print", action="store_true")
    args = parser.parse_args()
    return args


def async_main(node_editor):
    """Run the asynchronous main loop for the node editor.
    
    This function continuously updates all nodes in the graph until
    the terminate flag is set. It maintains separate dictionaries for
    image, result, and audio data passed between nodes.
    
    Parameters
    ----------
    node_editor : DpgNodeEditor
        The node editor instance managing the node graph.
    """
    node_image_dict = {}
    node_result_dict = {}
    node_audio_dict = {}
    while not node_editor.get_terminate_flag():
        update_node_info(
            node_editor, node_image_dict, node_result_dict, node_audio_dict
        )


def update_node_info(
    node_editor,
    node_image_dict,
    node_result_dict,
    node_audio_dict,
    mode_async=True,
):
    """Update all nodes in the node graph for one iteration.
    
    This function processes all nodes in topologically sorted order,
    updates their state, and stores the results in the provided dictionaries.
    
    Parameters
    ----------
    node_editor : DpgNodeEditor
        The node editor instance managing the node graph.
    node_image_dict : dict
        Dictionary mapping node IDs to image data.
    node_result_dict : dict
        Dictionary mapping node IDs to JSON result data.
    node_audio_dict : dict
        Dictionary mapping node IDs to audio data.
    mode_async : bool, optional
        If True, errors during node updates are caught and logged.
        If False, errors propagate. Default is True.
    """
    try:
        dpg.set_item_pos(node_editor.window, [0, 0])
        dpg.set_item_width(node_editor.window, dpg.get_viewport_client_width())
        dpg.set_item_height(node_editor.window, dpg.get_viewport_client_height())
    except Exception as e:
        logger.error(f"Failed to set node editor window properties: {e}")

    node_list = node_editor.get_node_list()

    sorted_node_connection_dict = node_editor.get_sorted_node_connection()

    for node_id_name in node_list:
        if node_id_name not in node_image_dict:
            node_image_dict[node_id_name] = None

        node_id, _ = node_id_name.split(":")
        connection_list = sorted_node_connection_dict.get(node_id_name, [])
        node_instance = node_editor.get_node_instances(node_id_name)
        logger.debug(
            f"Processing node {node_id_name} with connections: {connection_list}"
        )
        if mode_async:
            try:
                data = node_instance.update(
                    node_id,
                    connection_list,
                    node_image_dict,
                    node_result_dict,
                    node_audio_dict,
                )
            except Exception as e:
                logger.error(f"Error updating node {node_id_name}: {e}", exc_info=True)
                # sys.exit()
        else:
            data = node_instance.update(
                node_id,
                connection_list,
                node_image_dict,
                node_result_dict,
                node_audio_dict,
            )

        try:
            node_image_dict[node_id_name] = copy.deepcopy(data["image"])
            node_result_dict[node_id_name] = copy.deepcopy(data["json"])
            node_audio_dict[node_id_name] = copy.deepcopy(data["audio"])
        except Exception as e:
            logger.error(f"Error processing node {node_id_name} results: {e}")


def main():
    """Main entry point for the CV Studio application.
    
    This function initializes the application, sets up the node editor,
    configures cameras and serial devices, and starts the main event loop.
    """
    args = get_args()
    setting = args.setting
    unuse_async_draw = args.unuse_async_draw
    use_debug_print = args.use_debug_print

    # Setup logging based on debug flag
    log_level = "DEBUG" if use_debug_print else "INFO"
    setup_logging(level=getattr(__import__("logging"), log_level))

    logger.info("=" * 60)
    logger.info("CV_STUDIO Starting")
    logger.info("=" * 60)

    logger.info("Loading configuration")
    opencv_setting_dict = None
    with open(setting) as fp:
        opencv_setting_dict = json.load(fp)
    webcam_width = opencv_setting_dict["webcam_width"]
    webcam_height = opencv_setting_dict["webcam_height"]

    # Log GPU information
    if opencv_setting_dict.get("use_gpu", False):
        log_gpu_info()

    logger.info("Checking camera connections")
    device_no_list = check_camera_connection()
    camera_capture_list = []
    for device_no in device_no_list:
        video_capture = cv2.VideoCapture(device_no)
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, webcam_width)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, webcam_height)
        camera_capture_list.append(video_capture)
        logger.info(f"Camera {device_no} connected")

    opencv_setting_dict["device_no_list"] = device_no_list
    opencv_setting_dict["camera_capture_list"] = camera_capture_list

    editor_width = opencv_setting_dict["editor_width"]
    editor_height = opencv_setting_dict["editor_height"]

    serial_device_no_list = []
    serial_connection_list = []
    use_serial = opencv_setting_dict["use_serial"]
    if use_serial == True:
        try:
            from .node_editor.util import check_serial_connection
        except:
            from node_editor.util import check_serial_connection
        logger.info("Checking serial device connections")
        serial_device_no_list = check_serial_connection()
        for serial_device_no in serial_device_no_list:
            ser = serial.Serial(serial_device_no, 115200)
            serial_connection_list.append(ser)
            logger.info(f"Serial device {serial_device_no} connected")

    opencv_setting_dict["serial_device_no_list"] = serial_device_no_list
    opencv_setting_dict["serial_connection_list"] = serial_connection_list

    logger.info("Setting up DearPyGui")

    dpg.create_context()
    dpg.setup_dearpygui()
    dpg.create_viewport(
        title="CV_STUDIO",
        width=editor_width,
        height=editor_height,
    )

    # Using default DearPyGui font (no custom font needed)
    # DearPyGui will use its built-in default font automatically

    logger.info("Creating Node Editor")
    menu_dict = OrderedDict(
        {
            "Input": "InputNode",
            "VisionProcess": "ProcessNode",
            "VisionModel": "DLNode",
            "Stats": "StatsNode",
            "Trigger": "TriggerNode",
            "Router": "RouterNode",
            "Action": "ActionNode",
            "Video": "VideoNode",
            "Tracking": "TrackerNode",
            "Overlay": "OverlayNode",
            "Visual": "VisualNode",
            "TimeseriesML": "TimeseriesNode",
        }
    )

    dpg.show_viewport(maximized=True)

    current_path = os.path.dirname(os.path.abspath(__file__))

    node_editor = DpgNodeEditor(
        width=editor_width,
        height=editor_height,
        opencv_setting_dict=opencv_setting_dict,
        menu_dict=menu_dict,
        use_debug_print=use_debug_print,
        node_dir=current_path + "/node",
    )

    logger.info("Starting main event loop")
    if not unuse_async_draw:
        logger.info("Async draw is enabled")
        event_loop = asyncio.get_event_loop()
        event_loop.run_in_executor(None, async_main, node_editor)
        dpg.start_dearpygui()

    else:
        logger.info("Async draw is disabled")
        node_image_dict = {}
        node_result_dict = {}
        node_audio_dict = {}
        while dpg.is_dearpygui_running():
            update_node_info(
                node_editor,
                node_image_dict,
                node_result_dict,
                node_audio_dict,
                mode_async=False,
            )
            dpg.render_dearpygui_frame()

    logger.info("Terminating process")

    logger.info("Closing all nodes")
    node_list = node_editor.get_node_list()
    for node_id_name in node_list:
        node_id, node_name = node_id_name.split(":")
        node_instance = node_editor.get_node_instances(node_name)
        node_instance.close(node_id)

    logger.info("Releasing all video captures")
    for camera_capture in camera_capture_list:
        camera_capture.release()

    logger.info("Stopping event loop")
    node_editor.set_terminate_flag()
    event_loop.stop()

    logger.info("Destroying DearPyGui context")
    dpg.destroy_context()

    logger.info("CV_STUDIO shutdown complete")


if __name__ == "__main__":
    main()
