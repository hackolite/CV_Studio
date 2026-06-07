#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the Road Route mode of the CoordinateExamples node."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.InputNode import node_coordinate_examples as nce
from node.InputNode.node_coordinate_examples import (
    Node as CoordinateExamplesNode,
    RouteTripPlayer,
    ROAD_ROUTE_NAME,
    _haversine_km,
    get_example_names,
)


# A short straight route Paris -> a point ~10 km east. The OSRM polyline
# is approximated here as 3 waypoints so the test stays offline.
_FAKE_ROUTE = [
    (48.8566, 2.3522),
    (48.8566, 2.4200),
    (48.8566, 2.5000),
]


def _fake_geocoder(address):
    table = {
        "Paris, France": (48.8566, 2.3522),
        "Versailles, France": (48.8014, 2.1301),
        "Lyon, France": (45.7640, 4.8357),
    }
    return table.get((address or "").strip())


def _fake_router(start, end):
    return list(_FAKE_ROUTE)


def test_road_route_listed_in_examples():
    """Road Route must appear in the dropdown options."""
    assert ROAD_ROUTE_NAME in get_example_names()


def test_route_trip_player_loads_route_and_emits_moving_point():
    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=60.0,
        geocoder=_fake_geocoder, router=_fake_router,
    )
    assert player.start() is True
    assert player.is_ready
    assert player.error is None
    # Total distance should match the cumulative haversine of the fake route.
    expected_km = (
        _haversine_km(*_FAKE_ROUTE[0], *_FAKE_ROUTE[1])
        + _haversine_km(*_FAKE_ROUTE[1], *_FAKE_ROUTE[2])
    )
    assert abs(player.total_km - expected_km) < 1e-6

    # Right after start, the current position must be ~the start point
    # and be flagged as moving (is_moving == 1.0) so the Map node records
    # it in the trace.
    pt = player.get_coordinates()
    assert isinstance(pt, dict), "Road Route output must be a flat dict"
    assert bool(pt["is_moving"]), "is_moving should be truthy (1.0)"
    assert abs(pt["latitude"] - _FAKE_ROUTE[0][0]) < 1e-3
    assert abs(pt["longitude"] - _FAKE_ROUTE[0][1]) < 1e-2
    # OBD2 fields must be present and numeric
    for key in ("rpm", "speed_kmh", "coolant_temp_c", "instant_consumption_l100",
                "throttle_pos", "engine_load", "maf_g_s", "fuel_level_pct",
                "battery_voltage", "dtc_count"):
        assert key in pt, f"Missing OBD2 key: {key}"
        assert isinstance(pt[key], (int, float)), f"{key} must be numeric"


def test_route_trip_player_progresses_with_elapsed_time():
    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=60.0,
        geocoder=_fake_geocoder, router=_fake_router,
    )
    assert player.start()
    # Rewind start_time to fake that 1 minute (= 1 km at 60 km/h) has passed.
    player.start_time = time.time() - 60.0
    pt = player.get_coordinates()
    assert isinstance(pt, dict)
    # First waypoints are about ~5 km apart, so at 1 km we should still be
    # on the first segment but longitude has shifted east.
    assert pt["longitude"] > _FAKE_ROUTE[0][1]
    assert bool(pt["is_moving"])


def test_route_trip_player_ends_trip_and_marks_non_moving():
    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=600.0,
        geocoder=_fake_geocoder, router=_fake_router,
    )
    assert player.start()
    # Fast-forward well past the total duration of the route.
    player.start_time = time.time() - 3600.0
    pt = player.get_coordinates()
    assert isinstance(pt, dict)
    assert not bool(pt["is_moving"]), "is_moving should be falsy (0.0) at end"
    assert player.finished is True
    assert abs(pt["latitude"] - _FAKE_ROUTE[-1][0]) < 1e-6
    assert abs(pt["longitude"] - _FAKE_ROUTE[-1][1]) < 1e-6


def test_route_trip_player_set_speed_preserves_travelled_distance():
    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=60.0,
        geocoder=_fake_geocoder, router=_fake_router,
    )
    assert player.start()
    player.start_time = time.time() - 60.0  # 1 km travelled at 60 km/h
    pos_before = player.get_coordinates()
    player.set_speed(120.0)
    pos_after = player.get_coordinates()
    # Doubling the speed must not teleport the moving point.
    assert abs(pos_before["latitude"] - pos_after["latitude"]) < 1e-4
    assert abs(pos_before["longitude"] - pos_after["longitude"]) < 1e-4
    assert player.speed_kmh == 120.0


def test_route_trip_player_geocode_failure_sets_error():
    def bad_geocoder(addr):
        return None
    player = RouteTripPlayer(
        "Nowhere", "Somewhere", speed_kmh=50.0,
        geocoder=bad_geocoder, router=_fake_router,
    )
    assert player.start() is False
    assert player.is_ready is False
    assert player.error and "start" in player.error.lower()
    # An un-started player must not emit any coordinates.
    assert player.get_coordinates() == []


def test_node_update_road_route_idle_until_started(monkeypatch):
    """The node should emit no coordinates for Road Route until Start is pressed."""
    fake_values = {}

    def fake_get(tag):
        if tag.endswith(":DropdownValue"):
            return ROAD_ROUTE_NAME
        if tag.endswith(":RouteStartValue"):
            return "Paris, France"
        if tag.endswith(":RouteEndValue"):
            return "Versailles, France"
        if tag.endswith(":RouteSpeedValue"):
            return 60.0
        return fake_values.get(tag)

    def fake_set(tag, value):
        fake_values[tag] = value

    monkeypatch.setattr(nce, "dpg_get_value", fake_get)
    monkeypatch.setattr(nce, "dpg_set_value", fake_set)

    node = CoordinateExamplesNode()
    # Idle: nothing emitted, no player created.
    result = node.update(42, [], {}, {}, {})
    assert result["json"] == []
    assert node.route_player is None

    # Inject fake geocoder/router so start() succeeds offline, then "press Start".
    monkeypatch.setattr(nce, "geocode_address", _fake_geocoder)
    monkeypatch.setattr(nce, "fetch_driving_route", _fake_router)
    node.is_started = True
    result = node.update(42, [], {}, {}, {})
    # Road Route now emits a flat numeric dict (Chart-compatible).
    assert isinstance(result["json"], dict), "Road Route must return a flat dict"
    assert bool(result["json"]["is_moving"]), "is_moving must be truthy at start"
    assert "latitude" in result["json"]
    assert "longitude" in result["json"]
    # OBD2 keys must all be numeric
    for key in ("rpm", "speed_kmh", "coolant_temp_c", "instant_consumption_l100",
                "throttle_pos", "engine_load", "maf_g_s", "fuel_level_pct",
                "battery_voltage", "dtc_count"):
        assert key in result["json"], f"Missing OBD2 key: {key}"
        assert isinstance(result["json"][key], (int, float)), f"{key} not numeric"
    # Chart node guard: all values must be int or float
    assert all(
        isinstance(v, (int, float)) for v in result["json"].values()
    ), "Not all values are numeric — Chart node would reject this dict"
    assert node.route_player is not None


if __name__ == "__main__":
    test_road_route_listed_in_examples()
    test_route_trip_player_loads_route_and_emits_moving_point()
    test_route_trip_player_progresses_with_elapsed_time()
    test_route_trip_player_ends_trip_and_marks_non_moving()
    test_route_trip_player_set_speed_preserves_travelled_distance()
    test_route_trip_player_geocode_failure_sets_error()
    print("All Road Route tests passed ✓")
