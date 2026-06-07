#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for enlarged/translucent rendering of ``is_moving`` markers on the
Map node.

These tests exercise the small ``_moving_marker_style`` / ``_scaled_alpha``
helpers and verify, via a Pillow ImageDraw recording shim, that a coordinate
flagged with ``is_moving=True`` produces a marker whose bounding box is ~4x
the size of a plain one and whose fill alpha is ~half.
"""
import os
import sys

# Make the repo importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode import node_map
from node.VisualNode.node_map import (
    MOVING_POINT_ALPHA,
    MOVING_POINT_SCALE,
    _moving_marker_style,
    _scaled_alpha,
)


def test_moving_marker_style_defaults_for_static_point():
    assert _moving_marker_style({}) == (1.0, 1.0)
    assert _moving_marker_style({'is_moving': False}) == (1.0, 1.0)


def test_moving_marker_style_defaults_for_moving_point():
    scale, alpha = _moving_marker_style({'is_moving': True})
    assert scale == MOVING_POINT_SCALE
    assert alpha == MOVING_POINT_ALPHA


def test_moving_marker_style_per_point_overrides():
    scale, alpha = _moving_marker_style({
        'is_moving': True,
        'marker_scale': 2.5,
        'marker_alpha': 0.25,
    })
    assert scale == 2.5
    assert alpha == 0.25


def test_moving_marker_style_clamps_invalid_values():
    # Negative / zero scale falls back to 1.0
    scale, _ = _moving_marker_style({'is_moving': True, 'marker_scale': -3})
    assert scale == 1.0
    # alpha is clamped to [0, 1]
    _, alpha = _moving_marker_style({'is_moving': True, 'marker_alpha': 2.0})
    assert alpha == 1.0
    _, alpha = _moving_marker_style({'is_moving': True, 'marker_alpha': -1.0})
    assert alpha == 0.0


def test_scaled_alpha_clamps_and_rounds():
    assert _scaled_alpha(255, 0.5) == 128
    assert _scaled_alpha(90, 0.5) == 45
    assert _scaled_alpha(70, 0.0) == 0
    assert _scaled_alpha(70, 5.0) == 255  # clamped
    assert _scaled_alpha(0, 1.0) == 0


# ---------------------------------------------------------------------------
# Marker-rendering integration test using a recording ImageDraw shim
# ---------------------------------------------------------------------------

class _RecordingDraw:
    """Minimal stand-in for :class:`PIL.ImageDraw.ImageDraw` used to capture
    the parameters of every ``ellipse``/``line`` call performed by the marker
    rendering snippet under test."""

    def __init__(self):
        self.ellipses = []  # list of (bbox, fill, outline)
        self.lines = []

    def ellipse(self, bbox, fill=None, outline=None, width=1):
        self.ellipses.append({
            'bbox': tuple(bbox),
            'fill': fill,
            'outline': outline,
            'width': width,
        })

    def line(self, xy, fill=None, width=1, joint=None):
        self.lines.append({'xy': list(xy), 'fill': fill, 'width': width})


def _render_markers(draw, points, px_positions, map_w, map_h, tile_px, TILE_SIZE):
    """Inline re-implementation of the per-point marker loop in
    :func:`Node._render_with_direct_osm_tiles` so the test can drive it on a
    fake draw context without spinning up the whole tile pipeline."""
    r_outer = max(7, int(9 * (tile_px / float(TILE_SIZE))))
    r_inner = max(3, int(4 * (tile_px / float(TILE_SIZE))))
    for point, (fpx, fpy) in zip(points, px_positions):
        scale, alpha_factor = _moving_marker_style(point)
        r_outer_pt = max(1, int(round(r_outer * scale)))
        r_inner_pt = max(1, int(round(r_inner * scale)))
        if (fpx < -r_outer_pt or fpx >= map_w + r_outer_pt or
                fpy < -r_outer_pt or fpy >= map_h + r_outer_pt):
            continue
        draw.ellipse(
            (fpx - r_outer_pt + 1, fpy - r_outer_pt + 2,
             fpx + r_outer_pt + 1, fpy + r_outer_pt + 2),
            fill=(0, 0, 0, _scaled_alpha(70, alpha_factor)),
        )
        draw.ellipse(
            (fpx - r_outer_pt, fpy - r_outer_pt,
             fpx + r_outer_pt, fpy + r_outer_pt),
            fill=(255, 80, 0, _scaled_alpha(90, alpha_factor)),
        )
        draw.ellipse(
            (fpx - r_inner_pt, fpy - r_inner_pt,
             fpx + r_inner_pt, fpy + r_inner_pt),
            fill=(220, 30, 0, _scaled_alpha(255, alpha_factor)),
            outline=(255, 255, 255, _scaled_alpha(230, alpha_factor)),
            width=1,
        )


def test_moving_marker_is_about_four_times_bigger_and_half_alpha():
    points = [
        {'lat': 0.0, 'lon': 0.0, 'name': 'A'},  # static
        {'lat': 0.0, 'lon': 0.0, 'name': 'B'},  # static
        {'lat': 0.0, 'lon': 0.0, 'name': 'Current',
         'is_moving': True,
         'marker_scale': MOVING_POINT_SCALE,
         'marker_alpha': MOVING_POINT_ALPHA},
    ]
    px_positions = [(100.0, 100.0), (300.0, 100.0), (500.0, 100.0)]

    draw = _RecordingDraw()
    _render_markers(draw, points, px_positions, map_w=1024, map_h=512,
                    tile_px=256, TILE_SIZE=256)

    # 3 markers x 3 ellipses (shadow + halo + inner) = 9 calls
    assert len(draw.ellipses) == 9

    # Group ellipses per marker (rendered in input order)
    by_marker = [draw.ellipses[i * 3:(i + 1) * 3] for i in range(3)]
    static_halo = by_marker[0][1]
    moving_halo = by_marker[2][1]

    def _diag(bbox):
        x0, y0, x1, y1 = bbox
        return ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5

    static_diag = _diag(static_halo['bbox'])
    moving_diag = _diag(moving_halo['bbox'])

    # Moving marker should be ~4x larger (allow small rounding tolerance)
    ratio = moving_diag / static_diag
    assert abs(ratio - MOVING_POINT_SCALE) < 0.05, (
        f"expected ~{MOVING_POINT_SCALE}x, got {ratio:.3f}"
    )

    # Static markers keep full alpha; moving marker is at ~half alpha
    assert static_halo['fill'][3] == 90
    assert moving_halo['fill'][3] == _scaled_alpha(90, MOVING_POINT_ALPHA) == 45

    # Inner dot of moving marker should be at ~half alpha too
    moving_inner = by_marker[2][2]
    static_inner = by_marker[0][2]
    assert static_inner['fill'][3] == 255
    assert moving_inner['fill'][3] == 128


def test_coordinate_examples_gps_simulator_flags_moving():
    """The GPSMovementSimulator should mark its objects as ``is_moving=True``
    so the Map node renders them with the enlarged translucent style."""
    from node.InputNode.node_coordinate_examples import GPSMovementSimulator

    sim = GPSMovementSimulator(num_objects=2)
    coords = sim.get_coordinates()
    assert coords, "simulator should produce at least one coordinate"
    assert all(c.get('is_moving') is True for c in coords)


if __name__ == '__main__':
    # Allow running the file directly
    import pytest
    sys.exit(pytest.main([__file__, '-v']))
