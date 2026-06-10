#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Sizing Node  (System category)

Aide au dimensionnement des ressources hardware pour un pipeline CV_Studio.

L'utilisateur renseigne :
  • Résolution des flux (size)
  • Runtime cible (DeepStream / OpenVINO / OpenCV-ONNXRuntime)
  • GPU cible (sélectionné dans le catalogue — détermine automatiquement la VRAM)
  • CPU disponibles (cores logiques)
  • RAM disponible (GB, par créneaux de 8 GB)
  • FPS cible

Le bouton "Scan Éditeur" détecte automatiquement :
  • Modèles AI actifs (nœuds VisionModel / AudioModel présents dans l'éditeur)
  • Nombre de flux entrants (nœuds Input présents dans l'éditeur)
  • Nœuds VisionProcess et AudioProcess (overhead de traitement)

La sortie est un graphique matplotlib rendu en texture DPG :
  • Barres vertes  → ressource suffisante
  • Barres rouges  → ressource insuffisante
"""

import threading
from collections import Counter
import math

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
_BASELINE_FPS = 30.0

# ---------------------------------------------------------------------------
# Catalogue GPU  (VRAM réelle, par créneaux constructeur)
# ---------------------------------------------------------------------------
_GPU_CATALOG = {
    # tflops: FP32 shader performance (TFLOPS) – indicatif pour l'inférence
    "RTX 5090":          {"vram_gb": 32,  "tflops": 209.0},
    "RTX 5080":          {"vram_gb": 16,  "tflops": 137.0},
    "RTX 5070 Ti":       {"vram_gb": 16,  "tflops": 103.0},
    "RTX 5070":          {"vram_gb": 12,  "tflops":  77.0},
    "RTX 5060 Ti":       {"vram_gb": 16,  "tflops":  55.0},
    "RTX 5060":          {"vram_gb":  8,  "tflops":  42.0},
    "RTX 4090":          {"vram_gb": 24,  "tflops":  82.6},
    "RTX 4080 Super":    {"vram_gb": 16,  "tflops":  52.2},
    "RTX 4080":          {"vram_gb": 16,  "tflops":  48.7},
    "RTX 4070 Ti Super": {"vram_gb": 16,  "tflops":  44.1},
    "RTX 4070 Ti":       {"vram_gb": 12,  "tflops":  40.1},
    "RTX 4070 Super":    {"vram_gb": 12,  "tflops":  35.5},
    "RTX 4070":          {"vram_gb": 12,  "tflops":  29.1},
    "RTX 4060 Ti":       {"vram_gb": 16,  "tflops":  22.1},
    "RTX 4060":          {"vram_gb":  8,  "tflops":  15.1},
    "RTX 3090 Ti":       {"vram_gb": 24,  "tflops":  40.0},
    "RTX 3090":          {"vram_gb": 24,  "tflops":  35.6},
    "RTX 3080 Ti":       {"vram_gb": 12,  "tflops":  34.1},
    "RTX 3080":          {"vram_gb": 10,  "tflops":  29.8},
    "RTX 3070 Ti":       {"vram_gb":  8,  "tflops":  21.7},
    "RTX 3070":          {"vram_gb":  8,  "tflops":  20.3},
    "RTX 3060 Ti":       {"vram_gb":  8,  "tflops":  16.2},
    "RTX 3060":          {"vram_gb": 12,  "tflops":  12.7},
    "CPU only":          {"vram_gb":  0,  "tflops":   0.0},
}

_GPU_NAMES = list(_GPU_CATALOG.keys())

# ---------------------------------------------------------------------------
# Coûts par type de nœud AI détecté dans l'éditeur
#
# vram_gb     : VRAM pour charger les poids (une fois par nœud)
# ram_gb      : RAM hôte pour les poids + overhead framework
# cpu_per_inf : cœurs logiques consommés par inférence à _BASELINE_FPS
# ---------------------------------------------------------------------------
_NODE_AI_COSTS = {
    # VisionModel nodes
    "ObjectDetection":          {"vram_gb": 0.50, "ram_gb": 0.60, "cpu_per_inf": 1.5},
    "Classification":           {"vram_gb": 0.30, "ram_gb": 0.40, "cpu_per_inf": 1.0},
    "FaceDetection":            {"vram_gb": 0.25, "ram_gb": 0.35, "cpu_per_inf": 0.8},
    "PoseEstimation":           {"vram_gb": 0.50, "ram_gb": 0.70, "cpu_per_inf": 1.5},
    "SemanticSegmentation":     {"vram_gb": 1.00, "ram_gb": 1.50, "cpu_per_inf": 2.5},
    "MonocularDepthEstimation": {"vram_gb": 0.80, "ram_gb": 1.00, "cpu_per_inf": 2.0},
    "LLIE":                     {"vram_gb": 0.50, "ram_gb": 0.60, "cpu_per_inf": 1.2},
    "OnlineTraining":           {"vram_gb": 1.50, "ram_gb": 2.00, "cpu_per_inf": 4.0},
    # AudioModel nodes
    "AudioClassification":      {"vram_gb": 0.10, "ram_gb": 0.18, "cpu_per_inf": 0.4},
}

# Node tags that represent video/audio input flux
_INPUT_NODE_TAGS = frozenset({
    "Video", "Webcam", "RTSP", "HLS", "YouTube", "WebRTC", "Api", "Microphone",
})

# Node tags in the VisionProcess category (ProcessNode folder)
_VISION_PROCESS_TAGS = frozenset({
    "AdaptiveThreshold", "ApplyColorMap", "BilateralFilter", "Blur", "Brightness",
    "CLAHE", "Canny", "ColorSpace", "Contrast", "Crop", "CropMonitor",
    "EqualizeHist", "Flip", "GammaCorrection", "Grayscale", "IlluminationCorrect",
    "ImageAlphaBlend", "KernelSharpen", "Morphology", "NLMDenoise",
    "OmnidirectionalViewer", "Resize", "SimpleFilter", "Threshold",
    "UnsharpMask", "Zoom",
})

# Node tags in the AudioProcess category (AudioProcessNode folder)
_AUDIO_PROCESS_TAGS = frozenset({
    "BandPassFilter", "Compressor", "Decibel", "Equalizer",
    "NoiseGate", "Normalize", "Resample", "Spectrogram",
})

# Resource overhead added per VisionProcess / AudioProcess node present
_VISION_PROC_CPU = 0.10   # CPU cores per vision process node
_VISION_PROC_RAM = 0.05   # GB RAM per vision process node
_AUDIO_PROC_CPU  = 0.05   # CPU cores per audio process node
_AUDIO_PROC_RAM  = 0.03   # GB RAM per audio process node

# ---------------------------------------------------------------------------
# Catalogue de modèles (ressources estimées par inférence)
# (conservé pour compatibilité avec les fichiers sauvegardés existants)
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

# GFLOPs par inférence à 640×640 (@ batch=1, valeurs indicatives)
_MODEL_GFLOPS = {
    "YOLOv8n":  8.7,
    "YOLOv8s":  28.6,
    "YOLOv8m":  78.9,
    "YOLOv8l":  165.2,
    "YOLOv8x":  257.8,
    "YOLOv5n":  4.5,
    "YOLOv5s":  16.5,
    "YOLOv5m":  49.0,
    "YOLOv5l":  109.1,
    "YOLOv5x":  205.7,
    "NanoDet":  0.72,   # NanoDet-Plus-m @ 416×416 (not 640 – lighter model)
    "YAMNet":   1.0,    # audio, ~1 GFLOP
    "Custom-S": 30.0,
    "Custom-M": 80.0,
    "Custom-L": 200.0,
}

# Runtime multipliers applied on top of the base model costs.
_RUNTIME_MULT = {
    "DeepStream":          {"cpu": 0.40, "ram": 1.30, "vram": 1.00},
    "OpenVINO":            {"cpu": 1.20, "ram": 1.20, "vram": 0.05},
    "OpenCV-ONNXRuntime":  {"cpu": 2.00, "ram": 1.00, "vram": 0.05},
}

_RUNTIMES = list(_RUNTIME_MULT.keys())

_RESOLUTIONS = [
    "AI  (300×300)",
    "AI  (416×416)",
    "SD  (640×480)",
    "HD  (1280×720)",
    "FHD (1920×1080)",
    "4K  (3840×2160)",
]
_RESOLUTION_DEFAULT = "HD  (1280×720)"

# RAM slots disponibles (créneaux de 8 GB)
_RAM_SLOTS = [f"{n} GB" for n in [8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384, 512]]
_RAM_DEFAULT = "32 GB"

# Overhead réseau / capture par flux (RAM GB, CPU cores à 30 fps)
_STREAM_RAM_OVERHEAD  = 0.12   # GB / flux
_STREAM_CPU_OVERHEAD  = 0.40   # cores / flux @ 30 fps
_STREAM_VRAM_OVERHEAD = 0.04   # GB / flux (pipeline GPU)

# Overhead fixe du framework (OS + runtime)
_FIXED_RAM_OVERHEAD = 1.0   # GB
_FIXED_CPU_OVERHEAD = 0.5   # cores

# Chart dimensions (pixels)
_CHART_W = 420
_CHART_H = 280


def _build_gflops_info() -> str:
    """Build a compact multi-line string listing model GFLOPs."""
    lines = []
    for name, gf in _MODEL_GFLOPS.items():
        if gf < 1.0:
            lines.append(f"  {name}: {gf:.2f} GF")
        else:
            lines.append(f"  {name}: {gf:.0f} GF")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Editor introspection helpers
# ---------------------------------------------------------------------------

def _get_node_editor():
    """Retrieve the DpgNodeEditor singleton from the main module."""
    import sys
    main_module = sys.modules.get("__main__") or sys.modules.get("main")
    if main_module and hasattr(main_module, "_node_editor_ref"):
        return main_module._node_editor_ref
    return None


def _scan_editor_nodes():
    """
    Scan the live editor and return a summary dict:
      {
        "ai_nodes":        [(node_id_name, node_tag), ...],  # AI model nodes
        "n_streams":       int,                              # input flux count
        "n_vision_proc":   int,                              # VisionProcess count
        "n_audio_proc":    int,                              # AudioProcess count
      }
    """
    editor = _get_node_editor()
    result = {
        "ai_nodes": [],
        "n_streams": 0,
        "n_vision_proc": 0,
        "n_audio_proc": 0,
    }
    if editor is None:
        return result

    for node_id_name in editor._node_list:
        if ":" not in node_id_name:
            continue
        _, node_tag = node_id_name.split(":", 1)
        if node_tag in _NODE_AI_COSTS:
            result["ai_nodes"].append((node_id_name, node_tag))
        elif node_tag in _INPUT_NODE_TAGS:
            result["n_streams"] += 1
        elif node_tag in _VISION_PROCESS_TAGS:
            result["n_vision_proc"] += 1
        elif node_tag in _AUDIO_PROCESS_TAGS:
            result["n_audio_proc"] += 1

    return result


def _ram_slot_to_gb(slot_str: str) -> float:
    """Convert a RAM slot string like '32 GB' to a float."""
    try:
        return float(slot_str.replace("GB", "").strip())
    except ValueError:
        return 32.0


def _ceil8(value: float) -> int:
    """Round value up to the nearest multiple of 8."""
    return int(math.ceil(value / 8.0)) * 8


def _compute_needs(runtime, n_streams, fps, ai_node_tags,
                   n_vision_proc=0, n_audio_proc=0):
    """
    Retourne un dict {"cpu": float, "ram_gb": float, "vram_gb": float}
    indiquant les ressources nécessaires.

    ai_node_tags : list of node_tag strings (e.g. ["ObjectDetection", "AudioClassification"])
    """
    mult = _RUNTIME_MULT[runtime]
    fps_scale = max(fps, 1) / _BASELINE_FPS

    # Overheads fixes
    need_cpu  = _FIXED_CPU_OVERHEAD
    need_ram  = _FIXED_RAM_OVERHEAD
    need_vram = 0.0

    # Coût par flux (capture / decode)
    need_cpu  += n_streams * _STREAM_CPU_OVERHEAD * fps_scale
    need_ram  += n_streams * _STREAM_RAM_OVERHEAD
    need_vram += n_streams * _STREAM_VRAM_OVERHEAD

    # Overhead VisionProcess et AudioProcess
    need_cpu += n_vision_proc * _VISION_PROC_CPU * fps_scale
    need_ram += n_vision_proc * _VISION_PROC_RAM
    need_cpu += n_audio_proc * _AUDIO_PROC_CPU
    need_ram += n_audio_proc * _AUDIO_PROC_RAM

    # Coût des modèles AI (poids chargés 1 fois + inférence sur chaque flux)
    for tag in ai_node_tags:
        m = _NODE_AI_COSTS.get(tag)
        if m is None:
            continue
        need_ram  += m["ram_gb"] * mult["ram"]
        need_vram += m["vram_gb"] * mult["vram"]
        need_cpu  += m["cpu_per_inf"] * mult["cpu"] * n_streams * fps_scale

    return {
        "cpu":     round(need_cpu, 2),
        "ram_gb":  round(need_ram, 2),
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
                    default_value=_RESOLUTION_DEFAULT,  # HD
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

                # Input streams (read-only – updated by Scan)
                dpg.add_text(
                    tag=tag + ':StreamsDisplay',
                    default_value='Flux entrants : – (scan requis)',
                    color=(160, 220, 255),
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

                # RAM (créneaux de 8 GB)
                dpg.add_combo(
                    tag=tag + ':AvailRAM',
                    label='RAM',
                    items=_RAM_SLOTS,
                    default_value=_RAM_DEFAULT,
                    width=130,
                )

                dpg.add_spacer(height=4)
                dpg.add_text('-- GPU cible --', color=(200, 200, 200))

                # GPU model selector → auto-sets VRAM
                dpg.add_combo(
                    tag=tag + ':GPU',
                    label='Modèle GPU',
                    items=_GPU_NAMES,
                    default_value=_GPU_NAMES[0],
                    width=220,
                    callback=_callback_gpu_change,
                    user_data=tag,
                )

                # VRAM (read-only display, driven by GPU picker)
                dpg.add_text(
                    tag=tag + ':VRAMLabel',
                    default_value=(
                        f"VRAM : {_GPU_CATALOG[_GPU_NAMES[0]]['vram_gb']} GB"
                        f"  |  FP32 : {_GPU_CATALOG[_GPU_NAMES[0]].get('tflops', 0):.1f} TFLOPS"
                    ),
                    color=(160, 220, 255),
                )

                dpg.add_spacer(height=4)
                dpg.add_text('-- Modèles AI actifs --', color=(200, 200, 200))

                # Read-only display of editor-scanned AI nodes
                dpg.add_text(
                    tag=tag + ':AINodesList',
                    default_value='(cliquer Scan & Calculer)',
                    color=(180, 180, 180),
                    wrap=220,
                )

                dpg.add_spacer(height=4)

                # Combined Scan + Compute button
                dpg.add_button(
                    tag=tag + ':BtnScanCompute',
                    label='  🔍▶  Scan & Calculer  ',
                    width=220,
                    callback=_callback_scan_and_compute,
                    user_data=node,
                )

                dpg.add_spacer(height=4)

                # Status / summary text
                dpg.add_text(
                    tag=tag + ':Status',
                    default_value='Cliquer Scan & Calculer pour analyser.',
                    color=(180, 180, 180),
                    wrap=220,
                )

                dpg.add_spacer(height=6)
                dpg.add_text('-- GFLOPs modèles (indicatif) --', color=(200, 200, 200))
                dpg.add_text(
                    _build_gflops_info(),
                    color=(170, 210, 170),
                    wrap=220,
                )

                dpg.add_spacer(height=6)
                dpg.add_text('-- NVDEC & No-Copy --', color=(200, 200, 200))
                dpg.add_text(
                    "NVDEC : décodeur HW H.264/HEVC/AV1\n"
                    "intégré au GPU (Ampere+ : 2 moteurs).\n"
                    "Offloade le CPU du décodage vidéo.\n"
                    "\n"
                    "No-Copy (zero-copy) : avec DeepStream\n"
                    "ou GStreamer + nvvideoconvert, les\n"
                    "frames restent en VRAM (NvBufSurface)\n"
                    "→ aucun transfert PCIe CPU↔GPU.",
                    color=(210, 200, 170),
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
# Callbacks
# ---------------------------------------------------------------------------

def _callback_gpu_change(sender, app_data, user_data):
    """Update the VRAM/TFLOPS label when the GPU combo changes."""
    tag = user_data
    gpu_name = app_data or _GPU_NAMES[0]
    info = _GPU_CATALOG.get(gpu_name, {})
    vram = info.get("vram_gb", 0)
    tflops = info.get("tflops", 0.0)
    label = (
        f"VRAM : {vram} GB  |  FP32 : {tflops:.1f} TFLOPS"
        if tflops > 0 else
        f"VRAM : {vram} GB  (CPU only)"
    )
    try:
        dpg.set_value(tag + ':VRAMLabel', label)
    except Exception:
        pass


def _callback_scan_and_compute(sender, data, user_data):
    node = user_data
    threading.Thread(target=_do_scan_and_compute, args=(node,), daemon=True).start()


def _do_scan_and_compute(node):
    tag = node.tag_node_name
    try:
        # ---- Scan ----
        scan = _scan_editor_nodes()
        ai_tags = [t for _, t in scan["ai_nodes"]]
        n_streams = scan["n_streams"]
        n_vp = scan["n_vision_proc"]
        n_ap = scan["n_audio_proc"]

        # Update streams read-only display
        dpg_set_value(
            tag + ':StreamsDisplay',
            f'Flux entrants : {n_streams}',
        )

        # Build AI nodes display
        if ai_tags:
            counts = Counter(ai_tags)
            lines = [f"  • {t} ×{cnt}" for t, cnt in counts.items()]
            summary = "\n".join(lines)
        else:
            summary = "(aucun modèle AI détecté)"

        extra = []
        if n_vp:
            extra.append(f"VisionProcess : {n_vp} nœuds")
        if n_ap:
            extra.append(f"AudioProcess  : {n_ap} nœuds")
        if extra:
            summary += "\n" + "\n".join(extra)

        dpg_set_value(tag + ':AINodesList', summary)

        # ---- Compute ----
        runtime = dpg_get_value(tag + ':Runtime') or _RUNTIMES[0]
        fps = max(1, int(dpg_get_value(tag + ':FPS') or 30))
        avail_cpu = max(1.0, float(dpg_get_value(tag + ':AvailCPU') or 8))
        avail_ram = _ram_slot_to_gb(dpg_get_value(tag + ':AvailRAM') or _RAM_DEFAULT)

        gpu_name = dpg_get_value(tag + ':GPU') or _GPU_NAMES[0]
        avail_vram = float(_GPU_CATALOG.get(gpu_name, {}).get("vram_gb", 0))

        needs = _compute_needs(
            runtime, n_streams, fps, ai_tags,
            n_vision_proc=n_vp,
            n_audio_proc=n_ap,
        )
        need_cpu  = needs["cpu"]
        need_ram  = needs["ram_gb"]
        need_vram = needs["vram_gb"]

        rec_ram_slot  = _ceil8(need_ram)
        rec_vram_slot = _ceil8(need_vram)

        chart_img = _render_chart(
            avail_cpu, avail_ram, avail_vram,
            need_cpu, need_ram, need_vram,
        )

        tex_data = node.convert_cv_to_dpg(chart_img, _CHART_W, _CHART_H)
        try:
            dpg.set_value(node.tag_chart_texture, tex_data)
        except Exception:
            pass

        warnings = []
        if need_cpu > avail_cpu:
            warnings.append(f"⚠ CPU : besoin {need_cpu:.1f} cores > {avail_cpu:.0f}")
        if need_ram > avail_ram:
            warnings.append(
                f"⚠ RAM : besoin ≥{rec_ram_slot} GB (calculé {need_ram:.1f} GB) "
                f"> disponible {avail_ram:.0f} GB"
            )
        if need_vram > avail_vram:
            if avail_vram == 0:
                warnings.append(f"⚠ VRAM : besoin ≥{rec_vram_slot} GB mais CPU only")
            else:
                warnings.append(
                    f"⚠ VRAM : besoin ≥{rec_vram_slot} GB (calculé {need_vram:.1f} GB) "
                    f"> {gpu_name} ({avail_vram:.0f} GB)"
                )

        if warnings:
            status = "MANQUE DE RESSOURCES :\n" + "\n".join(warnings)
        else:
            status = (
                f"✓ OK  CPU:{need_cpu:.1f}/{avail_cpu:.0f}  "
                f"RAM:{rec_ram_slot}/{avail_ram:.0f}GB  "
                f"VRAM:{rec_vram_slot}/{avail_vram:.0f}GB ({gpu_name})"
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
    _ver = '0.0.2'

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

        return {
            "ver": self._ver,
            "pos": pos,
            "resolution": dpg_get_value(tag + ':Resolution') or _RESOLUTION_DEFAULT,
            "runtime": dpg_get_value(tag + ':Runtime') or _RUNTIMES[0],
            "fps": int(dpg_get_value(tag + ':FPS') or 30),
            "avail_cpu": int(dpg_get_value(tag + ':AvailCPU') or 8),
            "avail_ram": dpg_get_value(tag + ':AvailRAM') or _RAM_DEFAULT,
            "gpu": dpg_get_value(tag + ':GPU') or _GPU_NAMES[0],
        }

    def set_setting_dict(self, node_id, setting_dict):
        tag = str(node_id) + ':' + self.node_tag
        pos = setting_dict.get("pos", [0, 0])
        dpg.set_item_pos(tag, pos)

        try:
            res_val = setting_dict.get("resolution", _RESOLUTION_DEFAULT)
            if res_val not in _RESOLUTIONS:
                res_val = _RESOLUTION_DEFAULT
            dpg.set_value(tag + ':Resolution', res_val)
            dpg.set_value(tag + ':Runtime',
                          setting_dict.get("runtime", _RUNTIMES[0]))
            dpg.set_value(tag + ':FPS', setting_dict.get("fps", 30))
            dpg.set_value(tag + ':AvailCPU', setting_dict.get("avail_cpu", 8))

            # RAM slot – migrate old float value to nearest 8-GB slot string
            ram_val = setting_dict.get("avail_ram", _RAM_DEFAULT)
            if isinstance(ram_val, (int, float)):
                ram_val = f"{_ceil8(float(ram_val))} GB"
            if ram_val not in _RAM_SLOTS:
                ram_val = _RAM_DEFAULT
            dpg.set_value(tag + ':AvailRAM', ram_val)

            # GPU model
            gpu_val = setting_dict.get("gpu", _GPU_NAMES[0])
            if gpu_val not in _GPU_CATALOG:
                gpu_val = _GPU_NAMES[0]
            dpg.set_value(tag + ':GPU', gpu_val)
            info = _GPU_CATALOG[gpu_val]
            vram = info["vram_gb"]
            tflops = info.get("tflops", 0.0)
            label = (
                f"VRAM : {vram} GB  |  FP32 : {tflops:.1f} TFLOPS"
                if tflops > 0 else
                f"VRAM : {vram} GB  (CPU only)"
            )
            dpg.set_value(tag + ':VRAMLabel', label)

        except Exception:
            pass
