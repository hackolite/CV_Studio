#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the metric / trace features added to the Map node."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode.node_map import (
    Node as MapNode,
    METRIC_NONE,
    _metric_gradient_color,
    _metric_candidate_keys,
)


def test_metric_gradient_endpoints_and_clamping():
    # 0.0 should be green-dominant; 1.0 red-dominant.
    g = _metric_gradient_color(0.0)
    r = _metric_gradient_color(1.0)
    assert g[1] > g[0] and g[1] > g[2], f"green expected at 0.0, got {g}"
    assert r[0] > r[1] and r[0] > r[2], f"red expected at 1.0, got {r}"

    # Values outside [0, 1] should clamp instead of exploding.
    assert _metric_gradient_color(-1.0) == _metric_gradient_color(0.0)
    assert _metric_gradient_color(5.0) == _metric_gradient_color(1.0)

    # Non-numeric values fall back to a neutral grey (no crash).
    grey = _metric_gradient_color(None)
    assert grey == (170, 170, 170, 255)


def test_metric_candidate_keys_filters_spatial_and_out_of_range():
    points = [
        {"lat": 1, "lon": 2, "name": "A", "secousses": 0.1, "is_moving": True,
         "speed_kmh": 4.0},
        {"lat": 3, "lon": 4, "name": "B", "secousses": 0.9, "noise": 0.5},
    ]
    keys = _metric_candidate_keys(points)
    # ``secousses`` and ``noise`` are valid metrics; spatial / non-percent
    # keys must be excluded.
    assert "secousses" in keys
    assert "noise" in keys
    assert "lat" not in keys and "lon" not in keys
    assert "name" not in keys
    assert "is_moving" not in keys
    # speed_kmh = 4.0 is outside [0, 1] → not a metric candidate.
    assert "speed_kmh" not in keys


def test_extract_preserves_extra_keys():
    node = MapNode.create_for_testing()
    data = [
        {"latitude": 48.0, "longitude": 2.0, "name": "V1",
         "secousses": 0.42, "is_moving": True},
    ]
    pts = node._extract_lat_lon_from_json(data)
    assert len(pts) == 1
    assert pts[0]["lat"] == 48.0 and pts[0]["lon"] == 2.0
    # secousses / is_moving must survive the extraction so the Map node
    # can colour/track the point.
    assert pts[0]["secousses"] == 0.42
    assert pts[0]["is_moving"] is True


def test_record_trace_appends_moving_points_and_detects_end_of_trip():
    node = MapNode.create_for_testing()

    # Tracing disabled: history stays empty.
    end, hist = node._record_trace(
        [{"lat": 1.0, "lon": 2.0, "is_moving": True, "secousses": 0.1}],
        "secousses", trace_enabled=False,
    )
    assert end is False
    assert hist == []
    assert node._trace_history == []

    # Enable tracing and feed three moving frames.
    for i, val in enumerate([0.1, 0.4, 0.8]):
        end, hist = node._record_trace(
            [{"lat": 48.0 + i * 0.001, "lon": 2.0 + i * 0.001,
              "is_moving": True, "secousses": val}],
            "secousses", trace_enabled=True,
        )
        assert end is False
    assert len(node._trace_history) == 3
    assert [h["metric"] for h in node._trace_history] == [0.1, 0.4, 0.8]

    # Frame with no moving point after a recorded trip → end_of_trip.
    end, hist = node._record_trace([], "secousses", trace_enabled=True)
    assert end is True
    assert len(hist) == 3

    # A subsequent empty frame should not retrigger end_of_trip (no new
    # moving point has arrived in between).
    end, _ = node._record_trace([], "secousses", trace_enabled=True)
    assert end is False


def test_record_trace_resets_when_disabled_mid_trip():
    node = MapNode.create_for_testing()
    node._record_trace(
        [{"lat": 1.0, "lon": 2.0, "is_moving": True, "secousses": 0.5}],
        "secousses", trace_enabled=True,
    )
    assert node._trace_history
    # Turning trace off must clear the history so a fresh trip starts clean.
    end, hist = node._record_trace([], "secousses", trace_enabled=False)
    assert end is False
    assert hist == []
    assert node._trace_history == []


