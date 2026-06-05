#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""End-to-end test: the student must return *updated* predictions after
back-propagation so its improvement is observable (decreasing loss)."""

import numpy as np
import pytest

# The trainer pulls in onnxruntime/onnx/cv2; skip cleanly if unavailable.
st = pytest.importorskip("node.DLNode.online_training.student_trainer")
from node.DLNode.online_training.online_adapter import BoxAffineAdapter


def _make_trainer(training_active=True, lr=1e-4):
    """Build a StudentTrainer without loading a real ONNX model."""
    tr = st.StudentTrainer.__new__(st.StudentTrainer)
    tr.frames_processed = 0
    tr.total_score = 0.0
    tr.current_score = 0.0
    tr.best_score = 0.0
    tr.current_loss = float('inf')
    tr.best_loss = float('inf')
    tr.initial_loss = None
    tr.training_active = training_active
    tr._training_available = False
    tr._adaptation_available = True
    tr._ort_training_session = None
    tr._last_loss = None
    tr.score_threshold = 0.3
    tr.learning_rate = lr
    tr.num_classes = 80
    tr._adapter = BoxAffineAdapter(learning_rate=st._ADAPTER_LR_MIN)
    return tr


def test_student_outputs_change_and_loss_improves():
    tr = _make_trainer(training_active=True)
    teacher = [[20, 20, 60, 60], [100, 100, 140, 160]]
    raw = np.array([[38, 38, 78, 78], [118, 118, 158, 178]], dtype=np.float32)
    tr.infer = lambda f: (raw.copy(),
                          np.array([0.9, 0.9], dtype=np.float32),
                          np.array([0, 1], dtype=np.int64))
    frame = np.zeros((200, 200, 3), dtype=np.uint8)

    first = None
    for _ in range(150):
        res = tr.train_step(frame, teacher, [0.9, 0.9], [0, 1], score_threshold=0.3)
        if first is None:
            first = res['distillation']['loss']
            first_box = res['student_bboxes'][0].copy()

    # A real parameter update happened each active frame.
    assert res['training_step'] is True
    assert tr.get_stats()['adapter_updates'] == 150

    # The returned student boxes actually changed (learning is observable)…
    assert not np.allclose(first_box, res['student_bboxes'][0])
    # …and moved toward the teacher box [20, 20, 60, 60].
    assert abs(res['student_bboxes'][0][0] - 20) < abs(first_box[0] - 20)

    # The requested loss decreased → visible improvement.
    assert tr.current_loss < first
    assert tr.improvement > 0.0
    assert tr.improvement_pct > 0.0


def test_no_update_when_training_paused():
    tr = _make_trainer(training_active=False)
    teacher = [[20, 20, 60, 60]]
    raw = np.array([[38, 38, 78, 78]], dtype=np.float32)
    tr.infer = lambda f: (raw.copy(),
                          np.array([0.9], dtype=np.float32),
                          np.array([0], dtype=np.int64))
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    for _ in range(20):
        res = tr.train_step(frame, teacher, [0.9], [0], score_threshold=0.3)

    assert res['training_step'] is False
    assert tr.get_stats()['adapter_updates'] == 0
    assert tr._adapter.is_identity
    # With no learning, the output equals the raw inference (identity head).
    assert np.allclose(res['student_bboxes'][0], raw[0])


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
