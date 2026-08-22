#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression tests for deterministic cross-platform node discovery."""

import os
import sys
from unittest.mock import MagicMock


_mock_dpg = MagicMock()
_mock_dearpygui = MagicMock()
_mock_dearpygui.dearpygui = _mock_dpg
sys.modules['dearpygui'] = _mock_dearpygui
sys.modules['dearpygui.dearpygui'] = _mock_dpg

import node_editor.node_main as node_main  # noqa: E402


def test_node_editor_discovers_only_sorted_node_modules(monkeypatch, tmp_path):
    """Only node_*.py files should be loaded, in sorted order."""
    _mock_dpg.reset_mock()

    node_dir = tmp_path / "node"
    dl_dir = node_dir / "DLNode"
    dl_dir.mkdir(parents=True)
    for filename in ("node_zeta.py", "helper.py", "node_alpha.py"):
        (dl_dir / filename).write_text("# test\n", encoding="utf-8")

    loaded_modules = []

    def fake_import_module(import_path):
        loaded_modules.append(import_path)
        module = MagicMock()
        factory = MagicMock()
        short_name = import_path.rsplit(".", 1)[-1]
        label = short_name.replace("node_", "").title()
        factory.node_tag = label
        factory.node_label = label
        module.FactoryNode.return_value = factory
        return module

    monkeypatch.setattr(node_main, "import_module", fake_import_module)

    node_main.DpgNodeEditor(
        width=800,
        height=600,
        opencv_setting_dict={
            'webcam_width': 640,
            'webcam_height': 480,
            'input_window_width': 320,
            'input_window_height': 240,
        },
        menu_dict={"VisionModel": "DLNode"},
        node_dir=os.fspath(node_dir),
    )

    assert loaded_modules == [
        "node.DLNode.node_alpha",
        "node.DLNode.node_zeta",
    ]
