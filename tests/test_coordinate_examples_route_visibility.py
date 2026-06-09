#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests that the Road Route fields are reserved to the Road Route mode.

We verify the visibility-toggle helper without spinning up a Dear PyGui
context: ``_set_route_inputs_visible`` is expected to call
``dpg.configure_item`` with ``show=True/False`` for each of the three
Road Route attribute tags (RouteStart / RouteEnd / RouteSpeed).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode import node_coordinate_examples as nce
from node.InputNode.node_coordinate_examples import (
    Node as CoordinateExamplesNode,
    ROAD_ROUTE_NAME,
    GPS_SIMULATION_NAME,
)


class _DPGRecorder:
    def __init__(self):
        self.calls = []

    def configure_item(self, tag, **kwargs):
        self.calls.append((tag, kwargs))


def _patch_dpg(monkeypatch):
    rec = _DPGRecorder()
    monkeypatch.setattr(nce.dpg, "configure_item", rec.configure_item)
    return rec


def test_set_route_inputs_visible_true(monkeypatch):
    rec = _patch_dpg(monkeypatch)
    CoordinateExamplesNode._set_route_inputs_visible(7, True)
    tags = {tag for tag, kwargs in rec.calls if kwargs.get("show") is True}
    assert tags == {
        "7:CoordinateExamples:RouteStart",
        "7:CoordinateExamples:RouteEnd",
        "7:CoordinateExamples:RouteSpeed",
        "7:CoordinateExamples:OBDLevel",
    }


def test_set_route_inputs_visible_false(monkeypatch):
    rec = _patch_dpg(monkeypatch)
    CoordinateExamplesNode._set_route_inputs_visible(3, False)
    tags = {tag for tag, kwargs in rec.calls if kwargs.get("show") is False}
    assert tags == {
        "3:CoordinateExamples:RouteStart",
        "3:CoordinateExamples:RouteEnd",
        "3:CoordinateExamples:RouteSpeed",
        "3:CoordinateExamples:OBDLevel",
    }


def test_selection_change_to_other_mode_hides_route_fields(monkeypatch):
    """Switching to GPS Movement Simulation must hide both Road Route and GeoJSON Route inputs."""
    rec = _patch_dpg(monkeypatch)
    # Selection-change uses dpg_set_value to update the status text; stub it.
    monkeypatch.setattr(nce, "dpg_set_value", lambda *_a, **_kw: None)

    node = CoordinateExamplesNode()
    CoordinateExamplesNode.on_selection_change(
        sender=None,
        app_data=GPS_SIMULATION_NAME,
        user_data=(node, 12),
    )
    shows = {
        tag: kwargs.get("show")
        for tag, kwargs in rec.calls
        if ("Route" in tag or "OBD" in tag or "GeoJSON" in tag) and "show" in kwargs
    }
    assert shows == {
        "12:CoordinateExamples:RouteStart": False,
        "12:CoordinateExamples:RouteEnd": False,
        "12:CoordinateExamples:RouteSpeed": False,
        "12:CoordinateExamples:OBDLevel": False,
        "12:CoordinateExamples:GeoJSONRouteLoad": False,
        "12:CoordinateExamples:GeoJSONRouteFilePath": False,
        "12:CoordinateExamples:GeoJSONRouteSpeed": False,
        "12:CoordinateExamples:GeoJSONRouteUseTS": False,
    }


def test_selection_change_to_road_route_shows_fields(monkeypatch):
    rec = _patch_dpg(monkeypatch)
    monkeypatch.setattr(nce, "dpg_set_value", lambda *_a, **_kw: None)

    node = CoordinateExamplesNode()
    CoordinateExamplesNode.on_selection_change(
        sender=None,
        app_data=ROAD_ROUTE_NAME,
        user_data=(node, 5),
    )
    shows = {
        tag: kwargs.get("show")
        for tag, kwargs in rec.calls
        if ("Route" in tag or "OBD" in tag or "GeoJSON" in tag) and "show" in kwargs
    }
    assert shows == {
        "5:CoordinateExamples:RouteStart": True,
        "5:CoordinateExamples:RouteEnd": True,
        "5:CoordinateExamples:RouteSpeed": True,
        "5:CoordinateExamples:OBDLevel": True,
        "5:CoordinateExamples:GeoJSONRouteLoad": False,
        "5:CoordinateExamples:GeoJSONRouteFilePath": False,
        "5:CoordinateExamples:GeoJSONRouteSpeed": False,
        "5:CoordinateExamples:GeoJSONRouteUseTS": False,
    }


