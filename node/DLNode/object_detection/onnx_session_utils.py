#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared onnxruntime session utilities for CvStudio object detection.
"""

import logging
import re
from typing import List, Union

import onnxruntime

logger = logging.getLogger(__name__)

# Pattern that matches onnxruntime's IR version error, e.g.:
# "Unsupported model IR version: 14, max supported IR version: 13"
_IR_VERSION_ERROR_RE = re.compile(
    r"Unsupported model IR version.*max supported IR version[:\s]+(\d+)",
    re.IGNORECASE,
)


def make_session(
    model_source: Union[str, bytes, bytearray],
    providers: List[str],
) -> onnxruntime.InferenceSession:
    """Create an onnxruntime InferenceSession, clamping IR version if needed.

    If the model's IR version is higher than what the installed onnxruntime
    supports, the model proto is loaded via the ``onnx`` package, its
    ``ir_version`` field is clamped to the limit reported in the error message,
    and the session is retried from the in-memory bytes.

    Parameters
    ----------
    model_source : str or bytes
        File path or serialised model bytes to load.
    providers : list[str]
        Execution providers passed to InferenceSession.

    Returns
    -------
    onnxruntime.InferenceSession
    """
    try:
        return onnxruntime.InferenceSession(model_source, providers=providers)
    except Exception as exc:
        # onnxruntime does not expose stable public exception sub-types, so we
        # inspect the message to distinguish an IR-version error from other
        # failures (e.g. corrupted file, missing op).
        match = _IR_VERSION_ERROR_RE.search(str(exc))
        if match is None:
            raise

        max_ir = int(match.group(1))
        logger.warning(
            f"[ONNX] Model IR version is too high for this onnxruntime build "
            f"(max supported: {max_ir}). Clamping IR version and retrying."
        )
        try:
            import onnx  # noqa: PLC0415 (deferred import keeps cv2/numpy import-free)
        except ImportError:
            raise RuntimeError(
                "The 'onnx' package is required to load models with a high IR version. "
                "Re-install dependencies: pip install -r requirements.txt"
            ) from exc

        # Load from bytes if already in-memory, otherwise from file
        if isinstance(model_source, (bytes, bytearray)):
            model_proto = onnx.load_from_string(model_source)
        else:
            model_proto = onnx.load(model_source)

        original_ir = model_proto.ir_version
        model_proto.ir_version = max_ir
        logger.info(f"[ONNX] IR version clamped {original_ir} → {max_ir}.")
        return onnxruntime.InferenceSession(
            model_proto.SerializeToString(), providers=providers
        )
