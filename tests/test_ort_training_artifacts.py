#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for the end-to-end ORT-training backprop artifacts.

The pure-NumPy matcher is always tested. The ONNX graph build/run and the
artifact generation are skipped when ``onnx`` / ``onnxruntime`` /
``onnxruntime.training`` are not installed, mirroring the gating used by the
other online-training tests.
"""

import numpy as np
import pytest

from node.DLNode.online_training.ort_training_artifacts import (
    greedy_match_anchors,
    build_matched_targets,
    iou_matrix_numpy,
    is_ort_training_available,
    _ONNX_AVAILABLE,
)

if _ONNX_AVAILABLE:
    import onnx
    from onnx import helper, numpy_helper, TensorProto
    from node.DLNode.online_training.ort_training_artifacts import (
        build_student_loss_graph,
        merge_student_with_loss,
        select_trainable_params,
    )


# ─────────────────────────── NumPy matcher (always run) ──────────────────────
class TestGreedyMatcher:
    def test_iou_matrix_self(self):
        boxes = np.array([[0, 0, 10, 10], [5, 5, 15, 15]], dtype=np.float32)
        iou = iou_matrix_numpy(boxes, boxes)
        assert iou.shape == (2, 2)
        assert iou[0, 0] == pytest.approx(1.0, abs=1e-4)
        assert iou[1, 1] == pytest.approx(1.0, abs=1e-4)

    def test_empty_inputs(self):
        idx = greedy_match_anchors(np.zeros((0, 4)), np.zeros((0, 4)))
        assert idx.shape == (0,)
        idx2 = greedy_match_anchors(np.zeros((0, 4)), np.array([[0, 0, 1, 1]]))
        assert idx2.tolist() == [-1]

    def test_unique_assignment(self):
        # Two teacher boxes, three anchors; the best overlapping anchor wins and
        # each anchor is used at most once.
        anchors = np.array([
            [0, 0, 10, 10],     # matches teacher 0
            [100, 100, 110, 110],  # matches teacher 1
            [0, 0, 9, 9],       # also near teacher 0 but should not be reused
        ], dtype=np.float32)
        teachers = np.array([[0, 0, 10, 10], [100, 100, 110, 110]], dtype=np.float32)
        idx = greedy_match_anchors(anchors, teachers)
        assert idx.tolist() == [0, 1]
        assert len(set(idx.tolist())) == 2  # unique

    def test_more_teachers_than_anchors(self):
        anchors = np.array([[0, 0, 10, 10]], dtype=np.float32)
        teachers = np.array([[0, 0, 10, 10], [50, 50, 60, 60]], dtype=np.float32)
        idx = greedy_match_anchors(anchors, teachers)
        # First teacher (perfect overlap) gets the only anchor; second unmatched.
        assert idx[0] == 0
        assert idx[1] == -1

    def test_build_matched_targets_drops_unmatched(self):
        teacher_boxes = np.array([[0, 0, 10, 10], [50, 50, 60, 60]], dtype=np.float32)
        classes = [1, 2]
        anchor_idx = np.array([3, -1], dtype=np.int64)
        idx, tb, oh = build_matched_targets(teacher_boxes, classes, anchor_idx, num_classes=5)
        assert idx.tolist() == [3]
        assert tb.shape == (1, 4)
        assert oh.shape == (1, 5)
        assert oh[0].tolist() == [0, 1, 0, 0, 0]

    def test_build_matched_targets_none_when_no_match(self):
        out = build_matched_targets(
            np.array([[0, 0, 1, 1]], dtype=np.float32), [0],
            np.array([-1], dtype=np.int64), num_classes=3,
        )
        assert out is None


# ─────────────────────────── ONNX graph (needs onnx) ─────────────────────────
@pytest.mark.skipif(not _ONNX_AVAILABLE, reason="onnx not installed")
class TestStudentLossGraph:
    def _decode_yolo11(self, raw, num_classes):
        dec = raw[0].T
        cxcywh = dec[:, :4]
        scores = dec[:, 4:]
        x1 = cxcywh[:, 0] - cxcywh[:, 2] / 2
        y1 = cxcywh[:, 1] - cxcywh[:, 3] / 2
        x2 = cxcywh[:, 0] + cxcywh[:, 2] / 2
        y2 = cxcywh[:, 1] + cxcywh[:, 3] / 2
        return np.stack([x1, y1, x2, y2], 1), scores

    def test_graph_valid_and_io(self):
        m = build_student_loss_graph(num_classes=3, input_width=64, input_height=64)
        onnx.checker.check_model(m)
        inames = [i.name for i in m.graph.input]
        onames = [o.name for o in m.graph.output]
        assert set(["raw_output", "anchor_idx", "teacher_boxes_in", "teacher_onehot"]) <= set(inames)
        assert "total_loss" in onames

    def test_yolox_graph_valid(self):
        m = build_student_loss_graph(
            num_classes=2, input_width=64, input_height=64, output_format="yolox")
        onnx.checker.check_model(m)

    def test_forward_matches_reference(self, tmp_path):
        import onnxruntime as ort
        C, W, H, A = 3, 64, 64, 12
        m = build_student_loss_graph(num_classes=C, input_width=W, input_height=H)
        path = str(tmp_path / "loss.onnx")
        onnx.save(m, path)
        sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])

        raw = np.zeros((1, C + 4, A), dtype=np.float32)
        raw[0, 0, :] = 32; raw[0, 1, :] = 32; raw[0, 2, :] = 20; raw[0, 3, :] = 20
        raw[0, 4:, :] = 0.5
        pred_boxes, scores = self._decode_yolo11(raw, C)

        teacher = np.array([[20, 20, 44, 44]], dtype=np.float32)
        classes = np.array([1], dtype=np.int64)
        idx = greedy_match_anchors(pred_boxes, teacher)
        ai, tb, oh = build_matched_targets(teacher, classes, idx, C)
        out = sess.run(None, {
            "raw_output": raw, "anchor_idx": ai,
            "teacher_boxes_in": tb, "teacher_onehot": oh,
        })
        total, box, cls = (float(out[0]), float(out[1]), float(out[2]))

        # Reference computation (matches TorchStudent._build_loss semantics).
        a = int(ai[0]); pb = pred_boxes[a]; tbx = tb[0]
        diag = float(np.hypot(W, H)) + 1e-6
        l1 = np.abs(pb - tbx).mean() / diag
        ix1, iy1 = max(pb[0], tbx[0]), max(pb[1], tbx[1])
        ix2, iy2 = min(pb[2], tbx[2]), min(pb[3], tbx[3])
        inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
        ap = (pb[2] - pb[0]) * (pb[3] - pb[1])
        at = (tbx[2] - tbx[0]) * (tbx[3] - tbx[1])
        iou = inter / (ap + at - inter + 1e-6)
        ref_box = l1 + (1 - iou)
        p = np.clip(scores[a], 1e-6, 1 - 1e-6)
        ref_cls = float(-np.mean(oh[0] * np.log(p) + (1 - oh[0]) * np.log(1 - p)))

        assert box == pytest.approx(ref_box, rel=1e-4, abs=1e-4)
        assert cls == pytest.approx(ref_cls, rel=1e-4, abs=1e-4)
        assert total == pytest.approx(ref_box + ref_cls, rel=1e-4, abs=1e-4)


# ─────────────────────────── Merge + trainable selection ─────────────────────
@pytest.mark.skipif(not _ONNX_AVAILABLE, reason="onnx not installed")
class TestMergeStudent:
    def _tiny_student(self, tmp_path, num_classes=2):
        C = num_classes
        w = numpy_helper.from_array(
            np.random.randn(C + 4, 3, 1, 1).astype(np.float32), "conv_w")
        b = numpy_helper.from_array(np.zeros(C + 4, dtype=np.float32), "conv_b")
        n1 = helper.make_node("Conv", ["images", "conv_w", "conv_b"], ["feat"],
                              kernel_shape=[1, 1])
        shape = numpy_helper.from_array(np.array([1, C + 4, -1], dtype=np.int64), "rshape")
        n2 = helper.make_node("Reshape", ["feat", "rshape"], ["out"])
        gin = [helper.make_tensor_value_info("images", TensorProto.FLOAT, [1, 3, 8, 8])]
        gout = [helper.make_tensor_value_info("out", TensorProto.FLOAT, [1, C + 4, 64])]
        g = helper.make_graph([n1, n2], "student", gin, gout, initializer=[w, b, shape])
        sm = helper.make_model(g, opset_imports=[helper.make_opsetid("", 18)])
        sm.ir_version = 9
        path = str(tmp_path / "student.onnx")
        onnx.save(sm, path)
        return path

    def test_merge_single_loss_output(self, tmp_path):
        path = self._tiny_student(tmp_path)
        merged, sout = merge_student_with_loss(
            path, num_classes=2, input_width=64, input_height=64)
        onnx.checker.check_model(merged)
        assert sout == "out"
        assert [o.name for o in merged.graph.output] == ["total_loss"]

    def test_select_trainable_params(self, tmp_path):
        path = self._tiny_student(tmp_path)
        merged, _ = merge_student_with_loss(
            path, num_classes=2, input_width=64, input_height=64)
        trainable, frozen = select_trainable_params(merged, train_scope="all")
        assert set(trainable) == {"conv_w", "conv_b"}
        # Loss-graph constants and the int64 reshape param must stay frozen.
        assert "rshape" in frozen
        assert any(name.startswith("ld_") for name in frozen)

    def test_select_trainable_head_scope(self, tmp_path):
        path = self._tiny_student(tmp_path)
        merged, _ = merge_student_with_loss(
            path, num_classes=2, input_width=64, input_height=64)
        trainable, frozen = select_trainable_params(
            merged, train_scope="head", head_params=1)
        assert len(trainable) == 1
        assert "conv_w" not in trainable or "conv_b" not in trainable

    def test_merged_forward_runs(self, tmp_path):
        import onnxruntime as ort
        C = 2
        path = self._tiny_student(tmp_path, num_classes=C)
        merged, sout = merge_student_with_loss(
            path, num_classes=C, input_width=64, input_height=64)
        mp = str(tmp_path / "merged.onnx")
        onnx.save(merged, mp)
        sess = ort.InferenceSession(mp, providers=["CPUExecutionProvider"])
        student = ort.InferenceSession(path, providers=["CPUExecutionProvider"])

        img = np.random.rand(1, 3, 8, 8).astype(np.float32)
        raw = student.run(None, {"images": img})[0]
        dec = raw[0].T
        cx = dec[:, :4]
        pb = np.stack([cx[:, 0] - cx[:, 2] / 2, cx[:, 1] - cx[:, 3] / 2,
                       cx[:, 0] + cx[:, 2] / 2, cx[:, 1] + cx[:, 3] / 2], 1)
        teacher = np.array([[10, 10, 30, 30]], dtype=np.float32)
        idx = greedy_match_anchors(pb, teacher)
        ai, tb, oh = build_matched_targets(teacher, [0], idx, C)
        out = sess.run(None, {
            "images": img, "anchor_idx": ai,
            "teacher_boxes_in": tb, "teacher_onehot": oh,
        })
        assert np.isfinite(float(out[0]))


@pytest.mark.skipif(is_ort_training_available(), reason="ORT training installed")
def test_generate_artifacts_requires_ort_training():
    """When onnxruntime-training is absent, artifact generation must raise."""
    from node.DLNode.online_training.ort_training_artifacts import generate_training_artifacts
    with pytest.raises(RuntimeError):
        generate_training_artifacts(None, [], [], "/tmp/does-not-matter")
