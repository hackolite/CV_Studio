#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib.util
import os
import sys
import types
from unittest import mock

import pytest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSPECTOR_PATH = os.path.join(
    REPO_ROOT, 'node', 'DLNode', 'object_detection', 'onnx_inspector.py'
)


def _load_inspector_module():
    mocked = {
        'onnxruntime': mock.MagicMock(),
        'node.DLNode.object_detection.onnx_session_utils': types.SimpleNamespace(
            make_session=mock.MagicMock()
        ),
    }

    saved = {}
    for name, mod in mocked.items():
        saved[name] = sys.modules.get(name)
        sys.modules[name] = mod

    spec = importlib.util.spec_from_file_location('_onnx_batch_meta_test', INSPECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    for name, orig in saved.items():
        if orig is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = orig

    return module


INSPECTOR = _load_inspector_module()


@pytest.mark.parametrize(
    ("input_shape", "expected"),
    [
        ([1, 3, 640, 640], False),
        (["batch", 3, 640, 640], True),
        ([-1, 3, 640, 640], True),
        ([0, 3, 640, 640], False),
        ([None, 3, 640, 640], True),
        ([], False),
    ],
)
def test_has_dynamic_batch_dim(input_shape, expected):
    assert INSPECTOR.has_dynamic_batch_dim(input_shape) is expected


@pytest.mark.parametrize(
    ("input_shape", "output_format", "expected"),
    [
        (["batch", 3, 640, 640], "yolo11", True),
        (["batch", 3, 640, 640], "yolox", True),
        (["batch", 3, 640, 640], "nanodet", True),
        (["batch", 3, 640, 640], "ssd", False),
        ([1, 3, 640, 640], "yolo11", False),
        (["batch", 3, 640, 640], "unknown", False),
    ],
)
def test_supports_batched_detection(input_shape, output_format, expected):
    assert INSPECTOR.supports_batched_detection(input_shape, output_format) is expected
