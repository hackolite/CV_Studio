#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Homography node sport template combobox and multi-sport templates.
"""
import sys
import os
import unittest.mock as mock

# Mock dearpygui and related UI modules before any node imports
sys.modules['dearpygui'] = mock.MagicMock()
sys.modules['dearpygui.dearpygui'] = mock.MagicMock()
sys.modules['node_editor'] = mock.MagicMock()
_mock_util = mock.MagicMock()
_mock_util.dpg_get_value = mock.MagicMock(return_value=None)
_mock_util.dpg_set_value = mock.MagicMock(return_value=None)
sys.modules['node_editor.util'] = _mock_util
sys.modules['node.node_abc'] = mock.MagicMock()

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def _mock_detected_keypoints():
    """14 keypoints representing a detected tennis court in image coords."""
    return np.array([
        [100, 500], [700, 500], [700, 50],  [100, 50],
        [200, 500], [600, 500], [600, 50],  [200, 50],
        [200, 400], [600, 400], [200, 150], [600, 150],
        [400, 400], [400, 150],
    ], dtype=np.float32)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sport_templates_present():
    """All three sport templates are accessible."""
    from node.StatsNode.node_homography import Node
    assert 'Tennis' in Node.SPORT_TEMPLATES
    assert 'Badminton' in Node.SPORT_TEMPLATES
    assert 'Paddle' in Node.SPORT_TEMPLATES


def test_each_template_has_14_keypoints():
    """Every sport template has exactly 14 keypoints (matching TennisKeyPoints model output)."""
    from node.StatsNode.node_homography import Node
    for sport, template in Node.SPORT_TEMPLATES.items():
        n = len(template['keypoints'])
        assert n == 14, f'{sport} template has {n} keypoints, expected 14'


def test_each_template_has_required_fields():
    """Each template has sport, units, court_width, court_length fields."""
    from node.StatsNode.node_homography import Node
    for sport, template in Node.SPORT_TEMPLATES.items():
        assert 'sport' in template, f'{sport} template missing "sport" field'
        assert 'units' in template, f'{sport} template missing "units" field'
        assert 'court_width' in template, f'{sport} template missing "court_width" field'
        assert 'court_length' in template, f'{sport} template missing "court_length" field'


def test_tennis_template_unchanged():
    """Tennis template keypoints are unchanged."""
    from node.StatsNode.node_homography import Node
    t = Node.TENNIS_COURT_TEMPLATE
    assert t['keypoints'][2]['name'] == 'near_baseline_left_double_corner'
    assert t['keypoints'][2]['x'] == 0.00
    assert t['keypoints'][2]['y'] == 0.00
    assert t['keypoints'][0]['x'] == 1.37
    assert t['keypoints'][0]['y'] == 23.77


def test_badminton_template_dimensions():
    """Badminton template has official court dimensions."""
    from node.StatsNode.node_homography import Node
    t = Node.BADMINTON_COURT_TEMPLATE
    assert abs(t['court_width'] - 6.1) < 0.01
    assert abs(t['court_length'] - 13.4) < 0.01


def test_paddle_template_dimensions():
    """Paddle template has official court dimensions."""
    from node.StatsNode.node_homography import Node
    t = Node.PADDLE_COURT_TEMPLATE
    assert abs(t['court_width'] - 10.0) < 0.01
    assert abs(t['court_length'] - 20.0) < 0.01


def test_homography_works_for_all_sports():
    """_calculate_homography succeeds for all three sport templates."""
    from node.StatsNode.node_homography import Node
    detected = _mock_detected_keypoints()

    for sport, template in Node.SPORT_TEMPLATES.items():
        node = Node()
        node._opencv_setting_dict = {'use_pref_counter': False}
        node._selected_template = template
        H = node._calculate_homography(detected)
        assert H is not None, f'Homography failed for sport: {sport}'
        assert H.shape == (3, 3), f'Wrong shape for sport: {sport}'


def test_update_uses_selected_sport_template():
    """update() output includes the correct sport template."""
    from node.StatsNode.node_homography import Node
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}

    detected = _mock_detected_keypoints()
    master_json = {'model_name': 'TennisKeyPoints', 'score_th': 0.3, 'results_list': detected}
    node_result_dict = {'1:PoseEstimation': master_json}
    connection_list = [
        ['1:PoseEstimation:JSON:Output03', '2:Homography:JSON:Input01'],
    ]

    for sport in ('Tennis', 'Badminton', 'Paddle'):
        # Simulate combobox selection by pre-setting _selected_template
        node._selected_template = Node.SPORT_TEMPLATES[sport]
        result = node.update(
            node_id=2,
            connection_list=connection_list,
            node_image_dict={},
            node_result_dict=node_result_dict,
            node_audio_dict={},
        )
        assert result['json'] is not None, f'No JSON output for sport: {sport}'
        assert result['json']['template']['sport'] == sport, \
            f'Template sport mismatch for {sport}'


def test_point_transformation_for_badminton():
    """Points transform into the badminton court coordinate range."""
    from node.StatsNode.node_homography import Node
    node = Node()
    node._opencv_setting_dict = {'use_pref_counter': False}
    node._selected_template = Node.BADMINTON_COURT_TEMPLATE

    detected = _mock_detected_keypoints()
    H = node._calculate_homography(detected)
    assert H is not None

    # A point roughly in the middle of the image
    test_point = np.array([[400.0, 275.0]], dtype=np.float32)
    transformed = node._transform_points(test_point, H)
    assert transformed is not None
    print(f'  Badminton transformed point: {transformed[0]}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('=' * 60)
    print('Testing Homography Sport Templates')
    print('=' * 60)

    tests = [
        test_sport_templates_present,
        test_each_template_has_14_keypoints,
        test_each_template_has_required_fields,
        test_tennis_template_unchanged,
        test_badminton_template_dimensions,
        test_paddle_template_dimensions,
        test_homography_works_for_all_sports,
        test_update_uses_selected_sport_template,
        test_point_transformation_for_badminton,
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