def test_metric_candidate_keys_excludes_max_suffix():
    """Keys ending with ``_max`` must never appear in the metric selector,
    even when their values happen to be in [0, 1]."""
    points = [
        {
            "lat": 48.0, "lon": 2.0,
            "rpm": 3000.0, "rpm_max": 5500.0, "rpm_ratio": 0.545,
            "speed_kmh": 90.0, "speed_kmh_max": 130.0, "speed_kmh_ratio": 0.692,
            # Edge case: a _max value that is numerically ≤ 1 (should still be excluded)
            "fake_max": 0.5,
            "secousses": 0.3,
        }
    ]
    keys = _metric_candidate_keys(points)
    assert "rpm_ratio" in keys
    assert "speed_kmh_ratio" in keys
    assert "secousses" in keys
    # Raw OBD2 values > 1 are filtered by the value check.
    assert "rpm" not in keys
    assert "speed_kmh" not in keys
    # _max keys must always be excluded, regardless of their numeric value.
    assert "rpm_max" not in keys
    assert "speed_kmh_max" not in keys
    assert "fake_max" not in keys


def test_route_trip_player_obd2_ratios():
    """RouteTripPlayer.get_coordinates() must include _max and _ratio fields
    for every relevant OBD2 key, with ratios clamped to [0, 1]."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from node.InputNode.node_coordinate_examples import RouteTripPlayer

    route = [(48.0, 2.0), (48.1, 2.1)]
    player = RouteTripPlayer.__new__(RouteTripPlayer)
    # Minimal manual initialisation to avoid network calls.
    import random, time
    player.speed_kmh = 60.0
    player.route = route
    player.cum_km = [0.0, 15.7]
    player.total_km = 15.7
    player.start_time = time.time() - 1.0
    player.is_ready = True
    player.finished = False
    player._secousses = 0.15
    player._secousses_drift = 0.01
    player._coolant_temp = 90.0
    player._coolant_target = 90.0
    player._rpm = 2500.0
    player._rpm_drift = 0.0
    player._throttle = 30.0
    player._throttle_drift = 0.0
    player._engine_load = 50.0
    player._engine_load_drift = 0.0
    player._maf = 10.0
    player._maf_drift = 0.0
    player._consumption = 8.0
    player._consumption_drift = 0.0
    player._fuel_level = 75.0
    player._battery_voltage = 14.0
    player._battery_drift = 0.0
    player._dtc_count = 0.0

    result = player.get_coordinates()

    assert isinstance(result, dict), "get_coordinates() must return a dict when ready"

    ratio_keys = [
        "rpm_ratio", "speed_kmh_ratio", "coolant_temp_c_ratio",
        "instant_consumption_l100_ratio", "throttle_pos_ratio",
        "engine_load_ratio", "maf_g_s_ratio", "fuel_low_ratio",
    ]
    max_keys = [
        "rpm_max", "speed_kmh_max", "coolant_temp_c_max",
        "instant_consumption_l100_max", "throttle_pos_max",
        "engine_load_max", "maf_g_s_max",
    ]
    for k in ratio_keys:
        assert k in result, f"Missing ratio key: {k}"
        v = result[k]
        assert 0.0 <= v <= 1.0, f"{k}={v} is outside [0, 1]"
    for k in max_keys:
        assert k in result, f"Missing max key: {k}"
        assert result[k] > 0.0, f"{k} must be positive"

    # fuel_low_ratio = 1 - fuel/100, so with fuel=75 → 0.25
    assert abs(result["fuel_low_ratio"] - 0.25) < 1e-3

    # Ratio keys must show up in the Map metric selector.
    pts = [{"lat": 48.0, "lon": 2.0, **result}]
    map_keys = _metric_candidate_keys(pts)
    for k in ratio_keys:
        assert k in map_keys, f"Map node should offer {k} in combobox"
    for k in max_keys:
        assert k not in map_keys, f"Map node must NOT offer {k} in combobox"


if __name__ == "__main__":
    test_metric_gradient_endpoints_and_clamping()
    test_metric_candidate_keys_filters_spatial_and_out_of_range()
    test_extract_preserves_extra_keys()
    test_record_trace_appends_moving_points_and_detects_end_of_trip()
    test_record_trace_resets_when_disabled_mid_trip()
    test_metric_candidate_keys_excludes_max_suffix()
    test_route_trip_player_obd2_ratios()
    print("All map metric/trace tests passed ✓")
