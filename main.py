#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

# Add the current directory to Python path to allow imports from src package
# This is necessary when running main.py directly without installing the package
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
import dearpygui.dearpygui as dpg

from src.utils.logging import setup_logging, get_logger
from src.utils.gpu_utils import log_gpu_info

from node_editor.util import check_camera_connection
from node_editor.node_main import DpgNodeEditor

# Import timestamped queue system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Setup logging
logger = get_logger(__name__)

SPLASH_WINDOW_TAG = "cvstudio_splash_window"
SPLASH_PROGRESS_TAG = "cvstudio_splash_progress"
SPLASH_STATUS_TAG = "cvstudio_splash_status"
SPLASH_THEME_TAG = "cvstudio_splash_theme"
SPLASH_ACCENT_COLOR = (82, 196, 255, 255)
SPLASH_STATUS_DOT_CYCLE = 3


def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for both development and frozen mode.

    When running as a script, returns the path relative to the script directory.
    When running as a PyInstaller executable (.exe), returns the path relative to
    the temporary directory where PyInstaller extracts files (sys._MEIPASS).

    Args:
        relative_path (str): Relative path to the resource (e.g., 'assets/image.png')

    Returns:
        str: Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        frozen = True
    except AttributeError:
        # Running in normal Python environment (script mode)
        base_path = os.path.dirname(os.path.abspath(__file__))
        frozen = False

    # Normalize path separators for cross-platform compatibility
    # This handles cases where relative_path uses forward slashes on Windows
    resource_path = os.path.normpath(os.path.join(base_path, relative_path))
    
    # Debug logging to help troubleshoot path issues
    logger.debug(
        f"Resource path resolution:\n"
        f"  Frozen mode: {frozen}\n"
        f"  Base path: {base_path}\n"
        f"  Relative path: {relative_path}\n"
        f"  Resolved path: {resource_path}\n"
        f"  Path exists: {os.path.exists(resource_path)}"
    )
    
    return resource_path


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
        # Small sleep to prevent CPU hogging and keep UI responsive
        # Note: This function runs in a thread executor (not asyncio coroutine),
        # so time.sleep() is appropriate here to yield CPU to other threads
        # Increased to 10ms to ensure UI remains responsive during video playback
        time.sleep(0.01)  # 10ms sleep to yield CPU and keep UI responsive


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
                # Input node with explicit timestamp (e.g., Video node with FPS-based timing)
                node_image_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["image"]), node_provided_timestamp)
                node_result_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["json"]), node_provided_timestamp)
                node_audio_dict.set_with_timestamp(node_id_name, copy.deepcopy(data["audio"]), node_provided_timestamp)
                logger.debug(f"Node {node_id_name} used explicit timestamp {node_provided_timestamp:.6f}")
            else:
                # Input node without explicit timestamp - create new timestamp automatically
                node_image_dict[node_id_name] = copy.deepcopy(data["image"])
                node_result_dict[node_id_name] = copy.deepcopy(data["json"])
                node_audio_dict[node_id_name] = copy.deepcopy(data["audio"])
                logger.debug(f"Node {node_id_name} created new timestamp (input node)")
        except Exception as e:
            logger.error(f"Error processing node {node_id_name} results: {e}")


def _centered_position(viewport_width, viewport_height, window_width, window_height):
    """Return centered [x, y] coordinates for a child window inside a viewport."""
    return [
        max(0, int((viewport_width - window_width) / 2)),
        max(0, int((viewport_height - window_height) / 2)),
    ]


def _create_splash_theme():
    if dpg.does_item_exist(SPLASH_THEME_TAG):
        return

    with dpg.theme(tag=SPLASH_THEME_TAG):
        with dpg.theme_component(dpg.mvWindowAppItem):
            dpg.add_theme_color(
                dpg.mvThemeCol_WindowBg,
                (16, 18, 24, 245),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_Border,
                (
                    SPLASH_ACCENT_COLOR[0],
                    SPLASH_ACCENT_COLOR[1],
                    SPLASH_ACCENT_COLOR[2],
                    200,
                ),
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_WindowRounding,
                12,
                category=dpg.mvThemeCat_Core,
            )
            dpg.add_theme_style(
                dpg.mvStyleVar_WindowBorderSize,
                1.0,
                category=dpg.mvThemeCat_Core,
            )


