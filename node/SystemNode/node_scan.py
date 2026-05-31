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
from urllib.parse import urlparse, urlunparse

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node


def _mask_credentials(url):
    """Inject USERNAME:PASSWORD placeholder into URLs for easy copy-paste."""
    if not url or not isinstance(url, str):
        return url
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return url
        # Build netloc with USERNAME:PASSWORD@ placeholder
        netloc = "USERNAME:PASSWORD@"
        netloc += parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"
        return urlunparse((
            parsed.scheme, netloc,
            parsed.path, parsed.params,
            parsed.query, parsed.fragment,
        ))
    except Exception:
        pass
    return url


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


def _probe_ptz_on_ports(host, username="admin", pw="admin", timeout=3):
    """
    Probe common ONVIF ports (80, 8899, 8000) on a given host to detect
    PTZ capabilities. Uses GetCapabilities to check for PTZ service exposure.

    Returns:
        tuple: (ptz_supported: bool, url_ptz: str or None)
               url_ptz is the ONVIF device service URL on the port that
               responded with PTZ capability.
    """
    ONVIF_PORTS = [80, 8899, 8000]

    try:
        from onvif import ONVIFCamera
    except ImportError:
        return False, None

    from requests import Session
    from zeep.transports import Transport

    for port in ONVIF_PORTS:
        try:
            session = Session()
            session.timeout = timeout
            transport = Transport(session=session, timeout=timeout)
            cam = ONVIFCamera(host, port, username, pw, no_cache=True,
                              transport=transport)

            # Use GetCapabilities to check PTZ service presence
            capabilities = cam.devicemgmt.GetCapabilities({"Category": "PTZ"})
            if capabilities and getattr(capabilities, "PTZ", None):
                ptz_xaddr = getattr(capabilities.PTZ, "XAddr", None)
                if ptz_xaddr:
                    # PTZ service confirmed – use the device service URL
                    # (ptz_xaddr points to PTZ service, but we expose
                    #  the device_service endpoint for ONVIF control entry)
                    url_ptz = ptz_xaddr
                    return True, url_ptz
        except Exception:
            # Port not responding, not ONVIF, or no PTZ – try next port
            continue

    return False, None


