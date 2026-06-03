# -*- coding: utf-8 -*-
"""
NanoDetLite — Lightweight Object Detector
==========================================
Train on COCO and export a single verified ONNX model.

Usage
-----
    # 1. (Optional) download COCO 2017 train split first
    python train_nanodet.py --download-coco

    # 2. Train then export
    python train_nanodet.py

    # 3. Export only (from an existing checkpoint)
    python train_nanodet.py --export-only

    # 4. Quick smoke-test (2 steps per epoch)
    python train_nanodet.py --max-steps 2 --epochs 1

Outputs
-------
    checkpoints/best.pt   — best model weights (saved during training)
    nanodet.onnx          — verified ONNX export
    logs/train.log        — training log
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import random
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import requests
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as T
from torch.utils.data import DataLoader, random_split
from torchvision.datasets import CocoDetection
from torchvision.ops import box_iou, nms
from tqdm.auto import tqdm

# ============================================================
# LOGGING
# ============================================================
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "train.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

try:
    from torch.utils.tensorboard import SummaryWriter
    _TB_AVAILABLE = True
except ImportError:
    _TB_AVAILABLE = False
    log.warning("TensorBoard not available — pip install tensorboard to enable.")


# ============================================================
# CONFIG
# ============================================================
@dataclass
class Config:
    # Data
    img_dir:     str   = "coco/train2017"
    ann_path:    str   = "coco/annotations/instances_train2017.json"
    img_size:    int   = 320
    num_classes: int   = 80
    val_split:   float = 0.05

    # Training
    batch_size:   int           = 8
    epochs:       int           = 10
    max_steps:    Optional[int] = None   # None = no limit (use for debug)
    lr:           float         = 1e-4
    weight_decay: float         = 1e-4
    grad_clip:    float         = 10.0
    seed:         int           = 42

    # Focal loss
    focal_alpha: float = 0.25
    focal_gamma: float = 2.0

    # Loss weights
    w_cls: float = 1.0
    w_obj: float = 1.0
    w_box: float = 5.0

    # Box encoding — pure sigmoid (no exp)
    # xy : sigmoid(pred) → cell offset ∈ (0,1)
    # wh : sigmoid(pred) * wh_scale → size relative to image
    wh_scale: float = 2.0

    # Checkpoint
    ckpt_dir:   str           = "checkpoints"
    save_every: int           = 1
    resume:     Optional[str] = None

    # Export
    onnx_path: str = "nanodet.onnx"
    opset:     int = 18

    # Inference
    conf_threshold:    float = 0.4
    nms_iou_threshold: float = 0.5

    # mAP
    map_iou_threshold: float = 0.5

    # COCO valid category IDs (80 classes).
    # Leave empty ([]) for automatic dynamic mapping from the annotations file.
    coco_valid_ids: list = field(default_factory=lambda: [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 24, 25, 27, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
        41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58,
        59, 60, 61, 62, 63, 64, 65, 67, 70, 72, 73, 74, 75, 76, 77, 78, 79,
        80, 81, 82, 84, 85, 86, 87, 88, 89, 90,
    ])

    def __post_init__(self) -> None:
        assert 0 < self.val_split < 1,  "val_split must be in (0, 1)"
        assert self.img_size % 32 == 0, "img_size must be divisible by 32"
        if self.coco_valid_ids:
            assert len(self.coco_valid_ids) == self.num_classes, (
                f"num_classes ({self.num_classes}) != len(coco_valid_ids) "
                f"({len(self.coco_valid_ids)}). "
                "Set coco_valid_ids=[] for dynamic mapping."
            )

    @property
    def label_map(self) -> dict[int, int]:
        """category_id → contiguous index. Valid only when coco_valid_ids is set."""
        return {old: i for i, old in enumerate(self.coco_valid_ids)}

    @property
    def device(self) -> torch.device:
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    @property
    def feature_size(self) -> int:
        return self.img_size // 16


CFG = Config()


# ============================================================
# REPRODUCIBILITY
# ============================================================
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ============================================================
# MODEL
# ============================================================
class DWConv(nn.Module):
    """Depthwise-separable convolution (MobileNet-style)."""
    def __init__(self, in_ch: int, out_ch: int, stride: int = 1) -> None:
        super().__init__()
        self.depthwise = nn.Conv2d(
            in_ch, in_ch, 3, stride=stride, padding=1, groups=in_ch, bias=False
        )
        self.pointwise = nn.Conv2d(in_ch, out_ch, 1, bias=False)
        self.bn  = nn.BatchNorm2d(out_ch)
        self.act = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.bn(self.pointwise(self.depthwise(x))))


class Backbone(nn.Module):
    """4× DWConv stride-2 → total stride 16."""
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            DWConv(3,   16, stride=2),   # 320 → 160
            DWConv(16,  32, stride=2),   # 160 →  80
            DWConv(32,  64, stride=2),   #  80 →  40
            DWConv(64, 128, stride=2),   #  40 →  20
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class Head(nn.Module):
    """Single-scale detection head: classification / objectness / box regression."""
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        self.shared = nn.Conv2d(128, 128, 3, padding=1)
        self.cls    = nn.Conv2d(128, num_classes, 1)
        self.obj    = nn.Conv2d(128, 1, 1)
        self.box    = nn.Conv2d(128, 4, 1)
        self._init_biases()

    def _init_biases(self) -> None:
        prior_prob = 0.01
        bias_val   = -math.log((1 - prior_prob) / prior_prob)
        nn.init.constant_(self.cls.bias, bias_val)
        nn.init.constant_(self.obj.bias, bias_val)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = F.relu(self.shared(x), inplace=True)
        return self.cls(x), self.obj(x), self.box(x)


class NanoDetLite(nn.Module):
    def __init__(self, num_classes: int = 80) -> None:
        super().__init__()
        self.backbone = Backbone()
        self.head     = Head(num_classes)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        return self.head(self.backbone(x))


# ============================================================
# LABEL MAP
# ============================================================
def build_label_map_from_annotations(
    ann_path: str,
) -> tuple[dict[int, int], int]:
    """Build category_id → contiguous-index mapping from COCO annotations."""
    with open(ann_path, "r") as f:
        data = json.load(f)
    cats      = sorted(data["categories"], key=lambda c: c["id"])
    label_map = {c["id"]: i for i, c in enumerate(cats)}
    log.info(
        "Dynamic label map: %d classes (ids %d → %d)",
        len(label_map), cats[0]["id"], cats[-1]["id"],
    )
    return label_map, len(label_map)


# ============================================================
# TARGET BUILDING  (pure-sigmoid box encoding)
# ============================================================
def build_targets(
    targets:    list[list[dict]],
    batch_size: int,
    H:          int,
    W:          int,
    cfg:        Config,
    label_map:  dict[int, int],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Build cls_t / obj_t / box_t tensors from a list of COCO annotation dicts.

    Box encoding (symmetric with decoding — no exp()):
      tx, ty  : cell offset  ∈ [0, 1]
      tw, th  : size / (img_size * wh_scale)  ∈ [0, 1]
    """
    cls_t  = torch.zeros((batch_size, cfg.num_classes, H, W))
    obj_t  = torch.zeros((batch_size, 1, H, W))
    box_t  = torch.zeros((batch_size, 4, H, W))
    stride = cfg.img_size / H

    for b, anns in enumerate(targets):
        cls_ids, cxs, cys, ws, hs = [], [], [], [], []
        for ann in anns:
            if "bbox" not in ann or "category_id" not in ann:
                continue
            raw_id = ann["category_id"]
            if raw_id not in label_map:
                continue
            x, y, w, h = ann["bbox"]
            if w < 2 or h < 2:
                continue
            cls_ids.append(label_map[raw_id])
            cxs.append(x + w / 2)
            cys.append(y + h / 2)
            ws.append(w)
            hs.append(h)

        if not cls_ids:
            continue

        cls_ids_t = torch.tensor(cls_ids, dtype=torch.long)
        cx  = torch.tensor(cxs, dtype=torch.float32)
        cy  = torch.tensor(cys, dtype=torch.float32)
        w_t = torch.tensor(ws,  dtype=torch.float32)
        h_t = torch.tensor(hs,  dtype=torch.float32)

        gx = cx / stride
        gy = cy / stride
        ix = gx.long().clamp(0, W - 1)
        iy = gy.long().clamp(0, H - 1)

        tx = gx - ix.float()
        ty = gy - iy.float()
        tw = (w_t / cfg.img_size) / cfg.wh_scale
        th = (h_t / cfg.img_size) / cfg.wh_scale

        # Last annotation wins on cell collision (same as naive loop)
        cls_t[b, cls_ids_t, iy, ix] = 1.0
        obj_t[b, 0,         iy, ix] = 1.0
        box_t[b, 0,         iy, ix] = tx
        box_t[b, 1,         iy, ix] = ty
        box_t[b, 2,         iy, ix] = tw
        box_t[b, 3,         iy, ix] = th

    return cls_t, obj_t, box_t


