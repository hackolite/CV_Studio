#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the online affine box-correction head used to back-propagate the
requested distillation loss so the student visibly improves over time."""

import numpy as np
import pytest

from node.DLNode.online_training.online_adapter import BoxAffineAdapter


def _mean_l1(boxes_a, boxes_b, w, h):
    a = np.asarray(boxes_a, dtype=np.float64).reshape(-1, 4) / [w, h, w, h]
    b = np.asarray(boxes_b, dtype=np.float64).reshape(-1, 4) / [w, h, w, h]
    return float(np.mean(np.abs(a - b)))


class TestBoxAffineAdapter:
    def test_starts_as_identity(self):
        ad = BoxAffineAdapter()
        assert ad.is_identity
        boxes = [[10, 20, 30, 40], [50, 60, 70, 80]]
        out = ad.apply(boxes, 100, 100)
        assert np.allclose(out, np.asarray(boxes, dtype=np.float64))

    def test_apply_empty(self):
        ad = BoxAffineAdapter()
        out = ad.apply([], 100, 100)
        assert out.shape == (0, 4)

    def test_update_no_pairs_is_noop(self):
        ad = BoxAffineAdapter()
        updated, loss = ad.update([], [[0, 0, 10, 10]], 100, 100)
        assert updated is False
        assert loss == 0.0
        assert ad.is_identity

    def test_learns_systematic_translation(self):
        """Student boxes are shifted by a constant offset from the teacher.
        After several gradient steps the corrected boxes should be much closer."""
        w = h = 100.0
        rng = np.random.default_rng(0)
        teacher = rng.uniform(5, 60, size=(6, 2))
        teacher = np.hstack([teacher, teacher + 20.0])  # [x1,y1,x2,y2]
        offset = np.array([15.0, -10.0, 15.0, -10.0])    # systematic student bias
        student_raw = teacher + offset

        ad = BoxAffineAdapter(learning_rate=0.2)
        loss0 = _mean_l1(ad.apply(student_raw, w, h), teacher, w, h)
        for _ in range(200):
            corrected = ad.apply(student_raw, w, h)
            ad.update(teacher, corrected, w, h)
        loss1 = _mean_l1(ad.apply(student_raw, w, h), teacher, w, h)

        assert ad.updates > 0
        assert not ad.is_identity
        assert loss1 < loss0 * 0.25  # at least 4x closer

    def test_learns_systematic_scale(self):
        w = h = 200.0
        teacher = np.array([[20, 20, 60, 60], [100, 100, 140, 180]], dtype=np.float64)
        student_raw = teacher * 1.3  # student boxes systematically too large

        ad = BoxAffineAdapter(learning_rate=0.2)
        loss0 = _mean_l1(ad.apply(student_raw, w, h), teacher, w, h)
        for _ in range(300):
            corrected = ad.apply(student_raw, w, h)
            ad.update(teacher, corrected, w, h)
        loss1 = _mean_l1(ad.apply(student_raw, w, h), teacher, w, h)
        assert loss1 < loss0 * 0.5

    def test_reset_restores_identity(self):
        ad = BoxAffineAdapter(learning_rate=0.2)
        teacher = [[10, 10, 30, 30]]
        student = [[20, 20, 40, 40]]
        for _ in range(10):
            ad.update(teacher, ad.apply(student, 100, 100), 100, 100)
        assert not ad.is_identity
        ad.reset()
        assert ad.is_identity
        assert ad.updates == 0

    def test_apply_preserves_box_ordering(self):
        ad = BoxAffineAdapter()
        ad.params = np.array([-1.0, -1.0, 1.0, 1.0])  # forces a flip
        out = ad.apply([[10, 10, 30, 30]], 100, 100)
        assert out[0, 0] <= out[0, 2]
        assert out[0, 1] <= out[0, 3]


if __name__ == '__main__':
    raise SystemExit(pytest.main([__file__, '-v']))
