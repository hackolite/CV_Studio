#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ONVIF Network Scanner Node

Scans the local network for ONVIF-compliant devices using WS-Discovery,
then retrieves RTSP stream URIs (video, audio) and PTZ capabilities
via the ONVIF protocol.

Outputs a JSON dictionary with discovered devices and their profiles.
"""
import threading
import time
import traceback

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


# ---------------------------------------------------------------------------
# ONVIF / WS-Discovery helpers (lazy imports to avoid hard crash if missing)
# ---------------------------------------------------------------------------

def _discover_onvif_devices(timeout=4):
    """
    Use WS-Discovery to find ONVIF devices on the network.
    Returns a list of xaddr strings (e.g. http://192.168.1.10/onvif/device_service).
    """
    try:
        from wsdiscovery.discovery import ThreadedWSDiscovery
    except ImportError:
        try:
            from wsdiscovery import WSDiscovery as ThreadedWSDiscovery
        except ImportError:
            return []

    wsd = ThreadedWSDiscovery()
    wsd.start()
    # Scope for ONVIF devices
    from wsdiscovery.scope import Scope
    from wsdiscovery.qname import QName

    services = []
    try:
        # Search for ONVIF NetworkVideoTransmitter type
        ttype = QName("http://www.onvif.org/ver10/network/wsdl", "NetworkVideoTransmitter")
        services = wsd.searchServices(types=[ttype], timeout=timeout)
    except Exception:
        # Fallback: search all services
        try:
            services = wsd.searchServices(timeout=timeout)
        except Exception:
            pass
    wsd.stop()

    xaddrs = []
    for service in services:
        for xaddr in service.getXAddrs():
            if xaddr not in xaddrs:
                xaddrs.append(xaddr)
    return xaddrs


def _get_device_profiles(xaddr, username="admin", pw="admin", timeout=5):
    """
    Connect to an ONVIF device and retrieve media profiles with stream URIs.
    Returns a dict with device info, profiles, PTZ support.
    """
    try:
        from onvif import ONVIFCamera
    except ImportError:
        return None

    # Parse host/port from xaddr
    from urllib.parse import urlparse
    parsed = urlparse(xaddr)
    host = parsed.hostname
    port = parsed.port or 80

    result = {
        "xaddr": xaddr,
        "host": host,
        "port": port,
        "profiles": [],
        "ptz_supported": False,
        "error": None,
    }

    try:
        cam = ONVIFCamera(host, port, username, pw, no_cache=True)
        cam.devicemgmt.SetTimeout(timeout)

        # Get device info
        try:
            dev_info = cam.devicemgmt.GetDeviceInformation()
            result["manufacturer"] = getattr(dev_info, "Manufacturer", "")
            result["model"] = getattr(dev_info, "Model", "")
            result["firmware"] = getattr(dev_info, "FirmwareVersion", "")
        except Exception:
            pass

        # Get media service
        media_service = cam.create_media_service()
        profiles = media_service.GetProfiles()

        # Check PTZ support
        try:
            ptz_service = cam.create_ptz_service()
            if ptz_service:
                result["ptz_supported"] = True
        except Exception:
            pass

        for profile in profiles:
            profile_info = {
                "name": getattr(profile, "Name", ""),
                "token": getattr(profile, "token", ""),
                "video_stream_uri": None,
                "audio_stream_uri": None,
                "video_encoding": None,
                "audio_encoding": None,
                "resolution": None,
            }

            # Video encoder config
            vec = getattr(profile, "VideoEncoderConfiguration", None)
            if vec:
                profile_info["video_encoding"] = getattr(vec, "Encoding", None)
                res = getattr(vec, "Resolution", None)
                if res:
                    profile_info["resolution"] = f"{getattr(res, 'Width', '?')}x{getattr(res, 'Height', '?')}"

            # Audio encoder config
            aec = getattr(profile, "AudioEncoderConfiguration", None)
            if aec:
                profile_info["audio_encoding"] = getattr(aec, "Encoding", None)

            # Get stream URI (video)
            try:
                stream_setup = media_service.create_type("GetStreamUri")
                stream_setup.ProfileToken = profile.token
                stream_setup.StreamSetup = {
                    "Stream": "RTP-Unicast",
                    "Transport": {"Protocol": "RTSP"},
                }
                uri_response = media_service.GetStreamUri(stream_setup)
                profile_info["video_stream_uri"] = getattr(uri_response, "Uri", None)
            except Exception:
                pass

            # Audio typically shares the same RTSP URI on a different track
            if aec:
                profile_info["audio_stream_uri"] = profile_info["video_stream_uri"]

            result["profiles"].append(profile_info)

    except Exception as e:
        result["error"] = str(e)

    return result


# ---------------------------------------------------------------------------
# FactoryNode (DearPyGui node)
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = "Scan"
    node_tag = "Scan"

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
        node = ScanNode()

        node.tag_node_name = str(node_id) + ":" + node.node_tag
        node.tag_node_input01_name = (
            node.tag_node_name + ":" + node.TYPE_TEXT + ":Input01"
        )
        node.tag_node_output01_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":Output01"
        )
        node.tag_node_output01_value_name = (
            node.tag_node_name + ":" + node.TYPE_JSON + ":Output01Value"
        )

        node._opencv_setting_dict = opencv_setting_dict

        with dpg.node(
            tag=node.tag_node_name,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # --- Settings attribute (static) ---
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("ONVIF Network Scanner")
                dpg.add_separator()

                # Credentials
                dpg.add_text("Username:")
                dpg.add_input_text(
                    tag=node.tag_node_name + ":Username",
                    default_value="admin",
                    width=200,
                )
                dpg.add_text("Password:")
                dpg.add_input_text(
                    tag=node.tag_node_name + ":Password",
                    default_value="admin",
                    password=True,
                    width=200,
                )
                dpg.add_separator()

                # Timeout
                dpg.add_text("Discovery Timeout (s):")
                dpg.add_input_int(
                    tag=node.tag_node_name + ":Timeout",
                    default_value=4,
                    min_value=1,
                    max_value=30,
                    width=100,
                )
                dpg.add_separator()

                # Scan button
                dpg.add_button(
                    label="Scan Network",
                    tag=node.tag_node_name + ":ScanBtn",
                    width=200,
                    callback=node._callback_scan,
                    user_data=node.tag_node_name,
                )

                # Status text
                dpg.add_text(
                    tag=node.tag_node_name + ":Status",
                    default_value="Ready",
                    color=(180, 180, 180, 255),
                )
                dpg.add_separator()

                # Results display area
                dpg.add_text("Discovered Devices:")
                dpg.add_input_text(
                    tag=node.tag_node_name + ":Results",
                    default_value="",
                    multiline=True,
                    readonly=True,
                    width=380,
                    height=200,
                )

            # --- Output attribute (JSON) ---
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output01_value_name,
                    default_value="Output: JSON (devices)",
                )

        return node


# ---------------------------------------------------------------------------
# Node logic
# ---------------------------------------------------------------------------

class ScanNode(Node):
    _ver = "0.0.1"

    node_label = "Scan"
    node_tag = "Scan"

    _opencv_setting_dict = None
    _scan_results = {}  # tag_node_name -> list of device dicts
    _scan_running = {}  # tag_node_name -> bool
    _lock = threading.Lock()

    def __init__(self):
        pass

    def _callback_scan(self, sender, data, user_data):
        """Trigger an async network scan."""
        tag_node_name = user_data
        with self._lock:
            if self._scan_running.get(tag_node_name, False):
                return  # Already scanning
            self._scan_running[tag_node_name] = True

        dpg_set_value(tag_node_name + ":Status", "Scanning...")

        username = dpg_get_value(tag_node_name + ":Username") or "admin"
        pw = dpg_get_value(tag_node_name + ":Password") or "admin"
        timeout = dpg_get_value(tag_node_name + ":Timeout") or 4

        thread = threading.Thread(
            target=self._run_scan,
            args=(tag_node_name, username, pw, timeout),
            daemon=True,
        )
        thread.start()

    def _run_scan(self, tag_node_name, username, pw, timeout):
        """Run the ONVIF discovery + profile retrieval in a background thread."""
        try:
            # Phase 1: WS-Discovery
            xaddrs = _discover_onvif_devices(timeout=timeout)

            if not xaddrs:
                dpg_set_value(tag_node_name + ":Status", "No devices found")
                dpg_set_value(tag_node_name + ":Results", "No ONVIF devices discovered on the network.")
                with self._lock:
                    self._scan_results[tag_node_name] = []
                    self._scan_running[tag_node_name] = False
                return

            dpg_set_value(
                tag_node_name + ":Status",
                f"Found {len(xaddrs)} device(s), retrieving profiles...",
            )

            # Phase 2: Query each device for profiles
            devices = []
            for xaddr in xaddrs:
                device_info = _get_device_profiles(
                    xaddr, username=username, pw=pw, timeout=timeout
                )
                if device_info:
                    devices.append(device_info)

            with self._lock:
                self._scan_results[tag_node_name] = devices

            # Format display text
            display_lines = []
            for dev in devices:
                host = dev.get("host", "?")
                manufacturer = dev.get("manufacturer", "Unknown")
                model = dev.get("model", "Unknown")
                ptz = "Yes" if dev.get("ptz_supported") else "No"
                error = dev.get("error")

                display_lines.append(f"═══ {host} ═══")
                display_lines.append(f"  Manufacturer: {manufacturer}")
                display_lines.append(f"  Model: {model}")
                display_lines.append(f"  PTZ Control: {ptz}")

                if error:
                    display_lines.append(f"  ⚠ Error: {error}")

                for prof in dev.get("profiles", []):
                    name = prof.get("name", "?")
                    res = prof.get("resolution", "?")
                    v_enc = prof.get("video_encoding", "?")
                    a_enc = prof.get("audio_encoding", "None")
                    v_uri = prof.get("video_stream_uri", "N/A")

                    display_lines.append(f"  ── Profile: {name} ──")
                    display_lines.append(f"    Video: {v_enc} @ {res}")
                    display_lines.append(f"    Audio: {a_enc}")
                    display_lines.append(f"    RTSP:  {v_uri}")

                display_lines.append("")

            result_text = "\n".join(display_lines)
            dpg_set_value(tag_node_name + ":Results", result_text)
            dpg_set_value(
                tag_node_name + ":Status",
                f"Done — {len(devices)} device(s), "
                f"{sum(len(d.get('profiles', [])) for d in devices)} profile(s)",
            )

        except Exception as e:
            dpg_set_value(tag_node_name + ":Status", f"Error: {e}")
            dpg_set_value(tag_node_name + ":Results", traceback.format_exc())
            with self._lock:
                self._scan_results[tag_node_name] = []
        finally:
            with self._lock:
                self._scan_running[tag_node_name] = False

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        """
        Update method called each frame.
        Outputs the latest scan results as JSON to connected nodes.
        """
        tag_node_name = str(node_id) + ":" + self.node_tag

        # Output scan results to JSON dict for downstream nodes
        with self._lock:
            devices = self._scan_results.get(tag_node_name, [])
        if devices:
            # Build a simplified output structure
            output = {
                "scan_timestamp": time.time(),
                "device_count": len(devices),
                "devices": [],
            }
            for dev in devices:
                dev_entry = {
                    "host": dev.get("host"),
                    "port": dev.get("port"),
                    "manufacturer": dev.get("manufacturer", ""),
                    "model": dev.get("model", ""),
                    "ptz_supported": dev.get("ptz_supported", False),
                    "profiles": [],
                }
                for prof in dev.get("profiles", []):
                    dev_entry["profiles"].append({
                        "name": prof.get("name", ""),
                        "video_stream_uri": prof.get("video_stream_uri"),
                        "audio_stream_uri": prof.get("audio_stream_uri"),
                        "video_encoding": prof.get("video_encoding"),
                        "audio_encoding": prof.get("audio_encoding"),
                        "resolution": prof.get("resolution"),
                    })
                output["devices"].append(dev_entry)

            tag_output = tag_node_name + ":" + self.TYPE_JSON + ":Output01Value"
            node_result_dict[tag_output] = output

        return None, None
