#!/usr/bin/env python
# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from collections import defaultdict

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node as BaseNode
from src.utils.logging import get_logger

import matplotlib
matplotlib.use('Agg')  # force non-GUI backend
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg

logger = get_logger(__name__)

# Reference amplitude for dB calculation (normalized audio range)
DB_REFERENCE = 1.0
# Minimum RMS to avoid log(0)
MIN_RMS = 1e-10
# Rolling window duration in seconds
WINDOW_SECONDS = 60


def compute_db(audio_data):
    """Compute RMS-based decibel level from audio samples.

    Args:
        audio_data (np.ndarray): Audio samples as float array.

    Returns:
        float: dB value (negative or zero for normal signals).
    """
    if audio_data is None or len(audio_data) == 0:
        return None
    rms = float(np.sqrt(np.mean(audio_data.astype(np.float64) ** 2)))
    rms = max(rms, MIN_RMS)
    return 20.0 * np.log10(rms / DB_REFERENCE)


class FactoryNode:
    node_label = 'Decibel'
    node_tag = 'Decibel'

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
        node = Node()
        node.tag_node_name = str(node_id) + ':' + self.node_tag
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_AUDIO + ':Input01Value'
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        # Create initial black texture
        black_image = np.zeros((small_window_h, small_window_w, 3))
        black_texture = node.convert_cv_to_dpg(
            black_image,
            small_window_w,
            small_window_h,
        )

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                small_window_w,
                small_window_h,
                black_texture,
                tag=node.tag_node_output01_value_name,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
                tag=node.tag_node_name,
                parent=parent,
                label=self.node_label,
                pos=pos,
        ):
            # Audio input
            with dpg.node_attribute(
                    tag=node.tag_node_input01_name,
                    attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Input Audio',
                )

            # Chart image output
            with dpg.node_attribute(
                    tag=node.tag_node_output01_name,
                    attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Performance counter output
            if use_pref_counter:
                with dpg.node_attribute(
                        tag=node.tag_node_output02_name,
                        attribute_type=dpg.mvNode_Attr_Output,
                ):
                    dpg.add_text(
                        tag=node.tag_node_output02_value_name,
                        default_value='elapsed time(ms)',
                    )

        return node


class Node(BaseNode):
    _ver = '0.0.1'

    node_label = 'Decibel'
    node_tag = 'Decibel'

    _opencv_setting_dict = None

    def __init__(self):
        # Rolling 60-second round-robin: {datetime_second: db_value}
        self.db_history = {}
        # Performance throttle: render chart at most once per second
        self.last_render_time = 0
        self.render_interval = 1.0
        self.cached_chart_image = None

    def _current_second_bucket(self):
        """Return current time truncated to the second."""
        return datetime.now().replace(microsecond=0)

    def _cleanup_old_data(self):
        """Remove entries older than WINDOW_SECONDS."""
        cutoff = datetime.now() - timedelta(seconds=WINDOW_SECONDS)
        for bucket in list(self.db_history.keys()):
            if bucket < cutoff:
                del self.db_history[bucket]

    def _render_chart(self, small_window_w, small_window_h):
        """Render a bar chart of the last 60 seconds of dB values.

        Returns:
            np.ndarray: BGR image.
        """
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)

        if not self.db_history:
            ax.text(0.5, 0.5, 'Waiting for audio signal...',
                    ha='center', va='center', transform=ax.transAxes)
            ax.set_xlim(0, WINDOW_SECONDS)
            ax.set_ylim(-100, 0)
        else:
            # Build a full 60-second window ending at the latest bucket
            latest = max(self.db_history.keys())
            buckets = [latest - timedelta(seconds=i) for i in range(WINDOW_SECONDS - 1, -1, -1)]
            db_values = [self.db_history.get(b, None) for b in buckets]

            x_pos = np.arange(WINDOW_SECONDS)
            x_labels = [b.strftime('%H:%M:%S') for b in buckets]

            # Split into valid values and gaps
            valid_mask = [v is not None for v in db_values]
            bar_values = [v if v is not None else 0.0 for v in db_values]
            colors = ['steelblue' if m else 'lightgray' for m in valid_mask]

            ax.bar(x_pos, bar_values, color=colors, width=0.8)
            ax.set_xlabel('Time (seconds)')
            ax.set_ylabel('Level (dBFS)')
            ax.set_title('Microphone decibel level (1-minute rolling window)')

            # Show only a subset of x-tick labels to avoid crowding
            tick_step = max(1, WINDOW_SECONDS // 10)
            shown_ticks = list(range(0, WINDOW_SECONDS, tick_step))
            ax.set_xticks([x_pos[i] for i in shown_ticks])
            ax.set_xticklabels([x_labels[i] for i in shown_ticks], rotation=45, ha='right')

            ax.set_xlim(-0.5, WINDOW_SECONDS - 0.5)
            ax.set_ylim(-100, 0)
            ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        image = np.asarray(canvas.buffer_rgba())[:, :, :3]
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        plt.close(fig)
        return image

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_value01_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_value02_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        if self._opencv_setting_dict is None:
            small_window_w = 240
            small_window_h = 135
            use_pref_counter = False
        else:
            small_window_w = self._opencv_setting_dict['process_width']
            small_window_h = self._opencv_setting_dict['process_height']
            use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        if use_pref_counter:
            start_time = time.monotonic()

        # Retrieve audio data from connected source
        audio_data = None
        for connection_info in connection_list:
            connection_type = connection_info[0].split(':')[2]
            if connection_type == self.TYPE_AUDIO:
                src_key = ':'.join(connection_info[0].split(':')[:2])
                audio_entry = node_audio_dict.get(src_key, None)
                if audio_entry is not None:
                    if isinstance(audio_entry, dict):
                        audio_data = audio_entry.get('data', None)
                    elif isinstance(audio_entry, (list, tuple)) and len(audio_entry) == 2:
                        audio_data = audio_entry[0]
                break

        # Compute dB and store in round-robin history
        db_value = compute_db(audio_data)
        if db_value is not None:
            bucket = self._current_second_bucket()
            self.db_history[bucket] = db_value

        # Remove data older than 60 seconds
        self._cleanup_old_data()

        # Throttle chart rendering to once per second
        current_time = time.time()
        should_render = (current_time - self.last_render_time) >= self.render_interval

        chart_image = None
        if should_render or self.cached_chart_image is None:
            try:
                chart_image = self._render_chart(small_window_w, small_window_h)
                self.cached_chart_image = chart_image
                self.last_render_time = current_time
            except Exception as e:
                logger.error(f"Error rendering decibel chart: {e}", exc_info=True)
                chart_image = self.cached_chart_image
        else:
            chart_image = self.cached_chart_image

        if use_pref_counter:
            elapsed_time = time.monotonic() - start_time
            elapsed_time = int(elapsed_time * 1000)
            try:
                dpg_set_value(output_value02_tag, str(elapsed_time).zfill(4) + 'ms')
            except Exception as e:
                logger.debug(f"Could not set performance counter value: {e}")

        if chart_image is not None:
            try:
                texture = self.convert_cv_to_dpg(
                    chart_image,
                    small_window_w,
                    small_window_h,
                )
                dpg_set_value(output_value01_tag, texture)
            except Exception as e:
                logger.debug(f"Could not set output texture: {e}")

        return {"image": chart_image, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag_node_name)

        setting_dict = {}
        setting_dict['ver'] = self._ver
        setting_dict['pos'] = pos
        return setting_dict

    def set_setting_dict(self, node_id, setting_dict):
        pass
