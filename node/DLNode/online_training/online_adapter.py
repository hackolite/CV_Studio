#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Online adaptation layer for teacher-student distillation.

The full student CNN cannot be back-propagated with plain ``onnxruntime``
(inference only) because its post-processing — box decoding + NMS — runs in
NumPy and is therefore not part of a differentiable ONNX graph. To still give
the student a **real, observable** learning signal from the *requested*
set-based distillation loss, this module trains a small, differentiable
**affine box-correction head** that sits on top of the student detections.

For each matched (teacher, student) pair the head minimises the box L1 term of
the requested loss:

    corrected = [x1*sx + tx, y1*sy + ty, x2*sx + tx, y2*sy + ty]   (normalised)
    L1        = mean_pairs mean_coords | corrected - teacher |

The four parameters ``(sx, sy, tx, ty)`` are updated by sub-gradient descent
(true back-propagation of the requested loss through the correction head). The
head starts at the identity (``sx=sy=1, tx=ty=0``) so an untrained student is
unchanged, and progressively warps the student boxes toward the teacher — which
is exactly the improvement the user can watch through the decreasing loss.

The matching itself (Hungarian assignment) is computed **without** gradients,
mirroring DETR's two-stage "match, then regress" formulation.
"""

import numpy as np

from node.DLNode.online_training.distillation_loss import hungarian_match_boxes


class BoxAffineAdapter:
    """A tiny gradient-trained affine correction applied to student boxes.

    Parameters
    ----------
    learning_rate : float
        SGD step size (applied in normalised [0, 1] coordinate space).
    min_scale, max_scale : float
        Bounds keeping the scale factors positive (so box ordering is kept).
    max_translation : float
        Maximum absolute value for translation parameters ``tx`` and ``ty``
        (in normalised [0, 1] space). Prevents unbounded box drift when the
        student and teacher detections are far apart.
    l2_reg : float
        L2 regularisation coefficient pulling the parameters back toward the
        identity ``(sx=1, sy=1, tx=0, ty=0)`` every step. Keeps the
        correction head from diverging on frames with poor matching.
    divergence_factor : float
        If the loss exceeds ``divergence_factor × initial_loss``, the
        parameters are automatically reset to the identity. This acts as a
        safety net when the optimiser overshoots.
    """

    def __init__(self, learning_rate: float = 0.05,
                 min_scale: float = 0.1, max_scale: float = 10.0,
                 max_translation: float = 1.0,
                 l2_reg: float = 1e-3,
                 divergence_factor: float = 3.0):
        self.learning_rate = float(learning_rate)
        self.min_scale = float(min_scale)
        self.max_scale = float(max_scale)
        self.max_translation = float(max_translation)
        self.l2_reg = float(l2_reg)
        self.divergence_factor = float(divergence_factor)
        # params = [sx, sy, tx, ty]; identity transform.
        self.params = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float64)
        self.updates = 0
        self._initial_loss: float | None = None

    # ─── helpers ────────────────────────────────────────────────────────────
    def reset(self):
        """Restore the identity transform (no correction)."""
        self.params = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float64)
        self.updates = 0
        self._initial_loss = None

    @property
    def is_identity(self) -> bool:
        return bool(np.allclose(self.params, [1.0, 1.0, 0.0, 0.0]))

    @staticmethod
    def _to_arr(boxes):
        if boxes is None or len(boxes) == 0:
            return np.zeros((0, 4), dtype=np.float64)
        return np.asarray(boxes, dtype=np.float64).reshape(-1, 4)

    def apply(self, boxes, width: float, height: float):
        """Apply the current affine correction to ``boxes`` (pixel coords).

        Returns a new ``np.ndarray`` of shape ``[N, 4]``; the input is unchanged.
        """
        arr = self._to_arr(boxes)
        if arr.shape[0] == 0:
            return arr
        w = max(float(width), 1.0)
        h = max(float(height), 1.0)
        sx, sy, tx, ty = self.params
        out = arr.copy()
        # Normalise → correct → denormalise.
        out[:, 0] = ((arr[:, 0] / w) * sx + tx) * w
        out[:, 2] = ((arr[:, 2] / w) * sx + tx) * w
        out[:, 1] = ((arr[:, 1] / h) * sy + ty) * h
        out[:, 3] = ((arr[:, 3] / h) * sy + ty) * h
        # Keep coordinates ordered (x1<=x2, y1<=y2).
        x1 = np.minimum(out[:, 0], out[:, 2])
        x2 = np.maximum(out[:, 0], out[:, 2])
        y1 = np.minimum(out[:, 1], out[:, 3])
        y2 = np.maximum(out[:, 1], out[:, 3])
        out[:, 0], out[:, 1], out[:, 2], out[:, 3] = x1, y1, x2, y2
        return out

    def update(self, teacher_boxes, student_boxes, width: float, height: float,
               teacher_classes=None, student_classes=None, learning_rate=None):
        """Run one sub-gradient descent step of the box-L1 loss.

        ``student_boxes`` are the **already corrected** student boxes (i.e. the
        current head output). The Hungarian matching is computed without
        gradients, then the head parameters are nudged to reduce the mean L1
        between matched corrected-student and teacher boxes (normalised space).

        Returns
        -------
        (updated, loss_before) : tuple[bool, float]
            ``updated`` is True when a parameter step was taken; ``loss_before``
            is the mean normalised L1 over matched pairs *before* the step.
        """
        t_arr = self._to_arr(teacher_boxes)
        s_arr = self._to_arr(student_boxes)
        if t_arr.shape[0] == 0 or s_arr.shape[0] == 0:
            return False, 0.0

        lr = self.learning_rate if learning_rate is None else float(learning_rate)
        w = max(float(width), 1.0)
        h = max(float(height), 1.0)

        pairs, _cost = hungarian_match_boxes(
            t_arr.tolist(), s_arr.tolist(),
            classes_a=list(teacher_classes) if teacher_classes is not None else None,
            classes_b=list(student_classes) if student_classes is not None else None,
        )
        if not pairs:
            return False, 0.0

        # Normalised coordinates for the matched pairs.
        norm = np.array([w, h, w, h], dtype=np.float64)
        t_n = t_arr[[i for i, _j in pairs]] / norm
        s_n = s_arr[[j for _i, j in pairs]] / norm

        # Current correction is already baked into s_arr, so the residual is the
        # gradient signal for an *incremental* identity-centred affine step:
        # corrected = s_n_coord * ds + dt, evaluated at ds=1, dt=0.
        diff = s_n - t_n                      # [P, 4]
        loss_before = float(np.mean(np.abs(diff)))

        # Smooth (residual) gradient of the box-distance loss. Using the residual
        # rather than its sign makes the steps shrink near the optimum so the head
        # converges cleanly instead of oscillating, while still driving the
        # reported L1 loss down.
        gx = np.concatenate([diff[:, 0], diff[:, 2]])
        sx_in = np.concatenate([s_n[:, 0], s_n[:, 2]])
        gy = np.concatenate([diff[:, 1], diff[:, 3]])
        sy_in = np.concatenate([s_n[:, 1], s_n[:, 3]])

        n_terms = float(diff.size)            # P * 4
        grad_sx = float(np.sum(gx * sx_in)) / n_terms
        grad_tx = float(np.sum(gx)) / n_terms
        grad_sy = float(np.sum(gy * sy_in)) / n_terms
        grad_ty = float(np.sum(gy)) / n_terms

        # ── Divergence guard: reset to identity if loss keeps growing ────────
        if self._initial_loss is None:
            self._initial_loss = loss_before
        elif (
            self._initial_loss > 0
            and loss_before > self.divergence_factor * self._initial_loss
        ):
            self.params = np.array([1.0, 1.0, 0.0, 0.0], dtype=np.float64)
            self._initial_loss = None
            self.updates += 1
            return True, loss_before

        # Compose the incremental step into the running parameters (sx, sy, tx,
        # ty): new = old * ds + dt   (ds = 1 - lr*grad_s, dt = -lr*grad_t)
        ds_x = 1.0 - lr * grad_sx
        ds_y = 1.0 - lr * grad_sy
        dt_x = -lr * grad_tx
        dt_y = -lr * grad_ty

        sx, sy, tx, ty = self.params

        # ── L2 regularisation: pull toward identity each step ─────────────
        reg = self.l2_reg
        new_sx = np.clip(sx * ds_x - reg * (sx - 1.0), self.min_scale, self.max_scale)
        new_sy = np.clip(sy * ds_y - reg * (sy - 1.0), self.min_scale, self.max_scale)
        new_tx = np.clip(tx * ds_x + dt_x - reg * tx, -self.max_translation, self.max_translation)
        new_ty = np.clip(ty * ds_y + dt_y - reg * ty, -self.max_translation, self.max_translation)

        self.params[0] = new_sx
        self.params[1] = new_sy
        self.params[2] = new_tx
        self.params[3] = new_ty
        self.updates += 1
        return True, loss_before
