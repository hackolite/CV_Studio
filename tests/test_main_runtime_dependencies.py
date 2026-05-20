#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib

import pytest

main = importlib.import_module("main")


def test_format_missing_dependency_message_uses_install_package_name():
    message = main._format_missing_dependency_message("cv2", "opencv-contrib-python")

    assert "Missing Python module: cv2" in message
    assert "Install package: opencv-contrib-python" in message
    assert "pip install -r requirements.txt" in message


def test_import_runtime_module_raises_actionable_error_for_missing_dependency(monkeypatch):
    def fake_import_module(import_name):
        raise ModuleNotFoundError("No module named 'cv2'", name="cv2")

    monkeypatch.setattr(main.importlib, "import_module", fake_import_module)

    with pytest.raises(SystemExit) as exc_info:
        main._import_runtime_module("cv2")

    message = str(exc_info.value)
    assert "Missing Python module: cv2" in message
    assert "Install package: opencv-contrib-python" in message


def test_import_runtime_module_reraises_unknown_missing_module(monkeypatch):
    def fake_import_module(import_name):
        raise ModuleNotFoundError("No module named 'node_editor'", name="node_editor")

    monkeypatch.setattr(main.importlib, "import_module", fake_import_module)

    with pytest.raises(ModuleNotFoundError):
        main._import_runtime_module("node_editor.util")
