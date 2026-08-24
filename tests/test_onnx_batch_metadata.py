#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

pytest.importorskip("onnxruntime")

from node.DLNode.object_detection.onnx_inspector import (
    has_dynamic_batch_dim,
    supports_batched_detection,
)


@pytest.mark.parametrize(
    ("input_shape", "expected"),
    [
        ([1, 3, 640, 640], False),
        (["batch", 3, 640, 640], True),
        ([-1, 3, 640, 640], True),
        ([], False),
    ],
)
def test_has_dynamic_batch_dim(input_shape, expected):
    assert has_dynamic_batch_dim(input_shape) is expected


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
    assert supports_batched_detection(input_shape, output_format) is expected
