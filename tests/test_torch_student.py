#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the PyTorch-backed student backprop (node.DLNode.online_training.torch_student).

These tests are skipped when PyTorch is not installed. They verify the
differentiable decode, the distillation loss, and — most importantly — that a
real optimizer step actually back-propagates through a network and reduces the
loss (i.e. the student's backpropagation is functional).
"""

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from node.DLNode.online_training.torch_student import TorchStudent  # noqa: E402


def _make_student(num_classes=3, input_size=64, anchors=12):
    """Build a TorchStudent around a tiny trainable module (bypassing ONNX)."""
    import torch.nn as nn

    class TinyDetector(nn.Module):
        def __init__(self, c_plus_4, a, num_cls):
            super().__init__()
            # Learnable raw output of shape (1, C+4, A) — independent of input,
            # which is enough to exercise the decode/loss/backprop machinery.
            # Initialise to a realistic (non-degenerate) state so gradients flow.
            init = torch.zeros(1, c_plus_4, a)
            init[0, 0, :] = 32.0   # cx near image centre
            init[0, 1, :] = 32.0   # cy
            init[0, 2, :] = 20.0   # w
            init[0, 3, :] = 20.0   # h
            init[0, 4:, :] = 0.5   # class scores mid-range (BCE gradients flow)
            self.raw = nn.Parameter(init)

        def forward(self, x):
            return self.raw

    ts = object.__new__(TorchStudent)
    ts.model_path = "<tiny>"
    ts.input_width = input_size
    ts.input_height = input_size
    ts.output_format = "yolo11"
    ts.num_classes = num_classes
    ts.learning_rate = 0.5
    ts.train_scope = "all"
    ts.module = TinyDetector(num_classes + 4, anchors, num_classes)
    ts._trainable_params = list(ts.module.parameters())
    ts.optimizer = torch.optim.SGD(ts._trainable_params, lr=0.5, momentum=0.9)
    ts._initial_state = {k: v.detach().clone()
                         for k, v in ts.module.state_dict().items()}
    ts.updates = 0
    return ts


def test_decode_yolo11_shapes_and_boxes():
    ts = _make_student(num_classes=3, input_size=64, anchors=2)
    # raw (1, C+4, A): set one anchor to a known box cx,cy,w,h = 32,32,16,8
    with torch.no_grad():
        ts.module.raw[0, 0, 0] = 32.0
        ts.module.raw[0, 1, 0] = 32.0
        ts.module.raw[0, 2, 0] = 16.0
        ts.module.raw[0, 3, 0] = 8.0
    boxes, scores = ts._decode(ts.module.raw)
    assert boxes.shape == (2, 4)
    assert scores.shape == (2, 3)
    # First box: x1=24, y1=28, x2=40, y2=36
    np.testing.assert_allclose(
        boxes[0].detach().numpy(), [24.0, 28.0, 40.0, 36.0], atol=1e-4
    )


def test_loss_none_when_no_teacher():
    ts = _make_student()
    blob = np.zeros((1, 3, 64, 64), dtype=np.float32)
    assert ts.train_step(blob, [], [], 64, 64) is None


def test_backprop_is_functional_and_reduces_loss():
    """A real optimizer step must change weights and drive the loss down."""
    ts = _make_student(num_classes=3, input_size=64, anchors=12)
    blob = np.zeros((1, 3, 64, 64), dtype=np.float32)

    # One teacher box in original-image pixels (image == input size here).
    teacher_boxes = [[20.0, 20.0, 44.0, 44.0]]
    teacher_classes = [1]

    param_before = ts.module.raw.detach().clone()
    first = ts.train_step(blob, teacher_boxes, teacher_classes, 64, 64)
    assert first is not None
    # Weights actually moved (backprop happened).
    assert not torch.allclose(param_before, ts.module.raw.detach())
    assert ts.updates == 1

    losses = [first]
    for _ in range(40):
        losses.append(ts.train_step(blob, teacher_boxes, teacher_classes, 64, 64))

    # The training loss should decrease substantially.
    assert losses[-1] < losses[0]
    assert losses[-1] < 0.5 * losses[0]


def test_reset_restores_initial_weights():
    ts = _make_student()
    blob = np.zeros((1, 3, 64, 64), dtype=np.float32)
    ts.train_step(blob, [[10.0, 10.0, 40.0, 40.0]], [0], 64, 64)
    assert ts.updates == 1
    ts.reset()
    assert ts.updates == 0
    np.testing.assert_allclose(
        ts.module.raw.detach().numpy(),
        ts._initial_state["raw"].numpy(),
        atol=1e-6,
    )


def test_forward_numpy_returns_array():
    ts = _make_student(num_classes=3, input_size=64, anchors=5)
    blob = np.zeros((1, 3, 64, 64), dtype=np.float32)
    raw = ts.forward_numpy(blob)
    assert isinstance(raw, np.ndarray)
    assert raw.shape == (1, 7, 5)  # (1, C+4, A)
