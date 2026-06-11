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
    – cache keys include the tile definition (pixel resolution) and zoom
      (tile size in degrees) so tiles never collide across resolutions
    – once the first (non-default) position is defined the 8 km² beside it
      (a 3×3 neighbourhood) are prefetched in the background
  • Colormap rendering with per-formula default (NDVI → RdYlGn, etc.)
  • "Visible spectrum only" checkbox: restricts band options to the visible
    spectrum (B02/B03/B04) and grays out band slots set to other wavelengths
  • Maximum zoom: the display is cropped / rendered at full resolution with no
    unnecessary down-sampling.

Credentials are read from ``~/.cv_studio/copernicus_credentials.json``
(written by the companion *Settings* node in the System category).
"""

import concurrent.futures
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
# Maximum parallel tile downloads (mirrors the OSM tile prefetch pool size)
_FETCH_WORKERS = 4
# Ring of ~1 km tiles prefetched around the center tile so the "8 km beside"
# the position are already cached for smooth panning / zoom.  A ring of 1 tile
# yields the 8 tiles adjacent to the center (a 3×3 grid = center 1 km² + the 8
# neighbouring km²).  Prefetching runs in the background after the central area
# has been rendered and only downloads tiles that are not already cached.
_PREFETCH_RING = 1

# Default display resolution (pixels)
_DISPLAY_W  = 512
_DISPLAY_H  = 512

# Maximum number of GPS positions kept in the on-map trace history
_TRACE_MAX  = 5000

# Sentinel-2 L2A bands available in CDSE
_S2_BANDS = [
    "B01", "B02", "B03", "B04", "B05", "B06",
    "B07", "B08", "B8A", "B09", "B11", "B12",
]
_S1_BANDS = ["VV", "VH"]

# Sentinel-2 bands within the visible spectrum (~380-700 nm):
#   B02 (blue ≈490 nm), B03 (green ≈560 nm), B04 (red ≈665 nm)
_S2_VISIBLE_BANDS = ["B02", "B03", "B04"]
# Sentinel-1 is radar (C-band microwave) — nothing in the visible spectrum
_S1_VISIBLE_BANDS = []

_SOURCES = {
    "Sentinel-2 L2A": {"cdse_id": "sentinel-2-l2a",  "bands": _S2_BANDS,
                       "visible_bands": _S2_VISIBLE_BANDS},
    "Sentinel-2 L1C": {"cdse_id": "sentinel-2-l1c",  "bands": _S2_BANDS,
                       "visible_bands": _S2_VISIBLE_BANDS},
    "Sentinel-1 GRD": {"cdse_id": "sentinel-1-grd",   "bands": _S1_BANDS,
                       "visible_bands": _S1_VISIBLE_BANDS},
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
    # _TILE_PX (definition / pixel resolution) and _TILE_DEG (zoom / tile size
    # in degrees) are part of the key so cached tiles are never reused across a
    # different definition or zoom level — keeping the cache coherent if those
    # constants ever change.
    raw = (f"{cdse_id}_{tile_lat}_{tile_lon}_{formula_hash}_{date_from}_"
           f"{date_to}_{cloud}_{_TILE_PX}_{_TILE_DEG}")
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


def _ring_tiles(lat_center: float, lon_center: float, ring: int) -> list:
    """Return the tiles of a ``(2*ring+1)×(2*ring+1)`` grid centered on the tile
    that contains ``(lat_center, lon_center)``.

    For ``ring == 1`` this yields the center tile plus its 8 neighbours (a 3×3
    grid), i.e. the 1 km² around the position and the 8 km² beside it.
    """
    c_lat = math.floor(lat_center / _TILE_DEG)
    c_lon = math.floor(lon_center / _TILE_DEG)
    tiles = []
    for dlat in range(-ring, ring + 1):
        for dlon in range(-ring, ring + 1):
            tiles.append((c_lat + dlat, c_lon + dlon))
    return tiles


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
# Geo ↔ composite-pixel helpers (continuous GPS overlay rendering)
# ---------------------------------------------------------------------------

def _composite_geo_bounds(t_lat_min: int, t_lat_max: int,
                          t_lon_min: int, t_lon_max: int) -> tuple:
    """Return ``(lat_min, lat_max, lon_min, lon_max)`` in degrees for a
    composite assembled from the inclusive tile-index range."""
    return (
        t_lat_min       * _TILE_DEG,
        (t_lat_max + 1) * _TILE_DEG,
        t_lon_min       * _TILE_DEG,
        (t_lon_max + 1) * _TILE_DEG,
    )


def _latlon_to_composite_px(lat: float, lon: float, geo: tuple) -> tuple:
    """Convert ``(lat, lon)`` to float pixel ``(x, y)`` inside a composite
    whose geographic bounds are *geo* = (lat_min, lat_max, lon_min, lon_max).

    Row 0 of the composite is the northern edge (``lat_max``); pixels scale
    linearly at ``_TILE_PX / _TILE_DEG`` px per degree on both axes.
    """
    lat_min, lat_max, lon_min, lon_max = geo
    ppd = _TILE_PX / _TILE_DEG
    x = (lon - lon_min) * ppd
    y = (lat_max - lat) * ppd
    return x, y


def _pick_cmap(cmap: str, formula: str) -> str:
    """Return *cmap* or, when empty, a per-formula heuristic default."""
    if cmap:
        return cmap
    fl = (formula or "").lower().replace(" ", "")
    for kw, cm in _FORMULA_CMAP_HINTS.items():
        if kw in fl:
            return cm
    return "RdYlGn"


def _crop_view(base_bgr: np.ndarray, center_x: float, center_y: float,
               view_w: int, view_h: int) -> tuple:
    """Crop a ``view_h × view_w`` window centered on ``(center_x, center_y)``
    out of *base_bgr*, padding out-of-bounds areas with dark gray.

    Returns ``(view_bgr, x0, y0)`` where ``(x0, y0)`` is the top-left corner
    of the window in composite-pixel coordinates (needed to place overlay
    markers inside the view).
    """
    h, w = base_bgr.shape[:2]
    x0 = int(round(center_x - view_w / 2.0))
    y0 = int(round(center_y - view_h / 2.0))

    view = np.full((view_h, view_w, 3), 40, dtype=np.uint8)
    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(w, x0 + view_w), min(h, y0 + view_h)
    if sx1 > sx0 and sy1 > sy0:
        view[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = base_bgr[sy0:sy1, sx0:sx1]
    return view, x0, y0


def _draw_gps_overlay(view: np.ndarray, marker_xy: tuple,
                      trace_xy: list = None) -> np.ndarray:
    """Draw the GPS trace polyline and the current-position marker on *view*.

    Mirrors the OSM map node marker styling (node_map.py): a historic trace
    polyline (white halo + red line), then the live position as a
    semi-transparent halo + solid red dot + white rim, so the progression is
    visible directly on the satellite imagery.
    """
    out = view.copy()
    h, w = out.shape[:2]

    pts = [
        (int(round(x)), int(round(y)))
        for (x, y) in (trace_xy or [])
        if -w <= x < 2 * w and -h <= y < 2 * h
    ]
    if len(pts) >= 2:
        arr = np.array(pts, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(out, [arr], False, (255, 255, 255), 5, cv2.LINE_AA)
        cv2.polylines(out, [arr], False, (0, 30, 220), 2, cv2.LINE_AA)

    mx, my = int(round(marker_xy[0])), int(round(marker_xy[1]))
    if -20 <= mx < w + 20 and -20 <= my < h + 20:
        halo = out.copy()
        cv2.circle(halo, (mx, my), 11, (0, 80, 255), -1, cv2.LINE_AA)
        cv2.addWeighted(halo, 0.35, out, 0.65, 0, out)
        cv2.circle(out, (mx, my), 5, (0, 30, 220), -1, cv2.LINE_AA)
        cv2.circle(out, (mx, my), 5, (255, 255, 255), 1, cv2.LINE_AA)
    return out


# ---------------------------------------------------------------------------
# Display assembly helper (shared by the cache-hit path and _fetch_worker)
# ---------------------------------------------------------------------------

def _assemble_display(composite: np.ndarray, params: dict,
                      display_w: int, display_h: int) -> np.ndarray:
    """Apply colormap, legend overlay, and resize to produce a BGR display image.

    Used by both the synchronous cache-hit path in ``update()`` and the
    background ``_fetch_worker`` so the two code paths produce identical output.
    """
    cmap = _pick_cmap(params.get("cmap") or "", params.get("formula", ""))
    bgr_img = _apply_colormap(composite, cmap)
    finite  = composite[np.isfinite(composite)]
    if finite.size > 0:
        vmin, vmax = float(finite.min()), float(finite.max())
        legend_txt = f"{params.get('formula', '')}  [{vmin:.3f}, {vmax:.3f}]"
    else:
        legend_txt = params.get("formula", "")
    bgr_img = _draw_legend(bgr_img, legend_txt)
    return cv2.resize(bgr_img, (display_w, display_h),
                      interpolation=cv2.INTER_NEAREST)


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
                dpg.add_checkbox(
                    tag=tag + ":VisibleOnly",
                    label="Visible spectrum only",
                    default_value=False,
                    callback=node._on_visible_only_toggle,
                    user_data=tag,
                )
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
    _prefetching     = False
    _frame_lock      = None

    # Raw composite + its geographic bounds, kept so update() can re-render a
    # continuous view (sub-tile scrolling + GPS overlay) on every frame
    # without waiting for a new block fetch — mirrors node_map.py behaviour.
    _latest_composite = None
    _composite_geo    = None   # (lat_min, lat_max, lon_min, lon_max)
    _base_bgr         = None   # colormapped full composite (BGR uint8)
    _base_sig         = None   # (id(composite), cmap) cache signature
    _gps_trace        = None   # list of (lat, lon) — progression history

    def __init__(self):
        self._band_slots    = []
        self._band_slot_ctr = 0
        self._latest_frame  = None
        self._latest_meta   = {}
        self._frame_lock    = threading.Lock()
        self._fetching      = False
        self._prefetching   = False
        self._latest_composite = None
        self._composite_geo    = None
        self._base_bgr         = None
        self._base_sig         = None
        self._gps_trace        = []
        # Coordinates driven by JSON input (CoordinateExample or similar)
        self._current_lat       = 48.8566
        self._current_lon       = 2.3522
        self._last_fetch_lat    = None
        self._last_fetch_lon    = None
        self._coord_from_input  = False   # True once coords arrive from JSON input

    # ── Band-slot management ────────────────────────────────────────────────

    def _visible_only(self, tag_node: str) -> bool:
        """Return True when the 'Visible spectrum only' checkbox is checked."""
        try:
            return bool(dpg_get_value(tag_node + ":VisibleOnly"))
        except Exception:
            return False

    @staticmethod
    def _source_band_lists(tag_node: str) -> tuple:
        """Return ``(all_bands, visible_bands)`` for the current source."""
        source_name = dpg_get_value(tag_node + ":Source") or _SOURCE_NAMES[0]
        src = _SOURCES.get(source_name, _SOURCES[_SOURCE_NAMES[0]])
        return src["bands"], src.get("visible_bands", [])

    def _on_visible_only_toggle(self, sender, app_data, user_data):
        """Checkbox callback: gray out band options outside the visible
        spectrum (or restore the full band list when unchecked)."""
        tag_node = user_data
        self._refresh_band_slot_grayout(tag_node)

    def _refresh_band_slot_grayout(self, tag_node: str):
        """Apply the visible-only filter to every band-slot combo.

        When the filter is on, each combo only proposes visible-spectrum
        bands; a combo whose current selection is a non-visible wavelength is
        disabled (grayed out).  When the filter is off, the full band list is
        restored and every combo is re-enabled.
        """
        visible_only = self._visible_only(tag_node)
        bands, visible = self._source_band_lists(tag_node)
        for _, combo_tag in self._band_slots:
            try:
                value = dpg_get_value(combo_tag)
                if visible_only:
                    in_visible = value in visible
                    dpg.configure_item(
                        combo_tag,
                        items=visible,
                        enabled=in_visible and bool(visible),
                    )
                else:
                    dpg.configure_item(combo_tag, items=bands, enabled=True)
            except Exception:
                pass

    def _add_band_slot_internal(self, tag_node: str, default_band: str = "B04"):
        """Add a band slot to the node UI (called at init time or from button)."""
        self._band_slot_ctr += 1
        idx = self._band_slot_ctr
        slot_attr = tag_node + f":BandSlot{idx}"
        slot_combo= tag_node + f":BandCombo{idx}"
        slot_del  = tag_node + f":BandDel{idx}"

        # Determine the source to get band list
        bands, visible = self._source_band_lists(tag_node)
        if self._visible_only(tag_node) and visible:
            bands = visible

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
                    default_value=(default_band if default_band in bands
                                   else (bands[0] if bands else "")),
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
        bands, visible = self._source_band_lists(tag_node)
        if self._visible_only(tag_node) and visible:
            bands = visible
        default = bands[0] if bands else ""
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
        """Return the list of bands currently selected in the slots.

        When the 'Visible spectrum only' option is checked, bands outside the
        visible spectrum (grayed-out slots) are excluded.
        """
        visible_only = self._visible_only(tag_node)
        _, visible = self._source_band_lists(tag_node)
        result = []
        for _, combo_tag in self._band_slots:
            try:
                v = dpg_get_value(combo_tag)
                if v and (not visible_only or v in visible):
                    result.append(v)
            except Exception:
                pass
        return result

    # ── Fetch logic ─────────────────────────────────────────────────────────

    def _try_serve_from_cache(self, params: dict):
        """Try to build the display image using only on-disk cached tiles.

        Mirrors the pattern of ``node_map.py``'s ``get_osm_tile`` cache-first
        lookup: check the disk cache for every tile the requested area
        requires; if all are present, assemble the composite and return
        ``(display_bgr, meta)`` immediately so ``update()`` can refresh the
        texture without spinning up a background thread.

        Returns ``None`` when any tile is absent — the caller must then fall
        back to the background ``_fetch_worker`` to download the missing ones.
        """
        try:
            tiles, (lat_min, lat_max, lon_min, lon_max) = _bbox_tiles(
                params["lat"], params["lon"], params["radius"]
            )
        except Exception:
            return None
        if len(tiles) > _MAX_TILES * _MAX_TILES:
            return None

        # Derive composite dimensions from the actual tiles list to avoid
        # floating-point drift between ceil((lat_max-lat_min)/_TILE_DEG) and
        # the integer range produced by _bbox_tiles.
        t_lat_min  = min(tl   for (tl,   _) in tiles)
        t_lat_max  = max(tl   for (tl,   _) in tiles)
        t_lon_min  = min(tlon for (_,  tlon) in tiles)
        t_lon_max  = max(tlon for (_,  tlon) in tiles)
        n_lat_tiles = t_lat_max - t_lat_min + 1
        n_lon_tiles = t_lon_max - t_lon_min + 1

        composite = np.full(
            (n_lat_tiles * _TILE_PX, n_lon_tiles * _TILE_PX),
            np.nan, dtype=np.float32,
        )

        for (tl, tlon) in tiles:
            key = _tile_key(
                params["cdse_id"], tl, tlon,
                params["es_hash"],
                params["date_from"], params["date_to"],
                params["cloud"],
            )
            tile_data = _load_tile(key)
            if tile_data is None:
                return None  # cache miss — background download required
            _paste_tile(composite, tile_data, tl, tlon, t_lat_max, t_lon_min)

        display = _assemble_display(composite, params, self._display_w, self._display_h)
        geo = _composite_geo_bounds(t_lat_min, t_lat_max, t_lon_min, t_lon_max)
        with self._frame_lock:
            self._latest_composite = composite
            self._composite_geo    = geo
        meta = {
            "source":    params["source_name"],
            "formula":   params["formula"],
            "lat":       params["lat"],
            "lon":       params["lon"],
            "radius_km": params["radius"],
            "date_from": params["date_from"],
            "date_to":   params["date_to"],
            "tiles_new": 0,
        }
        return display, meta

    # ── Background prefetch of the 8 km² beside the position ─────────────────

    def _neighbour_keys(self, params: dict) -> list:
        """Return ``[(tile_lat, tile_lon, key), …]`` for the 3×3 neighbourhood
        (the 1 km² around the position and the 8 km² beside it).

        Pure helper — no I/O — so it can be unit-tested without a network or
        DearPyGui.
        """
        out = []
        for (tl, tlon) in _ring_tiles(params["lat"], params["lon"], _PREFETCH_RING):
            key = _tile_key(
                params["cdse_id"], tl, tlon,
                params["es_hash"],
                params["date_from"], params["date_to"],
                params["cloud"],
            )
            out.append((tl, tlon, key))
        return out

    def _prefetch_surrounding(self, params: dict) -> None:
        """Download the 8 km² beside the position into the disk cache.

        Mirrors the OSM tile prefetch in ``node_map.py``: launched in the
        background after the central area is rendered, it downloads only the
        neighbouring tiles that are not already cached so that subsequent
        panning / zoom around the first position is served instantly from disk.
        Skips quietly when ``requests`` is unavailable or another prefetch is
        already in flight.
        """
        if self._prefetching or not _HAS_REQUESTS:
            return
        missing = [
            (tl, tlon, key)
            for (tl, tlon, key) in self._neighbour_keys(params)
            if _load_tile(key) is None
        ]
        if not missing:
            return

        self._prefetching = True

        def _worker():
            try:
                def _download(item):
                    tl, tlon, key = item
                    try:
                        data = _fetch_tile_with_params(
                            params["cdse_id"], _tile_bbox(tl, tlon),
                            params["evalscript"],
                            params["date_from"], params["date_to"],
                            params["cloud"],
                        )
                        _save_tile(key, data)
                    except Exception as exc:
                        print(f"[CopernicusMap] prefetch tile ({tl}, {tlon}) failed: {exc}")

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(_FETCH_WORKERS, len(missing))
                ) as pool:
                    list(pool.map(_download, missing))
                print(f"[CopernicusMap] Prefetched {len(missing)} neighbour tile(s)")
            finally:
                self._prefetching = False

        threading.Thread(target=_worker, daemon=True).start()

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
        if self._visible_only(tag_node):
            visible = src_info.get("visible_bands", [])
            avail_bands = visible
            if not slot_bands:
                slot_bands = list(visible)
            # Drop the formula when it references non-visible wavelengths so
            # the evalscript never pulls bands outside the visible spectrum.
            if any(b not in visible for b in extra_bands):
                formula = ""
                extra_bands = []
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

            # Derive composite dimensions from the actual tiles list to avoid
            # floating-point drift between ceil((lat_max-lat_min)/_TILE_DEG)
            # and the integer range produced by _bbox_tiles.
            t_lat_min  = min(tl   for (tl,   _) in tiles)
            t_lat_max  = max(tl   for (tl,   _) in tiles)
            t_lon_min  = min(tlon for (_,  tlon) in tiles)
            t_lon_max  = max(tlon for (_,  tlon) in tiles)
            n_lat_tiles = t_lat_max - t_lat_min + 1
            n_lon_tiles = t_lon_max - t_lon_min + 1

            # Prepare the composite array
            composite = np.full(
                (n_lat_tiles * _TILE_PX, n_lon_tiles * _TILE_PX),
                np.nan, dtype=np.float32,
            )

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
                    _paste_tile(composite, tile_data, tl, tlon, t_lat_max, t_lon_min)
                else:
                    need_download.append((tl, tlon, key))

            total = len(need_download)
            print(f"[CopernicusMap] {len(tiles)} tile(s) total, {total} to download, "
                  f"{len(tiles) - total} from cache")

            if total > 0:
                dpg_set_value(
                    tag_node + ":Status",
                    f"Status: Downloading {total} tile(s)…",
                )
                # Download missing tiles in parallel (mirrors the OSM tile
                # prefetch approach in node_map.py: up to _FETCH_WORKERS
                # concurrent requests to avoid waiting sequentially).
                def _download_tile(item):
                    tl, tlon, key = item
                    bbox = _tile_bbox(tl, tlon)
                    data = _fetch_tile_with_params(
                        params["cdse_id"], bbox, params["evalscript"],
                        params["date_from"], params["date_to"], params["cloud"],
                    )
                    _save_tile(key, data)
                    return tl, tlon, data

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(_FETCH_WORKERS, total)
                ) as pool:
                    for tl, tlon, tile_data in pool.map(_download_tile, need_download):
                        _paste_tile(composite, tile_data, tl, tlon, t_lat_max, t_lon_min)

            # Apply colormap + legend + resize via shared helper
            display = _assemble_display(composite, params, self._display_w, self._display_h)

            with self._frame_lock:
                self._latest_frame = display
                self._latest_composite = composite
                self._composite_geo    = _composite_geo_bounds(
                    t_lat_min, t_lat_max, t_lon_min, t_lon_max,
                )
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

            # Warm the cache with the 8 km² beside the position so subsequent
            # panning / zoom around this first position is served from disk.
            self._prefetch_surrounding(params)

        except Exception as exc:
            print(f"[CopernicusMap] ERROR: {exc}")
            print(traceback.format_exc())
            short = str(exc)
            dpg_set_value(tag_node + ":Status",
                          f"Error: {short[:120]}" if len(short) > 120 else f"Error: {short}")
        finally:
            self._fetching = False

    # ── Continuous view rendering (GPS overlay + sub-tile scrolling) ─────────

    def _render_live_view(self, params: dict):
        """Render the display from the cached composite, centered on the
        *current* GPS position with sub-tile precision, then draw the trace
        polyline and position marker on top.

        Mirrors node_map.py: the map is re-rendered from cached data on every
        update so the view scrolls continuously instead of jumping by blocks,
        and the GPS point is always visible as an overlay.

        Returns the BGR display image, or ``None`` when no composite is
        available yet (caller falls back to the last block-rendered frame).
        """
        with self._frame_lock:
            composite = self._latest_composite
            geo       = self._composite_geo
        if composite is None or geo is None:
            return None

        # Colormap the full composite once per (composite, cmap) pair — the
        # per-frame work is then only a crop + resize + overlay.
        cmap = _pick_cmap(params.get("cmap") or "", params.get("formula", ""))
        sig  = (id(composite), cmap)
        if self._base_bgr is None or self._base_sig != sig:
            self._base_bgr = _apply_colormap(composite, cmap)
            self._base_sig = sig

        lat, lon = self._current_lat, self._current_lon
        ppd    = _TILE_PX / _TILE_DEG     # pixels per degree
        half_h = (params["radius"] / 111.0) * ppd
        half_w = (params["radius"]
                  / (111.0 * max(math.cos(math.radians(lat)), 1e-6))) * ppd
        view_h = max(2, int(round(2 * half_h)))
        view_w = max(2, int(round(2 * half_w)))

        cx, cy = _latlon_to_composite_px(lat, lon, geo)
        view, x0, y0 = _crop_view(self._base_bgr, cx, cy, view_w, view_h)

        sx = self._display_w / float(view_w)
        sy = self._display_h / float(view_h)
        disp = cv2.resize(view, (self._display_w, self._display_h),
                          interpolation=cv2.INTER_NEAREST)

        marker = ((cx - x0) * sx, (cy - y0) * sy)
        trace  = []
        for (tlat, tlon) in (self._gps_trace or []):
            tx, ty = _latlon_to_composite_px(tlat, tlon, geo)
            trace.append(((tx - x0) * sx, (ty - y0) * sy))
        disp = _draw_gps_overlay(disp, marker, trace)

        finite = composite[np.isfinite(composite)]
        if finite.size > 0:
            legend = (f"{params.get('formula', '')}  "
                      f"[{float(finite.min()):.3f}, {float(finite.max()):.3f}]")
        else:
            legend = params.get("formula", "")
        return _draw_legend(disp, legend)

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
                print(f"[CopernicusMap] JSON input received — src_key={src_key} "
                      f"src_result type={type(src_result).__name__}")
                coords = None
                if isinstance(src_result, dict):
                    # node_result_dict stores data["json"] directly (main.py:230),
                    # so src_result is already the coordinate payload — either a bare
                    # coordinate dict (latitude/lon keys from RouteTripPlayer) or a
                    # dict that wraps further data under a "json" key.
                    if "latitude" in src_result or "lat" in src_result:
                        coords = src_result
                    else:
                        coords = src_result.get("json")
                elif isinstance(src_result, list):
                    coords = src_result
                print(f"[CopernicusMap] coords extracted — type={type(coords).__name__} "
                      f"value={coords!r:.200}" if coords is not None else
                      f"[CopernicusMap] coords extracted — None")
                # RouteTripPlayer.get_coordinates() returns a bare dict (not a list);
                # wrap it so the loop below can process it uniformly.
                if isinstance(coords, dict):
                    print(f"[CopernicusMap] Bare dict coord received — wrapping in list")
                    coords = [coords]
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
                        print(f"[CopernicusMap] Coords updated from input — "
                              f"lat={centroid_lat:.6f}  lon={centroid_lon:.6f}  "
                              f"(from {len(lats)} point(s))")
                        self._current_lat      = centroid_lat
                        self._current_lon      = centroid_lon
                        self._coord_from_input = True
                        # Record the progression so it can be drawn as a trace
                        # overlay on the map (skip duplicate consecutive points).
                        if (not self._gps_trace
                                or abs(self._gps_trace[-1][0] - centroid_lat) > 1e-7
                                or abs(self._gps_trace[-1][1] - centroid_lon) > 1e-7):
                            self._gps_trace.append((centroid_lat, centroid_lon))
                            if len(self._gps_trace) > _TRACE_MAX:
                                self._gps_trace = self._gps_trace[-_TRACE_MAX:]
                        try:
                            dpg_set_value(
                                tag_node + ":CoordDisplay",
                                f"Lat: {centroid_lat:.4f}  Lon: {centroid_lon:.4f}",
                            )
                        except Exception:
                            pass
                    else:
                        print(f"[CopernicusMap] No valid lat/lon found in coords list "
                              f"(len={len(coords)})")
                else:
                    print(f"[CopernicusMap] coords is empty or not a list/dict — "
                          f"type={type(coords).__name__} value={coords!r:.100}")
                break

        # ── Auto-fetch only after the first *non-default* position is defined ──
        # The default Paris coordinates must NOT trigger a download: a fetch is
        # only started once a real position has arrived from the JSON input
        # (``_coord_from_input``).  The manual Fetch button still works
        # regardless.  Once triggered, fetch when no frame has been rendered yet
        # (first arrival) or when the center has shifted by at least half a tile
        # (~500 m at the equator).
        # Thread-safety note: _current_lat/_current_lon are only written here in
        # update() (main thread); _frame_lock guards _latest_frame which is written
        # by the background fetch thread, hence the targeted lock scope below.
        if not self._fetching and self._coord_from_input:
            with self._frame_lock:
                has_composite = self._latest_composite is not None
            needs_fetch = (
                not has_composite
                or self._last_fetch_lat is None
                or self._last_fetch_lon is None
                or abs(self._current_lat - self._last_fetch_lat) > _TILE_DEG * 0.5
                or abs(self._current_lon - self._last_fetch_lon) > _TILE_DEG * 0.5
            )
            if needs_fetch:
                params = self._collect_params(tag_node)
                # Fast path: serve from the on-disk tile cache synchronously
                # (mirrors node_map.py which re-renders from cached OSM tiles
                # on every update without waiting for a background thread).
                cached = self._try_serve_from_cache(params)
                if cached is not None:
                    display, meta = cached
                    with self._frame_lock:
                        self._latest_frame = display
                        self._latest_meta  = meta
                    self._last_fetch_lat = params["lat"]
                    self._last_fetch_lon = params["lon"]
                    print(
                        f"[CopernicusMap] All tiles from cache — "
                        f"lat={params['lat']:.4f}  lon={params['lon']:.4f}"
                    )
                    try:
                        dpg_set_value(tag_node + ":Status", "Status: Ready ✓ (from cache)")
                    except Exception:
                        pass
                    # Warm the cache with the 8 km² beside the position.
                    self._prefetch_surrounding(params)
                else:
                    # Some tiles are missing — start a background download
                    dpg_set_value(tag_node + ":Status", "Status: Fetching…")
                    self._fetching = True
                    t = threading.Thread(
                        target=self._fetch_worker,
                        args=(tag_node, params),
                        daemon=True,
                    )
                    t.start()
                    self._fetch_thread = t

        # ── Continuous render: re-draw the view from the cached composite on
        # every update, centered on the current GPS position with the trace +
        # marker overlay — like the OSM map node — instead of waiting for the
        # next block fetch to refresh the texture.
        live_frame = None
        if self._coord_from_input:
            try:
                live_frame = self._render_live_view(self._collect_params(tag_node))
            except Exception as exc:
                print(f"[CopernicusMap] live view render failed: {exc}")

        with self._frame_lock:
            frame = live_frame if live_frame is not None else self._latest_frame
            meta  = dict(self._latest_meta)

        if live_frame is not None:
            meta["gps"] = {"lat": self._current_lat, "lon": self._current_lon}
            meta["trace_len"] = len(self._gps_trace)

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
