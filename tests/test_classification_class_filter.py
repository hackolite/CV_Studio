#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests verifying that:
1. All built-in classification models expose their correct classes in
   _model_class_name_dict (the source for the class-filter dropdown).
2. get_setting_dict saves the class filter selection.
3. set_setting_dict restores the correct class filter items and selection.
4. The Node Chart receives the correct class_names from the classification
   result dict when a classification node is connected.
"""

import sys
import os
import unittest
import unittest.mock as mock

# Ensure repository root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Mock heavy C-extension / GUI dependencies so they never need to be present.
# ---------------------------------------------------------------------------
_MOCKS = [
    'numpy', 'cv2', 'onnxruntime',
    'dearpygui', 'dearpygui.dearpygui',
    'node_editor', 'node_editor.util',
    'src', 'src.utils', 'src.utils.logging', 'src.utils.gpu_utils',
]
for _m in _MOCKS:
    sys.modules.setdefault(_m, mock.MagicMock())

# Provide real dpg_get/set_value stubs used by the production code
_node_editor_util = sys.modules['node_editor.util']
_node_editor_util.dpg_get_value = mock.MagicMock(return_value='')
_node_editor_util.dpg_set_value = mock.MagicMock()

from node.DLNode.node_classification import Node
from node.DLNode.classification.imagenet_class_names import imagenet_class_names
from node.DLNode.classification.esc50_class_names import esc50_class_names


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_BUILTIN_MODEL_CLASS_NAMES = {
    'MobileNetV3 Small': imagenet_class_names,
    'MobileNetV3 Large': imagenet_class_names,
    'EfficientNet B0':   imagenet_class_names,
    'ResNet50':          imagenet_class_names,
    'Yolo-cls':          esc50_class_names,
    'Gender Recognition':   {0: 'Male', 1: 'Female'},
    'Pedestrian Gender':    {0: 'Male', 1: 'Female'},
}


# ===========================================================================
# 1. Class-name correctness for every built-in model
# ===========================================================================
class TestBuiltinModelClassNames(unittest.TestCase):
    """Each built-in model must be registered in all three class-level dicts."""

    def test_all_builtin_models_in_model_class(self):
        for name in _BUILTIN_MODEL_CLASS_NAMES:
            self.assertIn(name, Node._model_class,
                          f"'{name}' missing from Node._model_class")

    def test_all_builtin_models_in_model_path_setting(self):
        for name in _BUILTIN_MODEL_CLASS_NAMES:
            self.assertIn(name, Node._model_path_setting,
                          f"'{name}' missing from Node._model_path_setting")

    def test_all_builtin_models_in_class_name_dict(self):
        for name in _BUILTIN_MODEL_CLASS_NAMES:
            self.assertIn(name, Node._model_class_name_dict,
                          f"'{name}' missing from Node._model_class_name_dict")

    def test_imagenet_models_use_imagenet_classes(self):
        for name in ('MobileNetV3 Small', 'MobileNetV3 Large', 'EfficientNet B0', 'ResNet50'):
            self.assertIs(Node._model_class_name_dict[name], imagenet_class_names,
                          f"'{name}' should use imagenet_class_names")

    def test_yolo_cls_uses_esc50_classes(self):
        self.assertIs(Node._model_class_name_dict['Yolo-cls'], esc50_class_names)
        self.assertEqual(len(Node._model_class_name_dict['Yolo-cls']), 50)

    def test_gender_models_have_two_classes(self):
        for name in ('Gender Recognition', 'Pedestrian Gender'):
            d = Node._model_class_name_dict[name]
            self.assertEqual(len(d), 2)
            self.assertIn(0, d)
            self.assertIn(1, d)


# ===========================================================================
# 2. _build_class_filter_items
# ===========================================================================
class TestBuildClassFilterItems(unittest.TestCase):

    def test_returns_all_plus_sorted_entries(self):
        names = {0: 'cat', 2: 'dog', 1: 'bird'}
        items = Node._build_class_filter_items(names)
        self.assertEqual(items[0], 'All')
        self.assertEqual(items[1], '0: cat')
        self.assertEqual(items[2], '1: bird')
        self.assertEqual(items[3], '2: dog')

    def test_empty_dict_returns_all_only(self):
        items = Node._build_class_filter_items({})
        self.assertEqual(items, ['All'])


# ===========================================================================
# 3. get_setting_dict saves class filter; set_setting_dict restores it
# ===========================================================================
_CLS_MODULE = 'node.DLNode.node_classification'


class TestSettingDictClassFilter(unittest.TestCase):
    """
    Simulate a node restore: verify that set_setting_dict correctly rebuilds
    the class-filter dropdown items and restores the previously-saved value.
    """

    def _make_node_id(self):
        return '99'

    def test_get_setting_dict_includes_class_filter(self):
        """get_setting_dict must save the class filter tag."""
        node_id = self._make_node_id()
        tag_node_name = f"{node_id}:Classification"
        tag_class_filter_value = f"{tag_node_name}:TEXT:ClassFilterValue"
        tag_input02_value = f"{tag_node_name}:TEXT:Input02Value"

        get_value_map = {
            tag_input02_value: 'Gender Recognition',
            tag_class_filter_value: '1: Female',
            f"{tag_node_name}:FLOAT:ScoreThresholdValue": 0.5,
            f"{tag_node_name}:INT:BboxThicknessValue": 2,
            f"{tag_node_name}:INT:BatchSizeValue": 1,
        }

        with mock.patch(f'{_CLS_MODULE}.dpg_get_value', side_effect=lambda t: get_value_map.get(t, '')), \
             mock.patch(f'{_CLS_MODULE}.dpg') as dpg_mock:
            dpg_mock.get_item_pos.return_value = [0, 0]

            n = Node()
            n.tag_node_name = tag_node_name
            n.tag_delete_btn = tag_node_name + ':DeleteONNX'

            result = n.get_setting_dict(node_id)

        self.assertIn(tag_class_filter_value, result,
                      "get_setting_dict must include the class filter tag")
        self.assertEqual(result[tag_class_filter_value], '1: Female')

    def test_set_setting_dict_rebuilds_class_filter_items(self):
        """
        set_setting_dict must call dpg.configure_item on the class filter combo
        with the items for the restored model.
        """
        node_id = self._make_node_id()
        tag_node_name = f"{node_id}:Classification"
        tag_input02_value = f"{tag_node_name}:TEXT:Input02Value"
        tag_class_filter_value = f"{tag_node_name}:TEXT:ClassFilterValue"

        setting_dict = {
            tag_input02_value: 'Gender Recognition',
            tag_class_filter_value: '1: Female',
            f"{tag_node_name}:FLOAT:ScoreThresholdValue": 0.5,
            f"{tag_node_name}:INT:BboxThicknessValue": 2,
        }

        with mock.patch(f'{_CLS_MODULE}.dpg_set_value') as set_value_mock, \
             mock.patch(f'{_CLS_MODULE}.dpg') as dpg_mock:

            n = Node()
            n.tag_node_name = tag_node_name
            n.tag_delete_btn = tag_node_name + ':DeleteONNX'

            n.set_setting_dict(node_id, setting_dict)

            # configure_item must have been called with the class filter tag
            calls_for_filter = [
                c for c in dpg_mock.configure_item.call_args_list
                if c.args and c.args[0] == tag_class_filter_value
            ]
            self.assertTrue(
                len(calls_for_filter) >= 1,
                "dpg.configure_item must be called for the class filter combo to rebuild items",
            )
            # The items must include gender classes
            items_kwarg = calls_for_filter[0].kwargs.get('items', [])
            self.assertIn('All', items_kwarg)
            self.assertIn('0: Male', items_kwarg)
            self.assertIn('1: Female', items_kwarg)

    def test_set_setting_dict_restores_saved_filter_value(self):
        """
        set_setting_dict must call dpg_set_value on the class filter combo
        with the saved value.
        """
        node_id = self._make_node_id()
        tag_node_name = f"{node_id}:Classification"
        tag_input02_value = f"{tag_node_name}:TEXT:Input02Value"
        tag_class_filter_value = f"{tag_node_name}:TEXT:ClassFilterValue"

        saved_filter = '1: Female'
        setting_dict = {
            tag_input02_value: 'Gender Recognition',
            tag_class_filter_value: saved_filter,
            f"{tag_node_name}:FLOAT:ScoreThresholdValue": 0.5,
            f"{tag_node_name}:INT:BboxThicknessValue": 2,
        }

        set_value_calls = []

        with mock.patch(f'{_CLS_MODULE}.dpg_set_value',
                        side_effect=lambda t, v: set_value_calls.append((t, v))), \
             mock.patch(f'{_CLS_MODULE}.dpg'):

            n = Node()
            n.tag_node_name = tag_node_name
            n.tag_delete_btn = tag_node_name + ':DeleteONNX'

            n.set_setting_dict(node_id, setting_dict)

        filter_set_calls = [v for t, v in set_value_calls if t == tag_class_filter_value]
        self.assertTrue(
            len(filter_set_calls) >= 1,
            "dpg_set_value must be called to restore the class filter value",
        )
        self.assertEqual(filter_set_calls[-1], saved_filter,
                         "The restored class filter value must match the saved one")

    def test_set_setting_dict_defaults_to_all_when_not_saved(self):
        """
        Older session files have no class filter entry.  set_setting_dict
        must fall back to 'All'.
        """
        node_id = self._make_node_id()
        tag_node_name = f"{node_id}:Classification"
        tag_input02_value = f"{tag_node_name}:TEXT:Input02Value"
        tag_class_filter_value = f"{tag_node_name}:TEXT:ClassFilterValue"

        set_value_calls = []

        # No tag_class_filter_value key in the dict (old session)
        setting_dict = {
            tag_input02_value: 'ResNet50',
            f"{tag_node_name}:FLOAT:ScoreThresholdValue": 0.3,
            f"{tag_node_name}:INT:BboxThicknessValue": 2,
        }

        with mock.patch(f'{_CLS_MODULE}.dpg_set_value',
                        side_effect=lambda t, v: set_value_calls.append((t, v))), \
             mock.patch(f'{_CLS_MODULE}.dpg'):

            n = Node()
            n.tag_node_name = tag_node_name
            n.tag_delete_btn = tag_node_name + ':DeleteONNX'

            n.set_setting_dict(node_id, setting_dict)

        filter_set_calls = [v for t, v in set_value_calls if t == tag_class_filter_value]
        self.assertTrue(
            len(filter_set_calls) >= 1,
            "dpg_set_value must be called to set a default class filter value",
        )
        self.assertEqual(filter_set_calls[-1], 'All',
                         "Default class filter value must be 'All' when not saved")


# ===========================================================================
# 4. Classification result dict always contains class_names for chart nodes
# ===========================================================================
class TestClassificationResultContainsClassNames(unittest.TestCase):
    """
    The JSON result emitted by the classification node must always carry
    a non-empty 'class_names' dict so that connected chart nodes can populate
    their class-slot dropdowns correctly.
    """

    def test_all_builtin_models_have_non_empty_class_names(self):
        for model_name, expected_names in _BUILTIN_MODEL_CLASS_NAMES.items():
            names = Node._model_class_name_dict.get(model_name, {})
            self.assertTrue(
                len(names) > 0,
                f"Node._model_class_name_dict['{model_name}'] must not be empty"
            )

    def test_imagenet_has_1000_classes(self):
        for name in ('MobileNetV3 Small', 'MobileNetV3 Large', 'EfficientNet B0', 'ResNet50'):
            self.assertEqual(
                len(Node._model_class_name_dict[name]), 1000,
                f"'{name}' should have 1000 ImageNet classes"
            )

    def test_esc50_has_50_classes(self):
        self.assertEqual(len(Node._model_class_name_dict['Yolo-cls']), 50)


if __name__ == '__main__':
    unittest.main(verbosity=2)
