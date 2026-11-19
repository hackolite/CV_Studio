#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Make a YOLOX ONNX model run at another input size.

A YOLOX network is fully convolutional: the same weights work at any input
size that is a multiple of 32, only the amount of computation changes (it is
proportional to the number of pixels).  The exported file is however tied to
one size.  ``resize_yolox`` rewrites the size of the graph and nothing else.

This is how the small students shipped with the distillation node are made
(see docs/DISTILLATION_YOLOX.md): a network run on fewer pixels is faster but
sees less detail, and distillation teaches it to make the best of the pixels
it has on the scene it watches.

    python -m node.DLNode.online_training.distill.resize \
        --model node/DLNode/object_detection/YOLOX/model/yolox_nano.onnx \
        --size 320
"""
import argparse
import os

import onnx

from node.DLNode.online_training.distill import yolox_ops


def input_size(path):
    """``(height, width)`` of the input of an ONNX file, ``None`` if not fixed."""
    model = onnx.load(path, load_external_data=False)
    dims = [d.dim_value for d in model.graph.input[0].type.tensor_type.shape.dim]
    if len(dims) != 4 or not dims[2] or not dims[3]:
        return None
    return int(dims[2]), int(dims[3])


def resize_yolox(model, height, width):
    """Copy of a YOLOX model (path or ``ModelProto``) for another input size.

    The model must be a raw YOLOX export (``decode_in_inference=False``).  The
    weights are untouched.  Raises ``ValueError`` when the graph cannot run at
    the requested size.
    """
    yolox_ops.check_input_size(height, width)
    if isinstance(model, (str, os.PathLike)):
        model = onnx.load(model)
    else:
        copy = onnx.ModelProto()
        copy.CopyFrom(model)
        model = copy
    graph = model.graph

    in_dims = graph.input[0].type.tensor_type.shape.dim
    out_dims = graph.output[0].type.tensor_type.shape.dim
    if len(in_dims) != 4 or len(out_dims) != 3 or not out_dims[2].dim_value:
        raise ValueError("not a raw YOLOX model: [1, 3, H, W] -> [1, anchors, 5 + classes] expected")
    channels = out_dims[2].dim_value

    in_dims[2].dim_value, in_dims[3].dim_value = int(height), int(width)
    anchors = len(yolox_ops.make_grid(height, width)[1])
    out_dims[1].dim_value = anchors
    # Forget every shape computed for the previous size, and compute them
    # again: the inference fails if the graph does not produce ``anchors``.
    del graph.value_info[:]
    try:
        model = onnx.shape_inference.infer_shapes(model, strict_mode=True)
    except Exception as exc:
        raise ValueError(f"the model cannot run at {width}x{height}: {exc}") from exc

    shape = [d.dim_value for d in model.graph.output[0].type.tensor_type.shape.dim]
    if shape != [1, anchors, channels]:
        raise ValueError(
            f"the model cannot run at {width}x{height}: "
            f"output {shape}, expected {[1, anchors, channels]}"
        )
    onnx.checker.check_model(model)
    return model


def parse_size(text):
    """``'320'`` -> ``(320, 320)``; ``'416x256'`` (width x height) -> ``(256, 416)``."""
    parts = [int(part) for part in str(text).lower().split("x")]
    if len(parts) == 1:
        return parts[0], parts[0]
    if len(parts) == 2:
        return parts[1], parts[0]
    raise ValueError(f"size must be N or WIDTHxHEIGHT, got {text!r}")


def default_name(path, height, width):
    stem = os.path.splitext(os.path.basename(path))[0]
    size = str(width) if height == width else f"{width}x{height}"
    return os.path.join(os.path.dirname(path), f"{stem}_{size}.onnx")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--model", required=True, help="YOLOX ONNX file")
    parser.add_argument("--size", required=True,
                        help="new input size: N (square) or WIDTHxHEIGHT, multiples of 32")
    parser.add_argument("--output", help="default: <model>_<size>.onnx next to the model")
    args = parser.parse_args(argv)

    height, width = parse_size(args.size)
    output = args.output or default_name(args.model, height, width)
    onnx.save(resize_yolox(args.model, height, width), output)
    print(f"{output}: input {width}x{height}")


if __name__ == "__main__":
    main()
