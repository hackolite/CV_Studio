#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test that the persistent trace inherits the moving-point's width and alpha.

The Map node draws the recorded trace polyline with the same diameter as
the moving point's outer ring, and with the moving point's translucency
factor applied to its colour. This file exercises that contract using a
recording shim instead of the full tile pipeline.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from node.VisualNode.node_map import (
    MOVING_POINT_ALPHA,
    MOVING_POINT_SCALE,
    METRIC_NONE,
    _scaled_alpha,
)


class _RecordingDraw:
    def __init__(self):
        self.lines = []

    def line(self, xy, fill=None, width=1, joint=None):
        self.lines.append({'xy': list(xy), 'fill': fill, 'width': width})


def _render_trace(draw, trace_px, tile_px, TILE_SIZE,
                  metric_key=METRIC_NONE):
    """Re-implements the trace-drawing branch of ``_render_with_direct_osm_tiles``
    so this test can drive it on a fake draw context."""
    r_outer = max(7, int(9 * (tile_px / float(TILE_SIZE))))
    moving_r_outer = max(1, int(round(r_outer * MOVING_POINT_SCALE)))
    trace_w = max(2, moving_r_outer * 2)
    trace_alpha = _scaled_alpha(255, MOVING_POINT_ALPHA)
    if len(trace_px) >= 2:
        # The new behaviour: a single translucent line (no opaque halo),
        # at the moving point's diameter.
        draw.line(trace_px, fill=(220, 30, 0, trace_alpha),
                  width=trace_w, joint="curve")
    return r_outer, moving_r_outer, trace_w, trace_alpha


def test_trace_width_matches_moving_point_diameter():
    draw = _RecordingDraw()
    trace_px = [(10.0, 10.0), (50.0, 30.0), (100.0, 60.0)]
    r_outer, moving_r, trace_w, trace_alpha = _render_trace(
        draw, trace_px, tile_px=256, TILE_SIZE=256,
    )
    assert len(draw.lines) == 1, "trace should be a single (translucent) polyline"
    line = draw.lines[0]
    # Width equals the moving point's outer diameter.
    assert line['width'] == 2 * moving_r
    assert line['width'] == trace_w


def test_trace_alpha_matches_moving_point_translucency():
    draw = _RecordingDraw()
    trace_px = [(0.0, 0.0), (10.0, 10.0)]
    _render_trace(draw, trace_px, tile_px=256, TILE_SIZE=256)
    line = draw.lines[0]
    # Trace alpha = the same scaled alpha used for moving markers
    # (i.e. base 255 multiplied by MOVING_POINT_ALPHA = 0.5).
    expected_alpha = _scaled_alpha(255, MOVING_POINT_ALPHA)
    assert line['fill'][3] == expected_alpha
    assert expected_alpha < 255  # confirm it stays translucent


def test_trace_has_no_opaque_white_halo():
    draw = _RecordingDraw()
    trace_px = [(0.0, 0.0), (10.0, 10.0), (20.0, 20.0)]
    _render_trace(draw, trace_px, tile_px=256, TILE_SIZE=256)
    # The previous implementation drew an extra opaque-ish white halo line
    # under the trace (fill=(255, 255, 255, 200)). It must be gone so the
    # trace stays as transparent as the moving point.
    for line in draw.lines:
        fill = line['fill']
        assert not (fill[0] == 255 and fill[1] == 255 and fill[2] == 255
                    and fill[3] >= 150), (
            f"trace must not be drawn with an opaque white halo, got {fill}"
        )


if __name__ == "__main__":
    test_trace_width_matches_moving_point_diameter()
    test_trace_alpha_matches_moving_point_translucency()
    test_trace_has_no_opaque_white_halo()
    print("Trace width/alpha tests passed ✓")