def make_collate(cfg: Config, label_map: dict[int, int]):
    """Return a collate_fn that captures cfg and label_map."""
    H = W = cfg.feature_size

    def collate_fn(batch):
        imgs, targets = zip(*batch)
        cls_t, obj_t, box_t = build_targets(
            targets, len(batch), H, W, cfg, label_map
        )
        return torch.stack(imgs), cls_t, obj_t, box_t

    return collate_fn


# ============================================================
# LOSS
# ============================================================
def focal_loss(
    pred:   torch.Tensor,
    target: torch.Tensor,
    alpha:  float = 0.25,
    gamma:  float = 2.0,
) -> torch.Tensor:
    """Numerically-stable binary focal loss (via logits)."""
    pred_sig = torch.sigmoid(pred)
    pt  = pred_sig * target + (1 - pred_sig) * (1 - target)
    bce = F.binary_cross_entropy_with_logits(pred, target, reduction="none")
    return (alpha * (1 - pt) ** gamma * bce).mean()


def compute_loss(
    cls_p: torch.Tensor, obj_p: torch.Tensor, box_p: torch.Tensor,
    cls_t: torch.Tensor, obj_t: torch.Tensor, box_t: torch.Tensor,
    cfg:    Config,
    device: torch.device,
) -> tuple[torch.Tensor, dict[str, float]]:
    cls_loss = focal_loss(cls_p, cls_t, cfg.focal_alpha, cfg.focal_gamma)
    obj_loss = F.binary_cross_entropy_with_logits(obj_p, obj_t)

    mask = (obj_t > 0).squeeze(1)   # [B, H, W]
    if mask.any():
        p_sig    = torch.sigmoid(box_p.permute(0, 2, 3, 1)[mask])   # [N, 4]
        g        = box_t.permute(0, 2, 3, 1)[mask]                  # [N, 4]
        box_loss = F.smooth_l1_loss(p_sig, g)
    else:
        box_loss = torch.tensor(0.0, device=device)

    total   = cfg.w_cls * cls_loss + cfg.w_obj * obj_loss + cfg.w_box * box_loss
    details = {
        "loss/cls":   cls_loss.item(),
        "loss/obj":   obj_loss.item(),
        "loss/box":   box_loss.item(),
        "loss/total": total.item(),
    }
    return total, details


