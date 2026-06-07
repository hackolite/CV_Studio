#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the _fit_zoom_for_trace helper and zoom-scaled trace width.

Covers:
1. _fit_zoom_for_trace returns a zoom level that fits all points.
2. Trace width scales with zoom level (thinner when zoomed out).
3. Road Route JSON output is Chart-compatible (flat numeric dict) at end of trip.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode.node_map import (
    _fit_zoom_for_trace,
    MOVING_POINT_SCALE,
    TILE_SIZE,
    _scaled_alpha,
    MOVING_POINT_ALPHA,
)


# ---------------------------------------------------------------------------
# _fit_zoom_for_trace
# ---------------------------------------------------------------------------

def test_fit_zoom_single_point_returns_sensible_zoom():
    """A degenerate single-point trace must not crash and returns a valid zoom."""
    zoom = _fit_zoom_for_trace([48.85], [2.35], width_px=400, height_px=300)
    assert 3 <= zoom <= 17


def test_fit_zoom_city_route_gives_moderate_zoom():
    """A ~20 km Paris-Versailles trace should fit in a mid-range zoom level."""
    lats = [48.8566, 48.8014]   # Paris to Versailles
    lons = [2.3522, 2.1301]
    zoom = _fit_zoom_for_trace(lats, lons, width_px=400, height_px=300)
    # The distance spans ~0.2°, so we expect somewhere around zoom 10–13.
    assert 8 <= zoom <= 15, f"Unexpected zoom {zoom} for city-scale route"


def test_fit_zoom_intercity_route_gives_lower_zoom():
    """A Paris→Lyon trace (~400 km) should need a lower zoom than a city route."""
    lats_city = [48.8566, 48.8014]
    lons_city = [2.3522, 2.1301]
    zoom_city = _fit_zoom_for_trace(lats_city, lons_city, width_px=400, height_px=300)

    lats_long = [48.8566, 45.7640]   # Paris → Lyon
    lons_long = [2.3522, 4.8357]
    zoom_long = _fit_zoom_for_trace(lats_long, lons_long, width_px=400, height_px=300)

    assert zoom_long < zoom_city, (
        f"Long route zoom ({zoom_long}) should be lower than city zoom ({zoom_city})"
    )


def test_fit_zoom_respects_min_max_bounds():
    """The returned zoom must always stay in [min_zoom, max_zoom]."""
    # Artificially large bounding box → would push zoom below min_zoom
    zoom = _fit_zoom_for_trace(
        [0.0, 80.0], [-170.0, 170.0],
        width_px=200, height_px=200,
        min_zoom=3, max_zoom=17,
    )
    assert zoom == 3, f"Expected min_zoom=3, got {zoom}"

    # Very small bounding box → would push zoom above max_zoom
    zoom = _fit_zoom_for_trace(
        [48.85660, 48.85661], [2.35220, 2.35221],
        width_px=200, height_px=200,
        min_zoom=3, max_zoom=17,
    )
    assert zoom == 17, f"Expected max_zoom=17, got {zoom}"


# ---------------------------------------------------------------------------
# Zoom-scaled trace width
# ---------------------------------------------------------------------------

def _compute_trace_w(zoom_level, tile_px=256):
    """Mirror the trace-width formula from _render_with_direct_osm_tiles."""
    r_outer = max(7, int(9 * (tile_px / float(TILE_SIZE))))
    moving_r_outer = max(1, int(round(r_outer * MOVING_POINT_SCALE)))
    _base_trace_w = max(2, moving_r_outer * 2)
    _zoom_scale = max(0.15, zoom_level / 15.0)
    return max(2, int(_base_trace_w * _zoom_scale))


def test_trace_width_at_zoom15_equals_full_diameter():
    """At zoom 15 the scale factor is 1.0 and trace_w equals the moving-point diameter."""
    r_outer = max(7, int(9 * (256 / float(TILE_SIZE))))
    moving_r_outer = max(1, int(round(r_outer * MOVING_POINT_SCALE)))
    expected = max(2, moving_r_outer * 2)
    assert _compute_trace_w(15) == expected


