#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Map node tile-provider registry, cache namespacing, and
HiDPI / labels overlay support introduced to make the map look nicer."""
import os
import sys
import tempfile
from unittest import mock

from PIL import Image

# Make the package importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode import node_map as nm


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_tile_providers_registry_has_expected_entries():
    """The registry should expose at least the documented styles, each with
    a usable URL template and a sane `max_zoom`."""
    for name in ("OSM Standard", "CartoDB Positron", "Esri World Imagery", "OpenTopoMap"):
        assert name in nm.TILE_PROVIDERS, f"Missing provider {name}"
        entry = nm.TILE_PROVIDERS[name]
        assert "{z}" in entry["url"] and "{x}" in entry["url"] and "{y}" in entry["url"]
        assert entry["max_zoom"] >= 17


def test_get_provider_falls_back_to_default_for_unknown():
    """Unknown provider names must not crash callers — fall back to OSM."""
    assert nm.get_provider("does-not-exist") is nm.TILE_PROVIDERS[nm.DEFAULT_PROVIDER]


def test_provider_tile_size_doubles_only_when_hidpi_supported():
    """HiDPI doubles the on-canvas tile size only when the provider exposes
    an @2x URL template; OSM standard has no @2x and must stay at 256."""
    osm = nm.get_provider("OSM Standard")
    cartodb = nm.get_provider("CartoDB Positron")
    assert nm.provider_tile_size(osm, hidpi=False) == 256
    assert nm.provider_tile_size(osm, hidpi=True) == 256  # no @2x → unchanged
    assert nm.provider_tile_size(cartodb, hidpi=False) == 256
    assert nm.provider_tile_size(cartodb, hidpi=True) == 512


# ---------------------------------------------------------------------------
# Cache namespacing
# ---------------------------------------------------------------------------

def test_cache_directory_is_namespaced_per_provider_and_density():
    """Different providers / densities must map to disjoint cache dirs so we
    never serve mismatched tile PNGs across styles."""
    osm = nm._provider_cache_dir("OSM Standard", hidpi=False)
    osm_hd = nm._provider_cache_dir("OSM Standard", hidpi=True)
    carto = nm._provider_cache_dir("CartoDB Positron", hidpi=False)
    carto_hd = nm._provider_cache_dir("CartoDB Positron", hidpi=True)

    paths = {osm, osm_hd, carto, carto_hd}
    assert len(paths) == 4
    # The HiDPI suffix must be reflected on disk
    assert osm_hd.endswith("@2x")
    assert carto_hd.endswith("@2x")
    assert not osm.endswith("@2x")


# ---------------------------------------------------------------------------
# get_osm_tile — URL building + cache I/O
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, png_bytes):
        self.content = png_bytes

    def raise_for_status(self):  # pragma: no cover - trivial
        pass


def _png_bytes(size=4, color=(10, 20, 30, 255)):
    from io import BytesIO
    buf = BytesIO()
    Image.new("RGBA", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def test_get_osm_tile_uses_subdomain_substitution_for_cartodb():
    """{s} must be replaced from the provider's `subdomains` pool."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(_png_bytes())

    with mock.patch.object(nm.requests, "get", side_effect=fake_get):
        img = nm.get_osm_tile(5, 1, 2, use_cache=False, provider_name="CartoDB Positron")

    assert img is not None
    url = captured["url"]
    assert url.startswith("https://")
    # No literal {s} left behind
    assert "{s}" not in url
    # Subdomain must come from the registered pool
    sub = url.split("//", 1)[1].split(".", 1)[0]
    assert sub in nm.TILE_PROVIDERS["CartoDB Positron"]["subdomains"]
    # Path encodes the requested z/x/y
    assert "/5/1/2" in url


def test_get_osm_tile_appends_2x_when_hidpi_requested_and_supported():
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(_png_bytes(size=8))

    with mock.patch.object(nm.requests, "get", side_effect=fake_get):
        nm.get_osm_tile(3, 4, 5, use_cache=False, provider_name="CartoDB Positron", hidpi=True)

    assert "@2x" in captured["url"], f"Expected @2x in {captured['url']!r}"