# ============================================================
# DECODE — pure sigmoid, symmetric with encoding
# ============================================================
def decode(
    cls: torch.Tensor,
    obj: torch.Tensor,
    box: torch.Tensor,
    cfg: Config,
) -> Optional[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
    """
    Decode raw predictions → absolute pixel boxes (x1,y1,x2,y2).
    Returns (boxes [N,4], scores [N], labels [N]) or None if no confident detections.
    """
    B, _, H, W = cls.shape
    stride = cfg.img_size / H
    device = cls.device

    scores     = torch.sigmoid(cls) * torch.sigmoid(obj)   # [B, C, H, W]
    conf, label = scores.max(dim=1)                         # [B, H, W]
    keep        = conf > cfg.conf_threshold

    if not keep.any():
        return None

    gy, gx = torch.meshgrid(
        torch.arange(H, device=device, dtype=torch.float32),
        torch.arange(W, device=device, dtype=torch.float32),
        indexing="ij",
    )
    gx = gx.unsqueeze(0).expand(B, -1, -1)
    gy = gy.unsqueeze(0).expand(B, -1, -1)

    raw  = box.permute(0, 2, 3, 1)[keep]   # [N, 4]
    b_gx = gx[keep]
    b_gy = gy[keep]

    pred_cx = (torch.sigmoid(raw[:, 0]) + b_gx) * stride
    pred_cy = (torch.sigmoid(raw[:, 1]) + b_gy) * stride
    pred_w  = torch.sigmoid(raw[:, 2]) * cfg.wh_scale * cfg.img_size
    pred_h  = torch.sigmoid(raw[:, 3]) * cfg.wh_scale * cfg.img_size

    x1 = pred_cx - pred_w / 2
    y1 = pred_cy - pred_h / 2
    x2 = pred_cx + pred_w / 2
    y2 = pred_cy + pred_h / 2

    return torch.stack([x1, y1, x2, y2], dim=1), conf[keep], label[keep]


# ============================================================
# mAP
# ============================================================
def _ap_from_pr(precisions: np.ndarray, recalls: np.ndarray) -> float:
    """AP by 11-point interpolation (Pascal VOC 2010)."""
    ap = 0.0
    for thr in np.linspace(0, 1, 11):
        mask = recalls >= thr
        ap  += precisions[mask].max() if mask.any() else 0.0
    return ap / 11.0


def per_class_ap(
    all_pred_boxes:  list[torch.Tensor],
    all_pred_scores: list[torch.Tensor],
    all_pred_labels: list[torch.Tensor],
    all_gt_boxes:    list[torch.Tensor],
    all_gt_labels:   list[torch.Tensor],
    num_classes:     int,
    iou_threshold:   float = 0.5,
) -> dict[int, float]:
    """AP@iou_threshold per class, accumulating over all images (Pascal VOC style)."""
    class_preds: dict[int, list[tuple[float, int]]] = defaultdict(list)
    class_n_gt:  dict[int, int]                     = defaultdict(int)

    for p_boxes, p_scores, p_labels, g_boxes, g_labels in zip(
        all_pred_boxes, all_pred_scores, all_pred_labels,
        all_gt_boxes,   all_gt_labels,
    ):
        for cls_id in g_labels.tolist():
            class_n_gt[int(cls_id)] += 1

        for cls_id in range(num_classes):
            pred_mask = p_labels == cls_id
            gt_mask   = g_labels == cls_id
            p_b = p_boxes[pred_mask]
            p_s = p_scores[pred_mask]
            g_b = g_boxes[gt_mask]

            if p_b.shape[0] == 0:
                continue

            order   = p_s.argsort(descending=True)
            p_b     = p_b[order]
            matched = np.zeros(g_b.shape[0], dtype=bool)

            if g_b.shape[0] > 0:
                ious = box_iou(p_b, g_b).cpu().numpy()
                for i in range(p_b.shape[0]):
                    best_iou, best_gt = -1.0, -1
                    for j in range(g_b.shape[0]):
                        if not matched[j] and ious[i, j] > best_iou:
                            best_iou, best_gt = ious[i, j], j
                    is_tp = int(best_iou >= iou_threshold)
                    if is_tp:
                        matched[best_gt] = True
                    class_preds[cls_id].append((p_s[i].item(), is_tp))
            else:
                for i in range(p_b.shape[0]):
                    class_preds[cls_id].append((p_s[i].item(), 0))

    ap_per_class: dict[int, float] = {}
    for cls_id in range(num_classes):
        n_gt = class_n_gt.get(cls_id, 0)
        if n_gt == 0:
            ap_per_class[cls_id] = float("nan")
            continue
        preds = sorted(class_preds.get(cls_id, []), key=lambda x: -x[0])
        if not preds:
            ap_per_class[cls_id] = 0.0
            continue
        tp_arr     = np.array([p[1] for p in preds], dtype=np.float32)
        cum_tp     = np.cumsum(tp_arr)
        cum_fp     = np.cumsum(1 - tp_arr)
        recalls    = cum_tp / (n_gt + 1e-9)
        precisions = cum_tp / (cum_tp + cum_fp + 1e-9)
        ap_per_class[cls_id] = _ap_from_pr(precisions, recalls)

    return ap_per_class


def compute_map_50(
    all_pred_boxes:  list[torch.Tensor],
    all_pred_scores: list[torch.Tensor],
    all_pred_labels: list[torch.Tensor],
    all_gt_boxes:    list[torch.Tensor],
    all_gt_labels:   list[torch.Tensor],
    num_classes:     int,
    iou_threshold:   float = 0.5,
) -> tuple[float, dict[int, float]]:
    ap_dict   = per_class_ap(
        all_pred_boxes, all_pred_scores, all_pred_labels,
        all_gt_boxes,   all_gt_labels,
        num_classes,    iou_threshold,
    )
    valid_aps = [v for v in ap_dict.values() if not math.isnan(v)]
    map50     = float(np.mean(valid_aps)) if valid_aps else 0.0
    return map50, ap_dict


def compute_detection_metrics(
    all_pred_boxes:  list[torch.Tensor],
    all_pred_scores: list[torch.Tensor],
    all_pred_labels: list[torch.Tensor],
    all_gt_boxes:    list[torch.Tensor],
    all_gt_labels:   list[torch.Tensor],
    iou_threshold:   float = 0.5,
) -> dict[str, float]:
    """Global Precision / Recall / F1 (class-aware greedy matching)."""
    total_tp = total_fp = total_fn = 0

    for p_boxes, p_scores, p_labels, g_boxes, g_labels in zip(
        all_pred_boxes, all_pred_scores, all_pred_labels,
        all_gt_boxes,   all_gt_labels,
    ):
        n_gt = g_boxes.shape[0]
        n_p  = p_boxes.shape[0]
        if n_p == 0:
            total_fn += n_gt
            continue
        if n_gt == 0:
            total_fp += n_p
            continue

        order    = p_scores.argsort(descending=True)
        p_boxes  = p_boxes[order]
        p_labels = p_labels[order]
        ious     = box_iou(p_boxes, g_boxes).cpu()
        matched  = torch.zeros(n_gt, dtype=torch.bool)

        for i in range(n_p):
            same_class  = (p_labels[i] == g_labels)
            candidates  = same_class & ~matched
            if not candidates.any():
                total_fp += 1
                continue
            iou_row              = ious[i].clone()
            iou_row[~candidates] = -1.0
            best_iou, best_j     = iou_row.max(dim=0)
            if best_iou >= iou_threshold:
                total_tp        += 1
                matched[best_j]  = True
            else:
                total_fp += 1

        total_fn += int((~matched).sum().item())

    precision = total_tp / (total_tp + total_fp + 1e-9)
    recall    = total_tp / (total_tp + total_fn + 1e-9)
    f1        = 2 * precision * recall / (precision + recall + 1e-9)
    return {
        "metrics/precision": float(precision),
        "metrics/recall":    float(recall),
        "metrics/f1":        float(f1),
    }


@torch.no_grad()
def evaluate_map(
    model:      nn.Module,
    loader:     DataLoader,
    cfg:        Config,
    device:     torch.device,
    max_images: Optional[int] = None,
) -> tuple[float, dict[int, float], dict[str, float]]:
    """
    Run inference on `loader` and compute mAP@cfg.map_iou_threshold.

    Returns (mAP50, per_class_AP, detection_metrics).
    `max_images` limits the number of images evaluated (useful during training).
    """
    model.eval()
    all_pred_boxes:  list[torch.Tensor] = []
    all_pred_scores: list[torch.Tensor] = []
    all_pred_labels: list[torch.Tensor] = []
    all_gt_boxes:    list[torch.Tensor] = []
    all_gt_labels:   list[torch.Tensor] = []

    n_images = 0
    stride   = cfg.img_size / cfg.feature_size

    for imgs, cls_t, obj_t, box_t in tqdm(loader, desc="mAP eval", leave=False):
        imgs = imgs.to(device, non_blocking=True)
        cls_p, obj_p, box_p = model(imgs)
        B, _, H, W = cls_p.shape

        for b in range(B):
            result = decode(cls_p[b:b+1], obj_p[b:b+1], box_p[b:b+1], cfg)
            if result is not None:
                boxes, scores, labels = result
                keep_idx = nms(boxes, scores, cfg.nms_iou_threshold)
                all_pred_boxes.append(boxes[keep_idx].cpu())
                all_pred_scores.append(scores[keep_idx].cpu())
                all_pred_labels.append(labels[keep_idx].cpu())
            else:
                all_pred_boxes.append(torch.zeros((0, 4)))
                all_pred_scores.append(torch.zeros(0))
                all_pred_labels.append(torch.zeros(0, dtype=torch.long))

            pos_mask        = (obj_t[b, 0] > 0)
            pos_iy, pos_ix  = pos_mask.nonzero(as_tuple=True)

            if pos_iy.numel() > 0:
                raw_box     = box_t[b, :, pos_iy, pos_ix].T   # [N, 4]
                cx = (raw_box[:, 0] + pos_ix.float()) * stride
                cy = (raw_box[:, 1] + pos_iy.float()) * stride
                w  = raw_box[:, 2] * cfg.wh_scale * cfg.img_size
                h  = raw_box[:, 3] * cfg.wh_scale * cfg.img_size
                gt_boxes_b  = torch.stack([cx-w/2, cy-h/2, cx+w/2, cy+h/2], dim=1)
                gt_labels_b = cls_t[b, :, pos_iy, pos_ix].argmax(dim=0)
                all_gt_boxes.append(gt_boxes_b)
                all_gt_labels.append(gt_labels_b)
            else:
                all_gt_boxes.append(torch.zeros((0, 4)))
                all_gt_labels.append(torch.zeros(0, dtype=torch.long))

            n_images += 1
            if max_images is not None and n_images >= max_images:
                break

        if max_images is not None and n_images >= max_images:
            break

    map50, ap_dict = compute_map_50(
        all_pred_boxes, all_pred_scores, all_pred_labels,
        all_gt_boxes,   all_gt_labels,
        cfg.num_classes, cfg.map_iou_threshold,
    )
    det_metrics = compute_detection_metrics(
        all_pred_boxes, all_pred_scores, all_pred_labels,
        all_gt_boxes,   all_gt_labels,
        iou_threshold=cfg.map_iou_threshold,
    )
    return map50, ap_dict, det_metrics


# ============================================================
# CHECKPOINT
# ============================================================
class CheckpointManager:
    def __init__(self, ckpt_dir: str) -> None:
        self.ckpt_dir = Path(ckpt_dir)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        epoch:     int,
        model:     nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler,
        metrics:   dict,
        cfg:       Config,
    ) -> Path:
        path = self.ckpt_dir / f"epoch_{epoch:04d}.pt"
        torch.save({
            "epoch":     epoch,
            "model":     model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "metrics":   metrics,
            "cfg":       cfg.__dict__,
        }, path)
        log.info("Checkpoint saved: %s", path)
        return path

    def load(
        self,
        path:      str,
        model:     nn.Module,
        optimizer: torch.optim.Optimizer,
        scheduler,
    ) -> int:
        ckpt = torch.load(path, map_location="cpu")
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        scheduler.load_state_dict(ckpt["scheduler"])
        log.info("Resumed from %s (epoch %d)", path, ckpt["epoch"])
        return ckpt["epoch"]


