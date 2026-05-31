#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PTZ Control Node

Allows piloting a PTZ (Pan-Tilt-Zoom) camera via the ONVIF protocol.
Accepts a JSON input with `url_ptz` (ONVIF device service URL) and
credentials, then provides directional and zoom controls.
"""
import threading
import time

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node as BaseNode


# ---------------------------------------------------------------------------
# ONVIF PTZ helper
# ---------------------------------------------------------------------------

def _send_ptz_command(url_ptz, username, password, action, speed=0.5, timeout=3):
    """
    Send a PTZ movement command to an ONVIF camera.

    Args:
        url_ptz: ONVIF device service URL (e.g. http://host:port/onvif/device_service)
        username: ONVIF username
        password: ONVIF password
        action: one of 'up', 'down', 'left', 'right', 'zoom_in', 'zoom_out',
                'home', 'stop'
        speed: movement speed factor (0.0 - 1.0)
        timeout: connection timeout in seconds

    Returns:
        (bool, str): (success, message)
    """
    try:
        from onvif import ONVIFCamera
    except ImportError:
        return False, "onvif library not installed"

    try:
        from urllib.parse import urlparse
        from requests import Session
        from zeep.transports import Transport

        parsed = urlparse(url_ptz)
        host = parsed.hostname
        port = parsed.port or 80

        session = Session()
        session.timeout = timeout
        transport = Transport(session=session, timeout=timeout)
        cam = ONVIFCamera(host, port, username, password, no_cache=True,
                          transport=transport)

        # Get media service to find default profile token
        media_service = cam.create_media_service()
        profiles = media_service.GetProfiles()
        if not profiles:
            return False, "No media profiles found"

        profile_token = profiles[0].token

        # Create PTZ service
        ptz_service = cam.create_ptz_service()

        if action == "stop":
            ptz_service.Stop({"ProfileToken": profile_token})
            return True, "Stop sent"

        if action == "home":
            ptz_service.GotoHomePosition({"ProfileToken": profile_token})
            return True, "Home sent"

        # Build ContinuousMove request
        velocity = {"PanTilt": {"x": 0.0, "y": 0.0}, "Zoom": {"x": 0.0}}

        if action == "up":
            velocity["PanTilt"]["y"] = speed
        elif action == "down":
            velocity["PanTilt"]["y"] = -speed
        elif action == "left":
            velocity["PanTilt"]["x"] = -speed
        elif action == "right":
            velocity["PanTilt"]["x"] = speed
        elif action == "zoom_in":
            velocity["Zoom"]["x"] = speed
        elif action == "zoom_out":
            velocity["Zoom"]["x"] = -speed

        request = ptz_service.create_type("ContinuousMove")
        request.ProfileToken = profile_token
        request.Velocity = velocity
        ptz_service.ContinuousMove(request)

        return True, f"{action} sent"

    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# FactoryNode (DearPyGui node)
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = "CamControl"
    node_tag = "CamControl"

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=[0, 0],
        opencv_setting_dict=None,
        callback=None,
    ):
        node = PTZControlNode()
        node.tag_node_name = f"{node_id}:{node.node_tag}"
        tag_node_name = node.tag_node_name

        # Input: JSON (from Scan node with url_ptz)
        node.tag_node_input_json_name = (
            tag_node_name + ":" + node.TYPE_JSON + ":InputJson"
        )
        node.tag_node_input_json_value_name = (
            tag_node_name + ":" + node.TYPE_JSON + ":InputJsonValue"
        )

        node._opencv_setting_dict = opencv_setting_dict

        # Create button theme
        with dpg.theme() as btn_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (70, 130, 180, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 160, 210, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (50, 100, 150, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.theme() as stop_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 50, 50, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (210, 80, 80, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (150, 30, 30, 255))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))

        with dpg.node(
            tag=tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # --- JSON Input ---
            with dpg.node_attribute(
                tag=node.tag_node_input_json_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input_json_value_name,
                    default_value="Input: JSON (url_ptz)",
                )

            # --- Settings ---
            with dpg.node_attribute(
                tag=tag_node_name + ":Settings",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("PTZ Camera Control")

                # Manual URL override
                dpg.add_text("ONVIF URL (auto from scan or manual):")
                dpg.add_input_text(
                    tag=tag_node_name + ":UrlPtz",
                    default_value="",
                    hint="http://ip:port/onvif/device_service",
                    width=200,
                )

                # Credentials
                dpg.add_text("Username:")
                dpg.add_input_text(
                    tag=tag_node_name + ":Username",
                    default_value="admin",
                    width=200,
                )
                dpg.add_text("Password:")
                dpg.add_input_text(
                    tag=tag_node_name + ":Password",
                    default_value="admin",
                    password=True,
                    width=200,
                )

                # Speed
                dpg.add_text("Speed:")
                dpg.add_slider_float(
                    tag=tag_node_name + ":Speed",
                    default_value=0.5,
                    min_value=0.1,
                    max_value=1.0,
                    width=200,
                )

                # --- Directional buttons ---
                dpg.add_text("Direction:")

                # Row 1: Up
                btn_up = dpg.add_button(
                    label="   Up   ",
                    tag=tag_node_name + ":BtnUp",
                    callback=node._callback_ptz,
                    user_data=(tag_node_name, "up"),
                    width=90,
                )
                dpg.bind_item_theme(btn_up, btn_theme)

                # Row 2: Left / Home / Right
                with dpg.group(horizontal=True):
                    btn_left = dpg.add_button(
                        label=" Left ",
                        tag=tag_node_name + ":BtnLeft",
                        callback=node._callback_ptz,
                        user_data=(tag_node_name, "left"),
                        width=70,
                    )
                    dpg.bind_item_theme(btn_left, btn_theme)

                    btn_home = dpg.add_button(
                        label="Home",
                        tag=tag_node_name + ":BtnHome",
                        callback=node._callback_ptz,
                        user_data=(tag_node_name, "home"),
                        width=70,
                    )
                    dpg.bind_item_theme(btn_home, btn_theme)

                    btn_right = dpg.add_button(
                        label="Right",
                        tag=tag_node_name + ":BtnRight",
                        callback=node._callback_ptz,
                        user_data=(tag_node_name, "right"),
                        width=70,
                    )
                    dpg.bind_item_theme(btn_right, btn_theme)

                # Row 3: Down
                btn_down = dpg.add_button(
                    label=" Down ",
                    tag=tag_node_name + ":BtnDown",
                    callback=node._callback_ptz,
                    user_data=(tag_node_name, "down"),
                    width=90,
                )
                dpg.bind_item_theme(btn_down, btn_theme)


                # --- Zoom buttons ---
                dpg.add_text("Zoom:")
                with dpg.group(horizontal=True):
                    btn_zin = dpg.add_button(
                        label="Zoom +",
                        tag=tag_node_name + ":BtnZoomIn",
                        callback=node._callback_ptz,
                        user_data=(tag_node_name, "zoom_in"),
                        width=100,
                    )
                    dpg.bind_item_theme(btn_zin, btn_theme)

                    btn_zout = dpg.add_button(
                        label="Zoom -",
                        tag=tag_node_name + ":BtnZoomOut",
                        callback=node._callback_ptz,
                        user_data=(tag_node_name, "zoom_out"),
                        width=100,
                    )
                    dpg.bind_item_theme(btn_zout, btn_theme)


                # --- Stop button ---
                btn_stop = dpg.add_button(
                    label="STOP",
                    tag=tag_node_name + ":BtnStop",
                    callback=node._callback_ptz,
                    user_data=(tag_node_name, "stop"),
                    width=210,
                )
                dpg.bind_item_theme(btn_stop, stop_theme)


                # Status
                dpg.add_text(
                    tag=tag_node_name + ":Status",
                    default_value="Ready",
                    color=(180, 180, 180, 255),
                )

        return node


# ---------------------------------------------------------------------------
# Node logic
# ---------------------------------------------------------------------------

class PTZControlNode(BaseNode):
    _ver = "0.0.1"

    node_label = "CamControl"
    node_tag = "CamControl"

    _opencv_setting_dict = None
    _last_url_ptz = None  # store url_ptz from upstream JSON

    def __init__(self):
        super().__init__()

    def _callback_ptz(self, sender, data, user_data):
        """Handle PTZ button press."""
        tag_node_name, action = user_data

        # Get settings
        url_ptz = dpg_get_value(tag_node_name + ":UrlPtz") or ""
        # Fallback to upstream JSON url_ptz
        if not url_ptz.strip() and self._last_url_ptz:
            url_ptz = self._last_url_ptz

        if not url_ptz.strip():
            dpg_set_value(tag_node_name + ":Status", "No PTZ URL configured")
            return

        username = dpg_get_value(tag_node_name + ":Username") or "admin"
        password = dpg_get_value(tag_node_name + ":Password") or "admin"
        speed = dpg_get_value(tag_node_name + ":Speed") or 0.5

        dpg_set_value(tag_node_name + ":Status", f"Sending: {action}...")

        # Send command in background thread to avoid blocking UI
        thread = threading.Thread(
            target=self._send_command_thread,
            args=(tag_node_name, url_ptz, username, password, action, speed),
            daemon=True,
        )
        thread.start()

    def _send_command_thread(self, tag_node_name, url_ptz, username, password, action, speed):
        """Send PTZ command in background thread."""
        success, message = _send_ptz_command(
            url_ptz, username, password, action, speed=speed
        )
        if success:
            dpg_set_value(tag_node_name + ":Status", f"✓ {message}")
        else:
            dpg_set_value(tag_node_name + ":Status", f"✗ {message}")

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        """
        Update method called each frame.
        Reads upstream JSON to extract url_ptz for automatic configuration.
        """
        tag_node_name = f"{node_id}:{self.node_tag}"

        # Find connected JSON source
        connection_info_src = ""
        for connection_info in connection_list:
            connection_type = connection_info[0].split(":")[2]
            if connection_type == self.TYPE_JSON:
                connection_info_src = connection_info[0]
                connection_info_src = ":".join(connection_info_src.split(":")[:2])
                break

        # Get upstream JSON data (e.g. from Scan node)
        node_result = node_result_dict.get(connection_info_src, {})
        if node_result and isinstance(node_result, dict):
            # Direct url_ptz field
            if "url_ptz" in node_result and node_result["url_ptz"]:
                self._last_url_ptz = node_result["url_ptz"]
            # Or from first device in devices list
            elif "devices" in node_result:
                for dev in node_result.get("devices", []):
                    if dev.get("url_ptz"):
                        self._last_url_ptz = dev["url_ptz"]
                        break

        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        """Clean up when node is closed."""
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = f"{node_id}:{self.node_tag}"
        pos = dpg.get_item_pos(tag_node_name)

        url_ptz = dpg_get_value(tag_node_name + ":UrlPtz") or ""
        username = dpg_get_value(tag_node_name + ":Username") or "admin"
        password = dpg_get_value(tag_node_name + ":Password") or "admin"
        speed = dpg_get_value(tag_node_name + ":Speed") or 0.5

        return {
            "ver": self._ver,
            "pos": pos,
            tag_node_name + ":UrlPtz": url_ptz,
            tag_node_name + ":Username": username,
            tag_node_name + ":Password": password,
            tag_node_name + ":Speed": speed,
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = f"{node_id}:{self.node_tag}"

        url_ptz = setting_dict.get(tag_node_name + ":UrlPtz", "")
        username = setting_dict.get(tag_node_name + ":Username", "admin")
        password = setting_dict.get(tag_node_name + ":Password", "admin")
        speed = setting_dict.get(tag_node_name + ":Speed", 0.5)

        dpg_set_value(tag_node_name + ":UrlPtz", url_ptz)
        dpg_set_value(tag_node_name + ":Username", username)
        dpg_set_value(tag_node_name + ":Password", password)
        dpg_set_value(tag_node_name + ":Speed", speed)
