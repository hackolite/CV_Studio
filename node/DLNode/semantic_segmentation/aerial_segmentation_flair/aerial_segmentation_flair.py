#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FLAIR IGN Aerial Semantic Segmentation
U-Net (ResNet-34) with 5-channel input (R, G, B, NIR, MNH).

Two backends are provided:
- ``FlairAerialSegmentation``: PyTorch backend, 13-class FLAIR-1 model.
- ``FlairAerialSegmentationONNX``: ONNX Runtime backend, 19-class FLAIR-2
  INT8 quantised model (``flair_aerial_seg_int8_N.onnx``).
"""
import os
import numpy as np
import cv2 as cv
from node.DLNode.object_detection.onnx_session_utils import make_session

# ---------------------------------------------------------------------------
# FLAIR-1 class definitions (13 classes — PyTorch backend)
# ---------------------------------------------------------------------------
NUM_CLASSES = 13

FLAIR_CLASSES = {
    0:  "Background",
    1:  "Building",
    2:  "Pervious surface",
    3:  "Impervious surface",
    4:  "Low vegetation",
    5:  "High vegetation",
    6:  "Water",
    7:  "Swimming pool",
    8:  "Snow",
    9:  "Agricultural greenhouse",
    10: "Vineyard",
    11: "Moor",
    12: "Other",
}

# BGR order (OpenCV convention)
FLAIR_COLORS_BGR = {
    0:  (0,   0,   0),
    1:  (73,  73,  219),   # building — red
    2:  (122, 154, 189),   # pervious surface — beige
    3:  (128, 128, 128),   # impervious surface — grey
    4:  (100, 218, 170),   # low vegetation — light green
    5:  (34,  139, 34),    # high vegetation — dark green
    6:  (219, 152, 52),    # water — blue
    7:  (255, 204, 102),   # swimming pool — light blue
    8:  (255, 255, 255),   # snow — white
    9:  (200, 230, 200),   # greenhouse — pale green
    10: (240, 32,  160),   # vineyard — violet
    11: (63,  133, 205),   # moor — brown
    12: (200, 200, 200),   # other — light grey
}

# ---------------------------------------------------------------------------
# FLAIR-2 class definitions (19 classes — ONNX INT8 backend)
# ---------------------------------------------------------------------------
NUM_CLASSES_FLAIR2 = 19

FLAIR2_CLASSES = {
    0:  "No information",
    1:  "Building",
    2:  "Pervious surface",
    3:  "Impervious surface",
    4:  "Bare soil",
    5:  "Water",
    6:  "Coniferous",
    7:  "Deciduous",
    8:  "Brushwood",
    9:  "Vineyard",
    10: "Herbaceous vegetation",
    11: "Agricultural land",
    12: "Plowed land",
    13: "Swimming pool",
    14: "Snow",
    15: "Clear cut",
    16: "Mixed",
    17: "Ligneous",
    18: "Greenhouse",
}

# BGR order (OpenCV convention)
FLAIR2_COLORS_BGR = {
    0:  (0,   0,   0),     # no information — black
    1:  (73,  73,  219),   # building — red
    2:  (122, 154, 189),   # pervious surface — beige
    3:  (128, 128, 128),   # impervious surface — grey
    4:  (100, 130, 180),   # bare soil — tan
    5:  (219, 152, 52),    # water — blue
    6:  (34,  100, 34),    # coniferous — dark green
    7:  (60,  179, 113),   # deciduous — medium green
    8:  (80,  120, 60),    # brushwood — olive green
    9:  (240, 32,  160),   # vineyard — violet
    10: (100, 218, 170),   # herbaceous vegetation — light green
    11: (180, 220, 100),   # agricultural land — yellow-green
    12: (80,  60,  40),    # plowed land — brown
    13: (255, 204, 102),   # swimming pool — light blue
    14: (255, 255, 255),   # snow — white
    15: (40,  140, 230),   # clear cut — orange
    16: (50,  160, 80),    # mixed — forest green
    17: (30,  60,  20),    # ligneous — dark brown
    18: (200, 230, 200),   # greenhouse — pale green
}

_HF_REPO_ID = "IGNF/FLAIR-INC_segmentation-detection"
_HF_FILENAME = "flair_model.pth"
_PATCH_SIZE = 512

_DEFAULT_ONNX_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "model",
    "flair_aerial_seg_int8_N.onnx",
)


def _build_color_lut():
    """Return a (13, 3) uint8 array of BGR colors indexed by class id."""
    lut = np.zeros((NUM_CLASSES, 3), dtype=np.uint8)
    for cls_id, bgr in FLAIR_COLORS_BGR.items():
        lut[cls_id] = bgr
    return lut


def _build_color_lut2():
    """Return a (19, 3) uint8 array of BGR colors indexed by class id."""
    lut = np.zeros((NUM_CLASSES_FLAIR2, 3), dtype=np.uint8)
    for cls_id, bgr in FLAIR2_COLORS_BGR.items():
        lut[cls_id] = bgr
    return lut


_COLOR_LUT = _build_color_lut()
_COLOR_LUT2 = _build_color_lut2()


def colorize_flair_mask(mask):
    """
    Convert an argmax mask (H, W) uint8 into a BGR color image (H, W, 3).

    Args:
        mask: numpy array (H, W) with class indices in [0, NUM_CLASSES-1].

    Returns:
        color_image: numpy array (H, W, 3) uint8 in BGR.
    """
    return _COLOR_LUT[mask]


def colorize_flair2_mask(mask):
    """
    Convert an argmax mask (H, W) uint8 into a BGR color image (H, W, 3)
    using the 19-class FLAIR-2 palette.

    Args:
        mask: numpy array (H, W) with class indices in [0, NUM_CLASSES_FLAIR2-1].

    Returns:
        color_image: numpy array (H, W, 3) uint8 in BGR.
    """
    clipped = np.clip(mask, 0, NUM_CLASSES_FLAIR2 - 1)
    return _COLOR_LUT2[clipped]


def overlay_flair(bgr_image, mask, alpha=0.5):
    """
    Blend FLAIR color mask over a BGR image.

    Args:
        bgr_image: (H, W, 3) uint8.
        mask:      (H, W) uint8 argmax class mask.
        alpha:     blend weight for the color overlay (0=original, 1=color).

    Returns:
        blended: (H, W, 3) uint8.
    """
    color = colorize_flair_mask(mask).astype(np.float32)
    orig  = bgr_image.astype(np.float32)
    h, w  = mask.shape
    orig  = orig[:h, :w]
    return np.clip(orig * (1.0 - alpha) + color * alpha, 0, 255).astype(np.uint8)


def overlay_flair2(bgr_image, mask, alpha=0.5):
    """
    Blend FLAIR-2 color mask over a BGR image (19-class palette).

    Args:
        bgr_image: (H, W, 3) uint8.
        mask:      (H, W) uint8 argmax class mask.
        alpha:     blend weight for the color overlay (0=original, 1=color).

    Returns:
        blended: (H, W, 3) uint8.
    """
    color = colorize_flair2_mask(mask).astype(np.float32)
    orig  = bgr_image.astype(np.float32)
    h, w  = mask.shape
    orig  = orig[:h, :w]
    return np.clip(orig * (1.0 - alpha) + color * alpha, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class FlairAerialSegmentation:
    """
    FLAIR IGN aerial segmentation wrapper.

    Attributes:
        _torch_model: the loaded segmentation_models_pytorch U-Net.
        _device:      torch.device (cpu or cuda).
    """

    def __init__(
        self,
        model_path=None,
        providers=('CUDAExecutionProvider', 'CPUExecutionProvider'),
    ):
        """
        Args:
            model_path: Path to a local ``flair_model.pth`` file.
                        If *None* or the file does not exist, the model is
                        downloaded automatically from HuggingFace Hub the first
                        time this constructor is called.
            providers:  Sequence of ONNX-style provider strings.  Used only to
                        decide whether to run on CUDA: if 'CUDAExecutionProvider'
                        is first in the list and CUDA is available, the model
                        runs on GPU.
        """
        self._torch_model = None
        self._device = None

        try:
            import torch
            import segmentation_models_pytorch as smp
        except ImportError as exc:
            raise ImportError(
                f"[FlairAerialSegmentation] Missing dependency: {exc}. "
                "Install with: pip install torch segmentation-models-pytorch huggingface_hub"
            ) from exc

        # ------------------------------------------------------------------
        # Resolve model path
        # ------------------------------------------------------------------
        resolved_path = model_path
        if not resolved_path or not os.path.isfile(resolved_path):
            try:
                from huggingface_hub import hf_hub_download
                resolved_path = hf_hub_download(
                    repo_id=_HF_REPO_ID,
                    filename=_HF_FILENAME,
                )
            except Exception as exc:
                raise RuntimeError(
                    f"[FlairAerialSegmentation] Could not download model from "
                    f"HuggingFace ({_HF_REPO_ID}/{_HF_FILENAME}): {exc}"
                ) from exc

        # ------------------------------------------------------------------
        # Select device
        # ------------------------------------------------------------------
        use_cuda = (
            isinstance(providers, (list, tuple))
            and len(providers) > 0
            and providers[0] == 'CUDAExecutionProvider'
            and torch.cuda.is_available()
        )
        self._device = torch.device("cuda" if use_cuda else "cpu")

        # ------------------------------------------------------------------
        # Build model architecture and load weights
        # ------------------------------------------------------------------
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None,
            in_channels=5,       # R, G, B, NIR, MNH
            classes=NUM_CLASSES,
        )
        state_dict = torch.load(resolved_path, map_location="cpu")
        load_result = model.load_state_dict(state_dict, strict=False)
        if load_result.missing_keys:
            from src.utils.logging import get_logger
            _logger = get_logger(__name__)
            _logger.warning(
                "[FlairAerialSegmentation] Missing keys when loading weights: %s",
                load_result.missing_keys,
            )
        if load_result.unexpected_keys:
            from src.utils.logging import get_logger
            _logger = get_logger(__name__)
            _logger.warning(
                "[FlairAerialSegmentation] Unexpected keys when loading weights: %s",
                load_result.unexpected_keys,
            )
        model.eval()
        model.to(self._device)
        self._torch_model = model

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def __call__(self, image):
        """
        Run FLAIR segmentation on a BGR frame.

        The method synthesises a 5-channel (R, G, B, NIR, MNH) tile from the
        RGB image: NIR is approximated by the red channel and MNH is set to
        zero (no height data available in a live video feed).

        Args:
            image: (H, W, 3) uint8 BGR numpy array.

        Returns:
            segmentation_map: (NUM_CLASSES, H, W) float32 probability map
                              compatible with ``draw_semantic_segmentation_info``.
        """
        import torch

        H, W = image.shape[:2]

        # BGR → RGB, normalise to [0, 1]
        rgb = cv.cvtColor(image, cv.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # Build 5-channel input: R, G, B, NIR≈R, MNH=0
        nir = rgb[:, :, 0:1]
        mnh = np.zeros((H, W, 1), dtype=np.float32)
        img5 = np.concatenate([rgb, nir, mnh], axis=-1)  # (H, W, 5)

        # Patch-based inference
        score_map = self._infer_patches(img5, H, W)

        # Convert to per-class probability maps expected by the node
        # score_map shape: (NUM_CLASSES, H, W)
        return score_map.astype(np.float32)

    def _infer_patches(self, img5, H, W):
        """Run inference with 512×512 patches (50 % overlap) and blend results."""
        import torch

        score_map = np.zeros((NUM_CLASSES, H, W), dtype=np.float32)
        count_map = np.zeros((H, W), dtype=np.float32)

        step = _PATCH_SIZE // 2

        ys = list(range(0, H, step))
        xs = list(range(0, W, step))

        with torch.no_grad():
            for y in ys:
                for x in xs:
                    y2 = min(y + _PATCH_SIZE, H)
                    x2 = min(x + _PATCH_SIZE, W)
                    y1 = max(0, y2 - _PATCH_SIZE)
                    x1 = max(0, x2 - _PATCH_SIZE)

                    patch = img5[y1:y2, x1:x2]  # (ph, pw, 5)
                    ph, pw = patch.shape[:2]

                    # Pad to exactly PATCH_SIZE × PATCH_SIZE if needed
                    if ph < _PATCH_SIZE or pw < _PATCH_SIZE:
                        padded = np.zeros(
                            (_PATCH_SIZE, _PATCH_SIZE, 5), dtype=np.float32
                        )
                        padded[:ph, :pw] = patch
                        patch = padded

                    # (1, 5, H, W)
                    t = (
                        torch.from_numpy(patch.transpose(2, 0, 1))
                        .unsqueeze(0)
                        .to(self._device)
                    )
                    logits = self._torch_model(t)  # (1, 13, 512, 512)
                    probs = (
                        torch.softmax(logits, dim=1)
                        .squeeze(0)
                        .cpu()
                        .numpy()
                    )  # (13, 512, 512)

                    score_map[:, y1:y2, x1:x2] += probs[:, :ph, :pw]
                    count_map[y1:y2, x1:x2] += 1.0

        count_map = np.maximum(count_map, 1.0)
        score_map /= count_map[np.newaxis]
        return score_map

    def get_class_num(self):
        return NUM_CLASSES

    @staticmethod
    def get_argmax_mask(segmentation_map):
        """
        Convert a (NUM_CLASSES, H, W) probability map to an (H, W) argmax mask.

        Args:
            segmentation_map: float32 array (NUM_CLASSES, H, W).

        Returns:
            mask: uint8 array (H, W) with class indices.
        """
        return np.argmax(segmentation_map, axis=0).astype(np.uint8)


# ---------------------------------------------------------------------------
# ONNX backend — FLAIR-2 INT8 quantised model (19 classes)
# ---------------------------------------------------------------------------

class FlairAerialSegmentationONNX:
    """
    FLAIR-2 IGN aerial segmentation wrapper using ONNX Runtime.

    Accepts an INT8-quantised ONNX model exported from the FLAIR-2 U-Net
    with 5-channel input (R, G, B, NIR, MNH) and 19 output classes.

    This class implements the same ``__call__ / get_class_num`` interface as
    the other semantic segmentation models so it integrates directly with
    ``node_semantic_segmentation.py``.
    """

    def __init__(
        self,
        model_path=None,
        providers=('CUDAExecutionProvider', 'CPUExecutionProvider'),
    ):
        """
        Args:
            model_path: Path to ``flair_aerial_seg_int8_N.onnx``.
                        Defaults to the bundled copy in the ``model/`` folder.
            providers:  OnnxRuntime execution providers.
        """
        resolved = model_path or _DEFAULT_ONNX_MODEL_PATH
        if not os.path.isfile(resolved):
            raise FileNotFoundError(
                f"[FlairAerialSegmentationONNX] Model not found: {resolved}"
            )

        self._session = make_session(
            resolved,
            providers=list(providers),
            disable_optimizations=True,
        )
        self._input_name = self._session.get_inputs()[0].name
        self._num_classes = self._session.get_outputs()[0].shape[1]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_class_num(self):
        return self._num_classes

    def __call__(self, image):
        """
        Run FLAIR-2 ONNX segmentation on a BGR frame.

        The method synthesises a 5-channel (R, G, B, NIR, MNH) input from
        the RGB image: NIR is approximated by the red channel and MNH is set
        to zero (no height data available in a live video feed).

        Args:
            image: (H, W, 3) uint8 BGR numpy array.

        Returns:
            segmentation_map: (num_classes, H, W) float32 probability map
                              compatible with ``draw_semantic_segmentation_info``
                              and ``overlay_flair2``.
        """
        H, W = image.shape[:2]

        # BGR → RGB, normalise to [0, 1]
        rgb = cv.cvtColor(image, cv.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # Build 5-channel input: R, G, B, NIR≈R, MNH=0
        nir = rgb[:, :, 0:1]
        mnh = np.zeros((H, W, 1), dtype=np.float32)
        img5 = np.concatenate([rgb, nir, mnh], axis=-1)  # (H, W, 5)

        # (1, 5, H, W)
        inp = img5.transpose(2, 0, 1)[np.newaxis].astype(np.float32)

        # Inference — model accepts dynamic spatial dimensions
        logits = self._session.run(None, {self._input_name: inp})[0]  # (1, C, H, W)

        # Softmax over class axis → probability map
        logits_sq = logits.squeeze(0)  # (C, H, W)
        exp = np.exp(logits_sq - logits_sq.max(axis=0, keepdims=True))
        probs = exp / exp.sum(axis=0, keepdims=True)
        return probs.astype(np.float32)

    @staticmethod
    def get_argmax_mask(segmentation_map):
        """
        Convert a (num_classes, H, W) probability map to an (H, W) argmax mask.

        Args:
            segmentation_map: float32 array (num_classes, H, W).

        Returns:
            mask: uint8 array (H, W) with class indices.
        """
        return np.argmax(segmentation_map, axis=0).astype(np.uint8)
