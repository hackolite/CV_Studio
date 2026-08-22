#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Regression tests: deleting a node while its background thread is still
running must NOT crash (segfault / unhandled exception) on Linux.

Affected nodes:
- SystemSizingNode (_do_scan_and_compute calls dpg directly)
- VideoNode        (preprocess_thread / progress_callback call dpg directly)
- CopernicusMapNode (_fetch_worker calls dpg_set_value directly)

Fix: each node now exposes a _node_closed threading.Event that is set at the
start of close().  Background threads check this flag before calling any
DearPyGui API.
"""
import sys
import os
import threading
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Build a consistent dpg mock hierarchy before any project imports.
_dpg_mod = mock.MagicMock()
_dpg_root = mock.MagicMock()
_dpg_root.dearpygui = _dpg_mod
sys.modules['dearpygui'] = _dpg_root
sys.modules['dearpygui.dearpygui'] = _dpg_mod
sys.modules['cv2'] = mock.MagicMock()
sys.modules['numpy'] = mock.MagicMock()
sys.modules['yt_dlp'] = mock.MagicMock()
# node_system_sizing imports some optional libs
for _m in ('scipy', 'scipy.spatial', 'scipy.spatial.distance',
           'psutil', 'GPUtil', 'pynvml', 'PIL', 'PIL.Image',
           'PIL.ImageDraw', 'PIL.ImageFont',
           'matplotlib', 'matplotlib.pyplot', 'matplotlib.patches',
           'matplotlib.backends', 'matplotlib.backends.backend_agg',
           'librosa', 'soundfile'):
    sys.modules.setdefault(_m, mock.MagicMock())

_dpg = _dpg_mod   # alias used in tests


# ---------------------------------------------------------------------------
# SystemSizingNode
# ---------------------------------------------------------------------------

def test_system_sizing_node_closed_flag():
    from node.SystemNode.node_system_sizing import _Node
    node = _Node()
    assert not node._node_closed.is_set(), "_node_closed must start unset"
    node.close(node_id=1)
    assert node._node_closed.is_set(), "close() must set _node_closed"
    print("✓ SystemSizingNode: _node_closed flag works")


def test_system_sizing_no_dpg_calls_after_close():
    """_do_scan_and_compute must bail out if node is closed while scanning."""
    import node.SystemNode.node_system_sizing as nsz
    from node.SystemNode.node_system_sizing import _Node

    node = _Node()
    node.tag_node_name = "1:SystemSizing"
    node._opencv_setting_dict = {}
    node.tag_chart_texture = "1:SystemSizing:texture"

    scan_started = threading.Event()
    proceed_after_close = threading.Event()

    original_scan = nsz._scan_editor_nodes

    def slow_scan():
        scan_started.set()
        proceed_after_close.wait(timeout=5)
        return {"ai_nodes": [], "n_streams": 0, "n_vision_proc": 0, "n_audio_proc": 0}

    dpg_calls_after_close = []
    _dpg.reset_mock()

    with mock.patch.object(nsz, '_scan_editor_nodes', side_effect=slow_scan):
        # Start the scan in a background thread (as the node button would do)
        t = threading.Thread(target=nsz._do_scan_and_compute, args=(node,), daemon=True)
        t.start()

        assert scan_started.wait(timeout=2), "scan thread should have started"

        # Close the node (delete it)
        node.close(node_id=1)
        assert node._node_closed.is_set()

        # Intercept any dpg calls that happen after close — patch is active for
        # the entire remaining thread lifetime because the thread is still
        # blocked on proceed_after_close at this point.
        with mock.patch.object(nsz, 'dpg_set_value',
                               side_effect=lambda *a, **kw: dpg_calls_after_close.append(a)), \
             mock.patch.object(nsz.dpg, 'set_value',
                               side_effect=lambda *a, **kw: dpg_calls_after_close.append(a)):
            # Allow the scan to finish
            proceed_after_close.set()
            t.join(timeout=3)

    assert dpg_calls_after_close == [], (
        f"dpg calls made after close(): {dpg_calls_after_close}"
    )
    print("✓ SystemSizingNode: no dpg calls on deleted items after close()")


# ---------------------------------------------------------------------------
# VideoNode
# ---------------------------------------------------------------------------

def test_video_node_closed_flag():
    from node.InputNode.node_video import VideoNode
    node = VideoNode()
    assert not node._node_closed.is_set()
    node.close(node_id=1)
    assert node._node_closed.is_set()
    print("✓ VideoNode: _node_closed flag works")


def test_video_node_preprocess_thread_no_dpg_after_close():
    """preprocess_thread must not call dpg after node is deleted."""
    import node.InputNode.node_video as nv
    from node.InputNode.node_video import VideoNode

    node = VideoNode()
    node._opencv_setting_dict = {'audio_chunk_duration': 5.0, 'audio_chunk_step': 1.0}

    preprocess_started = threading.Event()
    proceed_after_close = threading.Event()

    dpg_calls_after_close = []

    def slow_preprocess(node_id, movie_path, chunk_duration, step_duration, progress_callback):
        preprocess_started.set()
        proceed_after_close.wait(timeout=5)
        # simulate a progress update
        progress_callback(0.5)

    with mock.patch.object(node, '_preprocess_video', side_effect=slow_preprocess):
        _dpg.configure_item.side_effect = None
        _dpg.does_item_exist.return_value = True

        # Start preprocessing
        node._trigger_preprocessing(
            node_id="1",
            tag_node_name="1:Video",
            movie_path="/tmp/fake.mp4",
        )

        assert preprocess_started.wait(timeout=2), "preprocess thread should start"

        # Delete the node
        node.close(node_id=1)
        assert node._node_closed.is_set()

        # Track dpg calls from this point on
        _dpg.configure_item.side_effect = lambda *a, **kw: dpg_calls_after_close.append(a)

        proceed_after_close.set()
        # Wait for preprocessing thread to finish
        for t in list(node._preprocessing_threads.values()):
            t.join(timeout=3)

    assert dpg_calls_after_close == [], (
        f"dpg.configure_item called after close(): {dpg_calls_after_close}"
    )
    print("✓ VideoNode: no dpg calls on deleted items after close()")


# ---------------------------------------------------------------------------
# CopernicusMapNode
# ---------------------------------------------------------------------------

def test_copernicus_node_closed_flag():
    # Mock heavy geo imports
    for m in ('sentinelhub', 'oauthlib', 'oauthlib.oauth2', 'requests', 'requests_oauthlib',
              'tifffile', 'imageio', 'concurrent', 'concurrent.futures'):
        sys.modules.setdefault(m, mock.MagicMock())

    from node.MapNode.node_copernicus_map import _Node
    node = _Node()
    assert not node._node_closed.is_set()
    node.close(node_id=1)
    assert node._node_closed.is_set()
    print("✓ CopernicusMapNode: _node_closed flag works")


def test_copernicus_fetch_worker_no_dpg_after_close():
    """_fetch_worker must not call dpg_set_value after the node is deleted."""
    for m in ('sentinelhub', 'oauthlib', 'oauthlib.oauth2', 'requests', 'requests_oauthlib',
              'tifffile', 'imageio', 'concurrent', 'concurrent.futures'):
        sys.modules.setdefault(m, mock.MagicMock())

    import node.MapNode.node_copernicus_map as nco
    from node.MapNode.node_copernicus_map import _Node

    node = _Node()

    fetch_started = threading.Event()
    proceed_after_close = threading.Event()
    dpg_calls_after_close = []

    def slow_bbox_tiles(lat, lon, radius):
        fetch_started.set()
        proceed_after_close.wait(timeout=5)
        return [], (0, 0, 0, 0)

    with mock.patch.object(nco, '_bbox_tiles', side_effect=slow_bbox_tiles):
        params = {
            "lat": 48.8566, "lon": 2.3522, "radius": 1,
            "source_name": "S2L2A", "cdse_id": "x",
            "evalscript": "", "es_hash": "x",
            "date_from": "2024-01-01", "date_to": "2024-01-31",
            "cloud": 30, "formula": "", "cmap": "RdYlGn",
            "true_color": False,
        }
        t = threading.Thread(
            target=node._fetch_worker,
            args=("1:CopernicusMap", params),
            daemon=True,
        )
        t.start()

        assert fetch_started.wait(timeout=2), "fetch thread should have started"
        node.close(node_id=1)
        assert node._node_closed.is_set()

        # Track dpg calls after close
        original_set_value = nco.dpg_set_value
        nco.dpg_set_value = lambda *a, **kw: dpg_calls_after_close.append(a)

        proceed_after_close.set()
        t.join(timeout=3)

        nco.dpg_set_value = original_set_value

    assert dpg_calls_after_close == [], (
        f"dpg_set_value called after close(): {dpg_calls_after_close}"
    )
    print("✓ CopernicusMapNode: no dpg calls on deleted items after close()")


if __name__ == '__main__':
    print("Testing node-deletion crash fix (all affected nodes)...")
    print("=" * 60)

    tests = [
        ("SystemSizingNode _node_closed flag",
         test_system_sizing_node_closed_flag),
        ("SystemSizingNode: no dpg after close",
         test_system_sizing_no_dpg_calls_after_close),
        ("VideoNode _node_closed flag",
         test_video_node_closed_flag),
        ("VideoNode: no dpg after close",
         test_video_node_preprocess_thread_no_dpg_after_close),
        ("CopernicusMapNode _node_closed flag",
         test_copernicus_node_closed_flag),
        ("CopernicusMapNode: no dpg after close",
         test_copernicus_fetch_worker_no_dpg_after_close),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"\n  {name}...")
        try:
            fn()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  ✗ FAILED: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
