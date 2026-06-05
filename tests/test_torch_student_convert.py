#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the read-only-directory resilient ONNX->torch conversion helper.

These exercise ``_convert_onnx_to_torch`` without requiring torch/onnx2torch to
be installed by monkeypatching the conversion entry point. The key behaviour is
that a ``PermissionError`` raised when onnx2torch tries to write next to the
model file (a read-only model directory) is recovered from by re-running the
conversion from a writable temporary working directory.
"""

import os
import sys
import types

from node.DLNode.online_training import torch_student


def test_convert_falls_back_on_permission_error(monkeypatch):
    sentinel_module = object()
    sentinel_proto = object()
    seen = {}

    def fake_convert(arg):
        if isinstance(arg, str):
            # Simulate onnx2torch writing a temp file next to a read-only model.
            raise PermissionError(13, "Permission denied", arg)
        seen["arg"] = arg
        seen["cwd"] = os.getcwd()
        return sentinel_module

    fake_onnx = types.ModuleType("onnx")
    fake_onnx.load = lambda path: sentinel_proto

    monkeypatch.setattr(torch_student, "_onnx2torch_convert", fake_convert)
    monkeypatch.setitem(sys.modules, "onnx", fake_onnx)

    original_cwd = os.getcwd()
    result = torch_student._convert_onnx_to_torch("/read/only/models/student.onnx")

    assert result is sentinel_module
    # The fallback converts the in-memory ModelProto, not the path string.
    assert seen["arg"] is sentinel_proto
    # Conversion ran from a writable temp dir, not the (read-only) model dir...
    assert seen["cwd"] != original_cwd
    # ...and the working directory is restored afterwards.
    assert os.getcwd() == original_cwd


def test_convert_passes_through_on_success(monkeypatch):
    sentinel_module = object()

    def fake_convert(arg):
        assert arg == "/models/student.onnx"
        return sentinel_module

    monkeypatch.setattr(torch_student, "_onnx2torch_convert", fake_convert)

    assert torch_student._convert_onnx_to_torch("/models/student.onnx") is sentinel_module