def test_get_setting_dict_omits_route_fields_for_non_route_mode(monkeypatch):
    """Saving a non-route mode must not persist Road Route inputs."""
    state = {
        "9:CoordinateExamples:DropdownValue": GPS_SIMULATION_NAME,
        "9:CoordinateExamples:RouteStartValue": "leaky-from",
        "9:CoordinateExamples:RouteEndValue": "leaky-to",
        "9:CoordinateExamples:RouteSpeedValue": 999.0,
        "9:CoordinateExamples:OBDLevelValue": nce.OBD_LEVEL_SPORT,
    }
    monkeypatch.setattr(nce, "dpg_get_value", lambda t: state.get(t))
    monkeypatch.setattr(nce.dpg, "get_item_pos", lambda _t: [0, 0])

    node = CoordinateExamplesNode()
    settings = node.get_setting_dict(9)
    assert settings["9:CoordinateExamples:DropdownValue"] == GPS_SIMULATION_NAME
    assert "9:CoordinateExamples:RouteStartValue" not in settings
    assert "9:CoordinateExamples:RouteEndValue" not in settings
    assert "9:CoordinateExamples:RouteSpeedValue" not in settings
    assert "9:CoordinateExamples:OBDLevelValue" not in settings


def test_get_setting_dict_persists_route_fields_for_road_route(monkeypatch):
    state = {
        "1:CoordinateExamples:DropdownValue": ROAD_ROUTE_NAME,
        "1:CoordinateExamples:RouteStartValue": "Paris, France",
        "1:CoordinateExamples:RouteEndValue": "Lyon, France",
        "1:CoordinateExamples:RouteSpeedValue": 80.0,
        "1:CoordinateExamples:OBDLevelValue": nce.OBD_LEVEL_SPORT,
    }
    monkeypatch.setattr(nce, "dpg_get_value", lambda t: state.get(t))
    monkeypatch.setattr(nce.dpg, "get_item_pos", lambda _t: [0, 0])

    node = CoordinateExamplesNode()
    settings = node.get_setting_dict(1)
    assert settings["1:CoordinateExamples:RouteStartValue"] == "Paris, France"
    assert settings["1:CoordinateExamples:RouteEndValue"] == "Lyon, France"
    assert settings["1:CoordinateExamples:RouteSpeedValue"] == 80.0
    assert settings["1:CoordinateExamples:OBDLevelValue"] == nce.OBD_LEVEL_SPORT


def test_obd_level_constants_and_profiles():
    """OBD_LEVELS must list all four profiles and _OBD_PROFILES must have matching keys."""
    assert nce.OBD_LEVEL_NORMAL in nce.OBD_LEVELS
    assert nce.OBD_LEVEL_SPORT in nce.OBD_LEVELS
    assert nce.OBD_LEVEL_ECO in nce.OBD_LEVELS
    assert nce.OBD_LEVEL_DEGRADED in nce.OBD_LEVELS
    for level in nce.OBD_LEVELS:
        assert level in nce._OBD_PROFILES
        p = nce._OBD_PROFILES[level]
        for key in ("rpm_init_range", "throttle_init_range", "engine_load_init_range",
                    "fuel_drain", "battery_init_range", "battery_min", "battery_max",
                    "coolant_target", "coolant_init", "dtc_on_prob", "dtc_off_prob"):
            assert key in p, f"Profile '{level}' missing key '{key}'"


def test_route_trip_player_default_obd_level():
    """RouteTripPlayer defaults to OBD_LEVEL_NORMAL when no obd_level is supplied."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    player = RouteTripPlayer("A", "B", 50.0)
    assert player.obd_level == nce.OBD_LEVEL_NORMAL


def test_route_trip_player_obd_level_sport_raises_rpm():
    """Sport profile should initialise RPM higher than the Normal profile."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    import statistics
    normal_rpms = [RouteTripPlayer("A", "B", 50.0, obd_level=nce.OBD_LEVEL_NORMAL)._rpm
                   for _ in range(50)]
    sport_rpms  = [RouteTripPlayer("A", "B", 50.0, obd_level=nce.OBD_LEVEL_SPORT)._rpm
                   for _ in range(50)]
    assert statistics.mean(sport_rpms) > statistics.mean(normal_rpms)


def test_route_trip_player_invalid_obd_level_falls_back():
    """An unrecognised obd_level must fall back to Normal without raising."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    player = RouteTripPlayer("A", "B", 50.0, obd_level="NonExistent")
    assert player.obd_level == nce.OBD_LEVEL_NORMAL


def test_set_obd_level_updates_profile():
    """set_obd_level should switch obd_level and update the coolant target."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    player = RouteTripPlayer("A", "B", 50.0, obd_level=nce.OBD_LEVEL_NORMAL)
    assert player.obd_level == nce.OBD_LEVEL_NORMAL
    player.set_obd_level(nce.OBD_LEVEL_DEGRADED)
    assert player.obd_level == nce.OBD_LEVEL_DEGRADED
    assert player._coolant_target == nce._OBD_PROFILES[nce.OBD_LEVEL_DEGRADED]["coolant_target"]


def test_set_obd_level_same_level_is_noop():
    """Calling set_obd_level with the current level must not change anything."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    player = RouteTripPlayer("A", "B", 50.0, obd_level=nce.OBD_LEVEL_ECO)
    before_rpm = player._rpm
    player.set_obd_level(nce.OBD_LEVEL_ECO)
    assert player._rpm == before_rpm  # state unchanged

if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
