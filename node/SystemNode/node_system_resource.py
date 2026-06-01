#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Resource Monitor Node

Monitors system resources (CPU, RAM, Disk I/O, GPU/VRAM) similar to htop.
Outputs JSON data every second compatible with the Chart node.

Output JSON format:
{
    "cpu_percent": float,         # CPU usage percentage (0-100)
    "ram_percent": float,         # RAM usage percentage (0-100)
    "ram_used_gb": float,         # RAM used in GB
    "ram_total_gb": float,        # RAM total in GB
    "disk_read_mb_s": float,      # Disk read speed MB/s
    "disk_write_mb_s": float,     # Disk write speed MB/s
    "gpu_percent": float,         # GPU usage percentage (0-100) if available
    "vram_percent": float,        # VRAM usage percentage (0-100) if available
    "vram_used_gb": float,        # VRAM used in GB if available
    "vram_total_gb": float,       # VRAM total in GB if available
    "net_sent_mb_s": float,       # Network sent MB/s
    "net_recv_mb_s": float,       # Network received MB/s
}
"""
import time
import threading

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node

try:
    import psutil
    _HAS_PSUTIL = True
    # Initial call to establish CPU baseline (first call always returns 0.0)
    psutil.cpu_percent(interval=None)
except ImportError:
    _HAS_PSUTIL = False

try:
    import pynvml
    pynvml.nvmlInit()
    _HAS_NVML = True
    _NVML_INITIALIZED = True
except Exception:
    _HAS_NVML = False
    _NVML_INITIALIZED = False


import atexit

def _shutdown_nvml():
    global _NVML_INITIALIZED
    if _NVML_INITIALIZED:
        try:
            pynvml.nvmlShutdown()
            _NVML_INITIALIZED = False
        except Exception:
            pass

atexit.register(_shutdown_nvml)


class FactoryNode:
    node_label = 'SystemResource'
    node_tag = 'SystemResource'

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
        node = _Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Output01Value'

        node._opencv_setting_dict = opencv_setting_dict

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=node.node_label,
                pos=pos,
        ):
            # Static attribute for status display
            with dpg.node_attribute(
                    tag=node.tag_node_name + ':Static',
                    attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_spacer(height=2)
                dpg.add_text(
                    tag=node.tag_node_name + ':CpuText',
                    default_value='CPU  ---%',
                )
                dpg.add_text(
                    tag=node.tag_node_name + ':RamText',
                    default_value='RAM  ---%  -.-- / -.-- GB',
                )
                dpg.add_spacer(height=4)
                dpg.add_text(
                    tag=node.tag_node_name + ':DiskText',
                    default_value='Disk R -.-- MB/s  W -.-- MB/s',
                )
                dpg.add_text(
                    tag=node.tag_node_name + ':NetText',
                    default_value='Net  ↑ -.-- MB/s  ↓ -.-- MB/s',
                )
                dpg.add_spacer(height=4)
                dpg.add_text(
                    tag=node.tag_node_name + ':GpuText',
                    default_value='GPU  ---%',
                )
                dpg.add_text(
                    tag=node.tag_node_name + ':VramText',
                    default_value='VRAM ---%  -.-- / -.-- GB',
                )
                dpg.add_spacer(height=2)

            # Output JSON
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(
                    tag=node.tag_node_output01_value_name,
                    default_value='JSON Output',
                )

        return node


class _Node(Node):
    _ver = '0.0.1'

    node_label = 'SystemResource'
    node_tag = 'SystemResource'

    _opencv_setting_dict = None

    # Shared state across instances
    _lock = threading.Lock()
    _last_disk_io = {}
    _last_net_io = {}
    _last_sample_time = {}
    _cached_data = {}

    def __init__(self):
        pass

    def _sample_resources(self, tag_node_name):
        """Sample system resources and return a dict."""
        data = {}
        now = time.time()

        # CPU
        if _HAS_PSUTIL:
            data['cpu_percent'] = psutil.cpu_percent(interval=None)

            # RAM
            mem = psutil.virtual_memory()
            data['ram_percent'] = mem.percent
            data['ram_used_gb'] = round(mem.used / (1024 ** 3), 2)
            data['ram_total_gb'] = round(mem.total / (1024 ** 3), 2)

            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                with self._lock:
                    last_disk = self._last_disk_io.get(tag_node_name)
                    last_time = self._last_sample_time.get(tag_node_name, now)
                dt = now - last_time
                if last_disk and dt > 0:
                    data['disk_read_mb_s'] = round(
                        (disk_io.read_bytes - last_disk.read_bytes) / (1024 ** 2) / dt, 2
                    )
                    data['disk_write_mb_s'] = round(
                        (disk_io.write_bytes - last_disk.write_bytes) / (1024 ** 2) / dt, 2
                    )
                else:
                    data['disk_read_mb_s'] = 0.0
                    data['disk_write_mb_s'] = 0.0
                with self._lock:
                    self._last_disk_io[tag_node_name] = disk_io
            except Exception:
                data['disk_read_mb_s'] = 0.0
                data['disk_write_mb_s'] = 0.0

            # Network I/O
            try:
                net_io = psutil.net_io_counters()
                with self._lock:
                    last_net = self._last_net_io.get(tag_node_name)
                    last_time = self._last_sample_time.get(tag_node_name, now)
                dt = now - last_time
                if last_net and dt > 0:
                    data['net_sent_mb_s'] = round(
                        (net_io.bytes_sent - last_net.bytes_sent) / (1024 ** 2) / dt, 2
                    )
                    data['net_recv_mb_s'] = round(
                        (net_io.bytes_recv - last_net.bytes_recv) / (1024 ** 2) / dt, 2
                    )
                else:
                    data['net_sent_mb_s'] = 0.0
                    data['net_recv_mb_s'] = 0.0
                with self._lock:
                    self._last_net_io[tag_node_name] = net_io
            except Exception:
                data['net_sent_mb_s'] = 0.0
                data['net_recv_mb_s'] = 0.0

            with self._lock:
                self._last_sample_time[tag_node_name] = now
        else:
            data['cpu_percent'] = 0.0
            data['ram_percent'] = 0.0
            data['ram_used_gb'] = 0.0
            data['ram_total_gb'] = 0.0
            data['disk_read_mb_s'] = 0.0
            data['disk_write_mb_s'] = 0.0
            data['net_sent_mb_s'] = 0.0
            data['net_recv_mb_s'] = 0.0

        # GPU / VRAM (NVIDIA via pynvml)
        if _HAS_NVML:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                data['gpu_percent'] = util.gpu
                data['vram_percent'] = round(mem_info.used / mem_info.total * 100, 1)
                data['vram_used_gb'] = round(mem_info.used / (1024 ** 3), 2)
                data['vram_total_gb'] = round(mem_info.total / (1024 ** 3), 2)
            except Exception:
                data['gpu_percent'] = 0.0
                data['vram_percent'] = 0.0
                data['vram_used_gb'] = 0.0
                data['vram_total_gb'] = 0.0
        else:
            data['gpu_percent'] = 0.0
            data['vram_percent'] = 0.0
            data['vram_used_gb'] = 0.0
            data['vram_total_gb'] = 0.0

        return data

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag

        # Sample every ~1 second
        now = time.time()
        with self._lock:
            last = self._last_sample_time.get(tag_node_name, 0)
        if now - last >= 1.0 or tag_node_name not in self._cached_data:
            data = self._sample_resources(tag_node_name)
            with self._lock:
                self._cached_data[tag_node_name] = data

            # Update display texts
            try:
                dpg_set_value(
                    tag_node_name + ':CpuText',
                    f"CPU  {data['cpu_percent']:.1f}%"
                )
                dpg_set_value(
                    tag_node_name + ':RamText',
                    f"RAM  {data['ram_percent']:.1f}%  {data['ram_used_gb']:.2f} / {data['ram_total_gb']:.2f} GB"
                )
                dpg_set_value(
                    tag_node_name + ':DiskText',
                    f"Disk R {data['disk_read_mb_s']:.2f} MB/s  W {data['disk_write_mb_s']:.2f} MB/s"
                )
                dpg_set_value(
                    tag_node_name + ':NetText',
                    f"Net  ↑ {data['net_sent_mb_s']:.2f} MB/s  ↓ {data['net_recv_mb_s']:.2f} MB/s"
                )
                dpg_set_value(
                    tag_node_name + ':GpuText',
                    f"GPU  {data['gpu_percent']:.1f}%"
                )
                dpg_set_value(
                    tag_node_name + ':VramText',
                    f"VRAM {data['vram_percent']:.1f}%  {data['vram_used_gb']:.2f} / {data['vram_total_gb']:.2f} GB"
                )
            except Exception:
                pass
        else:
            data = self._cached_data.get(tag_node_name, {})

        return {
            "image": None,
            "json": data,
            "audio": None,
        }

    def close(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        # Cleanup cached state
        with self._lock:
            self._last_disk_io.pop(tag_node_name, None)
            self._last_net_io.pop(tag_node_name, None)
            self._last_sample_time.pop(tag_node_name, None)
            self._cached_data.pop(tag_node_name, None)

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)
        return {
            "ver": self._ver,
            "pos": pos,
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = setting_dict.get("pos", [0, 0])
        dpg.set_item_pos(tag_node_name, pos)
