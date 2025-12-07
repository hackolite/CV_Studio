#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

# Import timestamped queue system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Setup logging
logger = get_logger(__name__)


def get_args():
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


def async_main(node_editor, queue_manager):
    # Create queue-backed dictionaries for backward compatibility
    node_image_dict = QueueBackedDict(queue_manager, "image")
    node_result_dict = QueueBackedDict(queue_manager, "json")
    node_audio_dict = QueueBackedDict(queue_manager, "audio")
    
    logger.info("Async main loop started with timestamped queue system")
    
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
    editor_width = dpg.get_viewport_client_width()
    editor_height = dpg.get_viewport_client_height()

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
            # Determine if this is an input node or a processing node
            # Input nodes have no IMAGE/AUDIO/JSON input connections
            # Processing nodes have at least one IMAGE/AUDIO/JSON input connection
            has_data_input = False
            source_timestamp = None
            
            for connection_info in connection_list:
                # Validate connection_info structure before accessing
                if not connection_info or len(connection_info) < 2:
                    continue
                
                connection_parts = connection_info[0].split(":")
                if len(connection_parts) < 3:
                    continue
                    
                connection_type = connection_parts[2]
                if connection_type in ["IMAGE", "AUDIO", "JSON"]:
                    has_data_input = True
                    # Get the timestamp from the source node
                    source_node_id = ":".join(connection_parts[:2])
                    
                    # Try to get timestamp based on connection type
                    if connection_type == "IMAGE":
                        source_timestamp = node_image_dict.get_timestamp(source_node_id)
                    elif connection_type == "AUDIO":
                        source_timestamp = node_audio_dict.get_timestamp(source_node_id)
                    elif connection_type == "JSON":
                        source_timestamp = node_result_dict.get_timestamp(source_node_id)
                    
                    # Use the first data connection's timestamp
                    if source_timestamp is not None:
                        break
            
            # Check if the node provided an explicit timestamp (e.g., FPS-based timestamp from Video node)
            # This allows input nodes to specify timestamps based on their internal timing (FPS, audio chunks, etc.)
            node_provided_timestamp = data.get("timestamp", None) if isinstance(data, dict) else None
            
            # Store data with appropriate timestamp
            # Priority:
            # 1. For processing nodes: preserve source timestamp from connected input
            # 2. For input nodes with explicit timestamp: use the node-provided timestamp (FPS-based, etc.)
            # 3. For input nodes without explicit timestamp: create new timestamp automatically
            if has_data_input and source_timestamp is not None:
                # Processing node - preserve source timestamp
                node_image_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["image"]), source_timestamp)
                node_result_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["json"]), source_timestamp)
                node_audio_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["audio"]), source_timestamp)
                logger.debug(f"Node {node_id_name} preserved timestamp {source_timestamp:.6f} from source")
            elif node_provided_timestamp is not None:
                # Input node with explicit timestamp (e.g., FPS-based timestamp)
                node_image_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["image"]), node_provided_timestamp)
                node_result_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["json"]), node_provided_timestamp)
                node_audio_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["audio"]), node_provided_timestamp)
                logger.debug(f"Node {node_id_name} used explicit timestamp {node_provided_timestamp:.6f} (FPS-based)")
            else:
                # Input node without explicit timestamp - create new timestamp automatically
                node_image_dict[node_id_name] = copy.deepcopy(data["image"])
                node_result_dict[node_id_name] = copy.deepcopy(data["json"])
                node_audio_dict[node_id_name] = copy.deepcopy(data["audio"])
                logger.debug(f"Node {node_id_name} created new timestamp (input node)")
        except Exception as e:
            logger.error(f"Error processing node {node_id_name} results: {e}")


def main():
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
    
    # Initialize timestamped buffer system
    logger.info("Initializing timestamped buffer system")
    queue_manager = NodeDataQueueManager(default_maxsize=10)
    logger.info("Buffer system initialized: keeps last 10 timestamped items per node for synchronization")

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
        event_loop.run_in_executor(None, async_main, node_editor, queue_manager)
        dpg.start_dearpygui()

    else:
        logger.info("Async draw is disabled")
        # Create queue-backed dictionaries
        node_image_dict = QueueBackedDict(queue_manager, "image")
        node_result_dict = QueueBackedDict(queue_manager, "json")
        node_audio_dict = QueueBackedDict(queue_manager, "audio")
        
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
