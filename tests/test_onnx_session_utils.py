#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for node.DLNode.object_detection.onnx_session_utils.

Focus on the initializer-in-graph-inputs cleanup that silences onnxruntime's
"Initializer ... appears in graph inputs" warnings.
"""

import pytest

onnx = pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
from onnx import TensorProto, helper, numpy_helper  # noqa: E402
import numpy as np  # noqa: E402

from node.DLNode.object_detection.onnx_session_utils import (  # noqa: E402
    make_session,
    remove_initializers_from_inputs,
)


def _model_with_initializer_in_inputs(ir_version=7):
    """Build an Add(x, w) model where the weight ``w`` is both an initializer
    and a declared graph input (the pattern that triggers the ORT warning)."""
    w = numpy_helper.from_array(np.ones((2, 2), dtype=np.float32), name="w")
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, [2, 2])
    w_in = helper.make_tensor_value_info("w", TensorProto.FLOAT, [2, 2])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, [2, 2])
    node = helper.make_node("Add", ["x", "w"], ["y"])
    graph = helper.make_graph([node], "g", [x, w_in], [y], initializer=[w])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = ir_version
    return model


def test_remove_initializers_from_inputs_strips_input():
    model = _model_with_initializer_in_inputs()
    assert {i.name for i in model.graph.input} == {"x", "w"}

    changed = remove_initializers_from_inputs(model)

    assert changed is True
    assert {i.name for i in model.graph.input} == {"x"}
    # Initializer itself is preserved as a weight.
    assert {i.name for i in model.graph.initializer} == {"w"}


def test_remove_initializers_noop_when_clean():
    model = _model_with_initializer_in_inputs()
    remove_initializers_from_inputs(model)
    # Second pass has nothing left to remove.
    assert remove_initializers_from_inputs(model) is False


def test_remove_initializers_skips_old_ir_version():
    model = _model_with_initializer_in_inputs(ir_version=3)
    # IR < 4 requires initializers to be listed as inputs; leave them.
    assert remove_initializers_from_inputs(model) is False
    assert {i.name for i in model.graph.input} == {"x", "w"}


def test_make_session_strips_initializer_inputs():
    model = _model_with_initializer_in_inputs()
    session = make_session(
        model.SerializeToString(), providers=["CPUExecutionProvider"]
    )
    # The redundant 'w' input is gone; only the real runtime input remains.
    assert [i.name for i in session.get_inputs()] == ["x"]

    out = session.run(
        None, {"x": np.zeros((2, 2), dtype=np.float32)}
    )[0]
    assert np.allclose(out, np.ones((2, 2), dtype=np.float32))


def test_strip_initializer_inputs_roundtrip():
    from node.DLNode.object_detection.onnx_session_utils import (
        _strip_initializer_inputs,
    )

    model = _model_with_initializer_in_inputs()
    cleaned = _strip_initializer_inputs(model.SerializeToString())
    cleaned_proto = onnx.load_from_string(cleaned)
    assert {i.name for i in cleaned_proto.graph.input} == {"x"}
    assert {i.name for i in cleaned_proto.graph.initializer} == {"w"}


def test_make_session_without_stripping_still_loads():
    model = _model_with_initializer_in_inputs()
    session = make_session(
        model.SerializeToString(),
        providers=["CPUExecutionProvider"],
        strip_initializer_inputs=False,
    )
    out = session.run(None, {"x": np.zeros((2, 2), dtype=np.float32)})[0]
    assert np.allclose(out, np.ones((2, 2), dtype=np.float32))
