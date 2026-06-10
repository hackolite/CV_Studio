#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sizing Node  (System category)

Aide au dimensionnement des ressources hardware pour un pipeline CV_Studio.

L'utilisateur renseigne :
  • Résolution des flux (size)
  • Runtime cible (DeepStream / OpenVINO / OpenCV-ONNXRuntime)
  • Nombre de flux entrants
  • CPU disponibles (cores logiques)
  • GPU disponibles (count)
  • VRAM disponible (GB, NVIDIA)
  • RAM disponible (GB)
  • FPS cible
  • Modèles AI actifs (cases à cocher parmi un catalogue intégré)

La sortie est un graphique matplotlib rendu en texture DPG :
  • Barres vertes  → ressource suffisante
  • Barres rouges  → ressource insuffisante
"""

import time
import threading

import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.node_abc import DpgNodeABC
from node.basenode import Node

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_agg import FigureCanvasAgg


# Baseline FPS used for per-inference CPU cost normalisation.
# cpu_per_inf values in _MODEL_DB are expressed at this FPS level; the
# estimator scales them linearly for other FPS targets.
_BASELINE_FPS = 30.0

# ---------------------------------------------------------------------------
# Catalogue de modèles (ressources estimées par inférence)
#
# Values are *approximate* order-of-magnitude estimates derived from:
#   • Published model benchmark results (Ultralytics, OpenCV Zoo, etc.)
#   • Typical observed memory footprints with ONNX/TensorRT backends
#   • Batch-size = 1 (single image per inference call)
#   • FP32 precision unless noted
#
# vram_gb     : GPU memory to load weights (excludes activation buffers)
# ram_gb      : host RAM for weights + framework overhead (no GPU offload)
# cpu_per_inf : logical CPU cores consumed by one inference call at _BASELINE_FPS
# ---------------------------------------------------------------------------
_MODEL_DB = {
    "YOLOv8n":   {"vram_gb": 0.20, "ram_gb": 0.30, "cpu_per_inf": 0.8},
    "YOLOv8s":   {"vram_gb": 0.40, "ram_gb": 0.55, "cpu_per_inf": 1.2},
    "YOLOv8m":   {"vram_gb": 0.80, "ram_gb": 1.00, "cpu_per_inf": 2.0},
    "YOLOv8l":   {"vram_gb": 1.50, "ram_gb": 2.00, "cpu_per_inf": 3.5},
    "YOLOv8x":   {"vram_gb": 3.00, "ram_gb": 4.00, "cpu_per_inf": 5.5},
    "YOLOv5n":   {"vram_gb": 0.18, "ram_gb": 0.28, "cpu_per_inf": 0.8},
    "YOLOv5s":   {"vram_gb": 0.35, "ram_gb": 0.50, "cpu_per_inf": 1.2},
    "YOLOv5m":   {"vram_gb": 0.75, "ram_gb": 0.95, "cpu_per_inf": 2.0},
    "YOLOv5l":   {"vram_gb": 1.40, "ram_gb": 1.90, "cpu_per_inf": 3.2},
    "YOLOv5x":   {"vram_gb": 2.80, "ram_gb": 3.80, "cpu_per_inf": 5.0},
    "NanoDet":   {"vram_gb": 0.15, "ram_gb": 0.20, "cpu_per_inf": 0.6},
    "YAMNet":    {"vram_gb": 0.10, "ram_gb": 0.18, "cpu_per_inf": 0.4},
    "Custom-S":  {"vram_gb": 0.30, "ram_gb": 0.40, "cpu_per_inf": 1.5},
    "Custom-M":  {"vram_gb": 0.80, "ram_gb": 1.00, "cpu_per_inf": 3.0},
    "Custom-L":  {"vram_gb": 2.00, "ram_gb": 2.50, "cpu_per_inf": 5.0},
}

_MODEL_NAMES = list(_MODEL_DB.keys())

# Runtime multipliers applied on top of the base model costs.
#
# Rationale (relative to a CPU-only ONNXRuntime baseline at 1.0):
#   DeepStream     – GPU-accelerated pipeline: CPU drops to ~0.4×, VRAM stays at
#                    1.0× (TensorRT backend), RAM increases ~30% (GStreamer/nvbuf).
#   OpenVINO       – CPU-optimised inference: CPU ~1.2× (optimised kernels),
#                    VRAM ~0.05× (minimal GPU use), RAM ~1.2× (IE overhead).
#   OpenCV-ONNXRuntime – pure-CPU path: CPU ~2.0× (no hardware opt),
#                        VRAM ~0.05× (negligible), RAM ~1.0×.
#
# These are coarse estimates; real-world values depend on hardware, batch size,
# model architecture, and runtime version.
_RUNTIME_MULT = {
    "DeepStream":          {"cpu": 0.40, "ram": 1.30, "vram": 1.00},
    "OpenVINO":            {"cpu": 1.20, "ram": 1.20, "vram": 0.05},
    "OpenCV-ONNXRuntime":  {"cpu": 2.00, "ram": 1.00, "vram": 0.05},
}

_RUNTIMES = list(_RUNTIME_MULT.keys())

_RESOLUTIONS = [
    "SD  (640×480)",
    "HD  (1280×720)",
    "FHD (1920×1080)",
    "4K  (3840×2160)",
]

# Overhead réseau / capture par flux (RAM GB, CPU cores à 30 fps)
_STREAM_RAM_OVERHEAD = 0.12   # GB / flux
_STREAM_CPU_OVERHEAD = 0.40   # cores / flux @ 30 fps
_STREAM_VRAM_OVERHEAD = 0.04  # GB / flux (pipeline GPU)

# Overhead fixe du framework (OS + runtime)
_FIXED_RAM_OVERHEAD = 1.0   # GB
_FIXED_CPU_OVERHEAD = 0.5   # cores

# Chart dimensions (pixels)
_CHART_W = 420
_CHART_H = 280


def _compute_needs(runtime, n_streams, fps, selected_models):
    """
    Retourne un dict {"cpu": float, "ram_gb": float, "vram_gb": float}
    indiquant les ressources nécessaires.
    """
    mult = _RUNTIME_MULT[runtime]
    fps_scale = max(fps, 1) / _BASELINE_FPS

    # Overheads fixes
    need_cpu = _FIXED_CPU_OVERHEAD
    need_ram = _FIXED_RAM_OVERHEAD
    need_vram = 0.0

    # Coût par flux (capture / decode / pre-post-proc)
    need_cpu += n_streams * _STREAM_CPU_OVERHEAD * fps_scale
    need_ram += n_streams * _STREAM_RAM_OVERHEAD
    need_vram += n_streams * _STREAM_VRAM_OVERHEAD

    # Coût des modèles  (poids hébergés 1 fois + inférence sur chaque flux)
    for mname in selected_models:
        m = _MODEL_DB[mname]
        # Mémoire modèle (chargée une fois)
        need_ram += m["ram_gb"] * mult["ram"]
        need_vram += m["vram_gb"] * mult["vram"]
        # Inférence : dépend du nb de flux × fps
        need_cpu += m["cpu_per_inf"] * mult["cpu"] * n_streams * fps_scale

    return {
        "cpu": round(need_cpu, 2),
        "ram_gb": round(need_ram, 2),
        "vram_gb": round(need_vram, 2),
    }


def _render_chart(avail_cpu, avail_ram, avail_vram, need_cpu, need_ram, need_vram,
                  chart_w=_CHART_W, chart_h=_CHART_H):
    """
    Génère un graphique matplotlib sous forme de ndarray BGR (uint8).
    Barres vertes = OK, rouges = insuffisant.
    """
    fig, ax = plt.subplots(figsize=(chart_w / 100, chart_h / 100), dpi=100)
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    resources = ["CPU\n(cores)", "RAM\n(GB)", "VRAM\n(GB)"]
    avail = [avail_cpu, avail_ram, avail_vram]
    needed = [need_cpu, need_ram, need_vram]

    x = np.arange(len(resources))
    bar_w = 0.35

    # Couleurs selon suffisance
    colors_need = []
    for a, n in zip(avail, needed):
        colors_need.append('#2ecc71' if n <= a else '#e74c3c')

    bars_avail = ax.bar(x - bar_w / 2, avail, bar_w,
                        label='Disponible', color='#3498db', alpha=0.85,
                        edgecolor='white', linewidth=0.5)
    bars_need = ax.bar(x + bar_w / 2, needed, bar_w,
                       label='Nécessaire', color=colors_need,
                       edgecolor='white', linewidth=0.5)

    # Valeurs au-dessus des barres
    for bar in bars_avail:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02 * max(avail + needed + [1]),
                f'{h:.1f}', ha='center', va='bottom', color='white', fontsize=7)
    for bar, c in zip(bars_need, colors_need):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.02 * max(avail + needed + [1]),
                f'{h:.1f}', ha='center', va='bottom', color='white', fontsize=7)

    ax.set_xticks(x)
    ax.set_xticklabels(resources, color='white', fontsize=9)
    ax.tick_params(axis='y', colors='white', labelsize=8)
    ax.spines['bottom'].set_color('#555')
    ax.spines['left'].set_color('#555')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.grid(True, color='#333', linestyle='--', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.set_title('Dimensionnement des ressources', color='white', fontsize=10, pad=8)

    green_patch = mpatches.Patch(color='#2ecc71', label='Nécessaire (OK)')
    red_patch = mpatches.Patch(color='#e74c3c', label='Nécessaire (insuffisant)')
    blue_patch = mpatches.Patch(color='#3498db', label='Disponible')
    ax.legend(handles=[blue_patch, green_patch, red_patch],
              facecolor='#2a2a3e', edgecolor='#555', labelcolor='white',
              fontsize=7, loc='upper right')

    fig.tight_layout(pad=0.5)

    canvas = FigureCanvasAgg(fig)
    canvas.draw()
    buf = canvas.buffer_rgba()
    img_rgba = np.frombuffer(buf, dtype=np.uint8).reshape(chart_h, chart_w, 4)
    img_bgr = img_rgba[:, :, :3][:, :, ::-1].copy()
    plt.close(fig)
    return img_bgr


class FactoryNode:
    node_label = 'Sizing'
    node_tag = 'Sizing'

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
        node._opencv_setting_dict = opencv_setting_dict or {}
        tag = node.tag_node_name

        # Pre-render blank chart
        blank = np.zeros((_CHART_H, _CHART_W, 3), dtype=np.uint8)
        blank_tex = node.convert_cv_to_dpg(blank, _CHART_W, _CHART_H)

        node.tag_chart_texture = tag + ':ChartTexture'

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                _CHART_W, _CHART_H, blank_tex,
                tag=node.tag_chart_texture,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(
            tag=tag,
            parent=parent,
            label=node.node_label,
            pos=pos,
        ):
            # ---- Configuration ----
            with dpg.node_attribute(
                tag=tag + ':Static',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_spacer(height=2)

                # Resolution
                dpg.add_combo(
                    tag=tag + ':Resolution',
                    label='Résolution',
                    items=_RESOLUTIONS,
                    default_value=_RESOLUTIONS[1],
                    width=220,
                )

                # Runtime
                dpg.add_combo(
                    tag=tag + ':Runtime',
                    label='Runtime',
                    items=_RUNTIMES,
                    default_value=_RUNTIMES[0],
                    width=220,
                )

                dpg.add_spacer(height=4)

                # Input streams
                dpg.add_input_int(
                    tag=tag + ':Streams',
                    label='Flux entrants',
                    default_value=1,
                    min_value=1,
                    max_value=64,
                    width=100,
                )

                # Target FPS
                dpg.add_input_int(
                    tag=tag + ':FPS',
                    label='FPS cible',
                    default_value=30,
                    min_value=1,
                    max_value=120,
                    width=100,
                )

                dpg.add_spacer(height=4)
                dpg.add_text('-- Ressources disponibles --', color=(200, 200, 200))

                # CPU
                dpg.add_input_int(
                    tag=tag + ':AvailCPU',
                    label='CPU cores',
                    default_value=8,
                    min_value=1,
                    max_value=256,
                    width=100,
                )

                # RAM
                dpg.add_input_float(
                    tag=tag + ':AvailRAM',
                    label='RAM (GB)',
                    default_value=16.0,
                    min_value=0.5,
                    max_value=2048.0,
                    width=100,
                    format='%.1f',
                )

                # GPU
                dpg.add_input_int(
                    tag=tag + ':AvailGPU',
                    label='GPU count',
                    default_value=1,
                    min_value=0,
                    max_value=16,
                    width=100,
                )

                # VRAM
                dpg.add_input_float(
                    tag=tag + ':AvailVRAM',
                    label='VRAM (GB)',
                    default_value=8.0,
                    min_value=0.0,
                    max_value=256.0,
                    width=100,
                    format='%.1f',
                )

                dpg.add_spacer(height=4)
                dpg.add_text('-- Modèles AI actifs --', color=(200, 200, 200))

                # Model checkboxes
                for mname in _MODEL_NAMES:
                    dpg.add_checkbox(
                        tag=tag + ':Model:' + mname,
                        label=mname,
                        default_value=False,
                    )

                dpg.add_spacer(height=6)

                # Compute button
                dpg.add_button(
                    tag=tag + ':BtnCompute',
                    label='  ▶  Calculer  ',
                    width=220,
                    callback=_callback_compute,
                    user_data=node,
                )

                dpg.add_spacer(height=4)

                # Status / summary text
                dpg.add_text(
                    tag=tag + ':Status',
                    default_value='Configurer puis cliquer Calculer.',
                    color=(180, 180, 180),
                    wrap=220,
                )

                dpg.add_spacer(height=4)

            # ---- Chart image output ----
            with dpg.node_attribute(
                tag=tag + ':ChartAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_image(node.tag_chart_texture)

        return node


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------

def _callback_compute(sender, data, user_data):
    node = user_data
    threading.Thread(target=_do_compute, args=(node,), daemon=True).start()


def _do_compute(node):
    tag = node.tag_node_name
    try:
        runtime = dpg_get_value(tag + ':Runtime') or _RUNTIMES[0]
        n_streams = max(1, int(dpg_get_value(tag + ':Streams') or 1))
        fps = max(1, int(dpg_get_value(tag + ':FPS') or 30))
        avail_cpu = max(1.0, float(dpg_get_value(tag + ':AvailCPU') or 8))
        avail_ram = max(0.1, float(dpg_get_value(tag + ':AvailRAM') or 16.0))
        avail_gpu = max(0, int(dpg_get_value(tag + ':AvailGPU') or 1))
        avail_vram = max(0.0, float(dpg_get_value(tag + ':AvailVRAM') or 8.0))

        # If no GPU available, effective VRAM = 0
        if avail_gpu == 0:
            avail_vram = 0.0

        selected_models = [
            mname for mname in _MODEL_NAMES
            if dpg_get_value(tag + ':Model:' + mname)
        ]

        needs = _compute_needs(runtime, n_streams, fps, selected_models)
        need_cpu = needs["cpu"]
        need_ram = needs["ram_gb"]
        need_vram = needs["vram_gb"]

        # Render chart
        chart_img = _render_chart(
            avail_cpu, avail_ram, avail_vram,
            need_cpu, need_ram, need_vram,
        )

        # Update texture
        tex_data = node.convert_cv_to_dpg(chart_img, _CHART_W, _CHART_H)
        try:
            dpg.set_value(node.tag_chart_texture, tex_data)
        except Exception:
            pass

        # Build status summary
        warnings = []
        if need_cpu > avail_cpu:
            warnings.append(f"⚠ CPU : besoin {need_cpu:.1f} cores > {avail_cpu:.0f}")
        if need_ram > avail_ram:
            warnings.append(f"⚠ RAM : besoin {need_ram:.1f} GB > {avail_ram:.1f} GB")
        if need_vram > avail_vram:
            if avail_gpu == 0:
                warnings.append(f"⚠ VRAM : besoin {need_vram:.1f} GB mais aucun GPU")
            else:
                warnings.append(f"⚠ VRAM : besoin {need_vram:.1f} GB > {avail_vram:.1f} GB")

        if warnings:
            status = "MANQUE DE RESSOURCES :\n" + "\n".join(warnings)
        else:
            status = (
                f"✓ OK  CPU:{need_cpu:.1f}/{avail_cpu:.0f}  "
                f"RAM:{need_ram:.1f}/{avail_ram:.1f}GB  "
                f"VRAM:{need_vram:.1f}/{avail_vram:.1f}GB"
            )

        dpg_set_value(tag + ':Status', status)

    except Exception as exc:
        try:
            dpg_set_value(tag + ':Status', f'Erreur: {exc}')
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Node class
# ---------------------------------------------------------------------------

class _Node(Node):
    _ver = '0.0.1'

    node_label = 'Sizing'
    node_tag = 'Sizing'

    _opencv_setting_dict = None
    tag_chart_texture = ''

    def __init__(self):
        pass

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        # Sizing is a purely interactive node – no per-frame computation needed.
        return {"image": None, "json": None, "audio": None}

    def close(self, node_id):
        pass

    def get_setting_dict(self, node_id):
        tag = str(node_id) + ':' + self.node_tag
        pos = dpg.get_item_pos(tag)

        model_states = {
            mname: bool(dpg_get_value(tag + ':Model:' + mname))
            for mname in _MODEL_NAMES
        }
        return {
            "ver": self._ver,
            "pos": pos,
            "resolution": dpg_get_value(tag + ':Resolution') or _RESOLUTIONS[1],
            "runtime": dpg_get_value(tag + ':Runtime') or _RUNTIMES[0],
            "streams": int(dpg_get_value(tag + ':Streams') or 1),
            "fps": int(dpg_get_value(tag + ':FPS') or 30),
            "avail_cpu": int(dpg_get_value(tag + ':AvailCPU') or 8),
            "avail_ram": float(dpg_get_value(tag + ':AvailRAM') or 16.0),
            "avail_gpu": int(dpg_get_value(tag + ':AvailGPU') or 1),
            "avail_vram": float(dpg_get_value(tag + ':AvailVRAM') or 8.0),
            "models": model_states,
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag = str(node_id) + ':' + self.node_tag
        pos = setting_dict.get("pos", [0, 0])
        dpg.set_item_pos(tag, pos)

        try:
            dpg.set_value(tag + ':Resolution',
                          setting_dict.get("resolution", _RESOLUTIONS[1]))
            dpg.set_value(tag + ':Runtime',
                          setting_dict.get("runtime", _RUNTIMES[0]))
            dpg.set_value(tag + ':Streams', setting_dict.get("streams", 1))
            dpg.set_value(tag + ':FPS', setting_dict.get("fps", 30))
            dpg.set_value(tag + ':AvailCPU', setting_dict.get("avail_cpu", 8))
            dpg.set_value(tag + ':AvailRAM', setting_dict.get("avail_ram", 16.0))
            dpg.set_value(tag + ':AvailGPU', setting_dict.get("avail_gpu", 1))
            dpg.set_value(tag + ':AvailVRAM', setting_dict.get("avail_vram", 8.0))
            for mname, state in setting_dict.get("models", {}).items():
                if mname in _MODEL_NAMES:
                    dpg.set_value(tag + ':Model:' + mname, bool(state))
        except Exception:
            pass