# ============================================================
# TRAINING LOOP
# ============================================================
def run_epoch(
    model:       nn.Module,
    loader:      DataLoader,
    optimizer:   torch.optim.Optimizer,
    scaler:      torch.amp.GradScaler,
    cfg:         Config,
    device:      torch.device,
    writer=None,
    global_step: int  = 0,
    train:       bool = True,
) -> tuple[dict[str, float], int]:
    model.train(train)
    totals:    dict[str, float] = {}
    n_batches: int = 0
    ctx = torch.amp.autocast("cuda", enabled=(device.type == "cuda"))

    with tqdm(loader, desc="train" if train else "val", leave=False) as pbar:
        for step, (imgs, cls_t, obj_t, box_t) in enumerate(pbar):
            imgs  = imgs.to(device,  non_blocking=True)
            cls_t = cls_t.to(device, non_blocking=True)
            obj_t = obj_t.to(device, non_blocking=True)
            box_t = box_t.to(device, non_blocking=True)

            with ctx:
                cls_p, obj_p, box_p = model(imgs)
                loss, details = compute_loss(
                    cls_p, obj_p, box_p, cls_t, obj_t, box_t, cfg, device
                )

            if train:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                scaler.step(optimizer)
                scaler.update()

                if writer:
                    for k, v in details.items():
                        writer.add_scalar(k, v, global_step)
                global_step += 1

            for k, v in details.items():
                totals[k] = totals.get(k, 0.0) + v
            n_batches += 1
            pbar.set_postfix(loss=f"{details['loss/total']:.4f}")

            if cfg.max_steps is not None and step >= cfg.max_steps - 1:
                log.debug("max_steps=%d reached.", cfg.max_steps)
                break

    averages = {k: v / n_batches for k, v in totals.items()}
    return averages, global_step


