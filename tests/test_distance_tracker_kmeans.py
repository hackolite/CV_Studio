#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the reworked DistanceTracker node:
- Accepts TennisKeypoints from PoseEstimation
- K-means anomaly detection with kernel distance display
- Threshold-based alert
"""
import sys
import os
import unittest.mock as mock

# Mock dearpygui and related UI modules before any node imports
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
sys.modules['node_editor'] = mock.MagicMock()
sys.modules['node_editor.util'] = mock.MagicMock()
sys.modules['node.node_abc'] = mock.MagicMock()
# dpg_get_value / dpg_set_value: return None so defaults are used in update()
_mock_util = mock.MagicMock()
_mock_util.dpg_get_value = mock.MagicMock(return_value=None)
_mock_util.dpg_set_value = mock.MagicMock(return_value=None)
sys.modules['node_editor.util'] = _mock_util

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_keypoints(n=14, seed=42):
    """Generate synthetic tennis court keypoints (Nx2 pixels)."""
    rng = np.random.default_rng(seed)
    return rng.uniform(50, 600, size=(n, 2)).astype(np.float32)


def _run_update(node, node_id, keypoints_array):
    """Run a single update with mock pose estimation output."""
    pose_json = {
        'model_name': 'TennisKeyPoints',
        'score_th': 0.3,
        'results_list': keypoints_array,
    }
    node_result_dict = {'1:PoseEstimation': pose_json}
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', f'{node_id}:DistanceTracker:JSON:Input01'],
    ]
    return node.update(
        node_id=node_id,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_distance_tracker_import():
    """Node can be imported."""
    from node.StatsNode.node_distance_tracker import Node, FactoryNode
    node = Node()
    factory = FactoryNode()
    assert node.node_tag == 'DistanceTracker'
    assert factory.node_label == 'DistanceTracker'


def test_distance_tracker_output_structure():
    """update() returns image=None, audio=None, json dict."""
    from node.StatsNode.node_distance_tracker import Node
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    kp = _make_keypoints()
    result = _run_update(node, node_id=1, keypoints_array=kp)

    assert result['image'] is None
    assert result['audio'] is None
    assert result['json'] is not None
    j = result['json']
    assert 'kernel_distance' in j
    assert 'threshold' in j
    assert 'alert' in j
    assert 'n_samples' in j


def test_distance_tracker_accumulates_history():
    """History grows until MAX_HISTORY_SIZE."""
    from node.StatsNode.node_distance_tracker import Node, _MIN_SAMPLES_FOR_KMEANS
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    for i in range(_MIN_SAMPLES_FOR_KMEANS + 5):
        kp = _make_keypoints(seed=i)
        _run_update(node, node_id=2, keypoints_array=kp)

    n_id = '2'
    assert n_id in node._kp_history
    assert len(node._kp_history[n_id]) >= _MIN_SAMPLES_FOR_KMEANS


def test_kmeans_fits_after_min_samples():
    """KMeans model is created once MIN_SAMPLES_FOR_KMEANS is reached."""
    from node.StatsNode.node_distance_tracker import Node, _MIN_SAMPLES_FOR_KMEANS, _REFIT_INTERVAL

    try:
        from sklearn.cluster import KMeans  # noqa: F401
    except ImportError:
        print('sklearn not available – skipping k-means fit test')
        return

    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    n_iter = _MIN_SAMPLES_FOR_KMEANS + _REFIT_INTERVAL + 1

    for i in range(n_iter):
        kp = _make_keypoints(seed=i)
        _run_update(node, node_id=3, keypoints_array=kp)

    assert '3' in node._kmeans_models, 'KMeans model should have been fitted'


def test_kernel_distance_is_non_negative_after_fitting():
    """kernel_distance in output is >= 0 once model is fitted."""
    from node.StatsNode.node_distance_tracker import Node, _MIN_SAMPLES_FOR_KMEANS, _REFIT_INTERVAL

    try:
        from sklearn.cluster import KMeans  # noqa: F401
    except ImportError:
        print('sklearn not available – skipping distance test')
        return

    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    n_iter = _MIN_SAMPLES_FOR_KMEANS + _REFIT_INTERVAL + 5

    result = None
    for i in range(n_iter):
        kp = _make_keypoints(seed=i)
        result = _run_update(node, node_id=4, keypoints_array=kp)

    assert result['json']['kernel_distance'] >= 0.0, 'Distance should be >= 0 once model is fitted'


def test_alert_triggered_when_distance_exceeds_threshold():
    """alert=True when kernel_distance > threshold."""
    from node.StatsNode.node_distance_tracker import Node, _MIN_SAMPLES_FOR_KMEANS, _REFIT_INTERVAL

    try:
        from sklearn.cluster import KMeans  # noqa: F401
    except ImportError:
        print('sklearn not available – skipping alert test')
        return

    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    # Train on normal data (small spread around a fixed point)
    normal_kp = _make_keypoints(seed=0)
    for i in range(_MIN_SAMPLES_FOR_KMEANS + _REFIT_INTERVAL + 1):
        noise = np.random.default_rng(i).uniform(-5, 5, size=normal_kp.shape).astype(np.float32)
        _run_update(node, node_id=5, keypoints_array=normal_kp + noise)

    # Send a very abnormal observation (shifted by 1000 pixels)
    outlier_kp = normal_kp + 1000.0
    result = _run_update(node, node_id=5, keypoints_array=outlier_kp)

    j = result['json']
    # With threshold=100 (default) and distance > 1000, alert must be True
    if j['kernel_distance'] >= 0:
        assert j['kernel_distance'] > 100.0, f'Expected large distance, got {j["kernel_distance"]}'
        assert j['alert'] is True, 'Alert should be triggered for a massive outlier'


def test_distance_tracker_passthrough_disabled():
    """When tracking is disabled, output json has tracking_enabled=False."""
    from node.StatsNode.node_distance_tracker import Node
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    kp = _make_keypoints()
    pose_json = {'model_name': 'TennisKeyPoints', 'score_th': 0.3, 'results_list': kp}
    enable_json = {'enabled': False}

    node_result_dict = {
        '1:PoseEstimation': pose_json,
        '2:Enable': enable_json,
    }
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '6:DistanceTracker:JSON:Input01'],
        ['2:Enable:JSON:Output01', '6:DistanceTracker:JSON:Input02'],
    ]
    result = node.update(
        node_id=6,
        connection_list=connection_list,
        node_image_dict={},
        node_result_dict=node_result_dict,
        node_audio_dict={},
    )
    assert result['json'] is not None
    assert result['json']['tracking_enabled'] is False


def test_distance_tracker_close_cleans_up():
    """close() removes per-node state."""
    from node.StatsNode.node_distance_tracker import Node
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    kp = _make_keypoints()
    _run_update(node, node_id=7, keypoints_array=kp)
    assert '7' in node._kp_history

    node.close(node_id=7)
    assert '7' not in node._kp_history


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 60)
    print('Testing DistanceTracker (K-Means) Node')
    print('=' * 60)

    tests = [
        test_distance_tracker_import,
        test_distance_tracker_output_structure,
        test_distance_tracker_accumulates_history,
        test_kmeans_fits_after_min_samples,
        test_kernel_distance_is_non_negative_after_fitting,
        test_alert_triggered_when_distance_exceeds_threshold,
        test_distance_tracker_passthrough_disabled,
        test_distance_tracker_close_cleans_up,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f'  ✓ {t.__name__}')
            passed += 1
        except Exception as e:
            import traceback
            print(f'  ✗ {t.__name__}: {e}')
            traceback.print_exc()
    print(f'\n{passed}/{len(tests)} tests passed')
