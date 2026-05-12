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
import os

import onnxruntime


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

    session = onnxruntime.InferenceSession(
        model_path, providers=["CPUExecutionProvider"]
    )

    # ---- Input info --------------------------------------------------------
    input_detail = session.get_inputs()[0]
    input_name = input_detail.name
    input_shape = list(input_detail.shape)

    input_height = 640
    input_width = 640
    if len(input_shape) == 4:
        if isinstance(input_shape[2], int) and input_shape[2] > 0:
            input_height = input_shape[2]
        if isinstance(input_shape[3], int) and input_shape[3] > 0:
            input_width = input_shape[3]

    # ---- Output info -------------------------------------------------------
    output_detail = session.get_outputs()[0]
    output_name = output_detail.name
    output_shape = list(output_detail.shape)

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
            except Exception:
                pass
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
            except Exception:
                pass
    except Exception:
        pass

    return {
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


def load_class_names_from_file(filepath: str) -> dict:
    """Load class names from a .txt or .json file.

    .txt  – one class name per line, index is line number starting at 0
    .json – either {"0": "cat", "1": "dog"} or ["cat", "dog"]

    Returns a dict {int_id: str_name} or empty dict on failure.
    """
    if not filepath or not os.path.isfile(filepath):
        return {}

    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f.readlines()]
            return {i: name for i, name in enumerate(lines) if name}
        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {int(k): str(v) for k, v in data.items()}
            elif isinstance(data, list):
                return {i: str(v) for i, v in enumerate(data)}
    except Exception:
        pass
    return {}
