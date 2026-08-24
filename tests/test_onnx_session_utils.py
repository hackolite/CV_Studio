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
    _normalize_provider_options,
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

    outputs = session.run(None, {"x": np.zeros((2, 2), dtype=np.float32)})
    result = outputs[0]  # single 'y' output tensor
    assert np.allclose(result, np.ones((2, 2), dtype=np.float32))


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


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1", "True"),
        ("0", "False"),
        (True, "True"),
        (False, "False"),
        ("true", "True"),
        ("False", "False"),
    ],
)
def test_normalize_provider_options_trt_bool_values(raw_value, expected):
    normalized = _normalize_provider_options(
        ["TensorrtExecutionProvider", "CUDAExecutionProvider"],
        [
            {"trt_engine_cache_enable": raw_value, "trt_fp16_enable": raw_value},
            {"arena_extend_strategy": "kSameAsRequested"},
        ],
    )

    assert normalized[0]["trt_engine_cache_enable"] == expected
    assert normalized[0]["trt_fp16_enable"] == expected
    assert normalized[1] == {"arena_extend_strategy": "kSameAsRequested"}


def test_make_session_normalizes_trt_provider_options(monkeypatch):
    captured = {}

    def fake_inference_session(*args, **kwargs):
        captured["provider_options"] = kwargs["provider_options"]
        return object()

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    session = make_session(
        b"not-a-real-model",
        providers=["TensorrtExecutionProvider", "CPUExecutionProvider"],
        provider_options=[{"trt_engine_cache_enable": "1"}, {}],
        strip_initializer_inputs=False,
    )

    assert session is not None
    assert captured["provider_options"] == [
        {"trt_engine_cache_enable": "True"},
        {},
    ]


def test_normalize_provider_options_pads_missing_entries():
    normalized = _normalize_provider_options(
        ["TensorrtExecutionProvider", "CPUExecutionProvider"],
        [{"trt_engine_cache_enable": "1"}],
    )

    assert normalized == [
        {"trt_engine_cache_enable": "True"},
        {},
    ]


def test_normalize_provider_options_truncates_extra_entries():
    normalized = _normalize_provider_options(
        ["CPUExecutionProvider"],
        [{"unused": "keep"}, {"extra": "drop"}],
    )

    assert normalized == [{"unused": "keep"}]


def test_normalize_provider_options_rejects_invalid_trt_bool_values():
    with pytest.raises(ValueError):
        _normalize_provider_options(
            ["TensorrtExecutionProvider"],
            [{"trt_engine_cache_enable": None}],
        )

    with pytest.raises(ValueError):
        _normalize_provider_options(
            ["TensorrtExecutionProvider"],
            [{"trt_engine_cache_enable": "maybe"}],
        )

    with pytest.raises(ValueError):
        _normalize_provider_options(
            ["TensorrtExecutionProvider"],
            [{"trt_engine_cache_enable": 2}],
        )
