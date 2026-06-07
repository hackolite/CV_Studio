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


if __name__ == "__main__":
    test_metric_gradient_endpoints_and_clamping()
    test_metric_candidate_keys_filters_spatial_and_out_of_range()
    test_extract_preserves_extra_keys()
    test_record_trace_appends_moving_points_and_detects_end_of_trip()
    test_record_trace_resets_when_disabled_mid_trip()
    print("All map metric/trace tests passed ✓")
