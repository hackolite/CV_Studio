#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test to verify that JSON import/export functionality works correctly.
This test verifies the fixes for:
1. Incorrect dictionary name (_node_instance_list vs _node_instances_list)
2. Incorrect import logic (should use factory to create nodes)
"""
import sys
import os
import json
from unittest.mock import MagicMock, patch, mock_open
import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock dearpygui for direct execution (when not using pytest)
if 'dearpygui' not in sys.modules:
    sys.modules['dearpygui'] = MagicMock()
    sys.modules['dearpygui.dearpygui'] = MagicMock()


@pytest.fixture(autouse=True)
def mock_dearpygui():
    """Mock dearpygui for all tests in this module when using pytest"""
    with patch.dict('sys.modules', {
        'dearpygui': MagicMock(),
        'dearpygui.dearpygui': MagicMock()
    }):
        yield


def test_export_uses_correct_dictionary():
    """
    Test that export function uses the correct _node_instances_list dictionary
    """
    print("Testing export uses correct _node_instances_list dictionary...")
    
    from node_editor.node_main import DpgNodeEditor
    
    # Mock dpg to avoid GUI initialization
    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
                            # Create a minimal node editor instance
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
    
    # Create a mock node with minimal required methods
    mock_node = MagicMock()
    mock_node.get_setting_dict = MagicMock(return_value={
        'ver': '1.0.0',
        'pos': [100, 200],
        'some_setting': 'value'
    })
    
    # Add mock node to the correct dictionary
    node_id_name = "1:TestNode"
    editor._node_instances_list[node_id_name] = mock_node
    editor._node_list = [node_id_name]
    editor._node_link_list = []
    
    # Mock file operations
    mock_data = {'file_path_name': '/tmp/test_export.json'}
    
    with patch('builtins.open', mock_open()) as mock_file:
        with patch('json.dump') as mock_json_dump:
            # Call export
            editor._callback_file_export(None, mock_data)
            
            # Verify json.dump was called
            assert mock_json_dump.called, "json.dump should have been called"
            
            # Get the dictionary that was passed to json.dump
            call_args = mock_json_dump.call_args
            exported_dict = call_args[0][0]
            
            # Verify the structure
            assert 'node_list' in exported_dict, "Exported dict should have node_list"
            assert 'link_list' in exported_dict, "Exported dict should have link_list"
            assert node_id_name in exported_dict, f"Exported dict should have {node_id_name}"
            
            # Verify get_setting_dict was called on the mock node
            assert mock_node.get_setting_dict.called, "get_setting_dict should have been called on node"
            
            print("✓ Export correctly uses _node_instances_list")


def test_import_uses_factory_to_create_nodes():
    """
    Test that import function uses factory to create node instances
    """
    print("\nTesting import uses factory to create nodes...")
    
    from node_editor.node_main import DpgNodeEditor
    
    # Mock dpg to avoid GUI initialization
    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
                            # Create a minimal node editor instance
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
    
    # Create mock factory and node
    mock_node = MagicMock()
    mock_node.tag_node_name = "1:TestNode"
    mock_node._ver = "1.0.0"
    mock_node.set_setting_dict = MagicMock()
    
    mock_factory = MagicMock()
    mock_factory.add_node = MagicMock(return_value=mock_node)
    mock_factory.style = MagicMock()
    
    # Add factory to editor
    editor._node_factory_list["TestNode"] = mock_factory
    
    # Create test import data
    import_data = {
        "node_list": ["1:TestNode"],
        "link_list": [],
        "1:TestNode": {
            "id": "1",
            "name": "TestNode",
            "setting": {
                "ver": "1.0.0",
                "pos": [100, 200],
                "some_setting": "value"
            }
        }
    }
    
    # Mock file operations
    mock_file_data = {'file_name': 'test.json', 'file_path_name': '/tmp/test.json'}
    
    with patch('builtins.open', mock_open(read_data=json.dumps(import_data))):
        with patch('dearpygui.dearpygui.bind_item_theme'):
            with patch('dearpygui.dearpygui.add_node_link'):
                # Call import
                editor._callback_file_import(None, mock_file_data)
    
    # Verify factory.add_node was called
    assert mock_factory.add_node.called, "Factory add_node should have been called"
    
    # Verify the node was added to _node_instances_list
    assert "1:TestNode" in editor._node_instances_list, "Node should be in _node_instances_list"
    assert editor._node_instances_list["1:TestNode"] == mock_node, "Correct node should be stored"
    
    # Verify set_setting_dict was called
    assert mock_node.set_setting_dict.called, "set_setting_dict should have been called"
    
    print("✓ Import correctly uses factory to create nodes")
    print("✓ Import correctly stores nodes in _node_instances_list")


def test_export_import_roundtrip(tmp_path):
    """
    Test that export and import work together correctly
    """
    print("\nTesting export/import roundtrip...")
    
    from node_editor.node_main import DpgNodeEditor
    
    # Mock dpg to avoid GUI initialization
    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
                            # Create editor for export
                            editor_export = DpgNodeEditor(
                                width=800,
                                height=600,
                                opencv_setting_dict={
                                    'webcam_width': 640,
                                    'webcam_height': 480,
                                    'input_window_width': 320,
                                    'input_window_height': 240,
                                }
                            )
                            
                            # Create editor for import
                            editor_import = DpgNodeEditor(
                                width=800,
                                height=600,
                                opencv_setting_dict={
                                    'webcam_width': 640,
                                    'webcam_height': 480,
                                    'input_window_width': 320,
                                    'input_window_height': 240,
                                }
                            )
    
    # Setup export scenario
    mock_node = MagicMock()
    mock_node.get_setting_dict = MagicMock(return_value={
        'ver': '1.0.0',
        'pos': [150, 250],
        'test_param': 'test_value'
    })
    
    node_id_name = "2:ExportNode"
    editor_export._node_instances_list[node_id_name] = mock_node
    editor_export._node_list = [node_id_name]
    editor_export._node_link_list = []
    
    # Export to temp file using pytest's tmp_path fixture
    tmp_file = tmp_path / "test_export.json"
    
    mock_export_data = {'file_path_name': str(tmp_file)}
    editor_export._callback_file_export(None, mock_export_data)
    
    # Verify file was created and has valid JSON
    assert tmp_file.exists(), "Export file should be created"
    
    exported_data = json.loads(tmp_file.read_text())
    
    assert 'node_list' in exported_data, "Exported data should have node_list"
    assert 'link_list' in exported_data, "Exported data should have link_list"
    assert node_id_name in exported_data, f"Exported data should have {node_id_name}"
    
    print("✓ Export creates valid JSON file")
    
    # Setup import scenario
    mock_imported_node = MagicMock()
    mock_imported_node.tag_node_name = node_id_name
    mock_imported_node._ver = "1.0.0"
    mock_imported_node.set_setting_dict = MagicMock()
    
    mock_factory = MagicMock()
    mock_factory.add_node = MagicMock(return_value=mock_imported_node)
    mock_factory.style = MagicMock()
    
    editor_import._node_factory_list["ExportNode"] = mock_factory
    
    # Import from temp file
    mock_import_data = {'file_name': 'test.json', 'file_path_name': str(tmp_file)}
    
    with patch('dearpygui.dearpygui.bind_item_theme'):
        with patch('dearpygui.dearpygui.add_node_link'):
            editor_import._callback_file_import(None, mock_import_data)
    
    # Verify import worked
    assert node_id_name in editor_import._node_instances_list, "Imported node should be in _node_instances_list"
    assert mock_factory.add_node.called, "Factory should have been used to create node"
    assert mock_imported_node.set_setting_dict.called, "Settings should have been applied to imported node"
    
    print("✓ Import successfully loads exported JSON file")
    print("✓ Export/import roundtrip works correctly")


def test_import_handles_empty_file():
    """
    Test that import handles edge cases gracefully
    """
    print("\nTesting import edge cases...")
    
    from node_editor.node_main import DpgNodeEditor
    
    # Mock dpg to avoid GUI initialization
    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
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
    
    # Test with "." filename (cancel)
    mock_data = {'file_name': '.', 'file_path_name': ''}
    editor._callback_file_import(None, mock_data)
    
    # Should not crash and node list should remain empty
    assert len(editor._node_list) == 0, "Node list should be empty after cancelled import"
    
    print("✓ Import handles cancelled file dialog correctly")


def test_export_appends_json_extension(tmp_path):
    """
    Test that export appends a .json extension when the chosen path is missing
    one, so the saved graph can always be located and re-imported.
    """
    print("\nTesting export appends .json extension...")

    from node_editor.node_main import DpgNodeEditor

    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
                            editor = DpgNodeEditor(
                                width=800,
                                height=600,
                                opencv_setting_dict={
                                    'webcam_width': 640,
                                    'webcam_height': 480,
                                    'input_window_width': 320,
                                    'input_window_height': 240,
                                },
                            )

    mock_node = MagicMock()
    mock_node.get_setting_dict = MagicMock(return_value={
        'ver': '1.0.0',
        'pos': [10, 20],
    })

    node_id_name = "3:ExtNode"
    editor._node_instances_list[node_id_name] = mock_node
    editor._node_list = [node_id_name]
    editor._node_link_list = []

    # Path without extension (as returned by the file dialog when the user
    # does not type one).
    tmp_file = tmp_path / "my_graph"
    editor._callback_file_export(None, {'file_path_name': str(tmp_file)})

    expected_file = tmp_path / "my_graph.json"
    assert expected_file.exists(), "Export should append .json extension"
    assert not tmp_file.exists(), "Export should not create an extension-less file"

    exported_data = json.loads(expected_file.read_text())
    assert node_id_name in exported_data

    print("✓ Export appends .json extension when missing")


def test_export_ignores_cancelled_dialog(tmp_path):
    """
    Test that export does nothing when the file dialog is cancelled (empty path
    or '.' file name), instead of crashing.
    """
    print("\nTesting export handles cancelled dialog...")

    from node_editor.node_main import DpgNodeEditor

    with patch('dearpygui.dearpygui.create_context'):
        with patch('dearpygui.dearpygui.file_dialog'):
            with patch('dearpygui.dearpygui.window'):
                with patch('dearpygui.dearpygui.menu_bar'):
                    with patch('dearpygui.dearpygui.node_editor'):
                        with patch('dearpygui.dearpygui.handler_registry'):
                            editor = DpgNodeEditor(
                                width=800,
                                height=600,
                                opencv_setting_dict={
                                    'webcam_width': 640,
                                    'webcam_height': 480,
                                    'input_window_width': 320,
                                    'input_window_height': 240,
                                },
                            )

    # Should not raise even though no nodes / no valid path are present.
    editor._callback_file_export(None, {'file_name': '.', 'file_path_name': ''})
    editor._callback_file_export(None, {})

    print("✓ Export handles cancelled dialog gracefully")


if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("Testing JSON Import/Export Functionality")
    print("=" * 60)
    print("Note: Use 'pytest tests/test_json_import_export.py' for best results")
    print("=" * 60)
    
    try:
        test_export_uses_correct_dictionary()
        test_import_uses_factory_to_create_nodes()
        
        # Create temp directory for roundtrip test
        with tempfile.TemporaryDirectory() as tmpdir:
            from pathlib import Path
            test_export_import_roundtrip(Path(tmpdir))
        
        test_import_handles_empty_file()
        
        print("\n" + "=" * 60)
        print("✓ All JSON import/export tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
