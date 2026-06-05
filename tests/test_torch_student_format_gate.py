#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the TorchStudent output-format gating.

The differentiable PyTorch backprop path implements the ``yolo11``, ``yolox``
and ``nanodet`` (single-output GFL/DFL) decodes. Detectors using other decodes
(e.g. ``nanodet_multi`` with separate per-level heads, or ``ssd``) must NOT take
that path — otherwise inference yields no student boxes and training performs no
real weight updates. These tests run without PyTorch installed because they only
exercise the pure-Python guard.
"""

from node.DLNode.online_training.torch_student import (
    SUPPORTED_FORMATS,
    is_format_supported,
)


def test_supported_formats_accepted():
    assert is_format_supported("yolo11")
    assert is_format_supported("yolox")
    assert is_format_supported("nanodet")


def test_supported_formats_case_insensitive():
    assert is_format_supported("YOLO11")
    assert is_format_supported("YOLOX")
    assert is_format_supported("NanoDet")


def test_unsupported_formats_rejected():
    for fmt in ("nanodet_multi", "ssd", "", "unknown"):
        assert not is_format_supported(fmt)


def test_supported_formats_constant():
    assert set(SUPPORTED_FORMATS) == {"yolo11", "yolox", "nanodet"}
