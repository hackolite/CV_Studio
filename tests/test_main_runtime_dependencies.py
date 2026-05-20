#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib

import pytest

main_module = importlib.import_module("main")


def test_format_missing_dependency_message_uses_install_package_name():
    message = main_module._format_missing_dependency_message("cv2", "opencv-contrib-python")

    assert "Missing Python module: cv2" in message
    assert "Install package: opencv-contrib-python" in message
    assert "pip install -r requirements.txt" in message


def test_import_runtime_module_missing_dependency_error(monkeypatch):
    def fake_import_module(import_name):
        raise ModuleNotFoundError("No module named 'cv2'", name="cv2")

    monkeypatch.setattr(main_module.importlib, "import_module", fake_import_module)

    with pytest.raises(SystemExit) as exc_info:
        main_module._import_runtime_module("cv2")

    message = str(exc_info.value)
    assert "Missing Python module: cv2" in message
    assert "Install package: opencv-contrib-python" in message


def test_import_runtime_module_reraises_unknown_module(monkeypatch):
    def fake_import_module(import_name):
        raise ModuleNotFoundError("No module named 'node_editor'", name="node_editor")

    monkeypatch.setattr(main_module.importlib, "import_module", fake_import_module)

    with pytest.raises(ModuleNotFoundError):
        main_module._import_runtime_module("node_editor.util")
