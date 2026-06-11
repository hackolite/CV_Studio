#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copernicus Satellite Map Node  (Map category)

Fetches Sentinel-2 (or Sentinel-1) satellite imagery from the Copernicus Data
Space Ecosystem (CDSE) Process API, with:

  • Dynamic band slots (add / remove — same UI pattern as ImageConcat)
  • Band-formula field:  e.g. ``(B08 - B04) / (B08 + B04)``  →  NDVI
  • Intelligent disk cache at 1 km × 1 km tile granularity
    – tiles are stored as ``~/.cv_studio/copernicus_tiles/<key>.npy``
    – on each new request only missing tiles are downloaded from CDSE
  • Colormap rendering with per-formula default (NDVI → RdYlGn, etc.)
  • Maximum zoom: the display is cropped / rendered at full resolution with no
    unnecessary down-sampling.

Credentials are read from ``~/.cv_studio/copernicus_credentials.json``
(written by the companion *Settings* node in the System category).
"""

import datetime
import hashlib
import json
import math
import os
import re
import threading
import time
import traceback

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

from node_editor.util import dpg_get_value, dpg_set_value
from node.basenode import Node

# ---------------------------------------------------------------------------
# Optional heavy imports — gracefully degraded if not installed
# ---------------------------------------------------------------------------
try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

try:
    import tifffile as _tifffile
    _HAS_TIFFFILE = True
except ImportError:
    _HAS_TIFFFILE = False

try:
    import matplotlib.cm as _mcm
    _HAS_MPL = True
except ImportError:
    _HAS_MPL = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# CDSE OAuth2 + Process API endpoints
_TOKEN_URL   = ("https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
                "/protocol/openid-connect/token")
_PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"

# Tile size in decimal degrees (≈ 1 km at the equator)
_TILE_DEG   = 0.009
# Pixel size of each downloaded tile
_TILE_PX    = 128
# Maximum tiles rendered in the display image (both axes)
_MAX_TILES  = 20   # → maximum 20×20 km² display area

# Default display resolution (pixels)
_DISPLAY_W  = 512
_DISPLAY_H  = 512

# Sentinel-2 L2A bands available in CDSE
_S2_BANDS = [
    "B01", "B02", "B03", "B04", "B05", "B06",
    "B07", "B08", "B8A", "B09", "B11", "B12",
]
_S1_BANDS = ["VV", "VH"]

_SOURCES = {
    "Sentinel-2 L2A": {"cdse_id": "sentinel-2-l2a",  "bands": _S2_BANDS},
    "Sentinel-2 L1C": {"cdse_id": "sentinel-2-l1c",  "bands": _S2_BANDS},
    "Sentinel-1 GRD": {"cdse_id": "sentinel-1-grd",   "bands": _S1_BANDS},
}
_SOURCE_NAMES = list(_SOURCES.keys())

_COLORMAPS = [
    "RdYlGn", "viridis", "plasma", "inferno", "magma",
    "gray", "jet", "coolwarm", "terrain",
]

# Per-formula keyword → default colormap heuristic
_FORMULA_CMAP_HINTS = {
    "ndvi": "RdYlGn",
    "ndwi": "Blues",
    "ndsi": "cool",
    "evi":  "YlGn",
}


def _last_month_dates() -> tuple:
    """Return ``(date_from, date_to)`` as ISO-format strings (YYYY-MM-DD)
    covering the previous calendar month, e.g. ``('2026-05-01', '2026-05-31')``.
    """
    today = datetime.date.today()
    first_of_this_month = today.replace(day=1)
    last_of_last_month  = first_of_this_month - datetime.timedelta(days=1)
    first_of_last_month = last_of_last_month.replace(day=1)
    return first_of_last_month.isoformat(), last_of_last_month.isoformat()


# ---------------------------------------------------------------------------
# Credentials helper (reads what the Settings node saved)
# ---------------------------------------------------------------------------

def _get_config_dir() -> str:
    d = os.path.join(os.path.expanduser("~"), ".cv_studio")
    os.makedirs(d, exist_ok=True)
    return d


def _load_credentials() -> dict:
    path = os.path.join(_get_config_dir(), "copernicus_credentials.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {"client_id": "", "client_secret": ""}


# ---------------------------------------------------------------------------
# OAuth2 token manager — shared singleton per Python process
# ---------------------------------------------------------------------------

class _TokenManager:
    """Thread-safe OAuth2 client-credentials token manager."""

    def __init__(self):
        self._lock   = threading.Lock()
        self._token  = None
        self._expiry = 0.0

    def get_token(self) -> str:
        with self._lock:
            if time.time() < self._expiry - 60:
                return self._token
            return self._refresh()

    def _refresh(self) -> str:
        creds = _load_credentials()
        if not (creds.get("client_id") and creds.get("client_secret")):
            raise RuntimeError(
                "Copernicus credentials not configured. "
                "Use the System → Settings node to enter your client_id / client_secret."
            )
        if not _HAS_REQUESTS:
            raise ImportError("The 'requests' package is required.")
        print(f"[CopernicusMap] POST {_TOKEN_URL}")
        _cid = creds['client_id']
        _cid_masked = _cid[:6] + "…" + _cid[-4:] if len(_cid) > 10 else "***"
        print(f"[CopernicusMap]   grant_type=client_credentials  client_id={_cid_masked}")
        resp = _requests.post(
            _TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     creds["client_id"],
                "client_secret": creds["client_secret"],
            },
            timeout=20,
        )
        print(f"[CopernicusMap] Token response: HTTP {resp.status_code}")
        if not resp.ok:
            print(f"[CopernicusMap] Auth error body:\n{resp.text[:500]}")
            raise RuntimeError(
                f"Copernicus auth failed ({resp.status_code}): {resp.text[:300]}"
            )
        data         = resp.json()
        self._token  = data["access_token"]
        self._expiry = time.time() + float(data.get("expires_in", 3600))
        print(f"[CopernicusMap] Token obtained, expires_in={data.get('expires_in', 3600)}s")
        return self._token


_TOKEN_MGR = _TokenManager()

# ---------------------------------------------------------------------------
# Disk tile cache
# ---------------------------------------------------------------------------

def _tile_cache_dir() -> str:
    d = os.path.join(_get_config_dir(), "copernicus_tiles")
    os.makedirs(d, exist_ok=True)
    return d


def _tile_key(cdse_id: str, tile_lat: int, tile_lon: int,
               formula_hash: str, date_from: str, date_to: str,
               cloud: int) -> str:
    raw = f"{cdse_id}_{tile_lat}_{tile_lon}_{formula_hash}_{date_from}_{date_to}_{cloud}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(key: str) -> str:
    return os.path.join(_tile_cache_dir(), key + ".npy")


def _load_tile(key: str):
    p = _cache_path(key)
    if os.path.exists(p):
        try:
            arr = np.load(p, allow_pickle=False)
            # Validate shape and dtype to reject corrupted cache files
            if arr.ndim != 2 or arr.shape != (_TILE_PX, _TILE_PX):
                return None
            if arr.dtype != np.float32:
                arr = arr.astype(np.float32)
            return arr
        except Exception:
            pass
    return None


def _save_tile(key: str, data: np.ndarray) -> None:
    np.save(_cache_path(key), data)


# ---------------------------------------------------------------------------
# Evalscript builder
# ---------------------------------------------------------------------------

def _extract_bands_from_formula(formula: str, available: list) -> list:
    """Return sorted unique band names mentioned in *formula*."""
    found = []
    for b in available:
        # Use word-boundary check so "B08" doesn't match inside "AB083"
        if re.search(r'\b' + re.escape(b) + r'\b', formula):
            found.append(b)
    # Deduplicate, preserve order
    seen = set()
    result = []
    for b in found:
        if b not in seen:
            seen.add(b)
            result.append(b)
    return result


def _formula_to_js(formula: str) -> str:
    """Minimal Python-to-JS conversion for arithmetic formulas."""
    # Python power operator → JS Math.pow (handle simple x**y)
    formula = re.sub(
        r'(\w+)\s*\*\*\s*(\w+)',
        lambda m: f'Math.pow({m.group(1)}, {m.group(2)})',
        formula,
    )
    return formula


def _build_evalscript(formula: str, bands: list, slot_bands: list,
                      use_float32: bool = True) -> str:
    """Return a SentinelHub evalscript for the given formula and bands.

    *slot_bands* lists the explicitly selected band slots; if any band in the
    formula is not in *slot_bands* it is added automatically.

    *use_float32* should be ``True`` when the response format supports 32-bit
    floats (e.g. ``image/tiff``).  Pass ``False`` when using ``image/png``,
    which only supports integer sample types: the evalscript will use
    ``sampleType: "AUTO"`` and clamp the output to ``[0, 1]`` so that the PNG
    response can be decoded correctly.
    """
    all_bands = list(dict.fromkeys(slot_bands + bands))  # preserve order, dedup
    if not all_bands:
        all_bands = ["B04"]  # fallback: red band

    band_list_js = ", ".join(f'"{b}"' for b in all_bands)
    assignments  = "\n  ".join(f"var {b} = sample.{b};" for b in all_bands)
    js_formula   = _formula_to_js(formula) if formula.strip() else all_bands[0]

    if use_float32:
        sample_type = "FLOAT32"
        clamp       = f"Math.max(-3.4e38, Math.min(3.4e38, {js_formula}))"
    else:
        sample_type = "AUTO"
        clamp       = f"Math.max(0.0, Math.min(1.0, {js_formula}))"

    return f"""\