def train(cfg: Config = CFG) -> None:
    set_seed(cfg.seed)
    device = cfg.device
    log.info("Device: %s", device)

    if not (Path(cfg.img_dir).exists() and Path(cfg.ann_path).exists()):
        log.error("Dataset not found: %s / %s", cfg.img_dir, cfg.ann_path)
        log.error("Run with --download-coco to download COCO first.")
        return

    transform = T.Compose([
        T.Resize((cfg.img_size, cfg.img_size)),
        T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        T.ToTensor(),
    ])

    full_dataset = CocoDetection(cfg.img_dir, cfg.ann_path, transform=transform)
    n_val   = max(1, int(len(full_dataset) * cfg.val_split))
    n_train = len(full_dataset) - n_val
    train_ds, val_ds = random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(cfg.seed),
    )
    log.info("Dataset: %d train, %d val", n_train, n_val)

    if cfg.coco_valid_ids:
        label_map   = cfg.label_map
        num_classes = cfg.num_classes
    else:
        label_map, num_classes = build_label_map_from_annotations(cfg.ann_path)
        if num_classes != cfg.num_classes:
            log.warning(
                "num_classes config (%d) != annotations (%d) — using %d",
                cfg.num_classes, num_classes, num_classes,
            )

    collate   = make_collate(cfg, label_map)
    n_workers             = min(4, os.cpu_count() or 1)
    use_persistent_workers = n_workers > 0   # persistent_workers requires num_workers > 0

    train_loader = DataLoader(
        train_ds, batch_size=cfg.batch_size, shuffle=True,
        collate_fn=collate, num_workers=n_workers,
        pin_memory=(device.type == "cuda"), persistent_workers=use_persistent_workers,
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg.batch_size, shuffle=False,
        collate_fn=collate, num_workers=max(1, n_workers // 2),
        pin_memory=(device.type == "cuda"), persistent_workers=use_persistent_workers,
    )

    model = NanoDetLite(cfg.num_classes).to(device)
    log.info("Parameters: %.2f M", sum(p.numel() for p in model.parameters()) / 1e6)

    optimizer   = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
    )
    total_steps = cfg.epochs * len(train_loader)
    scheduler   = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=total_steps, eta_min=cfg.lr * 1e-2
    )
    scaler   = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))
    ckpt_mgr = CheckpointManager(cfg.ckpt_dir)
    writer   = SummaryWriter(LOG_DIR / "tb") if _TB_AVAILABLE else None

    start_epoch = 0
    global_step = 0
    if cfg.resume:
        start_epoch = ckpt_mgr.load(cfg.resume, model, optimizer, scheduler)

    best_map50 = 0.0

    for epoch in range(start_epoch, cfg.epochs):
        log.info("── Epoch %d/%d ──", epoch + 1, cfg.epochs)

        train_metrics, global_step = run_epoch(
            model, train_loader, optimizer, scaler, cfg, device,
            writer=writer, global_step=global_step, train=True,
        )
        scheduler.step()

        with torch.no_grad():
            val_metrics, _ = run_epoch(
                model, val_loader, optimizer, scaler, cfg, device,
                writer=writer, global_step=global_step, train=False,
            )

        map50, ap_dict, det_metrics = evaluate_map(
            model, val_loader, cfg, device, max_images=500
        )

        log.info(
            "train_loss=%.4f  val_loss=%.4f  mAP@50=%.4f  "
            "P=%.3f  R=%.3f  F1=%.3f  lr=%.2e",
            train_metrics["loss/total"],
            val_metrics["loss/total"],
            map50,
            det_metrics["metrics/precision"],
            det_metrics["metrics/recall"],
            det_metrics["metrics/f1"],
            optimizer.param_groups[0]["lr"],
        )

        if writer:
            for k, v in val_metrics.items():
                writer.add_scalar("val/" + k.split("/")[1], v, epoch)
            writer.add_scalar("metrics/mAP50", map50, epoch)
            for k, v in det_metrics.items():
                writer.add_scalar(k, v, epoch)
            writer.add_scalar("lr", optimizer.param_groups[0]["lr"], epoch)

        if (epoch + 1) % cfg.save_every == 0:
            ckpt_mgr.save(
                epoch + 1, model, optimizer, scheduler,
                {**val_metrics, "mAP50": map50, **det_metrics}, cfg,
            )

        if map50 > best_map50:
            best_map50 = map50
            best_path  = Path(cfg.ckpt_dir) / "best.pt"
            torch.save(model.state_dict(), best_path)
            log.info("→ New best model saved (mAP@50=%.4f)", best_map50)

        valid_aps = [(c, v) for c, v in ap_dict.items() if not math.isnan(v)]
        top10     = sorted(valid_aps, key=lambda x: -x[1])[:10]
        log.info("  Top-10 AP: %s",
                 "  ".join(f"cls{c}={v:.3f}" for c, v in top10))

    if writer:
        writer.close()
    log.info("✔ TRAINING COMPLETE (best mAP@50=%.4f)", best_map50)


