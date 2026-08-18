#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Streaming output node for CV_Studio.

Accepts an image (and optional audio) input and streams live to popular
platforms (YouTube, Twitch, Facebook, Instagram, Restream, StreamYard) or
any custom RTMP/RTMPS endpoint, using an FFmpeg subprocess.

Supported platforms and their RTMP ingest URLs
-----------------------------------------------
YouTube   : rtmp://a.rtmp.youtube.com/live2/<key>
Twitch    : rtmp://live.twitch.tv/app/<key>
Facebook  : rtmps://live-api-s.facebook.com:443/rtmp/<key>
Instagram : rtmp://live-upload.instagram.com:80/rtmp/<key>
Restream  : rtmp://live.restream.io/live/<key>
StreamYard: rtmp://b.streamyard.com/<key>
Custom    : user-supplied full URL (key field is ignored)
"""

import copy
import logging
import queue
import shutil
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
# Platform RTMP URL templates
# ---------------------------------------------------------------------------
PLATFORMS = [
    "YouTube",
    "Twitch",
    "Facebook",
    "Instagram",
    "Restream",
    "StreamYard",
    "Custom",
]

_PLATFORM_URL = {
    "YouTube":    "rtmp://a.rtmp.youtube.com/live2/{key}",
    "Twitch":     "rtmp://live.twitch.tv/app/{key}",
    "Facebook":   "rtmps://live-api-s.facebook.com:443/rtmp/{key}",
    "Instagram":  "rtmp://live-upload.instagram.com:80/rtmp/{key}",
    "Restream":   "rtmp://live.restream.io/live/{key}",
    "StreamYard": "rtmp://b.streamyard.com/{key}",
    "Custom":     "{key}",  # key field contains the full URL
}

# ---------------------------------------------------------------------------
# FFmpeg resolution presets
# ---------------------------------------------------------------------------
RESOLUTIONS = ["1920x1080", "1280x720", "854x480", "640x360"]

# ---------------------------------------------------------------------------
# Helper: locate ffmpeg executable
# ---------------------------------------------------------------------------

def _find_ffmpeg() -> str:
    """Return a usable ffmpeg executable path."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    found = shutil.which("ffmpeg")
    return found if found is not None else "ffmpeg"