//VERSION=3
function setup() {{
  return {{
    input: [{{bands: [{band_list_js}]}}],
    output: {{bands: 1, sampleType: "{sample_type}"}}
  }};
}}
function evaluatePixel(sample) {{
  {assignments}
  return [{clamp}];
}}
"""




def _bbox_tiles(lat_center: float, lon_center: float, radius_km: float):
    """Return list of (tile_lat, tile_lon) that cover the requested area."""
    # Convert radius to degrees (approx)
    delta_lat = (radius_km / 111.0)
    delta_lon = (radius_km / (111.0 * max(math.cos(math.radians(lat_center)), 1e-6)))

    lat_min = lat_center - delta_lat
    lat_max = lat_center + delta_lat
    lon_min = lon_center - delta_lon
    lon_max = lon_center + delta_lon

    t_lat_min = math.floor(lat_min / _TILE_DEG)
    t_lat_max = math.floor(lat_max / _TILE_DEG)
    t_lon_min = math.floor(lon_min / _TILE_DEG)
    t_lon_max = math.floor(lon_max / _TILE_DEG)

    tiles = []
    for tl in range(t_lat_min, t_lat_max + 1):
        for tlon in range(t_lon_min, t_lon_max + 1):
            tiles.append((tl, tlon))
    return tiles, (lat_min, lat_max, lon_min, lon_max)


def _tile_bbox(tile_lat: int, tile_lon: int) -> list:
    """Return [lon_min, lat_min, lon_max, lat_max] for a grid tile."""
    return [
        tile_lon       * _TILE_DEG,
        tile_lat       * _TILE_DEG,
        (tile_lon + 1) * _TILE_DEG,
        (tile_lat + 1) * _TILE_DEG,
    ]


# ---------------------------------------------------------------------------
# Colormap application
# ---------------------------------------------------------------------------

def _apply_colormap(arr: np.ndarray, cmap_name: str,
                    vmin: float = None, vmax: float = None) -> np.ndarray:
    """Map a 2-D float32 array to an RGB uint8 image using *cmap_name*.

    Falls back to a hand-coded RdYlGn gradient when matplotlib is absent.
    """
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.zeros((*arr.shape, 3), dtype=np.uint8)

    lo = float(vmin) if vmin is not None else float(finite.min())
    hi = float(vmax) if vmax is not None else float(finite.max())
    if hi == lo:
        hi = lo + 1e-6
    norm = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)

    if _HAS_MPL:
        cmap = _mcm.get_cmap(cmap_name)
        rgba = cmap(norm)                          # (H, W, 4) float64 0-1
        rgb  = (rgba[..., :3] * 255).astype(np.uint8)
        # DearPyGui expects BGR
        return rgb[..., ::-1]
    else:
        # Fallback: RdYlGn-like gradient via linear interpolation
        # anchors: 0=red, 0.5=yellow, 1=green
        r = np.where(norm < 0.5, 220,          np.interp(norm, [0.5, 1.0], [220, 50])).astype(np.uint8)
        g = np.interp(norm, [0.0, 0.5, 1.0], [50, 220, 200]).astype(np.uint8)
        b = np.zeros_like(r)
        return np.stack([b, g, r], axis=-1)   # BGR


# ---------------------------------------------------------------------------
# FactoryNode — registered by the node editor's dynamic discovery
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = "CopernicusMap"
    node_tag   = "CopernicusMap"

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

        node = _Node()
        node.tag_node_name     = str(node_id) + ":" + node.node_tag
        node._opencv_setting_dict = opencv_setting_dict

        tag = node.tag_node_name
        w   = _DISPLAY_W
        h   = _DISPLAY_H

        # Create the black placeholder texture
        black = np.zeros((h, w, 3), dtype=np.float32)
        tex_data = black.ravel()

        tag_out_img     = tag + ":IMAGE:Output01"
        tag_out_img_val = tag + ":IMAGE:Output01Value"
        tag_out_json    = tag + ":JSON:Output01"
        tag_out_json_val= tag + ":JSON:Output01Value"

        node._tag_out_img_val  = tag_out_img_val
        node._tag_out_json_val = tag_out_json_val
        node._display_w        = w
        node._display_h        = h

        with dpg.texture_registry(show=False):
            dpg.add_raw_texture(
                w, h, tex_data,
                tag=tag_out_img_val,
                format=dpg.mvFormat_Float_rgb,
            )

        with dpg.node(tag=tag, parent=parent, label=node.node_label, pos=pos):

            # ── Image output (top) ─────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_out_img,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_image(tag_out_img_val)

            # ── Coordinate input (from CoordinateExample or similar) ───────
            with dpg.node_attribute(
                tag=tag + ":JSON:Input01",
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text("Coordinates (optional)", color=[180, 180, 180])

            # ── Source / area settings ─────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ":SettingsStatic",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_combo(
                    tag=tag + ":Source",
                    items=_SOURCE_NAMES,
                    default_value=_SOURCE_NAMES[0],
                    width=220,
                    label="Source",
                )
                dpg.add_spacer(height=2)
                dpg.add_text(
                    tag=tag + ":CoordDisplay",
                    default_value="Lat/Lon: connect Coordinates input",
                    color=[180, 180, 180],
                )
                dpg.add_slider_int(
                    tag=tag + ":Radius",
                    label="Radius (km)",
                    default_value=1,
                    min_value=1,
                    max_value=50,
                    width=160,
                )
                dpg.add_spacer(height=3)
                _df, _dt = _last_month_dates()
                dpg.add_input_text(
                    tag=tag + ":DateFrom",
                    label="From",
                    default_value=_df,
                    width=130,
                    hint="YYYY-MM-DD",
                )
                dpg.add_input_text(
                    tag=tag + ":DateTo",
                    label="To",
                    default_value=_dt,
                    width=130,
                    hint="YYYY-MM-DD",
                )
                dpg.add_slider_int(
                    tag=tag + ":CloudCover",
                    label="Cloud % max",
                    default_value=30,
                    min_value=0,
                    max_value=100,
                    width=160,
                )
                dpg.add_spacer(height=4)

            # ── Band slots (like ImageConcat) ──────────────────────────────
            with dpg.node_attribute(
                tag=tag + ":BandCtrlStatic",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text("── Bands ──")
                dpg.add_button(
                    tag=tag + ":AddBandBtn",
                    label="+ Add band slot",
                    width=170,
                    callback=node._add_band_slot,
                    user_data=tag,
                )

            # Initial band slots (B04 + B08 — needed for NDVI default)
            node._band_slots    = []
            node._band_slot_ctr = 0
            node._add_band_slot_internal(tag, "B04")
            node._add_band_slot_internal(tag, "B08")

            # ── Band formula ───────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ":FormulaStatic",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_spacer(height=3)
                dpg.add_text("── Band formula ──")
                dpg.add_input_text(
                    tag=tag + ":Formula",
                    default_value="(B08 - B04) / (B08 + B04)",
                    width=260,
                    hint="e.g. (B08 - B04) / (B08 + B04)",
                )
                dpg.add_combo(
                    tag=tag + ":Colormap",
                    items=_COLORMAPS,
                    default_value="RdYlGn",
                    width=160,
                    label="Colormap",
                )
                dpg.add_spacer(height=4)

            # ── Status ────────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ":FetchStatic",
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(tag=tag + ":Status", default_value="Status: —")
                dpg.add_spacer(height=2)

            # ── JSON output ────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_out_json,
                attribute_type=dpg.mvNode_Attr_Output,
            ):
                dpg.add_text(tag=tag_out_json_val, default_value="Metadata JSON")

        return node


# ---------------------------------------------------------------------------
# Node implementation
# ---------------------------------------------------------------------------

class _Node(Node):
    _ver = "0.0.1"
    node_label = "CopernicusMap"
    node_tag   = "CopernicusMap"

    TYPE_JSON = "JSON"

    _opencv_setting_dict = None

    # Per-instance state
    _band_slots    = None   # list of slot tag strings
    _band_slot_ctr = 0

    _tag_out_img_val  = ""
    _tag_out_json_val = ""
    _display_w        = _DISPLAY_W
    _display_h        = _DISPLAY_H

    # Latest rendered BGR frame + metadata (updated from background thread)
    _latest_frame    = None
    _latest_meta     = {}
    _fetch_thread    = None
    _fetching        = False
    _frame_lock      = None

    def __init__(self):
        self._band_slots    = []
        self._band_slot_ctr = 0
        self._latest_frame  = None
        self._latest_meta   = {}
        self._frame_lock    = threading.Lock()
        self._fetching      = False
        # Coordinates driven by JSON input (CoordinateExample or similar)
        self._current_lat       = 48.8566
        self._current_lon       = 2.3522
        self._last_fetch_lat    = None
        self._last_fetch_lon    = None
        self._coord_from_input  = False   # True once coords arrive from JSON input

    # ── Band-slot management ────────────────────────────────────────────────

    def _add_band_slot_internal(self, tag_node: str, default_band: str = "B04"):
        """Add a band slot to the node UI (called at init time or from button)."""
        self._band_slot_ctr += 1
        idx = self._band_slot_ctr
        slot_attr = tag_node + f":BandSlot{idx}"
        slot_combo= tag_node + f":BandCombo{idx}"
        slot_del  = tag_node + f":BandDel{idx}"

        # Determine the source to get band list
        source_name = dpg_get_value(tag_node + ":Source") or _SOURCE_NAMES[0]
        bands = _SOURCES.get(source_name, _SOURCES[_SOURCE_NAMES[0]])["bands"]

        # The node attribute is inserted above the formula section
        # We rely on DPG's parent ordering — attributes are appended in order
        with dpg.node_attribute(
            tag=slot_attr,
            attribute_type=dpg.mvNode_Attr_Static,
            parent=tag_node,
        ):
            with dpg.group(horizontal=True):
                dpg.add_combo(
                    tag=slot_combo,
                    items=bands,
                    default_value=default_band if default_band in bands else bands[0],
                    width=100,
                    label=f"B{idx}",
                )
                dpg.add_button(
                    tag=slot_del,
                    label=" × ",
                    width=30,
                    callback=self._remove_band_slot,
                    user_data=(tag_node, slot_attr, slot_combo),
                )

        self._band_slots.append((slot_attr, slot_combo))

    def _add_band_slot(self, sender, app_data, user_data):
        """Button callback: add a new band slot."""
        tag_node = user_data
        source_name = dpg_get_value(tag_node + ":Source") or _SOURCE_NAMES[0]
        bands = _SOURCES.get(source_name, _SOURCES[_SOURCE_NAMES[0]])["bands"]
        default = bands[0]
        self._add_band_slot_internal(tag_node, default)

    def _remove_band_slot(self, sender, app_data, user_data):
        """Button callback: remove a band slot."""
        tag_node, slot_attr, slot_combo = user_data
        # Remove from internal list
        self._band_slots = [
            (a, c) for (a, c) in self._band_slots if a != slot_attr
        ]
        try:
            dpg.delete_item(slot_attr)
        except Exception:
            pass

    def _get_slot_bands(self, tag_node: str) -> list:
        """Return the list of bands currently selected in the slots."""
        result = []
        for _, combo_tag in self._band_slots:
            try:
                v = dpg_get_value(combo_tag)
                if v:
                    result.append(v)
            except Exception:
                pass
        return result

    # ── Fetch logic ─────────────────────────────────────────────────────────

    def _on_fetch(self, sender, app_data, user_data):
        """Fetch button callback — launches a background download."""
        tag_node = user_data
        if self._fetching:
            return
        params = self._collect_params(tag_node)
        dpg_set_value(tag_node + ":Status", "Status: Fetching…")
        self._fetching = True
        t = threading.Thread(
            target=self._fetch_worker,
            args=(tag_node, params),
            daemon=True,
        )
        t.start()
        self._fetch_thread = t

    def _collect_params(self, tag_node: str) -> dict:
        source_name = dpg_get_value(tag_node + ":Source") or _SOURCE_NAMES[0]
        lat         = self._current_lat
        lon         = self._current_lon
        radius      = int(dpg_get_value(tag_node + ":Radius") or 1)
        _lm_from, _lm_to = _last_month_dates()
        date_from   = str(dpg_get_value(tag_node + ":DateFrom") or _lm_from)
        date_to     = str(dpg_get_value(tag_node + ":DateTo")   or _lm_to)
        cloud       = int(dpg_get_value(tag_node + ":CloudCover") or 30)
        formula     = str(dpg_get_value(tag_node + ":Formula") or "(B08 - B04) / (B08 + B04)")
        cmap        = str(dpg_get_value(tag_node + ":Colormap") or "RdYlGn")
        slot_bands  = self._get_slot_bands(tag_node)

        src_info    = _SOURCES.get(source_name, _SOURCES[_SOURCE_NAMES[0]])
        cdse_id     = src_info["cdse_id"]
        avail_bands = src_info["bands"]
        extra_bands = _extract_bands_from_formula(formula, avail_bands)
        evalscript  = _build_evalscript(formula, extra_bands, slot_bands,
                                        use_float32=_HAS_TIFFFILE)
        es_hash     = hashlib.md5(evalscript.encode()).hexdigest()[:8]

        return {
            "source_name": source_name,
            "cdse_id":     cdse_id,
            "lat":         lat,
            "lon":         lon,
            "radius":      radius,
            "date_from":   date_from,
            "date_to":     date_to,
            "cloud":       cloud,
            "formula":     formula,
            "cmap":        cmap,
            "evalscript":  evalscript,
            "es_hash":     es_hash,
        }

    def _fetch_worker(self, tag_node: str, params: dict):
        """Background worker: download missing tiles, assemble and render."""
        print(
            f"[CopernicusMap] Fetch started — lat={params['lat']:.4f}  lon={params['lon']:.4f}"
            f"  radius={params['radius']} km  source={params['source_name']}"
            f"  dates={params['date_from']}→{params['date_to']}  cloud<={params['cloud']}%"
        )
        print(f"[CopernicusMap] Evalscript:\n{params['evalscript']}")
        try:
            tiles, (lat_min, lat_max, lon_min, lon_max) = _bbox_tiles(
                params["lat"], params["lon"], params["radius"]
            )
            # Clamp to _MAX_TILES × _MAX_TILES to avoid huge requests
            if len(tiles) > _MAX_TILES * _MAX_TILES:
                dpg_set_value(tag_node + ":Status",
                              f"Status: Area too large (>{_MAX_TILES**2} tiles). "
                              "Reduce radius.")
                self._fetching = False
                return

            n_lat_tiles = max(1, math.ceil((lat_max - lat_min) / _TILE_DEG))
            n_lon_tiles = max(1, math.ceil((lon_max - lon_min) / _TILE_DEG))
            t_lat_min   = math.floor(lat_min / _TILE_DEG)
            t_lon_min   = math.floor(lon_min / _TILE_DEG)
            # t_lat_max_idx: tile-index of the northernmost row (used to invert
            # the latitude axis when pasting tiles — higher lat → lower row).
            t_lat_max_idx = t_lat_min + n_lat_tiles - 1

            # Prepare the composite array
            full_h = n_lat_tiles * _TILE_PX
            full_w = n_lon_tiles * _TILE_PX
            composite = np.full((full_h, full_w), np.nan, dtype=np.float32)

            need_download = []
            for (tl, tlon) in tiles:
                key = _tile_key(
                    params["cdse_id"], tl, tlon,
                    params["es_hash"],
                    params["date_from"], params["date_to"],
                    params["cloud"],
                )
                tile_data = _load_tile(key)
                if tile_data is not None:
                    _paste_tile(composite, tile_data, tl, tlon, t_lat_max_idx, t_lon_min)
                else:
                    need_download.append((tl, tlon, key))

            total = len(need_download)
            print(f"[CopernicusMap] {len(tiles)} tile(s) total, {total} to download, "
                  f"{len(tiles) - total} from cache")
            for i, (tl, tlon, key) in enumerate(need_download):
                dpg_set_value(
                    tag_node + ":Status",
                    f"Status: Downloading tile {i+1}/{total}…",
                )
                bbox = _tile_bbox(tl, tlon)
                # Inject the correct date range and cloud cover into the payload
                tile_data = _fetch_tile_with_params(
                    params["cdse_id"], bbox, params["evalscript"],
                    params["date_from"], params["date_to"], params["cloud"],
                )
                _save_tile(key, tile_data)
                _paste_tile(composite, tile_data, tl, tlon, t_lat_max_idx, t_lon_min)

            # Apply colormap → BGR uint8 image
            cmap = params["cmap"]
            if not cmap:
                # Auto-select based on formula heuristic
                fl = params["formula"].lower().replace(" ", "")
                cmap = "RdYlGn"
                for kw, cm in _FORMULA_CMAP_HINTS.items():
                    if kw in fl:
                        cmap = cm
                        break

            bgr_img = _apply_colormap(composite, cmap)

            # Add formula legend overlay (value range)
            finite = composite[np.isfinite(composite)]
            if finite.size > 0:
                vmin, vmax = float(finite.min()), float(finite.max())
                legend_txt = f"{params['formula']}  [{vmin:.3f}, {vmax:.3f}]"
            else:
                legend_txt = params["formula"]
            bgr_img = _draw_legend(bgr_img, legend_txt)

            # Resize to display size
            display = cv2.resize(bgr_img, (self._display_w, self._display_h),
                                 interpolation=cv2.INTER_NEAREST)

            with self._frame_lock:
                self._latest_frame = display
                self._latest_meta  = {
                    "source":    params["source_name"],
                    "formula":   params["formula"],
                    "lat":       params["lat"],
                    "lon":       params["lon"],
                    "radius_km": params["radius"],
                    "date_from": params["date_from"],
                    "date_to":   params["date_to"],
                    "tiles_new": total,
                }

            # Record the coordinates used for this fetch so auto-fetch can
            # detect when the view has moved to a genuinely new area.
            self._last_fetch_lat = params["lat"]
            self._last_fetch_lon = params["lon"]

            print(f"[CopernicusMap] Fetch done — {total} new tile(s) downloaded")
            dpg_set_value(tag_node + ":Status",
                          f"Status: Done ✓  ({total} new tiles)")

        except Exception as exc:
            print(f"[CopernicusMap] ERROR: {exc}")
            print(traceback.format_exc())
            short = str(exc)
            dpg_set_value(tag_node + ":Status",
                          f"Error: {short[:120]}" if len(short) > 120 else f"Error: {short}")
        finally:
            self._fetching = False

    # ── Node lifecycle ──────────────────────────────────────────────────────

    def update(
        self,
        node_id,
        connection_list,
        node_image_dict,
        node_result_dict,
        node_audio_dict,
    ):
        tag_node = str(node_id) + ":" + self.node_tag

        # ── Read coordinates from a connected JSON source (e.g. CoordinateExample)
        for conn in connection_list:
            conn_type = conn[0].split(":")[2] if len(conn[0].split(":")) > 2 else ""
            if conn_type == self.TYPE_JSON:
                src_key = ":".join(conn[0].split(":")[:2])
                src_result = node_result_dict.get(src_key, {})
                coords = None
                if isinstance(src_result, dict):
                    coords = src_result.get("json")
                elif isinstance(src_result, list):
                    coords = src_result
                if isinstance(coords, list) and coords:
                    lats = []
                    lons = []
                    for item in coords:
                        if not isinstance(item, dict):
                            continue
                        lat_val = item.get("latitude") or item.get("lat")
                        lon_val = item.get("longitude") or item.get("lon")
                        if lat_val is not None and lon_val is not None:
                            lats.append(float(lat_val))
                            lons.append(float(lon_val))
                    if lats and lons:
                        centroid_lat = sum(lats) / len(lats)
                        centroid_lon = sum(lons) / len(lons)
                        self._current_lat      = centroid_lat
                        self._current_lon      = centroid_lon
                        self._coord_from_input = True
                        try:
                            dpg_set_value(
                                tag_node + ":CoordDisplay",
                                f"Lat: {centroid_lat:.4f}  Lon: {centroid_lon:.4f}",
                            )
                        except Exception:
                            pass
                break

        # ── Auto-fetch when no map data is available or the centre has shifted ──
        # Trigger when: no fetch is in progress, and either no frame has been
        # rendered yet (first arrival) or the centre has shifted by at least half
        # a tile (~500 m at the equator).  Uses the default Paris coordinates
        # until an explicit JSON input overrides them.
        # Thread-safety note: _current_lat/_current_lon are only written here in
        # update() (main thread); _frame_lock guards _latest_frame which is written
        # by the background fetch thread, hence the targeted lock scope below.
        if not self._fetching:
            with self._frame_lock:
                has_frame = self._latest_frame is not None
            needs_fetch = (
                not has_frame
                or self._last_fetch_lat is None
                or self._last_fetch_lon is None
                or abs(self._current_lat - self._last_fetch_lat) > _TILE_DEG * 0.5
                or abs(self._current_lon - self._last_fetch_lon) > _TILE_DEG * 0.5
            )
            if needs_fetch:
                params = self._collect_params(tag_node)
                dpg_set_value(tag_node + ":Status", "Status: Fetching…")
                self._fetching = True
                t = threading.Thread(
                    target=self._fetch_worker,
                    args=(tag_node, params),
                    daemon=True,
                )
                t.start()
                self._fetch_thread = t

        with self._frame_lock:
            frame = self._latest_frame
            meta  = dict(self._latest_meta)

        if frame is not None:
            # Push texture to DPG (max-zoom: no intermediate down-sample)
            tex = frame.astype(np.float32) / 255.0
            tex = np.flip(tex, 2).ravel()   # BGR → RGB, flatten
            try:
                dpg.set_value(self._tag_out_img_val, tex)
            except Exception:
                pass

        return {
            "image": frame,
            "json":  meta,
            "audio": None,
        }

    def close(self, node_id):
        pass


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _paste_tile(composite: np.ndarray, tile: np.ndarray,
                tile_lat: int, tile_lon: int,
                t_lat_max: int, t_lon_min: int) -> None:
    """Write *tile* into *composite* at the correct position.

    Latitude increases northward, but image rows increase downward, so the
    northernmost tile (highest ``tile_lat``) is placed at row 0 and the
    southernmost tile (lowest ``tile_lat``) at the bottom of the composite.
    ``t_lat_max`` is the tile-index of the northernmost row of the grid
    (i.e. ``t_lat_min + n_lat_tiles - 1``).
    ``t_lon_min`` is the tile-index of the westernmost column.
    """
    # Invert latitude axis: higher tile_lat (north) maps to lower row (top).
    row = (t_lat_max - tile_lat) * _TILE_PX
    col = (tile_lon  - t_lon_min) * _TILE_PX
    h, w = tile.shape[:2]
    r_end = min(row + h, composite.shape[0])
    c_end = min(col + w, composite.shape[1])
    if row >= composite.shape[0] or col >= composite.shape[1]:
        return
    composite[row:r_end, col:c_end] = tile[:r_end - row, :c_end - col]


def _fetch_tile_with_params(cdse_id: str, bbox: list, evalscript: str,
                             date_from: str, date_to: str,
                             cloud: int, timeout: int = 60) -> np.ndarray:
    """Like ``_fetch_tile`` but with injected date/cloud parameters."""
    if not _HAS_REQUESTS:
        raise ImportError("requests is required.")

    token = _TOKEN_MGR.get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    lon_min, lat_min, lon_max, lat_max = bbox

    if _HAS_TIFFFILE:
        fmt = {"type": "image/tiff", "parameters": {"compression": "none"}}
    else:
        fmt = {"type": "image/png"}

    payload = {
        "input": {
            "bounds": {
                "bbox": [lon_min, lat_min, lon_max, lat_max],
                "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
            },
            "data": [{
                "type": cdse_id,
                "dataFilter": {
                    "timeRange": {
                        "from": f"{date_from}T00:00:00Z",
                        "to":   f"{date_to}T23:59:59Z",
                    },
                    "maxCloudCoverage": cloud,
                },
            }],
        },
        "output": {
            "width":  _TILE_PX,
            "height": _TILE_PX,
            "responses": [{"identifier": "default", "format": fmt}],
        },
        "evalscript": evalscript,
    }

    print(f"[CopernicusMap] POST {_PROCESS_URL}")
    print(f"[CopernicusMap]   bbox={bbox}  cdse_id={cdse_id}  dates={date_from}→{date_to}  cloud<={cloud}%")

    resp = _requests.post(_PROCESS_URL, json=payload, headers=headers, timeout=timeout)
    print(f"[CopernicusMap] Process response: HTTP {resp.status_code}"
          f"  content-type={resp.headers.get('Content-Type', '?')}")
    if not resp.ok:
        print(f"[CopernicusMap] Process error body:\n{resp.text[:500]}")
        raise RuntimeError(
            f"CDSE Process API error ({resp.status_code}): {resp.text[:300]}"
        )

    if _HAS_TIFFFILE:
        import io
        arr = _tifffile.imread(io.BytesIO(resp.content))
        arr = arr.squeeze().astype(np.float32)
    else:
        img_arr = np.frombuffer(resp.content, dtype=np.uint8)
        img = cv2.imdecode(img_arr, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print(f"[CopernicusMap] PNG decode failed. Response size={len(resp.content)} bytes")
            print(f"[CopernicusMap] First 200 bytes: {resp.content[:200]}")
            raise ValueError("Failed to decode PNG response from CDSE.")
        arr = img.astype(np.float32) / 255.0

    return arr


def _draw_legend(bgr_img: np.ndarray, text: str) -> np.ndarray:
    """Overlay a small text legend at the bottom of the image."""
    out = bgr_img.copy()
    h, w = out.shape[:2]
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.35, w / 1200)
    thickness  = 1
    color      = (255, 255, 255)

    (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
    x = max(4, (w - tw) // 2)
    y = h - 6

    # Semi-transparent background rectangle
    overlay = out.copy()
    cv2.rectangle(overlay, (0, y - th - 4), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, out, 0.5, 0, out)
    cv2.putText(out, text, (x, y), font, font_scale, color, thickness, cv2.LINE_AA)
    return out
