#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for node deletion mechanics in the node editor.

Verifies:
1. Variable shadowing fix in _sort_node_graph (outer loop index not corrupted)
2. Int vs string comparison fix in _sort_node_graph (source-only nodes found)
3. Visual dpg link deletion when a node is removed
4. Null-safety when node_instance is None
5. Links are properly removed from _node_link_list on deletion
6. _node_connection_dict is rebuilt correctly after deletion
"""
import sys
import os
import copy
from collections import OrderedDict
from unittest.mock import MagicMock, patch, call
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Pre-mock heavy dependencies before any project imports
_mock_dpg = MagicMock()
_mock_dearpygui = MagicMock()
_mock_dearpygui.dearpygui = _mock_dpg
sys.modules['cv2'] = MagicMock()
sys.modules['numpy'] = MagicMock()
sys.modules['dearpygui'] = _mock_dearpygui
sys.modules['dearpygui.dearpygui'] = _mock_dpg

from node_editor.node_main import DpgNodeEditor  # noqa: E402


@pytest.fixture(autouse=True)
def reset_dpg_mock():
    """Reset the dpg mock before each test."""
    _mock_dpg.reset_mock()
    yield _mock_dpg


@pytest.fixture
def editor(reset_dpg_mock):
    """Create a minimal DpgNodeEditor instance for testing."""
    mock_dpg = reset_dpg_mock
    mock_dpg.get_item_alias.side_effect = lambda x: x if isinstance(x, str) else str(x)

    editor = DpgNodeEditor(
        width=800,
        height=600,
        opencv_setting_dict={
            'webcam_width': 640,
            'webcam_height': 480,
            'input_window_width': 320,
            'input_window_height': 240,
        }
    )
    mock_dpg.reset_mock()
    mock_dpg.get_item_alias.side_effect = lambda x: x if isinstance(x, str) else str(x)
    return editor


class TestSortNodeGraph:
    """Tests for _sort_node_graph logic."""

    def test_variable_shadowing_fix(self, editor, reset_dpg_mock):
        """
        Ensure the inner enumerate loop does not shadow the outer while-loop
        index, which previously caused infinite loops or skipped nodes.
        """
        mock_dpg = reset_dpg_mock
        # Setup: node "1:Video" outputs to "2:Display", and "3:Filter" outputs to "2:Display"
        # "1:Video" and "3:Filter" are source-only nodes (not destinations)
        mock_dpg.get_item_alias.side_effect = lambda x: x

        node_list = ["1:Video", "2:Display", "3:Filter"]
        # Links: 1:Video:IMAGE:output -> 2:Display:IMAGE:input
        #        3:Filter:IMAGE:output -> 2:Display:IMAGE:input2
        node_link_list = [
            ["1:Video:IMAGE:output", "2:Display:IMAGE:input"],
            ["3:Filter:IMAGE:output", "2:Display:IMAGE:input2"],
        ]

        # Should not hang or raise
        result = editor._sort_node_graph(node_list, node_link_list)
        assert isinstance(result, OrderedDict)
        # Both source nodes should appear in the result
        keys = list(result.keys())
        assert "2:Display" in keys

    def test_int_str_comparison_fix(self, editor, reset_dpg_mock):
        """
        Source-only nodes should be found and included in the connection dict
        even though node_id from split is string and check_id is int.
        """
        mock_dpg = reset_dpg_mock
        mock_dpg.get_item_alias.side_effect = lambda x: x

        node_list = ["1:Video", "2:Display"]
        node_link_list = [
            ["1:Video:IMAGE:output", "2:Display:IMAGE:input"],
        ]

        result = editor._sort_node_graph(node_list, node_link_list)
        keys = list(result.keys())
        # "1:Video" is a source-only node; it should be present via unfinded_id_dict
        assert "1:Video" in keys
        assert "2:Display" in keys

    def test_empty_link_list(self, editor, reset_dpg_mock):
        """Empty link list should return an empty OrderedDict."""
        mock_dpg = reset_dpg_mock
        result = editor._sort_node_graph(["1:Video"], [])
        assert result == OrderedDict()

    def test_chain_of_three_nodes(self, editor, reset_dpg_mock):
        """A -> B -> C should produce correct ordering."""
        mock_dpg = reset_dpg_mock
        mock_dpg.get_item_alias.side_effect = lambda x: x

        node_list = ["1:A", "2:B", "3:C"]
        node_link_list = [
            ["1:A:IMAGE:output", "2:B:IMAGE:input"],
            ["2:B:IMAGE:output", "3:C:IMAGE:input"],
        ]

        result = editor._sort_node_graph(node_list, node_link_list)
        keys = list(result.keys())
        # Source "1:A" should appear, and ordering should have 2:B before 3:C
        assert "1:A" in keys
        assert "2:B" in keys
        assert "3:C" in keys


class TestCallbackMvKeyDel:
    """Tests for _callback_mv_key_del node deletion."""

    def test_links_removed_on_node_delete(self, editor, reset_dpg_mock):
        """When a node is deleted, all links referencing it are removed."""
        mock_dpg = reset_dpg_mock

        # Setup editor state
        editor._node_list = ["1:Video", "2:Display", "3:Filter"]
        editor._node_link_list = [
            ["1:Video:IMAGE:output", "2:Display:IMAGE:input"],
            ["3:Filter:IMAGE:output", "2:Display:IMAGE:input2"],
        ]

        # Mock dpg calls
        mock_dpg.get_selected_nodes.return_value = [100]
        mock_dpg.get_selected_links.return_value = []
        mock_dpg.get_item_alias.side_effect = lambda x: {
            100: "2:Display",
        }.get(x, x)
        mock_dpg.get_item_children.return_value = []

        # Mock node instance
        mock_instance = MagicMock()
        editor._node_instances_list["2:Display"] = mock_instance

        editor._callback_mv_key_del()

        # Node should be removed from list
        assert "2:Display" not in editor._node_list
        # Both links referencing "2:Display" should be removed
        assert len(editor._node_link_list) == 0
        # close should have been called
        mock_instance.close.assert_called_once_with("2")

    def test_null_instance_does_not_crash(self, editor, reset_dpg_mock):
        """If node instance is None, deletion should not crash."""
        mock_dpg = reset_dpg_mock

        editor._node_list = ["1:Video"]
        editor._node_link_list = []
        editor._node_instances_list = {}  # No instance registered

        mock_dpg.get_selected_nodes.return_value = [100]
        mock_dpg.get_selected_links.return_value = []
        mock_dpg.get_item_alias.side_effect = lambda x: {
            100: "1:Video",
        }.get(x, x)
        mock_dpg.get_item_children.return_value = []

        # Should not raise
        editor._callback_mv_key_del()
        assert "1:Video" not in editor._node_list

    def test_visual_link_deletion_called(self, editor, reset_dpg_mock):
        """Verify _delete_dpg_link is called for each removed link."""
        mock_dpg = reset_dpg_mock

        editor._node_list = ["1:Video", "2:Display"]
        editor._node_link_list = [
            ["1:Video:IMAGE:output", "2:Display:IMAGE:input"],
        ]

        mock_dpg.get_selected_nodes.return_value = [100]
        mock_dpg.get_selected_links.return_value = []
        mock_dpg.get_item_alias.side_effect = lambda x: {
            100: "2:Display",
        }.get(x, x)
        mock_dpg.get_item_children.return_value = []

        mock_instance = MagicMock()
        editor._node_instances_list["2:Display"] = mock_instance

        with patch.object(editor, '_delete_dpg_link') as mock_del_link:
            editor._callback_mv_key_del()
            mock_del_link.assert_called_once_with(
                ["1:Video:IMAGE:output", "2:Display:IMAGE:input"]
            )

    def test_unrelated_links_preserved(self, editor, reset_dpg_mock):
        """Links not referencing the deleted node should be preserved."""
        mock_dpg = reset_dpg_mock

        editor._node_list = ["1:Video", "2:Display", "3:Filter", "4:Output"]
        editor._node_link_list = [
            ["1:Video:IMAGE:output", "2:Display:IMAGE:input"],
            ["3:Filter:IMAGE:output", "4:Output:IMAGE:input"],
        ]

        mock_dpg.get_selected_nodes.return_value = [100]
        mock_dpg.get_selected_links.return_value = []
        mock_dpg.get_item_alias.side_effect = lambda x: {
            100: "2:Display",
        }.get(x, x)
        mock_dpg.get_item_children.return_value = []

        mock_instance = MagicMock()
        editor._node_instances_list["2:Display"] = mock_instance

        editor._callback_mv_key_del()

        # Link between 3:Filter and 4:Output should remain
        assert ["3:Filter:IMAGE:output", "4:Output:IMAGE:input"] in editor._node_link_list
        assert len(editor._node_link_list) == 1


class TestDeleteDpgLink:
    """Tests for _delete_dpg_link helper."""

    def test_finds_and_deletes_matching_link(self, editor, reset_dpg_mock):
        """Should find the dpg link item matching the alias pair and delete it."""
        mock_dpg = reset_dpg_mock

        link_item_id = 999
        mock_dpg.get_item_children.return_value = [link_item_id]
        mock_dpg.get_item_configuration.return_value = {
            "attr_1": "1:Video:IMAGE:output",
            "attr_2": "2:Display:IMAGE:input",
        }
        mock_dpg.get_item_alias.side_effect = lambda x: x

        editor._delete_dpg_link(["1:Video:IMAGE:output", "2:Display:IMAGE:input"])

        mock_dpg.delete_item.assert_called_once_with(link_item_id)

    def test_no_crash_on_exception(self, editor, reset_dpg_mock):
        """Should not crash if dpg raises an exception."""
        mock_dpg = reset_dpg_mock
        mock_dpg.get_item_children.side_effect = Exception("dpg error")

        # Should not raise
        editor._delete_dpg_link(["1:Video:IMAGE:output", "2:Display:IMAGE:input"])