# ---------------------------------------------------------------------------
# FactoryNode
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = "Streaming"
    node_tag = "Streaming"

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
        if pos is None:
            pos = [0, 0]

        node = StreamingNode()
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

        black_image = np.zeros((small_window_w, small_window_h, 3))
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

            # Platform selector
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_combo(
                    tag=tag + ":Platform",
                    items=PLATFORMS,
                    default_value="YouTube",
                    width=small_window_w,
                    label="Platform",
                )

            # Stream key / custom URL
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_input_text(
                    tag=tag + ":StreamKey",
                    default_value="",
                    hint="Stream key (or full URL for Custom)",
                    width=small_window_w,
                )

            # Resolution selector
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_combo(
                    tag=tag + ":Resolution",
                    items=RESOLUTIONS,
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

            # Start / Stop button
            with dpg.node_attribute(
                tag=tag + ":ButtonAttr",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_button(
                    tag=tag + ":Button",
                    label="▶ Start Stream",
                    width=small_window_w,
                    callback=node._on_button,
                    user_data=tag,
                )

            # Status text
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_text(
                    tag=tag + ":Status",
                    default_value="● Stopped",
                    color=(180, 180, 180, 255),
                )

        return node


# ---------------------------------------------------------------------------
# StreamingNode
# ---------------------------------------------------------------------------

class StreamingNode(Node):
    _ver = "0.0.1"
    node_label = "Streaming"
    node_tag = "Streaming"

    _opencv_setting_dict = None

    # Per-instance streaming state (keyed by tag_node_name)
    _ffmpeg_proc: dict = {}
    _frame_queues: dict = {}
    _writer_threads: dict = {}
    _streaming: dict = {}

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # GUI callback
    # ------------------------------------------------------------------

    def _on_button(self, sender, app_data, user_data):
        tag = user_data
        if self._streaming.get(tag, False):
            self._stop_stream(tag)
        else:
            self._start_stream(tag)

    # ------------------------------------------------------------------
    # Stream lifecycle
    # ------------------------------------------------------------------

    def _build_rtmp_url(self, tag: str) -> str:
        platform = dpg_get_value(tag + ":Platform") or "YouTube"
        key = dpg_get_value(tag + ":StreamKey") or ""
        template = _PLATFORM_URL.get(platform, "{key}")
        return template.format(key=key.strip())

    def _start_stream(self, tag: str):
        url = self._build_rtmp_url(tag)
        if not url:
            self._set_status(tag, "⚠ No stream key", (255, 200, 0, 255))
            return

        res_str = dpg_get_value(tag + ":Resolution") or "1280x720"
        try:
            w_str, h_str = res_str.split("x")
            out_w, out_h = int(w_str), int(h_str)
        except Exception:
            out_w, out_h = 1280, 720

        fps = int(dpg_get_value(tag + ":FPS") or 30)
        ffmpeg_exe = _find_ffmpeg()

        # Build FFmpeg command: read raw BGR frames from stdin, push to RTMP
        cmd = [
            ffmpeg_exe,
            "-y",
            # Video input (raw BGR from pipe)
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{out_w}x{out_h}",
            "-r", str(fps),
            "-i", "pipe:0",
            # Audio: silence if no audio provided (simplifies startup)
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            # Video encoding
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "zerolatency",
            "-b:v", "3000k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", str(fps * 2),
            # Audio encoding
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            # Map streams
            "-map", "0:v:0",
            "-map", "1:a:0",
            # Output
            "-f", "flv",
            url,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        except Exception as exc:
            logger.error("StreamingNode[%s]: FFmpeg launch failed: %s", tag, exc)
            self._set_status(tag, f"⚠ FFmpeg error: {exc}", (255, 80, 80, 255))
            return

        self._ffmpeg_proc[tag] = proc
        self._streaming[tag] = True
        self._frame_queues[tag] = queue.Queue(maxsize=4)

        # Writer thread: forwards frames from queue to ffmpeg stdin
        t = threading.Thread(
            target=self._writer_loop,
            args=(tag, proc, out_w, out_h),
            daemon=True,
        )
        t.start()
        self._writer_threads[tag] = t

        # Stderr monitor thread
        threading.Thread(
            target=self._stderr_monitor,
            args=(tag, proc),
            daemon=True,
        ).start()

        platform = dpg_get_value(tag + ":Platform") or "YouTube"
        self._set_status(tag, f"● Live → {platform}", (80, 255, 80, 255))
        if dpg.does_item_exist(tag + ":Button"):
            dpg.configure_item(tag + ":Button", label="■ Stop Stream")
        logger.info("StreamingNode[%s]: Stream started → %s", tag, url)

    def _stop_stream(self, tag: str):
        self._streaming[tag] = False
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
                q.put_nowait(None)  # sentinel to unblock writer loop
            except Exception:
                pass
        self._set_status(tag, "● Stopped", (180, 180, 180, 255))
        if dpg.does_item_exist(tag + ":Button"):
            dpg.configure_item(tag + ":Button", label="▶ Start Stream")
        logger.info("StreamingNode[%s]: Stream stopped.", tag)

    # ------------------------------------------------------------------
    # Background threads
    # ------------------------------------------------------------------

    def _writer_loop(self, tag: str, proc: subprocess.Popen, w: int, h: int):
        """Pull frames from the queue and write raw bytes to ffmpeg stdin."""
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
                    logger.warning("StreamingNode[%s]: FFmpeg stdin closed.", tag)
                    break
        except Exception as exc:
            logger.error("StreamingNode[%s]: Writer loop error: %s", tag, exc)
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    def _stderr_monitor(self, tag: str, proc: subprocess.Popen):
        """Monitor FFmpeg stderr and update status on connection errors."""
        try:
            for line in proc.stderr:
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    logger.debug("StreamingNode[%s] ffmpeg: %s", tag, decoded)
                if "Connection refused" in decoded or "Failed to connect" in decoded:
                    self._set_status(tag, "⚠ Connection failed", (255, 80, 80, 255))
        except Exception:
            pass
        ret = proc.wait()
        if self._streaming.get(tag, False) and ret != 0:
            self._set_status(tag, f"⚠ FFmpeg exit {ret}", (255, 80, 80, 255))
            self._streaming[tag] = False
            if dpg.does_item_exist(tag + ":Button"):
                dpg.configure_item(tag + ":Button", label="▶ Start Stream")

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

        # Resolve upstream node name
        connection_info_src = ""
        for connection_info in connection_list:
            src = connection_info[0]
            src = src.split(":")[:2]
            connection_info_src = ":".join(src)

        small_window_w = self._opencv_setting_dict["process_width"]
        small_window_h = self._opencv_setting_dict["process_height"]

        frame = node_image_dict.get(connection_info_src, None)

        if frame is not None:
            display = copy.deepcopy(frame)

            # Push frame to streaming queue (non-blocking)
            if self._streaming.get(tag_node_name, False):
                q = self._frame_queues.get(tag_node_name)
                if q is not None:
                    try:
                        q.put_nowait(copy.deepcopy(frame))
                    except queue.Full:
                        pass  # Drop frame if queue is full (back-pressure)

            texture = self.convert_cv_to_dpg(
                display, small_window_w, small_window_h
            )
            dpg_set_value(input_value01_tag, texture)

        return {"image": frame, "json": None, "audio": None}

    # ------------------------------------------------------------------
    # close() — called when the node is removed
    # ------------------------------------------------------------------

    def close(self, node_id):
        tag_node_name = str(node_id) + ":" + self.node_tag
        if self._streaming.get(tag_node_name, False):
            self._stop_stream(tag_node_name)