def test_trace_width_smaller_at_low_zoom():
    """Lower zoom levels must produce a smaller (or equal) trace width."""
    w_high = _compute_trace_w(15)
    w_mid = _compute_trace_w(10)
    w_low = _compute_trace_w(5)
    assert w_low <= w_mid <= w_high, (
        f"Trace widths should decrease with zoom: zoom5={w_low}, zoom10={w_mid}, zoom15={w_high}"
    )


def test_trace_width_never_below_2():
    """Even at the minimum zoom the trace must be at least 2 px wide."""
    assert _compute_trace_w(1) >= 2
    assert _compute_trace_w(3) >= 2


# ---------------------------------------------------------------------------
# Road Route OBD2 / Chart compatibility
# ---------------------------------------------------------------------------

def test_road_route_output_all_numeric_chart_compatible():
    """The Road Route JSON output must be a flat dict where every value is numeric."""
    import time
    from node.InputNode.node_coordinate_examples import RouteTripPlayer, _haversine_km

    _FAKE_ROUTE = [
        (48.8566, 2.3522),
        (48.8566, 2.4200),
        (48.8566, 2.5000),
    ]

    def _fake_geocoder(address):
        return {"Paris, France": (48.8566, 2.3522), "Versailles, France": (48.8014, 2.1301)}.get(
            (address or "").strip()
        )

    def _fake_router(start, end):
        return list(_FAKE_ROUTE)

    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=60.0,
        geocoder=_fake_geocoder, router=_fake_router,
    )
    assert player.start()

    pt = player.get_coordinates()
    assert isinstance(pt, dict), "Road Route must return a flat dict"

    # Chart node guard
    assert all(isinstance(v, (int, float)) for v in pt.values()), (
        "All values in the Road Route dict must be int or float for Chart compatibility"
    )

    # Required OBD2 keys
    obd2_keys = (
        "rpm", "speed_kmh", "coolant_temp_c", "instant_consumption_l100",
        "throttle_pos", "engine_load", "maf_g_s", "fuel_level_pct",
        "battery_voltage", "dtc_count",
    )
    for key in obd2_keys:
        assert key in pt, f"Missing OBD2 key: {key}"

    # Plausibility checks
    assert 700 <= pt["rpm"] <= 5000, f"rpm out of range: {pt['rpm']}"
    assert 0 <= pt["coolant_temp_c"] <= 120, f"coolant_temp_c out of range"
    assert 0 <= pt["throttle_pos"] <= 100
    assert 0 <= pt["engine_load"] <= 100
    assert 0 <= pt["fuel_level_pct"] <= 100
    assert 11 <= pt["battery_voltage"] <= 15
    assert pt["dtc_count"] >= 0


def test_road_route_end_of_trip_is_moving_zero():
    """is_moving must be 0.0 (falsy float) at the end of the route."""
    from node.InputNode.node_coordinate_examples import RouteTripPlayer
    import time as _time

    _FAKE_ROUTE = [
        (48.8566, 2.3522),
        (48.8566, 2.4200),
        (48.8566, 2.5000),
    ]

    def _fake_geocoder(addr):
        return {"Paris, France": (48.8566, 2.3522), "Versailles, France": (48.8014, 2.1301)}.get(
            (addr or "").strip()
        )

    player = RouteTripPlayer(
        "Paris, France", "Versailles, France", speed_kmh=600.0,
        geocoder=_fake_geocoder, router=lambda *_: list(_FAKE_ROUTE),
    )
    assert player.start()
    player.start_time = _time.time() - 3600.0  # fast-forward past end

    pt = player.get_coordinates()
    assert isinstance(pt, dict)
    assert pt["is_moving"] == 0.0, f"Expected 0.0, got {pt['is_moving']}"
    assert not bool(pt["is_moving"])
    assert player.finished is True


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