def _get_device_profiles(xaddr, username="admin", pw="admin", timeout=5):
    """
    Connect to an ONVIF device and retrieve media profiles with stream URIs.
    Returns a dict with device info, profiles, PTZ support, url_video, url_ptz.
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
        "url_video": None,
        "url_ptz": None,
        "error": None,
    }

    try:
        from requests import Session
        from zeep.transports import Transport

        session = Session()
        session.timeout = timeout
        transport = Transport(session=session, timeout=timeout)
        cam = ONVIFCamera(host, port, username, pw, no_cache=True,
                          transport=transport)

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

        # Check PTZ support: first try on current connection, then probe other ports
        try:
            capabilities = cam.devicemgmt.GetCapabilities({"Category": "PTZ"})
            if capabilities and getattr(capabilities, "PTZ", None):
                ptz_xaddr = getattr(capabilities.PTZ, "XAddr", None)
                if ptz_xaddr:
                    result["ptz_supported"] = True
                    result["url_ptz"] = ptz_xaddr
        except Exception:
            pass

        # If PTZ not found on the discovery port, probe other common ports
        if not result["ptz_supported"]:
            try:
                ptz_supported, url_ptz = _probe_ptz_on_ports(
                    host, username=username, pw=pw, timeout=min(timeout, 3)
                )
                result["ptz_supported"] = ptz_supported
                result["url_ptz"] = url_ptz
            except Exception:
                # PTZ probe failed – camera may not be motorized
                result["ptz_supported"] = False
                result["url_ptz"] = None

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

        # Set url_video from the first profile that has a video stream URI
        for prof in result["profiles"]:
            if prof.get("video_stream_uri"):
                result["url_video"] = prof["video_stream_uri"]
                break

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

                # Timeout
                dpg.add_text("Discovery Timeout (s):")
                dpg.add_input_int(
                    tag=node.tag_node_name + ":Timeout",
                    default_value=4,
                    min_value=1,
                    max_value=30,
                    width=100,
                )

                # Scan button
                dpg.add_button(
                    label="Scan Network",
                    tag=node.tag_node_name + ":ScanBtn",
                    width=200,
                    callback=node._callback_scan,
                    user_data=node.tag_node_name,
                )

                # Copy results button
                dpg.add_button(
                    label="Copy Results",
                    tag=node.tag_node_name + ":CopyBtn",
                    width=200,
                    callback=node._callback_copy,
                    user_data=node.tag_node_name,
                )

                # Status text
                dpg.add_text(
                    tag=node.tag_node_name + ":Status",
                    default_value="Ready",
                    color=(180, 180, 180, 255),
                )

                # Results display area (rich formatted)
                dpg.add_text("Discovered Devices:", color=[180, 180, 180])
                with dpg.child_window(
                    tag=node.tag_node_name + ":ResultsPanel",
                    width=400,
                    height=250,
                    border=True,
                ):
                    dpg.add_text(
                        tag=node.tag_node_name + ":ResultsPlaceholder",
                        default_value="Press 'Scan Network' to discover devices.",
                        color=[120, 120, 120],
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

    def _clear_results_panel(self, tag_node_name):
        """Clear all children from the results panel."""
        results_panel = tag_node_name + ":ResultsPanel"
        placeholder_tag = tag_node_name + ":ResultsPlaceholder"
        if dpg.does_item_exist(placeholder_tag):
            dpg.delete_item(placeholder_tag)
        for child in dpg.get_item_children(results_panel, 1) or []:
            dpg.delete_item(child)
        return results_panel

    def _callback_copy(self, sender, data, user_data):
        """Copy scan results as text to the system clipboard."""
        tag_node_name = user_data
        with self._lock:
            devices = self._scan_results.get(tag_node_name, [])

        if not devices:
            dpg_set_value(tag_node_name + ":Status", "Nothing to copy")
            return

        lines = []
        for dev in devices:
            host = dev.get("host", "?")
            manufacturer = dev.get("manufacturer", "Unknown")
            model = dev.get("model", "Unknown")
            ptz = dev.get("ptz_supported", False)
            url_video = _mask_credentials(dev.get("url_video")) or "N/A"
            url_ptz = _mask_credentials(dev.get("url_ptz")) or "N/A"
            error = dev.get("error")

            lines.append(f"Host: {host}")
            lines.append(f"  Manufacturer: {manufacturer}")
            lines.append(f"  Model: {model}")
            lines.append(f"  PTZ Control: {'YES' if ptz else 'NO'}")
            lines.append(f"  Video URL: {url_video}")
            lines.append(f"  PTZ URL: {url_ptz}")
            if error:
                lines.append(f"  Error: {error}")

            for prof in dev.get("profiles", []):
                name = prof.get("name", "?")
                res = prof.get("resolution", "?")
                v_enc = prof.get("video_encoding", "?")
                a_enc = prof.get("audio_encoding", "None")
                v_uri = _mask_credentials(prof.get("video_stream_uri")) or "N/A"
                lines.append(f"  Profile: {name}")
                lines.append(f"    Video: {v_enc} @ {res}")
                lines.append(f"    Audio: {a_enc if a_enc else 'None'}")
                lines.append(f"    RTSP: {v_uri}")

            lines.append("")

        text = "\n".join(lines)
        dpg.set_clipboard_text(text)
        dpg_set_value(tag_node_name + ":Status", "Copied to clipboard!")

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
                results_panel = self._clear_results_panel(tag_node_name)
                dpg.add_text(
                    "No ONVIF devices discovered on the network.",
                    parent=results_panel,
                    color=[255, 165, 0],
                )
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

            # Format display — rich text inside the results child_window
            results_panel = self._clear_results_panel(tag_node_name)

            # Populate with rich device cards
            for idx, dev in enumerate(devices):
                host = dev.get("host", "?")
                manufacturer = dev.get("manufacturer", "Unknown")
                model = dev.get("model", "Unknown")
                ptz = dev.get("ptz_supported", False)
                url_video = _mask_credentials(dev.get("url_video")) or "N/A"
                url_ptz = _mask_credentials(dev.get("url_ptz")) or "N/A"
                error = dev.get("error")

                # Device header (selectable)
                dpg.add_input_text(
                    default_value=host,
                    readonly=True,
                    width=280,
                    parent=results_panel,
                )

                # Manufacturer / Model
                with dpg.group(horizontal=True, parent=results_panel):
                    dpg.add_text("  Manufacturer:")
                    dpg.add_text(f"{manufacturer}", color=[200, 200, 255])

                with dpg.group(horizontal=True, parent=results_panel):
                    dpg.add_text("  Model:")
                    dpg.add_text(f"{model}", color=[200, 200, 255])

                # PTZ status with color indicator
                with dpg.group(horizontal=True, parent=results_panel):
                    dpg.add_text("  PTZ Control:")
                    if ptz:
                        dpg.add_text("YES", color=[0, 255, 0])  # Green
                    else:
                        dpg.add_text("NO", color=[255, 80, 80])  # Red

                # URLs (selectable input fields for copy-paste)
                with dpg.group(horizontal=True, parent=results_panel):
                    dpg.add_text("  Video URL:", color=[255, 180, 130])
                    dpg.add_input_text(
                        default_value=url_video if url_video else "N/A",
                        readonly=True,
                        width=280,
                    )

                with dpg.group(horizontal=True, parent=results_panel):
                    dpg.add_text("  PTZ URL:", color=[255, 180, 130])
                    dpg.add_input_text(
                        default_value=url_ptz if url_ptz else "N/A",
                        readonly=True,
                        width=280,
                    )

                # Error if any
                if error:
                    with dpg.group(horizontal=True, parent=results_panel):
                        dpg.add_text("  ⚠ Error:", color=[255, 165, 0])
                        dpg.add_text(f"{error}", color=[255, 165, 0], wrap=280)

                # Profiles
                for prof in dev.get("profiles", []):
                    name = prof.get("name", "?")
                    res = prof.get("resolution", "?")
                    v_enc = prof.get("video_encoding", "?")
                    a_enc = prof.get("audio_encoding", "None")
                    v_uri = _mask_credentials(prof.get("video_stream_uri")) or "N/A"

                    dpg.add_spacer(height=4, parent=results_panel)
                    dpg.add_text(
                        f"    Profile: {name}",
                        parent=results_panel,
                        color=[180, 255, 180],  # Light green
                    )

                    with dpg.group(horizontal=True, parent=results_panel):
                        dpg.add_text("      Video:")
                        dpg.add_text(
                            f"{v_enc} @ {res}",
                            color=[255, 255, 200],
                        )

                    with dpg.group(horizontal=True, parent=results_panel):
                        dpg.add_text("      Audio:")
                        dpg.add_text(
                            a_enc if a_enc else "None",
                            color=[255, 255, 200],
                        )

                    with dpg.group(horizontal=True, parent=results_panel):
                        dpg.add_text("      RTSP:", color=[255, 180, 130])
                        dpg.add_input_text(
                            default_value=v_uri if v_uri else "N/A",
                            readonly=True,
                            width=260,
                        )

                # Spacer between devices
                if idx < len(devices) - 1:
                    dpg.add_spacer(height=8, parent=results_panel)
                    dpg.add_spacer(height=4, parent=results_panel)
            dpg_set_value(
                tag_node_name + ":Status",
                f"Done — {len(devices)} device(s), "
                f"{sum(len(d.get('profiles', [])) for d in devices)} profile(s)",
            )

        except Exception as e:
            dpg_set_value(tag_node_name + ":Status", f"Error: {e}")
            results_panel = self._clear_results_panel(tag_node_name)
            dpg.add_text(
                "Error during scan:",
                parent=results_panel,
                color=[255, 80, 80],
            )
            dpg.add_text(
                traceback.format_exc(),
                parent=results_panel,
                color=[255, 120, 120],
                wrap=370,
            )
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
        output = None
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
                    "url_video": _mask_credentials(dev.get("url_video")),
                    "url_ptz": _mask_credentials(dev.get("url_ptz")),
                    "profiles": [],
                }
                for prof in dev.get("profiles", []):
                    dev_entry["profiles"].append({
                        "name": prof.get("name", ""),
                        "video_stream_uri": _mask_credentials(prof.get("video_stream_uri")),
                        "audio_stream_uri": _mask_credentials(prof.get("audio_stream_uri")),
                        "video_encoding": prof.get("video_encoding"),
                        "audio_encoding": prof.get("audio_encoding"),
                        "resolution": prof.get("resolution"),
                    })
                output["devices"].append(dev_entry)

            tag_output = tag_node_name + ":" + self.TYPE_JSON + ":Output01Value"
            node_result_dict[tag_output] = output

        return {"image": None, "json": output, "audio": None}
