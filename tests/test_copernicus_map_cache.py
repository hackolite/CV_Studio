#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the CopernicusMap node cache-first path and parallel downloads.

Exercises the module-level helpers (_tile_key, _load_tile, _save_tile,
_bbox_tiles, _paste_tile, _apply_colormap, _draw_legend, _assemble_display)
and the _Node._try_serve_from_cache method without requiring DearPyGui.
"""

import importlib.util
import math
import os
import sys
import threading
import types
from unittest import mock

import numpy as np
import pytest

# ── Module loading ────────────────────────────────────────────────────────────

REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(REPO_ROOT, "node", "MapNode", "node_copernicus_map.py")


def _load_module(tmp_cache_dir: str):
    """Load node_copernicus_map with all heavy dependencies mocked.

    Redirects the tile cache directory to *tmp_cache_dir* so tests never
    touch the real ``~/.cv_studio/copernicus_tiles`` folder.
    """
    import cv2 as _real_cv2

    dpg_mock = mock.MagicMock()
    dpg_mock.mvNode_Attr_Output = 1
    dpg_mock.mvNode_Attr_Input  = 2
    dpg_mock.mvNode_Attr_Static = 3
    dpg_mock.mvFormat_Float_rgb = 0

    mocked = {
        "cv2":                _real_cv2,   # use the real cv2 for image ops
        "dearpygui":          types.ModuleType("dearpygui"),
        "dearpygui.dearpygui": dpg_mock,
        "node_editor":        types.ModuleType("node_editor"),
        "node_editor.util":   types.SimpleNamespace(
            dpg_get_value=mock.MagicMock(return_value=None),
            dpg_set_value=mock.MagicMock(),
        ),
        "node.basenode":      types.SimpleNamespace(Node=type("BaseNode", (), {})),
    }
    mocked["dearpygui"].dearpygui = dpg_mock
    mocked["node_editor"].util    = mocked["node_editor.util"]

    originals = {k: sys.modules.get(k) for k in mocked}
    for k, v in mocked.items():
        sys.modules[k] = v

    spec   = importlib.util.spec_from_file_location("_cop_map_test", MODULE_PATH)
    mod    = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Redirect tile cache to the temp directory
    mod._tile_cache_dir = lambda: tmp_cache_dir

    for k, original in originals.items():
        if original is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = original

    return mod


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tmp_cache(tmp_path_factory):
    return str(tmp_path_factory.mktemp("cop_cache"))


@pytest.fixture(scope="module")
def M(tmp_cache):
    """The copernicus_map module, loaded once per test session."""
    os.makedirs(tmp_cache, exist_ok=True)
    return _load_module(tmp_cache)


# ── Helpers ───────────────────────────────────────────────────────────────────

_TILE_VALUE = 0.5


def _make_tile(M, value=_TILE_VALUE):
    return np.full((M._TILE_PX, M._TILE_PX), value, dtype=np.float32)


def _make_params(M, **overrides):
    base = {
        "source_name": "Sentinel-2 L2A",
        "cdse_id":     "sentinel-2-l2a",
        "lat":         48.852,
        "lon":         2.349,
        "radius":      1,
        "date_from":   "2026-05-01",
        "date_to":     "2026-05-31",
        "cloud":       30,
        "formula":     "(B08 - B04) / (B08 + B04)",
        "cmap":        "RdYlGn",
        "evalscript":  "//VERSION=3",
        "es_hash":     "deadbeef",
    }
    base.update(overrides)
    return base


def _make_node(M):
    node = M._Node.__new__(M._Node)
    node._band_slots          = []
    node._band_slot_ctr       = 0
    node._latest_frame        = None
    node._latest_meta         = {}
    node._frame_lock          = threading.Lock()
    node._fetching            = False
    node._current_lat         = 48.852
    node._current_lon         = 2.349
    node._last_fetch_lat      = None
    node._last_fetch_lon      = None
    node._display_w           = 256
    node._display_h           = 256
    node._tag_out_img_val     = ""
    node._tag_out_json_val    = ""
    node._opencv_setting_dict = {}
    return node


def _populate_cache(M, params, value=_TILE_VALUE):
    """Pre-fill disk cache with synthetic tiles for the given params area."""
    tiles, _ = M._bbox_tiles(params["lat"], params["lon"], params["radius"])
    for (tl, tlon) in tiles:
        key = M._tile_key(
            params["cdse_id"], tl, tlon,
            params["es_hash"],
            params["date_from"], params["date_to"],
            params["cloud"],
        )
        M._save_tile(key, _make_tile(M, value))
    return tiles


# ── _tile_key ─────────────────────────────────────────────────────────────────

def test_tile_key_deterministic(M):
    k1 = M._tile_key("s2l2a", 5427, 260, "abc123", "2026-05-01", "2026-05-31", 30)
    k2 = M._tile_key("s2l2a", 5427, 260, "abc123", "2026-05-01", "2026-05-31", 30)
    assert k1 == k2


def test_tile_key_differs_on_position(M):
    k1 = M._tile_key("s2l2a", 5427, 260, "abc", "2026-05-01", "2026-05-31", 30)
    k2 = M._tile_key("s2l2a", 5427, 261, "abc", "2026-05-01", "2026-05-31", 30)
    assert k1 != k2


def test_tile_key_differs_on_dates(M):
    k1 = M._tile_key("s2l2a", 5427, 260, "abc", "2026-05-01", "2026-05-31", 30)
    k2 = M._tile_key("s2l2a", 5427, 260, "abc", "2026-04-01", "2026-04-30", 30)
    assert k1 != k2


# ── _load_tile / _save_tile ───────────────────────────────────────────────────

def test_load_tile_missing(M):
    assert M._load_tile("__totally_absent_key__") is None


def test_save_and_load_tile(M):
    key  = "roundtrip_key"
    tile = _make_tile(M, 0.75)
    M._save_tile(key, tile)
    loaded = M._load_tile(key)
    assert loaded is not None
    np.testing.assert_array_almost_equal(loaded, tile)


def test_load_tile_wrong_shape_returns_none(M, tmp_cache):
    """A cache file whose shape differs from (_TILE_PX, _TILE_PX) is rejected."""
    key  = "bad_shape_key"
    path = M._cache_path(key)
    np.save(path, np.zeros((10, 10), dtype=np.float32))
    assert M._load_tile(key) is None


# ── _bbox_tiles ───────────────────────────────────────────────────────────────

def test_bbox_tiles_returns_nonempty(M):
    tiles, bbox = M._bbox_tiles(48.852, 2.349, 1)
    assert len(tiles) > 0


def test_bbox_tiles_covers_center(M):
    lat, lon = 48.852, 2.349
    tiles, _ = M._bbox_tiles(lat, lon, 1)
    t_lat = math.floor(lat / M._TILE_DEG)
    t_lon = math.floor(lon / M._TILE_DEG)
    assert (t_lat, t_lon) in tiles


def test_bbox_tiles_large_radius_exceeds_max(M):
    tiles, _ = M._bbox_tiles(48.852, 2.349, 100)
    assert len(tiles) > M._MAX_TILES * M._MAX_TILES


# ── _paste_tile ───────────────────────────────────────────────────────────────

def test_paste_tile_northernmost_goes_to_top_row(M):
    px = M._TILE_PX
    composite = np.zeros((2 * px, 2 * px), dtype=np.float32)
    tile      = np.ones((px, px), dtype=np.float32)
    # Two-row grid: lat indices 0 (south) and 1 (north)
    # t_lat_max=1, t_lon_min=0 → northernmost tile (lat=1) → row 0
    M._paste_tile(composite, tile, 1, 0, 1, 0)
    assert composite[0, 0] == 1.0
    assert composite[px, 0] == 0.0  # southern row untouched


# ── _apply_colormap / _draw_legend ───────────────────────────────────────────

def test_apply_colormap_shape(M):
    px  = M._TILE_PX
    arr = np.linspace(-1, 1, px * px, dtype=np.float32).reshape(px, px)
    out = M._apply_colormap(arr, "RdYlGn")
    assert out.shape == (px, px, 3)


def test_apply_colormap_all_nan_returns_zeros(M):
    px           = M._TILE_PX
    nan_array    = np.full((px, px), np.nan, dtype=np.float32)
    out          = M._apply_colormap(nan_array, "RdYlGn")
    assert out.shape == (px, px, 3)


def test_draw_legend_preserves_shape(M):
    bgr = np.zeros((128, 128, 3), dtype=np.uint8)
    out = M._draw_legend(bgr, "NDVI  [0.1, 0.9]")
    assert out.shape == bgr.shape


# ── _assemble_display ─────────────────────────────────────────────────────────

def test_assemble_display_output_size(M):
    px        = M._TILE_PX
    composite = np.linspace(0, 1, px * px, dtype=np.float32).reshape(px, px)
    params    = _make_params(M)
    out       = M._assemble_display(composite, params, 256, 256)
    assert out.shape == (256, 256, 3)


def test_assemble_display_empty_cmap_uses_heuristic(M):
    """When cmap='' the formula-based heuristic must pick a valid colormap."""
    composite = _make_tile(M, 0.3)
    params    = _make_params(M, formula="(B08 - B04) / (B08 + B04)", cmap="")
    out       = M._assemble_display(composite, params, 128, 128)
    assert out.shape == (128, 128, 3)


# ── _FETCH_WORKERS constant ───────────────────────────────────────────────────

def test_fetch_workers_is_positive(M):
    assert M._FETCH_WORKERS >= 1


# ── _Node._try_serve_from_cache ───────────────────────────────────────────────

def test_try_serve_from_cache_miss(M):
    """Returns None when the tile cache is empty."""
    node   = _make_node(M)
    params = _make_params(M, lat=0.0, lon=0.0)  # different coords → unique keys
    result = node._try_serve_from_cache(params)
    assert result is None


def test_try_serve_from_cache_full_hit(M):
    """Returns (display, meta) when every required tile is cached."""
    node   = _make_node(M)
    params = _make_params(M)
    _populate_cache(M, params)

    result = node._try_serve_from_cache(params)
    assert result is not None

    display, meta = result
    assert display.shape == (node._display_h, node._display_w, 3)
    assert meta["tiles_new"] == 0
    assert meta["lat"] == params["lat"]
    assert meta["lon"] == params["lon"]


def test_try_serve_from_cache_partial_miss(M):
    """Returns None when at least one tile is absent from the cache."""
    node   = _make_node(M)
    # Use coordinates that produce multiple tiles; pre-populate only the first
    params = _make_params(M, radius=2)
    tiles, _ = M._bbox_tiles(params["lat"], params["lon"], params["radius"])
    if len(tiles) < 2:
        pytest.skip("Area produces only one tile; partial miss not testable")

    tl, tlon = tiles[0]
    key = M._tile_key(
        params["cdse_id"], tl, tlon,
        params["es_hash"],
        params["date_from"], params["date_to"],
        params["cloud"],
    )
    M._save_tile(key, _make_tile(M))

    result = node._try_serve_from_cache(params)
    assert result is None


def test_try_serve_from_cache_area_too_large(M):
    """Returns None immediately for an area that exceeds _MAX_TILES²."""
    node   = _make_node(M)
    params = _make_params(M, radius=200)
    result = node._try_serve_from_cache(params)
    assert result is None


def test_try_serve_from_cache_meta_tiles_new_is_zero(M):
    """tiles_new must be 0 when the result comes entirely from cache."""
    node   = _make_node(M)
    params = _make_params(M, lat=48.860, lon=2.340)
    _populate_cache(M, params)

    result = node._try_serve_from_cache(params)
    assert result is not None
    _, meta = result
    assert meta["tiles_new"] == 0