# ============================================================
# ONNX EXPORT
# ============================================================
def export_onnx(
    model:        Optional[nn.Module] = None,
    cfg:          Config              = CFG,
    weights_path: Optional[str]       = None,
) -> None:
    """
    Export NanoDetLite to a single verified ONNX file.

    Outputs (3 feature maps from the detection head):
      - cls  [1, num_classes, H, W]  — class logits
      - obj  [1, 1,           H, W]  — objectness logits
      - box  [1, 4,           H, W]  — box regression (sigmoid-encoded)
    """
    if model is None:
        model = NanoDetLite(cfg.num_classes)
        if weights_path and Path(weights_path).exists():
            ckpt  = torch.load(weights_path, map_location="cpu")
            state = ckpt.get("model", ckpt)   # support both full ckpt and bare state_dict
            model.load_state_dict(state)
            log.info("Weights loaded from %s", weights_path)
        else:
            log.warning(
                "No weights file found at '%s' — exporting with random weights.",
                weights_path,
            )

    model.eval().cpu()
    dummy = torch.randn(1, 3, cfg.img_size, cfg.img_size)

    torch.onnx.export(
        model,
        dummy,
        cfg.onnx_path,
        input_names=["input"],
        output_names=["cls", "obj", "box"],
        opset_version=cfg.opset,
        do_constant_folding=True,
    )
    log.info("ONNX exported: %s", cfg.onnx_path)

    # Verify coherence between PyTorch and OnnxRuntime
    try:
        import onnx
        import onnxruntime as ort

        onnx.checker.check_model(onnx.load(cfg.onnx_path))
        log.info("ONNX model check passed.")

        sess     = ort.InferenceSession(cfg.onnx_path, providers=["CPUExecutionProvider"])
        ort_outs = sess.run(None, {"input": dummy.numpy()})

        with torch.no_grad():
            pt_outs = [t.numpy() for t in model(dummy)]

        for i, (pt, ort_out) in enumerate(zip(pt_outs, ort_outs)):
            max_diff = np.abs(pt - ort_out).max()
            log.info("Output[%d] max_diff PyTorch/ONNX = %.2e", i, max_diff)
            assert max_diff < 1e-4, (
                f"Numerical discrepancy too large on output[{i}]: {max_diff:.2e}"
            )

        log.info("✔ ONNX verified — PyTorch / OnnxRuntime outputs match.")

    except ImportError:
        log.warning("onnx / onnxruntime not installed — skipping verification.")
    except AssertionError as e:
        log.error("ONNX verification failed: %s", e)
        raise


