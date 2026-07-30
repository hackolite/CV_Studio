#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VectorField node: receives tracking JSON from a MultiObjectTracking node and
renders a vector field (arrows) on a grid overlay.

Each cell of the grid shows the average velocity of tracked objects whose
bounding box overlapped that cell.  Arrow properties:
  - direction   → motion direction
  - length      → fixed (uniform for all arrows)
  - color       → speed norm (blue=slow → green → red=fast)

Data is stored in a round-robin buffer with configurable retention:
  - Minutes  (1–60 min)
  - Hours    (1–24 h)
  - Infinite (keep full history from node creation)

A "Cell size" slider controls the grid resolution (square cells, 10–200 px).
"""
import time
from collections import deque

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node
from src.utils.logging import get_logger

logger = get_logger(__name__)

_PERIOD_MODES = ['Minutes', 'Hours', 'Infinite']
_DEFAULT_CELL_SIZE = 64
_DEFAULT_PERIOD_MODE = 'Minutes'
_DEFAULT_DURATION = 5


def _speed_to_bgr(norm_speed: float):
    """Map a normalised speed in [0, 1] to a BGR colour (blue→green→red)."""
    # Hue 120° (green/blue) → 0° (red); full saturation and brightness for visibility
    hue = int((1.0 - norm_speed) * 120)  # 0…120 → red…green
    hsv = np.array([[[hue, 255, 255]]], dtype=np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    return (int(bgr[0, 0, 0]), int(bgr[0, 0, 1]), int(bgr[0, 0, 2]))


class FactoryNode:
    node_label = 'VectorField'
    node_tag = 'VectorField'

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

        node = Node()
        node.tag_node_name = str(node_id) + ':' + node.node_tag

        # ── input ports ──────────────────────────────────────────────────────
        node.tag_node_input01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01'
        node.tag_node_input01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Input01Value'
        node.tag_node_input02_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02'
        node.tag_node_input02_value_name = node.tag_node_name + ':' + node.TYPE_JSON + ':Input02Value'

        # ── output ports ─────────────────────────────────────────────────────
        node.tag_node_output01_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01'
        node.tag_node_output01_value_name = node.tag_node_name + ':' + node.TYPE_IMAGE + ':Output01Value'
        node.tag_node_output02_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02'
        node.tag_node_output02_value_name = node.tag_node_name + ':' + node.TYPE_TIME_MS + ':Output02Value'

        node._opencv_setting_dict = opencv_setting_dict
        small_window_w = node._opencv_setting_dict['process_width']
        small_window_h = node._opencv_setting_dict['process_height']
        use_pref_counter = node._opencv_setting_dict['use_pref_counter']

        black_image = np.zeros((small_window_h, small_window_w, 3), dtype=np.uint8)
        black_texture = node.convert_cv_to_dpg(black_image, small_window_w, small_window_h)

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
            label=node.node_label,
            pos=pos,
        ):
            # Image input
            with dpg.node_attribute(
                tag=node.tag_node_input01_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input01_value_name,
                    default_value='Image',
                )

            # JSON tracker input
            with dpg.node_attribute(
                tag=node.tag_node_input02_name,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(
                    tag=node.tag_node_input02_value_name,
                    default_value='JSON Tracker',
                )

            # Image output (vector field overlay)
            with dpg.node_attribute(
                tag=node.tag_node_output01_name,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(node.tag_node_output01_value_name)

            # Cell size slider
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_int(
                    tag=node.tag_node_name + ':CellSize',
                    label='Cell size (px)',
                    width=small_window_w - 80,
                    default_value=_DEFAULT_CELL_SIZE,
                    min_value=10,
                    max_value=200,
                )

            # Period mode dropdown
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_combo(
                    tag=node.tag_node_name + ':PeriodMode',
                    label='Period mode',
                    items=_PERIOD_MODES,
                    default_value=_DEFAULT_PERIOD_MODE,
                    width=small_window_w - 100,
                )

            # Duration slider (1–60 for Minutes, 1–24 for Hours; hidden for Infinite)
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_int(
                    tag=node.tag_node_name + ':Duration',
                    label='Duration',
                    width=small_window_w - 80,
                    default_value=_DEFAULT_DURATION,
                    min_value=1,
                    max_value=60,
                )

            # Blend alpha: weight of the vector overlay vs. background image
            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dpg.add_slider_float(
                    tag=node.tag_node_name + ':BlendAlpha',
                    label='Blend Alpha',
                    width=small_window_w - 80,
                    default_value=0.85,
                    min_value=0.0,
                    max_value=1.0,
                )

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


class Node(Node):
    _ver = '0.0.1'

    node_label = 'VectorField'
    node_tag = 'VectorField'

    # Per-node position history:
    #   { node_id_str: { track_id: deque([(cx, cy, timestamp), ...]) } }
    _history = {}

    def __init__(self):
        pass

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _retention_seconds(mode: str, duration: int) -> float:
        if mode == 'Minutes':
            return duration * 60.0
        if mode == 'Hours':
            return duration * 3600.0
        return float('inf')  # Infinite

    def _prune_history(self, node_id_str: str, cutoff: float):
        """Drop history entries whose timestamp is older than *cutoff*."""
        hist = self._history.get(node_id_str, {})
        for tid in list(hist.keys()):
            dq = hist[tid]
            while dq and dq[0][4] < cutoff:
                dq.popleft()
            if not dq:
                del hist[tid]

    # ── update ────────────────────────────────────────────────────────────────

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node_name = str(node_id) + ':' + self.node_tag
        output_image_tag = tag_node_name + ':' + self.TYPE_IMAGE + ':Output01Value'
        output_time_tag = tag_node_name + ':' + self.TYPE_TIME_MS + ':Output02Value'

        small_window_w = self._opencv_setting_dict['process_width']
        small_window_h = self._opencv_setting_dict['process_height']
        use_pref_counter = self._opencv_setting_dict['use_pref_counter']

        # Read UI parameters
        cell_size = dpg_get_value(tag_node_name + ':CellSize') or _DEFAULT_CELL_SIZE
        cell_size = max(10, int(cell_size))
        period_mode = dpg_get_value(tag_node_name + ':PeriodMode') or _DEFAULT_PERIOD_MODE
        duration = dpg_get_value(tag_node_name + ':Duration') or _DEFAULT_DURATION
        duration = max(1, int(duration))
        blend_alpha = dpg_get_value(tag_node_name + ':BlendAlpha')
        if blend_alpha is None:
            blend_alpha = 0.85
        blend_alpha = float(blend_alpha)

        # Resolve input connections
        image_src = ''
        json_src = ''
        for conn in connection_list:
            conn_type = conn[0].split(':')[2]
            if conn_type == self.TYPE_IMAGE:
                image_src = ':'.join(conn[0].split(':')[:2])
            elif conn_type in (self.TYPE_JSON, 'JSON'):
                json_src = ':'.join(conn[0].split(':')[:2])

        frame = node_image_dict.get(image_src) if image_src else None
        json_data = node_result_dict.get(json_src) if json_src else None

        if use_pref_counter:
            start_time = time.monotonic()

        node_id_str = str(node_id)
        if node_id_str not in self._history:
            self._history[node_id_str] = {}
        hist = self._history[node_id_str]

        now = time.monotonic()
        retention = self._retention_seconds(period_mode, duration)
        cutoff = (now - retention) if retention != float('inf') else 0.0

        # ── update history ────────────────────────────────────────────────────
        if json_data and isinstance(json_data, dict):
            track_ids = json_data.get('track_ids', [])
            bboxes = json_data.get('bboxes', [])
            for tid, bbox in zip(track_ids, bboxes):
                x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
                if tid not in hist:
                    hist[tid] = deque()
                # Store full bbox + timestamp so all covered cells get contributions
                hist[tid].append((x1, y1, x2, y2, now))

        # ── prune old entries ─────────────────────────────────────────────────
        self._prune_history(node_id_str, cutoff)

        # ── render ────────────────────────────────────────────────────────────
        output_frame = None
        if frame is not None:
            fh, fw = frame.shape[:2]

            # Prepare display frame (resize + ensure BGR)
            if fw != small_window_w or fh != small_window_h:
                display = cv2.resize(frame, (small_window_w, small_window_h))
            else:
                display = frame.copy()
            if len(display.shape) == 2:
                display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)
            elif display.shape[2] == 4:
                display = cv2.cvtColor(display, cv2.COLOR_BGRA2BGR)

            # Scale factors from original frame coords to display coords
            scale_x = small_window_w / fw if fw > 0 else 1.0
            scale_y = small_window_h / fh if fh > 0 else 1.0

            # Grid layout
            n_cols = max(1, small_window_w // cell_size)
            n_rows = max(1, small_window_h // cell_size)

            # Accumulate velocity vectors per grid cell
            cell_vx = np.zeros((n_rows, n_cols), dtype=np.float64)
            cell_vy = np.zeros((n_rows, n_cols), dtype=np.float64)
            cell_cnt = np.zeros((n_rows, n_cols), dtype=np.int32)

            for tid, dq in hist.items():
                pts = list(dq)
                if len(pts) < 2:
                    continue
                for i in range(1, len(pts)):
                    x1p, y1p, x2p, y2p, pt = pts[i - 1]
                    x1c, y1c, x2c, y2c, ct = pts[i]
                    dt = ct - pt
                    if dt <= 1e-6:
                        continue
                    # Centre velocity in display-pixel / second
                    vx = ((x1c + x2c) - (x1p + x2p)) / 2.0 / dt * scale_x
                    vy = ((y1c + y2c) - (y1p + y2p)) / 2.0 / dt * scale_y
                    # Average bbox in display coords covers all cells it overlaps
                    ax1 = ((x1p + x1c) / 2.0) * scale_x
                    ay1 = ((y1p + y1c) / 2.0) * scale_y
                    ax2 = ((x2p + x2c) / 2.0) * scale_x
                    ay2 = ((y2p + y2c) / 2.0) * scale_y
                    col_min = max(0, int(ax1 // cell_size))
                    col_max = min(n_cols - 1, int(ax2 // cell_size))
                    row_min = max(0, int(ay1 // cell_size))
                    row_max = min(n_rows - 1, int(ay2 // cell_size))
                    for r in range(row_min, row_max + 1):
                        for c in range(col_min, col_max + 1):
                            cell_vx[r, c] += vx
                            cell_vy[r, c] += vy
                            cell_cnt[r, c] += 1

            # Build vector-field overlay
            overlay = np.zeros_like(display)
            half_cell = cell_size // 2

            valid = cell_cnt > 0
            if valid.any():
                cnt_safe = np.where(valid, cell_cnt, 1)
                avg_vx = np.where(valid, cell_vx / cnt_safe, 0.0)
                avg_vy = np.where(valid, cell_vy / cnt_safe, 0.0)
                speeds = np.sqrt(avg_vx ** 2 + avg_vy ** 2)
                max_speed = float(speeds.max())
                if max_speed < 1e-6:
                    max_speed = 1.0

                # All arrows share the same fixed length; only colour varies by speed
                arrow_len = max(4, half_cell - 2)
                arrow_thickness = 2

                for r in range(n_rows):
                    for c in range(n_cols):
                        if cell_cnt[r, c] == 0:
                            continue
                        norm_speed = speeds[r, c] / max_speed

                        cx_cell = c * cell_size + half_cell
                        cy_cell = r * cell_size + half_cell

                        vx_ = avg_vx[r, c]
                        vy_ = avg_vy[r, c]
                        spd = speeds[r, c]
                        if spd < 1e-9:
                            continue

                        # Unit direction vector; length is always arrow_len
                        nx = vx_ / spd
                        ny = vy_ / spd

                        ex = int(cx_cell + nx * arrow_len)
                        ey = int(cy_cell + ny * arrow_len)

                        color = _speed_to_bgr(norm_speed)

                        # Dark outline for contrast
                        cv2.arrowedLine(
                            overlay,
                            (cx_cell, cy_cell),
                            (ex, ey),
                            (0, 0, 0),
                            thickness=arrow_thickness + 2,
                            tipLength=0.35,
                            line_type=cv2.LINE_AA,
                        )
                        # Coloured arrow on top
                        cv2.arrowedLine(
                            overlay,
                            (cx_cell, cy_cell),
                            (ex, ey),
                            color,
                            thickness=arrow_thickness,
                            tipLength=0.35,
                            line_type=cv2.LINE_AA,
                        )

            # Draw faint grid lines on the overlay
            grid_color = (50, 50, 50)
            for c in range(n_cols + 1):
                x = c * cell_size
                if x < small_window_w:
                    cv2.line(overlay, (x, 0), (x, small_window_h - 1), grid_color, 1)
            for r in range(n_rows + 1):
                y = r * cell_size
                if y < small_window_h:
                    cv2.line(overlay, (0, y), (small_window_w - 1, y), grid_color, 1)

            # Blend with background
            if blend_alpha >= 1.0:
                output_frame = overlay
            elif blend_alpha <= 0.0:
                output_frame = display
            else:
                output_frame = cv2.addWeighted(
                    display, 1.0 - blend_alpha,
                    overlay, blend_alpha,
                    0,
                )

            texture = self.convert_cv_to_dpg(output_frame, small_window_w, small_window_h)
            dpg_set_value(output_image_tag, texture)

        if use_pref_counter and frame is not None:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            try:
                dpg_set_value(output_time_tag, str(elapsed_ms).zfill(4) + 'ms')
            except Exception:
                pass

        return {'image': output_frame, 'json': None, 'audio': None}

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def close(self, node_id):
        self._history.pop(str(node_id), None)

    # ── serialisation ─────────────────────────────────────────────────────────

    def get_setting_dict(self, node_id):
        tag_node_name = str(node_id) + ':' + self.node_tag
        try:
            pos = dpg.get_item_pos(tag_node_name)
        except Exception:
            pos = [0, 0]
        return {
            'ver': self._ver,
            'pos': pos,
            'cell_size': dpg_get_value(tag_node_name + ':CellSize') or _DEFAULT_CELL_SIZE,
            'period_mode': dpg_get_value(tag_node_name + ':PeriodMode') or _DEFAULT_PERIOD_MODE,
            'duration': dpg_get_value(tag_node_name + ':Duration') or _DEFAULT_DURATION,
            'blend_alpha': (
                dpg_get_value(tag_node_name + ':BlendAlpha')
                if dpg_get_value(tag_node_name + ':BlendAlpha') is not None
                else 0.85
            ),
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag_node_name = str(node_id) + ':' + self.node_tag
        try:
            dpg_set_value(
                tag_node_name + ':CellSize',
                int(setting_dict.get('cell_size', _DEFAULT_CELL_SIZE)),
            )
            dpg_set_value(
                tag_node_name + ':PeriodMode',
                setting_dict.get('period_mode', _DEFAULT_PERIOD_MODE),
            )
            dpg_set_value(
                tag_node_name + ':Duration',
                int(setting_dict.get('duration', _DEFAULT_DURATION)),
            )
            dpg_set_value(
                tag_node_name + ':BlendAlpha',
                float(setting_dict.get('blend_alpha', 0.85)),
            )
        except Exception:
            pass