def show_splash_screen(duration_seconds=1.8, steps=60):
    """
    Show a startup splash window with an animated progress bar.

    Args:
        duration_seconds (float): Total splash duration in seconds.
                                  Values <= 0 skip waiting between animation frames.
        steps (int): Number of animation updates during the splash display (higher is smoother).
                     Values <= 0 are clamped to 1 to avoid division issues.

    Side effects:
        Creates a temporary DearPyGui splash window, renders frames for the animation,
        blocks startup during the splash duration, then deletes the splash window.
    """
    steps = max(1, int(steps))
    duration_seconds = max(0.0, float(duration_seconds))
    _create_splash_theme()

    viewport_width = dpg.get_viewport_client_width()
    viewport_height = dpg.get_viewport_client_height()
    if viewport_width <= 0 or viewport_height <= 0:
        viewport_width = dpg.get_viewport_width()
        viewport_height = dpg.get_viewport_height()

    splash_width = 560
    splash_height = 260
    splash_pos = _centered_position(
        viewport_width,
        viewport_height,
        splash_width,
        splash_height,
    )

    with dpg.window(
        tag=SPLASH_WINDOW_TAG,
        label="CvStudio.dev",
        pos=splash_pos,
        width=splash_width,
        height=splash_height,
        no_title_bar=True,
        no_move=True,
        no_resize=True,
        no_close=True,
        no_collapse=True,
        no_scrollbar=True,
        no_saved_settings=True,
    ):
        dpg.add_spacer(height=22)
        dpg.add_text("CvStudio.dev", color=SPLASH_ACCENT_COLOR)
        dpg.add_spacer(height=6)
        dpg.add_text("Computer Vision Studio", color=(220, 228, 240, 255))
        dpg.add_spacer(height=16)
        dpg.add_separator()
        dpg.add_spacer(height=12)
        dpg.add_text("Initialization…", tag=SPLASH_STATUS_TAG, color=(168, 176, 192, 255))
        dpg.add_spacer(height=8)
        dpg.add_progress_bar(
            default_value=0.0,
            width=splash_width - 60,
            tag=SPLASH_PROGRESS_TAG,
            overlay="0%",
        )

    dpg.bind_item_theme(SPLASH_WINDOW_TAG, SPLASH_THEME_TAG)

    for step in range(steps):
        progress = float(step + 1) / float(steps)
        # Intentionally cycles through 1..N dots for a continuous "loading" pulse.
        dots = "." * ((step % SPLASH_STATUS_DOT_CYCLE) + 1)
        dpg.set_value(SPLASH_PROGRESS_TAG, progress)
        dpg.configure_item(SPLASH_PROGRESS_TAG, overlay=f"{int(progress * 100)}%")
        dpg.set_value(SPLASH_STATUS_TAG, f"Initialization{dots}")
        dpg.render_dearpygui_frame()
        time.sleep(duration_seconds / float(steps))

    if dpg.does_item_exist(SPLASH_WINDOW_TAG):
        dpg.delete_item(SPLASH_WINDOW_TAG)


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
    logger.debug(f"Configuration file path: {setting}")
    
    # Verify the configuration file exists before attempting to load
    if not os.path.exists(setting):
        logger.error(f"Configuration file not found: {setting}")
        # Check if we're in a frozen (PyInstaller) environment
        if getattr(sys, 'frozen', False):
            logger.error(f"Running in frozen mode. Base path (_MEIPASS): {sys._MEIPASS}")
            logger.error("The setting.json file may not have been properly bundled with PyInstaller.")
            logger.error("Please ensure CV_Studio.spec includes: datas.append(('node_editor', 'node_editor'))")
        else:
            logger.error("Running in script mode. The setting.json file should be in node_editor/setting/")
        raise FileNotFoundError(f"Configuration file not found: {setting}")
    
    opencv_setting_dict = None
    with open(setting) as fp:
        opencv_setting_dict = json.load(fp)
    logger.info("Configuration loaded successfully")
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

    # Viewport must be visible before rendering splash frames.
    dpg.show_viewport(maximized=True)
    show_splash_screen()

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
            "NLPModel": "NLPModelNode",
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
    # Enable multiprocessing support for frozen executables (PyInstaller)
    # This must be called before any multiprocessing code runs
    # On Windows, when the executable spawns child processes for multiprocessing,
    # they will re-execute this script with special arguments that freeze_support() handles
    multiprocessing.freeze_support()
    main()