# ============================================================
# COCO DOWNLOAD  (optional helper — call with --download-coco)
# ============================================================
def _safe_remove(path: str) -> None:
    if os.path.exists(path):
        log.info("Removing: %s", path)
        os.remove(path)


def _download_file(url: str, path: str, retries: int = 5) -> None:
    for attempt in range(retries):
        try:
            log.info("Downloading (%d/%d) %s", attempt + 1, retries, path)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total      = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
            if total > 0 and downloaded < total * 0.95:
                raise RuntimeError("Incomplete download")
            log.info("Downloaded: %s", path)
            return
        except Exception as e:
            log.warning("Download error: %s", e)
            time.sleep(2)
    raise RuntimeError(f"Failed to download after {retries} attempts: {path}")


def _validate_zip(path: str) -> bool:
    try:
        if not zipfile.is_zipfile(path):
            raise ValueError("Not a valid zip archive")
        with zipfile.ZipFile(path, "r") as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f"Corrupt entry: {bad}")
        return True
    except Exception as e:
        log.warning("ZIP invalid: %s → %s", path, e)
        return False


def _safe_extract(zip_path: str, out_dir: str) -> None:
    marker = os.path.join(out_dir, f".extracted_{os.path.basename(zip_path)}")
    if os.path.exists(marker):
        log.info("Already extracted: %s", zip_path)
        return
    log.info("Extracting %s ...", zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_dir)
    open(marker, "w").close()
    log.info("Extracted: %s", zip_path)


