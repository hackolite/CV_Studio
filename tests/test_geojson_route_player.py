#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for GeoJSONRoutePlayer in the CoordinatesExample node.

Tests cover:
- Parsing LineString / MultiLineString / FeatureCollection GeoJSON
- Timestamp extraction (numeric, ISO 8601)
- Speed-based interpolation
- Timestamp-based playback
- Idle behaviour (no file loaded → empty list)
- Route listed in dropdown options
- Node-level update wiring (idle until Start)
- get/set_setting_dict persistence for Route mode
"""
import json
import os
import sys
import time
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode import node_coordinate_examples as nce
from node.InputNode.node_coordinate_examples import (
    Node as CoordinateExamplesNode,
    GeoJSONRoutePlayer,
    GEOJSON_ROUTE_NAME,
    _haversine_km,
    get_example_names,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_geojson(data):
    """Write *data* to a temporary .geojson file and return its path."""
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".geojson", delete=False, encoding="utf-8"
    )
    json.dump(data, fh)
    fh.close()
    return fh.name


# A simple 3-waypoint route (approx Paris area).
_COORDS = [
    [2.3522, 48.8566],   # [lon, lat]
    [2.3600, 48.8590],
    [2.3700, 48.8620],
]

_LINE_GEOJSON = {
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": _COORDS},
    "properties": {},
}

_COLLECTION_GEOJSON = {
    "type": "FeatureCollection",
    "features": [_LINE_GEOJSON],
}

_MULTILINE_GEOJSON = {
    "type": "Feature",
    "geometry": {
        "type": "MultiLineString",
        "coordinates": [_COORDS[:2], _COORDS[1:]],
    },
    "properties": {},
}

# Timestamps matching _COORDS: 0 s, 60 s, 120 s
_COORDS_WITH_TS = {
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": _COORDS},
    "properties": {"coordTimes": [0.0, 60.0, 120.0]},
}

_COORDS_WITH_ISO_TS = {
    "type": "Feature",
    "geometry": {"type": "LineString", "coordinates": _COORDS},
    "properties": {
        "coordTimes": [
            "2024-03-01T10:00:00",
            "2024-03-01T10:01:00",
            "2024-03-01T10:02:00",
        ]
    },
}


# ---------------------------------------------------------------------------
# Unit tests – GeoJSONRoutePlayer
# ---------------------------------------------------------------------------

def test_geojson_route_listed_in_examples():
    """Route must appear in the dropdown options."""
    assert GEOJSON_ROUTE_NAME in get_example_names()


def test_load_linestring_feature():
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0)
        assert player.load() is True
        assert player.is_ready
        assert len(player.route) == 3
        assert player.total_km > 0
        assert player.error is None
    finally:
        os.unlink(path)


def test_load_feature_collection():
    path = _write_geojson(_COLLECTION_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0)
        assert player.load() is True
        assert len(player.route) == 3
    finally:
        os.unlink(path)


def test_load_multilinestring():
    path = _write_geojson(_MULTILINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0)
        assert player.load() is True
        # MultiLineString merges both segments; first and last point of _COORDS
        # are present but the middle point is duplicated.
        assert len(player.route) >= 3
    finally:
        os.unlink(path)


def test_load_missing_file_returns_error():
    player = GeoJSONRoutePlayer("/nonexistent/route.geojson", speed_kmh=50.0)
    assert player.load() is False
    assert player.is_ready is False
    assert player.error is not None


def test_load_invalid_json_returns_error():
    fh = tempfile.NamedTemporaryFile(
        mode="w", suffix=".geojson", delete=False, encoding="utf-8"
    )
    fh.write("not valid json {{{")
    fh.close()
    try:
        player = GeoJSONRoutePlayer(fh.name, speed_kmh=50.0)
        assert player.load() is False
        assert player.error is not None
    finally:
        os.unlink(fh.name)


def test_load_no_path_returns_error():
    player = GeoJSONRoutePlayer("", speed_kmh=50.0)
    assert player.load() is False
    assert "No GeoJSON file specified" in player.error


def test_get_coordinates_idle_returns_empty_list():
    player = GeoJSONRoutePlayer("", speed_kmh=50.0)
    assert player.get_coordinates() == []


def test_get_coordinates_returns_moving_point():
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0)
        assert player.load()
        pt = player.get_coordinates()
        assert isinstance(pt, dict)
        assert "latitude" in pt and "longitude" in pt
        assert pt["is_moving"] == 1.0
        # Should start very close to first waypoint.
        lat0, lon0 = _COORDS[0][1], _COORDS[0][0]
        assert abs(pt["latitude"] - lat0) < 1e-3
        assert abs(pt["longitude"] - lon0) < 1e-3
    finally:
        os.unlink(path)


def test_route_progresses_with_elapsed_time():
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=60.0)
        assert player.load()
        # Simulate 1 minute (= 1 km at 60 km/h) elapsed.
        player.start_time = time.time() - 60.0
        pt = player.get_coordinates()
        # Starting longitude was ~2.3522; after travelling we should be further east.
        assert pt["longitude"] > _COORDS[0][0]
        assert pt["is_moving"] == 1.0
    finally:
        os.unlink(path)


def test_route_ends_and_marks_non_moving():
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=600.0)
        assert player.load()
        # Far past the route duration.
        player.start_time = time.time() - 3600.0
        pt = player.get_coordinates()
        assert pt["is_moving"] == 0.0
        assert player.finished is True
        # Must be at the last waypoint.
        assert abs(pt["latitude"] - _COORDS[-1][1]) < 1e-6
        assert abs(pt["longitude"] - _COORDS[-1][0]) < 1e-6
    finally:
        os.unlink(path)


def test_set_speed_preserves_position():
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=60.0)
        assert player.load()
        player.start_time = time.time() - 60.0  # 1 km at 60 km/h
        pt_before = player.get_coordinates()
        player.set_speed(120.0)
        pt_after = player.get_coordinates()
        # Position must not jump.
        assert abs(pt_before["latitude"] - pt_after["latitude"]) < 1e-4
        assert abs(pt_before["longitude"] - pt_after["longitude"]) < 1e-4
        assert player.speed_kmh == 120.0
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Timestamp support
# ---------------------------------------------------------------------------

def test_numeric_timestamps_detected():
    path = _write_geojson(_COORDS_WITH_TS)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0, use_timestamps=True)
        assert player.load()
        assert player.has_timestamps is True
        assert player._use_timestamps is True
        assert abs(player.total_duration - 120.0) < 1e-6
        # Timestamps must be relative (first == 0).
        assert player.timestamps[0] == 0.0
        assert abs(player.timestamps[-1] - 120.0) < 1e-6
    finally:
        os.unlink(path)


def test_iso_timestamps_detected():
    path = _write_geojson(_COORDS_WITH_ISO_TS)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0, use_timestamps=True)
        assert player.load()
        assert player.has_timestamps is True
        assert abs(player.total_duration - 120.0) < 1.0  # 2 minutes
    finally:
        os.unlink(path)


def test_timestamp_playback_at_half_duration():
    """At elapsed = total_duration / 2, position must be ~the middle waypoint."""
    path = _write_geojson(_COORDS_WITH_TS)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0, use_timestamps=True)
        assert player.load()
        # total_duration = 120 s; at 60 s elapsed we should be at waypoint index 1.
        player.start_time = time.time() - 60.0
        pt = player.get_coordinates()
        mid_lat, mid_lon = _COORDS[1][1], _COORDS[1][0]
        assert abs(pt["latitude"] - mid_lat) < 1e-4
        assert abs(pt["longitude"] - mid_lon) < 1e-4
        assert pt["is_moving"] == 1.0
    finally:
        os.unlink(path)


def test_use_timestamps_false_ignores_timestamps():
    """With use_timestamps=False, timestamps in the file must NOT be used."""
    path = _write_geojson(_COORDS_WITH_TS)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0, use_timestamps=False)
        assert player.load()
        assert player.has_timestamps is True   # found in file
        assert player._use_timestamps is False  # but not active
    finally:
        os.unlink(path)


def test_no_timestamps_in_file_ignores_use_timestamps_flag():
    """When the GeoJSON has no timestamps, use_timestamps=True is silently ignored."""
    path = _write_geojson(_LINE_GEOJSON)
    try:
        player = GeoJSONRoutePlayer(path, speed_kmh=50.0, use_timestamps=True)
        assert player.load()
        assert player.has_timestamps is False
        assert player._use_timestamps is False
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Node-level wiring tests
# ---------------------------------------------------------------------------

def test_node_update_route_idle_until_started(monkeypatch, tmp_path):
    """Route mode must not emit coordinates until Start is pressed."""
    geojson_path = str(tmp_path / "route.geojson")
    with open(geojson_path, "w") as f:
        json.dump(_LINE_GEOJSON, f)

    fake_values = {}

    def fake_get(tag):
        if tag.endswith(":DropdownValue"):
            return GEOJSON_ROUTE_NAME
        if tag.endswith(":GeoJSONRouteFilePathValue"):
            return geojson_path
        if tag.endswith(":GeoJSONRouteSpeedValue"):
            return 50.0
        if tag.endswith(":GeoJSONRouteUseTSValue"):
            return False
        return fake_values.get(tag)

    def fake_set(tag, value):
        fake_values[tag] = value

    monkeypatch.setattr(nce, "dpg_get_value", fake_get)
    monkeypatch.setattr(nce, "dpg_set_value", fake_set)

    node = CoordinateExamplesNode()
    # Before Start: nothing emitted, no player created.
    result = node.update(42, [], {}, {}, {})
    assert result["json"] == []
    assert node.geojson_route_player is None

    # After Start: player created, coordinates emitted.
    node.is_started = True
    result = node.update(42, [], {}, {}, {})
    assert isinstance(result["json"], dict), "Route must return a position dict"
    assert "latitude" in result["json"]
    assert "longitude" in result["json"]
    assert result["json"]["is_moving"] == 1.0
    assert node.geojson_route_player is not None


def test_node_update_route_no_file_emits_empty(monkeypatch):
    """Route mode without a file path must emit [] and update status."""
    fake_values = {}

    def fake_get(tag):
        if tag.endswith(":DropdownValue"):
            return GEOJSON_ROUTE_NAME
        if tag.endswith(":GeoJSONRouteFilePathValue"):
            return ""  # no file
        if tag.endswith(":GeoJSONRouteSpeedValue"):
            return 50.0
        if tag.endswith(":GeoJSONRouteUseTSValue"):
            return False
        return fake_values.get(tag)

    def fake_set(tag, value):
        fake_values[tag] = value

    monkeypatch.setattr(nce, "dpg_get_value", fake_get)
    monkeypatch.setattr(nce, "dpg_set_value", fake_set)

    node = CoordinateExamplesNode()
    node.is_started = True
    result = node.update(7, [], {}, {}, {})
    assert result["json"] == []
    assert node.geojson_route_player is None


def test_get_setting_dict_persists_geojson_route_fields(monkeypatch):
    state = {
        "3:CoordinateExamples:DropdownValue": GEOJSON_ROUTE_NAME,
        "3:CoordinateExamples:GeoJSONRouteFilePathValue": "/tmp/my_route.geojson",
        "3:CoordinateExamples:GeoJSONRouteSpeedValue": 80.0,
        "3:CoordinateExamples:GeoJSONRouteUseTSValue": True,
    }
    monkeypatch.setattr(nce, "dpg_get_value", lambda t: state.get(t))
    monkeypatch.setattr(nce.dpg, "get_item_pos", lambda _t: [0, 0])

    node = CoordinateExamplesNode()
    settings = node.get_setting_dict(3)
    assert settings["3:CoordinateExamples:GeoJSONRouteFilePathValue"] == "/tmp/my_route.geojson"
    assert settings["3:CoordinateExamples:GeoJSONRouteSpeedValue"] == 80.0
    assert settings["3:CoordinateExamples:GeoJSONRouteUseTSValue"] is True


def test_get_setting_dict_omits_geojson_route_fields_for_non_route_mode(monkeypatch):
    state = {
        "4:CoordinateExamples:DropdownValue": "AISTRACKER",
        "4:CoordinateExamples:GeoJSONRouteFilePathValue": "leaky-path",
        "4:CoordinateExamples:GeoJSONRouteSpeedValue": 999.0,
        "4:CoordinateExamples:GeoJSONRouteUseTSValue": True,
    }
    monkeypatch.setattr(nce, "dpg_get_value", lambda t: state.get(t))
    monkeypatch.setattr(nce.dpg, "get_item_pos", lambda _t: [0, 0])

    node = CoordinateExamplesNode()
    settings = node.get_setting_dict(4)
    assert "4:CoordinateExamples:GeoJSONRouteFilePathValue" not in settings
    assert "4:CoordinateExamples:GeoJSONRouteSpeedValue" not in settings
    assert "4:CoordinateExamples:GeoJSONRouteUseTSValue" not in settings


def test_selection_change_to_geojson_route_shows_geojson_fields(monkeypatch):
    """Switching to Route must show GeoJSON inputs and hide Road Route inputs."""
    from tests.test_coordinate_examples_route_visibility import _DPGRecorder

    rec = _DPGRecorder()
    monkeypatch.setattr(nce.dpg, "configure_item", rec.configure_item)
    monkeypatch.setattr(nce, "dpg_set_value", lambda *_a, **_kw: None)

    node = CoordinateExamplesNode()
    CoordinateExamplesNode.on_selection_change(
        sender=None,
        app_data=GEOJSON_ROUTE_NAME,
        user_data=(node, 99),
    )
    shows = {
        tag: kwargs.get("show")
        for tag, kwargs in rec.calls
        if "show" in kwargs
    }
    # Road Route inputs must be hidden.
    assert shows.get("99:CoordinateExamples:RouteStart") is False
    assert shows.get("99:CoordinateExamples:RouteEnd") is False
    assert shows.get("99:CoordinateExamples:RouteSpeed") is False
    assert shows.get("99:CoordinateExamples:OBDLevel") is False
    # GeoJSON Route inputs must be shown.
    assert shows.get("99:CoordinateExamples:GeoJSONRouteLoad") is True
    assert shows.get("99:CoordinateExamples:GeoJSONRouteFilePath") is True
    assert shows.get("99:CoordinateExamples:GeoJSONRouteSpeed") is True
    assert shows.get("99:CoordinateExamples:GeoJSONRouteUseTS") is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
