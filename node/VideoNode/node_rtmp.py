#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RTMP output node for CV_Studio.

Accepts an image (and optional audio) input and exposes a local RTMP stream
that OBS Studio (or any RTMP client) can connect to as a media source.

How it works
------------
FFmpeg reads raw BGR frames from a stdin pipe, encodes them as H.264/AAC and
serves the result as an RTMP stream using its built-in ``-listen 1`` server
mode.  No external relay (mediamtx, nginx-rtmp …) is required.

OBS connects to the URL *after* clicking "▶ Start RTMP":

    rtmp://localhost:1935/live/cv_studio

OBS configuration (Media Source)
---------------------------------
* Source → Add → Media Source
* Input: ``rtmp://localhost:1935/live/cv_studio``
* Network Buffering: 0 MB  (lowest latency)
* Reconnect Delay: 1 s
"""

import logging
import os
import queue
import shutil
import socket
import subprocess
import threading
import time

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_PORT = 1935
_DEFAULT_STREAM_KEY = "cv_studio"
_RESOLUTIONS = ["1920x1080", "1280x720", "854x480", "640x360"]

# Auto-incremented port counter so that each new node gets a unique default port
_next_port = _DEFAULT_PORT

# ---------------------------------------------------------------------------
# Helper: locate ffmpeg
# ---------------------------------------------------------------------------


def _find_ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    return found if found is not None else "ffmpeg"


_MAX_RESTART_ATTEMPTS = 10   # stop after this many consecutive auto-restarts
_RESTART_DELAY_S = 3.0       # seconds to wait before auto-restarting


def _is_port_free(port: int) -> bool:
    """Return True only if the port is not currently listened on.

    Use SO_REUSEADDR=1 so that a port that is still in TIME_WAIT (from a
    recently-killed FFmpeg) is still considered free — matching what FFmpeg
    itself does when it binds the socket.
    """
    for host in ("127.0.0.1", "0.0.0.0"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((host, port))
        except OSError:
            return False
    return True


# ---------------------------------------------------------------------------
# FactoryNode
# ---------------------------------------------------------------------------


class FactoryNode:
    node_label = "RTMPOutput"
    node_tag = "RTMPOutput"

    def __init__(self):
        pass

    def add_node(
        self,
        parent,
        node_id,
        pos=None,
        opencv_setting_dict=None,
        callback=None,
    ):
        global _next_port
        if pos is None:
            pos = [0, 0]

        node = RTMPOutputNode()
        node.tag_node_name = str(node_id) + ":" + node.node_tag
        node.tag_node_input01_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Input01"
        )
        node.tag_node_input01_value_name = (
            node.tag_node_name + ":" + node.TYPE_IMAGE + ":Input01Value"
        )

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = opencv_setting_dict["process_width"]
        small_window_h = opencv_setting_dict["process_height"]

        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image, small_window_w, small_window_h
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_input01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        tag = node.tag_node_name

        # Each new node gets its own default port so two nodes don't collide
        node_port = _next_port
        _next_port += 1

        default_key = _DEFAULT_STREAM_KEY
        default_url = f"rtmp://localhost:{node_port}/live/{default_key}"

        with dpg.node(
            tag=tag,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # Image input
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_image(node.tag_node_input01_value_name)

            # Port setting
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_int(
                    tag=tag + ":Port",
                    default_value=node_port,
                    min_value=1024,
                    max_value=65535,
                    width=small_window_w,
                    label="Port",
                    callback=node._on_settings_changed,
                    user_data=tag,
                )

            # Stream key
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(
                    tag=tag + ":StreamKey",
                    default_value=default_key,
                    hint="stream key (path segment)",
                    width=small_window_w,
                    callback=node._on_settings_changed,
                    user_data=tag,
                )

            # Resolution
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_combo(
                    tag=tag + ":Resolution",
                    items=_RESOLUTIONS,
                    default_value="1280x720",
                    width=small_window_w,
                    label="Resolution",
                )

            # FPS
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_int(
                    tag=tag + ":FPS",
                    default_value=30,
                    min_value=1,
                    max_value=60,
                    width=small_window_w,
                    label="FPS",
                )

            # OBS URL display
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(
                    tag=tag + ":URLLabel",
                    default_value=f"OBS URL: {default_url}",
                    color=(150, 220, 255, 255),
                    wrap=small_window_w,
                )

            # Start / Stop button
            with dpg.node_attribute(
                tag=tag + ":ButtonAttr",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=tag + ":Button",
                    label="▶ Start RTMP",
                    width=small_window_w,
                    callback=node._on_button,
                    user_data=tag,
                )

            # Status
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(
                    tag=tag + ":Status",
                    default_value="● Stopped",
                    color=(180, 180, 180, 255),
                )

        return node


# ---------------------------------------------------------------------------
# RTMPOutputNode
# ---------------------------------------------------------------------------


class RTMPOutputNode(Node):
    _ver = "0.0.1"
    node_label = "RTMPOutput"
    node_tag = "RTMPOutput"

    _opencv_setting_dict = None

    def __init__(self):
        self._ffmpeg_proc: dict = {}
        self._frame_queues: dict = {}
        self._writer_threads: dict = {}
        self._streaming: dict = {}
        self._restart_count: dict = {}  # consecutive auto-restart attempts per tag
        self._stream_params: dict = {}  # saved params for auto-restart

    # ------------------------------------------------------------------
    # GUI callback
    # ------------------------------------------------------------------

    def _on_button(self, sender, app_data, user_data):
        tag = user_data
        if self._streaming.get(tag, False):
            self._stop(tag)
        else:
            self._start(tag)

    def _on_settings_changed(self, sender, app_data, user_data):
        """Update the OBS URL label whenever port or stream key changes."""
        tag = user_data
        if not self._streaming.get(tag, False):
            obs_url = self._rtmp_url(tag)
            if dpg.does_item_exist(tag + ":URLLabel"):
                dpg.set_value(tag + ":URLLabel", f"OBS URL: {obs_url}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _rtmp_url(self, tag: str) -> str:
        port = int(dpg_get_value(tag + ":Port") or _DEFAULT_PORT)
        key = (dpg_get_value(tag + ":StreamKey") or _DEFAULT_STREAM_KEY).strip()
        return f"rtmp://localhost:{port}/live/{key}"

    def _start(self, tag: str, _auto_restart: bool = False):
        port = int(dpg_get_value(tag + ":Port") or _DEFAULT_PORT)
        key = (dpg_get_value(tag + ":StreamKey") or _DEFAULT_STREAM_KEY).strip()
        res_str = dpg_get_value(tag + ":Resolution") or "1280x720"
        fps = int(dpg_get_value(tag + ":FPS") or 30)

        try:
            w_str, h_str = res_str.split("x")
            out_w, out_h = int(w_str), int(h_str)
        except Exception:
            out_w, out_h = 1280, 720

        rtmp_url = f"rtmp://0.0.0.0:{port}/live/{key}"
        obs_url = f"rtmp://localhost:{port}/live/{key}"

        if not _is_port_free(port):
            self._set_status(tag, f"⚠ Port {port} already in use", (255, 80, 80, 255))
            logger.error("RTMPOutputNode[%s]: port %d is already in use.", tag, port)
            return

        # Save params so auto-restart can re-use them
        self._stream_params[tag] = (out_w, out_h, fps, rtmp_url, obs_url)

        # Reset restart counter when the user manually starts
        if not _auto_restart:
            self._restart_count[tag] = 0

        # Update URL label (show the URL OBS should use)
        if dpg.does_item_exist(tag + ":URLLabel"):
            dpg.set_value(tag + ":URLLabel", f"OBS URL: {obs_url}")

        ffmpeg_exe = _find_ffmpeg()
        cmd = [
            ffmpeg_exe,
            "-y",
            # Raw BGR video from stdin
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{out_w}x{out_h}",
            "-r", str(fps),
            "-i", "pipe:0",
            # Silent audio fallback
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            # Video encode: H.264, ultra-low latency
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "4000k",
            "-maxrate", "4000k",
            "-bufsize", "8000k",
            "-pix_fmt", "yuv420p",
            "-g", str(fps * 4),
            # Audio encode
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            # Map streams
            "-map", "0:v:0",
            "-map", "1:a:0",
            # RTMP server mode: FFmpeg listens, OBS connects
            "-f", "flv",
            "-listen", "1",
            rtmp_url,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:
            logger.error("RTMPOutputNode[%s]: FFmpeg launch failed: %s", tag, exc)
            self._set_status(tag, f"⚠ FFmpeg error: {exc}", (255, 80, 80, 255))
            return

        self._ffmpeg_proc[tag] = proc
        self._streaming[tag] = True

        # Drain any stale frames before the new connection receives data
        old_q = self._frame_queues.get(tag)
        if old_q is not None:
            while not old_q.empty():
                try:
                    old_q.get_nowait()
                except queue.Empty:
                    break

        self._frame_queues[tag] = queue.Queue(maxsize=2)

        t = threading.Thread(
            target=self._writer_loop,
            args=(tag, proc, out_w, out_h),
            daemon=True,
        )
        t.start()
        self._writer_threads[tag] = t

        threading.Thread(
            target=self._stderr_monitor,
            args=(tag, proc),
            daemon=True,
        ).start()

        self._set_status(tag, f"⏳ Waiting for OBS…  →  {obs_url}", (255, 200, 0, 255))
        if dpg.does_item_exist(tag + ":Button"):
            dpg.configure_item(tag + ":Button", label="■ Stop RTMP")
        logger.info("RTMPOutputNode[%s]: FFmpeg RTMP server listening at %s", tag, obs_url)

    def _stop(self, tag: str):
        self._streaming[tag] = False
        self._stream_params.pop(tag, None)  # prevent any pending auto-restart
        self._restart_count[tag] = 0

        proc = self._ffmpeg_proc.pop(tag, None)
        if proc:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

        q = self._frame_queues.pop(tag, None)
        if q:
            try:
                q.put_nowait(None)
            except Exception:
                pass

        self._set_status(tag, "● Stopped", (180, 180, 180, 255))
        if dpg.does_item_exist(tag + ":Button"):
            dpg.configure_item(tag + ":Button", label="▶ Start RTMP")
        logger.info("RTMPOutputNode[%s]: Stopped.", tag)

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------

    def _writer_loop(self, tag: str, proc: subprocess.Popen, w: int, h: int):
        try:
            while self._streaming.get(tag, False):
                try:
                    frame = self._frame_queues[tag].get(timeout=1.0)
                except queue.Empty:
                    continue
                if frame is None:
                    break
                resized = cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
                try:
                    proc.stdin.write(resized.tobytes())
                except BrokenPipeError:
                    logger.warning("RTMPOutputNode[%s]: FFmpeg stdin closed.", tag)
                    break
        except Exception as exc:
            logger.error("RTMPOutputNode[%s]: Writer loop error: %s", tag, exc)
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    def _stderr_monitor(self, tag: str, proc: subprocess.Popen):
        try:
            for line in proc.stderr:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    logger.debug("RTMPOutputNode[%s] ffmpeg: %s", tag, decoded)
                # FFmpeg prints this when an RTMP client connects in -listen mode
                if "Sending publish" in decoded or "start time:" in decoded or "Output #0" in decoded:
                    obs_url = self._rtmp_url(tag)
                    self._set_status(tag, f"● Live  →  {obs_url}", (80, 255, 80, 255))
                    self._restart_count[tag] = 0  # reset counter on successful connection
        except Exception:
            pass
        ret = proc.wait()
        if self._streaming.get(tag, False):
            # Unexpected exit — try to auto-restart so OBS can reconnect
            attempt = self._restart_count.get(tag, 0) + 1
            self._restart_count[tag] = attempt
            if attempt <= _MAX_RESTART_ATTEMPTS:
                logger.warning(
                    "RTMPOutputNode[%s]: FFmpeg exited (code %d), auto-restart %d/%d in %.0fs…",
                    tag, ret, attempt, _MAX_RESTART_ATTEMPTS, _RESTART_DELAY_S,
                )
                self._set_status(
                    tag,
                    f"↺ Reconnecting ({attempt}/{_MAX_RESTART_ATTEMPTS})…",
                    (255, 200, 0, 255),
                )
                # Clean up the dead process before restarting
                self._ffmpeg_proc.pop(tag, None)
                self._streaming[tag] = False
                time.sleep(_RESTART_DELAY_S)
                # Only restart if the user hasn't manually stopped it
                if tag in self._stream_params:
                    self._start(tag, _auto_restart=True)
            else:
                logger.error(
                    "RTMPOutputNode[%s]: FFmpeg exited (code %d), max restarts reached.",
                    tag, ret,
                )
                self._set_status(tag, f"⚠ FFmpeg exit {ret} (max retries)", (255, 80, 80, 255))
                self._streaming[tag] = False
                if dpg.does_item_exist(tag + ":Button"):
                    dpg.configure_item(tag + ":Button", label="▶ Start RTMP")
        elif ret != 0:
            self._set_status(tag, f"⚠ FFmpeg exit {ret}", (255, 80, 80, 255))
            if dpg.does_item_exist(tag + ":Button"):
                dpg.configure_item(tag + ":Button", label="▶ Start RTMP")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, tag: str, text: str, color=(180, 180, 180, 255)):
        if dpg.does_item_exist(tag + ":Status"):
            dpg.set_value(tag + ":Status", text)
            dpg.configure_item(tag + ":Status", color=color)

    # ------------------------------------------------------------------
    # update() — called every frame by the pipeline
    # ------------------------------------------------------------------

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ":" + self.node_tag
        input_value01_tag = (
            tag_node_name + ":" + self.TYPE_IMAGE + ":Input01Value"
        )

        connection_info_src = ""
        for connection_info in connection_list:
            src = connection_info[0]
            src = src.split(":")[:2]
            connection_info_src = ":".join(src)

        small_window_w = self._opencv_setting_dict["process_width"]
        small_window_h = self._opencv_setting_dict["process_height"]

        frame = node_image_dict.get(connection_info_src, None)

        if frame is not None:
            if self._streaming.get(tag_node_name, False):
                q = self._frame_queues.get(tag_node_name)
                if q is not None:
                    try:
                        q.put_nowait(np.array(frame))
                    except queue.Full:
                        pass

            texture = self.convert_cv_to_dpg(
                frame, small_window_w, small_window_h
            )
            dpg_set_value(input_value01_tag, texture)

        return {"image": frame, "json": None, "audio": None}

    # ------------------------------------------------------------------
    # close()
    # ------------------------------------------------------------------

    def close(self, node_id):
        tag_node_name = str(node_id) + ":" + self.node_tag
        if self._streaming.get(tag_node_name, False):
            self._stop(tag_node_name)