def download_coco(data_dir: str = "coco") -> None:
    """Download and extract the COCO 2017 train split + annotations."""
    os.makedirs(data_dir, exist_ok=True)
    files = {
        "train2017.zip":   "http://images.cocodataset.org/zips/train2017.zip",
        "annotations.zip": "http://images.cocodataset.org/annotations/annotations_trainval2017.zip",
    }
    for name, url in files.items():
        if os.path.exists(name) and _validate_zip(name):
            log.info("Valid cache: %s", name)
        else:
            _safe_remove(name)
            _download_file(url, name)
            if not _validate_zip(name):
                _safe_remove(name)
                raise RuntimeError(f"Download permanently corrupted: {name}")
        _safe_extract(name, data_dir)

    ann_path = os.path.join(data_dir, "annotations", "instances_train2017.json")
    with open(ann_path, "r") as f:
        data = json.load(f)
    log.info(
        "COCO ready — images: %d, annotations: %d",
        len(data["images"]), len(data["annotations"]),
    )


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train NanoDetLite on COCO and export a verified ONNX model."
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="Skip training; load best.pt and export ONNX only.",
    )
    parser.add_argument(
        "--download-coco", action="store_true",
        help="Download COCO 2017 train split before training.",
    )
    parser.add_argument("--epochs",      type=int,   default=CFG.epochs)
    parser.add_argument("--batch-size",  type=int,   default=CFG.batch_size)
    parser.add_argument("--lr",          type=float, default=CFG.lr)
    parser.add_argument(
        "--max-steps", type=int, default=CFG.max_steps,
        help="Maximum steps per epoch (None = unlimited; use small value for smoke tests).",
    )
    parser.add_argument(
        "--resume", type=str, default=None,
        help="Path to a checkpoint (.pt) to resume training from.",
    )
    parser.add_argument("--onnx-path",   type=str,   default=CFG.onnx_path)
    parser.add_argument("--ckpt-dir",    type=str,   default=CFG.ckpt_dir)
    args = parser.parse_args()

    CFG.epochs     = args.epochs
    CFG.batch_size = args.batch_size
    CFG.lr         = args.lr
    CFG.max_steps  = args.max_steps
    CFG.onnx_path  = args.onnx_path
    CFG.ckpt_dir   = args.ckpt_dir
    if args.resume:
        CFG.resume = args.resume

    if args.download_coco:
        download_coco()

    if not args.export_only:
        train(CFG)

    best_weights = Path(CFG.ckpt_dir) / "best.pt"
    export_onnx(
        cfg=CFG,
        weights_path=str(best_weights) if best_weights.exists() else None,
    )
