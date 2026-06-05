#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Regression test for the OnlineTraining student "green blocks everywhere" bug.

When the PyTorch backprop path is active, the displayed student detections are
produced by ``StudentTrainer._torch_infer``: it runs the torch-converted module
and decodes the raw output with ``CustomONNX._postprocess_nanodet``.

Historically that decode relied on a statistical *reg-first* heuristic. The
heuristic inspects the torch-converted output and can misdetect the channel
layout, scrambling the class/reg split so (almost) every anchor clears the
score threshold — flooding the OnlineTraining display with thousands of
false-positive green student boxes (nanodet-plus-m_416 symptom).

The fix forces ``_torch_infer`` to decode NanoDet with the *same* explicit
layout / activation used by the differentiable training decode
(``TorchStudent._decode_nanodet``): classes-first (``reg_first_override`` taken
from ``TorchStudent.nanodet_reg_first``) and raw logits (``cls_pre_activated=
False``). This test pins that contract.
"""

import numpy as np
import pytest

st = pytest.importorskip("node.DLNode.online_training.student_trainer")


class _StubTorch:
    """Stand-in for TorchStudent returning a fixed raw output."""

    def __init__(self, raw, nanodet_reg_first=False):
        self._raw = raw
        self.nanodet_reg_first = nanodet_reg_first

    def forward_numpy(self, blob):
        return self._raw


class _StubModel:
    """Stand-in for CustomONNX recording the nanodet post-process call."""

    def __init__(self):
        self.calls = []

    def _preprocess(self, frame):
        return np.zeros((1, 3, 8, 8), np.float32), 1.0

    def _postprocess_nanodet(self, raw, orig_w, orig_h,
                             cls_pre_activated=None, reg_first_override=None):
        self.calls.append({
            "cls_pre_activated": cls_pre_activated,
            "reg_first_override": reg_first_override,
        })
        return np.array([]), np.array([]), np.array([])


def _make_trainer(nanodet_reg_first=False):
    tr = st.StudentTrainer.__new__(st.StudentTrainer)
    tr.output_format = "nanodet"
    tr._student_model = _StubModel()
    tr._torch = _StubTorch(np.zeros((1, 4, 112), np.float32),
                           nanodet_reg_first=nanodet_reg_first)
    tr._torch_backprop = True
    return tr


def test_torch_infer_nanodet_forces_explicit_layout():
    tr = _make_trainer(nanodet_reg_first=False)
    frame = np.zeros((8, 8, 3), np.uint8)

    tr._torch_infer(frame)

    assert tr._student_model.calls, "expected _postprocess_nanodet to be called"
    call = tr._student_model.calls[-1]
    # The decode must NOT fall back to the statistical heuristic (None); it must
    # match the differentiable training decode so the display cannot flood.
    assert call["cls_pre_activated"] is False
    assert call["reg_first_override"] is False


def test_torch_infer_nanodet_propagates_reg_first_layout():
    tr = _make_trainer(nanodet_reg_first=True)
    frame = np.zeros((8, 8, 3), np.uint8)

    tr._torch_infer(frame)

    call = tr._student_model.calls[-1]
    assert call["reg_first_override"] is True
