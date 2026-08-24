#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for node.DLNode.object_detection.onnx_session_utils.

Focus on the initializer-in-graph-inputs cleanup that silences onnxruntime's
"Initializer ... appears in graph inputs" warnings.
"""

import pytest

onnx = pytest.importorskip("onnx")
onnxruntime = pytest.importorskip("onnxruntime")
from onnx import TensorProto, helper, numpy_helper  # noqa: E402
import numpy as np  # noqa: E402

from node.DLNode.object_detection.onnx_session_utils import (  # noqa: E402
    _normalize_provider_options,
    filter_available_providers,
    make_session,
    remove_initializers_from_inputs,
)


def _pretend_gpu_providers_available(monkeypatch):
    """Make TensorRT/CUDA look available so provider-specific paths can be tested.

    ``make_session`` now drops execution providers that the installed
    onnxruntime build does not offer, so tests that exercise TensorRT/CUDA
    behaviour must advertise those providers explicitly.
    """
    monkeypatch.setattr(
        onnxruntime,
        "get_available_providers",
        lambda: [
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ],
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
    _pretend_gpu_providers_available(monkeypatch)
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


@pytest.mark.parametrize("invalid_value", [None, "maybe", 2])
def test_normalize_provider_options_rejects_invalid_trt_bool_values(invalid_value):
    with pytest.raises(ValueError):
        _normalize_provider_options(
            ["TensorrtExecutionProvider"],
            [{"trt_engine_cache_enable": invalid_value}],
        )


# ---------------------------------------------------------------------------
# TensorRT fallback tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("trt_error_msg", [
    "TensorRT EP failed to create engine from network for fused node: TensorrtExecutionProvider_TRTKernel_graph_main_0",
    "TensorRT EP failed to build engine",
    "Unsupported SM: 0x601",
])
def test_make_session_falls_back_when_trt_fails(monkeypatch, trt_error_msg):
    _pretend_gpu_providers_available(monkeypatch)
    """When TensorRT raises an engine-build error, make_session retries without it."""
    call_log = []

    def fake_inference_session(*args, **kwargs):
        providers = kwargs.get("providers", [])
        call_log.append(list(providers))
        if "TensorrtExecutionProvider" in providers:
            raise RuntimeError(trt_error_msg)
        return object()

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    session = make_session(
        b"not-a-real-model",
        providers=["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        strip_initializer_inputs=False,
    )

    assert session is not None
    # First call with TRT, second without
    assert call_log[0] == ["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"]
    assert "TensorrtExecutionProvider" not in call_log[1]


def test_make_session_trt_fallback_preserves_provider_options(monkeypatch):
    """Provider options for surviving providers are preserved on TRT fallback."""
    _pretend_gpu_providers_available(monkeypatch)
    captured = {}

    def fake_inference_session(*args, **kwargs):
        providers = kwargs.get("providers", [])
        if "TensorrtExecutionProvider" in providers:
            raise RuntimeError("TensorRT EP failed to create engine from network")
        captured["providers"] = list(providers)
        captured["provider_options"] = list(kwargs.get("provider_options", []))
        return object()

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    make_session(
        b"not-a-real-model",
        providers=["TensorrtExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"],
        provider_options=[
            {"trt_fp16_enable": "True"},
            {"arena_extend_strategy": "kSameAsRequested"},
            {},
        ],
        strip_initializer_inputs=False,
    )

    assert captured["providers"] == ["CUDAExecutionProvider", "CPUExecutionProvider"]
    assert captured["provider_options"] == [
        {"arena_extend_strategy": "kSameAsRequested"},
        {},
    ]


def test_make_session_reraises_when_trt_is_only_provider(monkeypatch):
    """When TRT is the only provider and it fails, the error is re-raised."""
    def fake_inference_session(*args, **kwargs):
        raise RuntimeError("TensorRT EP failed to create engine from network")

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    with pytest.raises(RuntimeError, match="TensorRT EP failed"):
        make_session(
            b"not-a-real-model",
            providers=["TensorrtExecutionProvider"],
            strip_initializer_inputs=False,
        )


def test_make_session_reraises_non_trt_errors(monkeypatch):
    """Non-TRT errors are not caught by the TRT fallback path."""
    def fake_inference_session(*args, **kwargs):
        raise RuntimeError("Model file not found")

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    with pytest.raises(RuntimeError, match="Model file not found"):
        make_session(
            b"not-a-real-model",
            providers=["TensorrtExecutionProvider", "CPUExecutionProvider"],
            strip_initializer_inputs=False,
        )


# ---------------------------------------------------------------------------
# Unavailable-provider filtering
# ---------------------------------------------------------------------------

def test_filter_available_providers_drops_unavailable(monkeypatch):
    """Providers missing from the ORT build are dropped, keeping options aligned."""
    monkeypatch.setattr(
        onnxruntime, "get_available_providers", lambda: ["CPUExecutionProvider"]
    )

    providers, options = filter_available_providers(
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
        [{"arena_extend_strategy": "kSameAsRequested"}, {"cpu": "opt"}],
    )

    assert providers == ["CPUExecutionProvider"]
    assert options == [{"cpu": "opt"}]


def test_filter_available_providers_keeps_all_when_available(monkeypatch):
    _pretend_gpu_providers_available(monkeypatch)

    providers, options = filter_available_providers(
        ["CUDAExecutionProvider", "CPUExecutionProvider"], None
    )

    assert providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]
    assert options is None


def test_filter_available_providers_keeps_input_when_none_available(monkeypatch):
    """With nothing available, the request is passed through so ORT reports it."""
    monkeypatch.setattr(onnxruntime, "get_available_providers", lambda: [])

    providers, options = filter_available_providers(["CUDAExecutionProvider"], None)

    assert providers == ["CUDAExecutionProvider"]
    assert options is None


def test_make_session_does_not_apply_cuda_tuning_on_cpu_fallback(monkeypatch):
    """A CPU-only build must not inherit the single-threaded CUDA session tuning."""
    monkeypatch.setattr(
        onnxruntime, "get_available_providers", lambda: ["CPUExecutionProvider"]
    )
    captured = {}

    def fake_inference_session(*args, **kwargs):
        captured["providers"] = list(kwargs.get("providers", []))
        captured["sess_options"] = kwargs["sess_options"]
        return object()

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    make_session(
        b"not-a-real-model",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        strip_initializer_inputs=False,
    )

    assert captured["providers"] == ["CPUExecutionProvider"]
    # Default ORT thread-pool settings (0 = "let ORT decide"), not the 1/1 cap.
    assert captured["sess_options"].intra_op_num_threads != 1
    assert captured["sess_options"].enable_cpu_mem_arena is True


def test_make_session_cuda_defaults_do_not_disable_cudnn_workspace(monkeypatch):
    """cudnn_conv_use_max_workspace must not be forced to '0' (kills conv perf)."""
    _pretend_gpu_providers_available(monkeypatch)
    captured = {}

    def fake_inference_session(*args, **kwargs):
        captured["provider_options"] = list(kwargs.get("provider_options", []))
        return object()

    monkeypatch.setattr(onnxruntime, "InferenceSession", fake_inference_session)

    make_session(
        b"not-a-real-model",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        strip_initializer_inputs=False,
    )

    assert "cudnn_conv_use_max_workspace" not in captured["provider_options"][0]
