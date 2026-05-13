#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ONNX model inspector for CvStudio.

Extracts metadata from an ONNX file:
  - input/output names and shapes
  - auto-detection of output format (YOLO11-style vs YOLOX-style)
  - class names embedded in Ultralytics ONNX metadata
"""

import ast
import json
import logging
import os

import onnxruntime

logger = logging.getLogger(__name__)


def inspect_onnx_model(model_path: str) -> dict:
    """Inspect an ONNX model and return a metadata dictionary.

    Parameters
    ----------
    model_path : str
        Absolute path to the .onnx file.

    Returns
    -------
    dict with keys:
        input_name       (str)   – name of the first input tensor
        input_shape      (list)  – shape of the first input tensor, e.g. [1, 3, 640, 640]
        output_name      (str)   – name of the first output tensor
        output_shape     (list)  – shape of the first output tensor
        output_format    (str)   – 'yolo11' | 'yolox' | 'unknown'
        num_classes      (int)   – detected number of classes (0 if unknown)
        class_names      (dict)  – {int_id: str_name} extracted from ONNX metadata,
                                   empty dict if not available
        input_width      (int)   – inferred from shape[3] if available, else 640
        input_height     (int)   – inferred from shape[2] if available, else 640
    """
    if not os.path.isfile(model_path):
        raise FileNotFoundError(f"ONNX model not found: {model_path}")

    logger.info(f"[ONNX Inspector] Loading model: {model_path}")

    session = onnxruntime.InferenceSession(
        model_path, providers=["CPUExecutionProvider"]
    )

    # ---- Input info --------------------------------------------------------
    input_detail = session.get_inputs()[0]
    input_name = input_detail.name
    input_shape = list(input_detail.shape)
    logger.info(f"[ONNX Inspector] Input tensor: name='{input_name}', shape={input_shape}")

    input_height = 640
    input_width = 640
    if len(input_shape) == 4:
        if isinstance(input_shape[2], int) and input_shape[2] > 0:
            input_height = input_shape[2]
        else:
            logger.warning(
                f"[ONNX Inspector] Height dimension is dynamic or invalid "
                f"('{input_shape[2]}'); defaulting to {input_height}."
            )
        if isinstance(input_shape[3], int) and input_shape[3] > 0:
            input_width = input_shape[3]
        else:
            logger.warning(
                f"[ONNX Inspector] Width dimension is dynamic or invalid "
                f"('{input_shape[3]}'); defaulting to {input_width}."
            )
    else:
        logger.warning(
            f"[ONNX Inspector] Unexpected input rank {len(input_shape)} "
            f"(expected 4 for BCHW); defaulting to {input_height}x{input_width}."
        )
    logger.info(f"[ONNX Inspector] Effective input size: {input_width}x{input_height} (WxH)")

    # ---- Output info -------------------------------------------------------
    output_detail = session.get_outputs()[0]
    output_name = output_detail.name
    output_shape = list(output_detail.shape)
    logger.info(f"[ONNX Inspector] Output tensor: name='{output_name}', shape={output_shape}")

    # ---- Format detection --------------------------------------------------
    # YOLO11 / YOLOv8 Ultralytics:  output shape [1, num_classes+4, num_anchors]
    # YOLOX:                         output shape [1, num_anchors, num_classes+5]
    output_format = "unknown"
    num_classes = 0

    if len(output_shape) == 3:
        dim1 = output_shape[1]  # middle dimension
        dim2 = output_shape[2]  # last dimension
        if isinstance(dim1, int) and isinstance(dim2, int):
            # YOLO11: dim1 = num_classes+4, dim2 >> dim1 (many anchors)
            # YOLOX:  dim2 = num_classes+5, dim1 >> dim2 (many anchors)
            if dim1 < dim2 and dim1 > 4:
                # Likely YOLO11 style: [1, C+4, anchors]
                output_format = "yolo11"
                num_classes = dim1 - 4
            elif dim2 < dim1 and dim2 > 5:
                # Likely YOLOX style: [1, anchors, C+5]
                output_format = "yolox"
                num_classes = dim2 - 5
            elif dim1 < dim2 and dim1 == 4:
                # Edge case: exactly 4 dims on axis1 → treat as yolo11 with 0 classes
                output_format = "yolo11"
                num_classes = 0
            else:
                logger.warning(
                    f"[ONNX Inspector] Cannot determine output format from shape "
                    f"{output_shape} (dim1={dim1}, dim2={dim2}). "
                    f"Will default to 'yolo11' at inference time."
                )
        else:
            logger.warning(
                f"[ONNX Inspector] Output shape has dynamic dimensions "
                f"{output_shape}; format detection skipped."
            )
    else:
        logger.warning(
            f"[ONNX Inspector] Unexpected output rank {len(output_shape)} "
            f"(expected 3); format detection skipped."
        )

    if output_format != "unknown":
        logger.info(
            f"[ONNX Inspector] Detected output format: '{output_format}', "
            f"estimated num_classes={num_classes}"
        )

    # ---- Embedded class names (Ultralytics) --------------------------------
    class_names: dict = {}
    try:
        model_meta = session.get_modelmeta()
        custom_meta = model_meta.custom_metadata_map  # dict[str, str]
        if "names" in custom_meta:
            raw = custom_meta["names"]
            # Ultralytics stores as Python dict literal: {0: 'cat', 1: 'dog', ...}
            try:
                parsed = ast.literal_eval(raw)
                if isinstance(parsed, dict):
                    class_names = {int(k): str(v) for k, v in parsed.items()}
                    if num_classes == 0:
                        num_classes = len(class_names)
                    logger.info(
                        f"[ONNX Inspector] Found {len(class_names)} class names "
                        f"in ONNX 'names' metadata."
                    )
            except Exception as exc:
                logger.warning(
                    f"[ONNX Inspector] Failed to parse 'names' metadata: {exc}"
                )
        if not class_names and "labels" in custom_meta:
            raw = custom_meta["labels"]
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    class_names = {int(k): str(v) for k, v in parsed.items()}
                elif isinstance(parsed, list):
                    class_names = {i: str(v) for i, v in enumerate(parsed)}
                if num_classes == 0:
                    num_classes = len(class_names)
                logger.info(
                    f"[ONNX Inspector] Found {len(class_names)} class names "
                    f"in ONNX 'labels' metadata."
                )
            except Exception as exc:
                logger.warning(
                    f"[ONNX Inspector] Failed to parse 'labels' metadata: {exc}"
                )
        if not class_names:
            logger.info(
                "[ONNX Inspector] No embedded class names found in ONNX metadata."
            )
    except Exception as exc:
        logger.warning(f"[ONNX Inspector] Could not read model metadata: {exc}")

    result = {
        "input_name": input_name,
        "input_shape": input_shape,
        "output_name": output_name,
        "output_shape": output_shape,
        "output_format": output_format,
        "num_classes": num_classes,
        "class_names": class_names,
        "input_width": input_width,
        "input_height": input_height,
    }
    logger.info(
        f"[ONNX Inspector] Inspection complete — "
        f"format='{output_format}', classes={num_classes}, "
        f"input={input_width}x{input_height}"
    )
    return result


def load_class_names_from_file(filepath: str) -> dict:
    """Load class names from a .txt or .json file.

    .txt  – one class name per line, index is line number starting at 0
    .json – either {"0": "cat", "1": "dog"} or ["cat", "dog"]

    Returns a dict {int_id: str_name} or empty dict on failure.
    """
    if not filepath or not os.path.isfile(filepath):
        logger.warning(f"[ONNX Inspector] Class names file not found: '{filepath}'")
        return {}

    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f.readlines()]
            result = {i: name for i, name in enumerate(lines) if name}
            logger.info(f"[ONNX Inspector] Loaded {len(result)} class names from TXT: {filepath}")
            return result
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                result = {int(k): str(v) for k, v in data.items()}
            elif isinstance(data, list):
                result = {i: str(v) for i, v in enumerate(data)}
            else:
                logger.warning(f"[ONNX Inspector] Unexpected JSON format in {filepath}")
                return {}
            logger.info(f"[ONNX Inspector] Loaded {len(result)} class names from JSON: {filepath}")
            return result
        else:
            logger.warning(f"[ONNX Inspector] Unsupported class names file extension: '{ext}'")
    except Exception as exc:
        logger.warning(f"[ONNX Inspector] Failed to load class names from '{filepath}': {exc}")
    return {}