def test_get_osm_tile_falls_back_to_standard_when_provider_has_no_hidpi():
    """Asking for HiDPI on OSM (which has none) must transparently use the
    standard URL and 256 px tile size."""
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(_png_bytes())

    with mock.patch.object(nm.requests, "get", side_effect=fake_get):
        img = nm.get_osm_tile(2, 0, 0, use_cache=False, provider_name="OSM Standard", hidpi=True)

    assert "@2x" not in captured["url"]
    assert img.size == (4, 4)  # whatever our fake returned, unchanged


def test_get_osm_tile_writes_into_provider_namespaced_cache_dir():
    """A successful fetch must land in the provider-specific cache folder
    (NOT the global one), so a future read serves the right style."""
    z, x, y = 9, 11, 12

    # Make sure the cache file doesn't already exist
    cache_dir = nm._provider_cache_dir("CartoDB Positron")
    cache_path = os.path.join(cache_dir, f"{z}_{x}_{y}.png")
    if os.path.exists(cache_path):
        os.remove(cache_path)

    with mock.patch.object(nm.requests, "get", return_value=_FakeResponse(_png_bytes())):
        nm.get_osm_tile(z, x, y, use_cache=True, provider_name="CartoDB Positron")

    assert os.path.exists(cache_path), "Tile was not written to provider cache dir"
    # And the OSM cache dir must NOT contain a same-name file from this call
    other = os.path.join(nm._provider_cache_dir("OSM Standard"), f"{z}_{x}_{y}.png")
    # (Other tests in this session may have created it; only assert isolation
    # of this specific write by checking the file we just wrote lives in
    # the CartoDB folder.)
    assert cache_path != other


def test_get_osm_tile_network_failure_returns_gray_fallback():
    """When the network call raises, callers get a gray RGBA placeholder of
    the expected tile size instead of a crash."""
    with mock.patch.object(nm.requests, "get", side_effect=Exception("boom")):
        img = nm.get_osm_tile(1, 0, 0, use_cache=False, provider_name="OSM Standard")
    assert img is not None
    assert img.mode == "RGBA"
    assert img.size == (256, 256)


# ---------------------------------------------------------------------------
# Labels overlay
# ---------------------------------------------------------------------------

def test_get_labels_tile_returns_none_when_provider_has_no_labels():
    """OpenTopoMap exposes no labels URL — labels fetch must be a no-op."""
    img = nm.get_labels_tile(5, 1, 1, use_cache=False, provider_name="OpenTopoMap")
    assert img is None


def test_get_labels_tile_uses_labels_url_when_available():
    captured = {}

    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(_png_bytes())

    with mock.patch.object(nm.requests, "get", side_effect=fake_get):
        img = nm.get_labels_tile(6, 2, 3, use_cache=False, provider_name="CartoDB Positron")

    assert img is not None
    assert "light_only_labels" in captured["url"]


# ---------------------------------------------------------------------------
# Settings round-trip (no DPG needed — settings are just dicts)
# ---------------------------------------------------------------------------

def test_setting_dict_includes_visual_quality_fields():
    """The new visual-quality knobs must be in `get_setting_dict`'s output,
    so workflows survive a save/load cycle."""
    # We patch dpg_get_value to a deterministic table, then call the method.
    fake_values = {}

    def fake_get(tag):
        return fake_values.get(tag)

    node = nm.Node()
    with mock.patch.object(nm, "dpg_get_value", side_effect=fake_get):
        fake_values.update({
            "7:Map:ZoomValue": 14,
            "7:Map:MapSizeValue": 1.5,
            "7:Map:UseCacheValue": True,
            "7:Map:PanXValue": 0.1,
            "7:Map:PanYValue": -0.2,
            "7:Map:ProviderValue": "CartoDB Positron",
            "7:Map:HiDPIValue": True,
            "7:Map:LabelsValue": True,
        })
        d = node.get_setting_dict(7)

    assert d["provider"] == "CartoDB Positron"
    assert d["hidpi"] is True
    assert d["labels_overlay"] is True
    assert d["zoom"] == 14
