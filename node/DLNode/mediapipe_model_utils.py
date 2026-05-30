"""Utilities for downloading MediaPipe task model files.

MediaPipe >= 0.10.14 removed the legacy ``mp.solutions`` API.  All wrappers
in this project now use the ``mp.tasks`` API, which requires explicit ``.tflite``
model files.  This module provides a thin helper that downloads a model from
Google Cloud Storage on first use and caches it locally.
"""

import os
import sys
import urllib.request
import logging

logger = logging.getLogger(__name__)

_GCS_BASE = "https://storage.googleapis.com/mediapipe-models"

# Mapping of logical model name  -> (GCS path segment, filename)
_MODEL_CATALOG = {
    "face_detector_short": (
        "face_detector/blaze_face_short_range/float16/1",
        "blaze_face_short_range.tflite",
    ),
    "face_landmarker": (
        "face_landmarker/face_landmarker/float16/1",
        "face_landmarker.task",
    ),
    "hand_landmarker": (
        "hand_landmarker/hand_landmarker/float16/1",
        "hand_landmarker.task",
    ),
    "pose_landmarker_lite": (
        "pose_landmarker/pose_landmarker_lite/float16/1",
        "pose_landmarker_lite.task",
    ),
    "pose_landmarker_full": (
        "pose_landmarker/pose_landmarker_full/float16/1",
        "pose_landmarker_full.task",
    ),
    "pose_landmarker_heavy": (
        "pose_landmarker/pose_landmarker_heavy/float16/1",
        "pose_landmarker_heavy.task",
    ),
    "selfie_segmenter": (
        "image_segmenter/selfie_segmenter/float16/1",
        "selfie_segmenter.tflite",
    ),
    "selfie_segmenter_landscape": (
        "image_segmenter/selfie_segmenter_landscape/float16/1",
        "selfie_segmenter_landscape.tflite",
    ),
}


def _cache_dir():
    """Return (and create) a directory for caching downloaded models."""
    if getattr(sys, "frozen", False):
        # Running as a bundled executable
        from src.utils.paths import get_models_dir

        base = get_models_dir("mediapipe_tasks")
    else:
        base = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "_mediapipe_task_models",
        )
    os.makedirs(base, exist_ok=True)
    return base


def get_model_path(model_key: str) -> str:
    """Return the local filesystem path for *model_key*, downloading if needed.

    Parameters
    ----------
    model_key:
        One of the keys in ``_MODEL_CATALOG`` (e.g. ``"face_detector_short"``).

    Returns
    -------
    str
        Absolute path to the ``.tflite`` file.
    """
    if model_key not in _MODEL_CATALOG:
        raise ValueError(
            f"Unknown MediaPipe model key: {model_key!r}. "
            f"Available: {sorted(_MODEL_CATALOG)}"
        )

    gcs_path, filename = _MODEL_CATALOG[model_key]
    local_path = os.path.join(_cache_dir(), filename)

    if os.path.isfile(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    url = f"{_GCS_BASE}/{gcs_path}/{filename}"
    logger.info("Downloading MediaPipe model %s from %s …", model_key, url)
    try:
        urllib.request.urlretrieve(url, local_path)
    except Exception:
        # Clean up partial file
        if os.path.exists(local_path):
            os.remove(local_path)
        raise

    logger.info("Saved MediaPipe model to %s", local_path)
    return local_path
