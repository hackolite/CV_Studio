#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared onnxruntime session utilities for CvStudio object detection.
"""

import logging
import re
from typing import List, Optional, Union

import onnxruntime

logger = logging.getLogger(__name__)

_TRT_BOOL_PROVIDER_OPTION_KEYS = {
    "trt_engine_cache_enable",
    "trt_context_memory_sharing_enable",
    "trt_cuda_graph_enable",
    "trt_dump_ep_context_model",
    "trt_detailed_build_log",
    "trt_engine_hw_compatible",
    "trt_fp16_enable",
    "trt_force_sequential_engine_build",
    "trt_int8_enable",
    "trt_layer_norm_fp32_fallback",
    "trt_sparsity_enable",
}

# Pattern that matches onnxruntime's IR version error, e.g.:
# "Unsupported model IR version: 14, max supported IR version: 13"
_IR_VERSION_ERROR_RE = re.compile(
    r"Unsupported model IR version.*max supported IR version[:\s]+(\d+)",
    re.IGNORECASE,
)

# Pattern that matches TensorRT engine build failures (e.g. unsupported GPU SM).
# These are fatal for TensorRT but recoverable by falling back to CUDA/CPU.
# Examples:
#   "TensorRT EP failed to create engine from network for fused node: ..."
#   "IBuilder::buildSerializedNetwork: Error Code 1: ... (Unsupported SM: 0x601)"
_TRT_FAIL_RE = re.compile(
    r"TensorRT EP failed|Unsupported SM:",
    re.IGNORECASE,
)

# Execution providers that actually offload compute to the GPU.  Used to detect
# the "user asked for GPU but silently got CPU" situation.
_GPU_PROVIDERS = ("TensorrtExecutionProvider", "CUDAExecutionProvider")


def _provider_name(provider) -> str:
    """Return the provider name from either a plain string or a (name, opts) tuple."""
    return provider if isinstance(provider, str) else provider[0]


def filter_available_providers(providers, provider_options=None):
    """Drop execution providers that this onnxruntime build cannot offer.

    OnnxRuntime silently ignores unknown/unregistered providers, so requesting
    ``CUDAExecutionProvider`` from a CPU-only ``onnxruntime`` wheel yields a
    working — but fully CPU-bound — session with no error.  That makes "GPU
    mode" look mysteriously slow.  This helper detects the situation up front
    and logs it loudly so the cause is obvious.

    Parameters
    ----------
    providers : list
        Requested providers (strings or ``(name, options)`` tuples).
    provider_options : list[dict] or None
        Per-provider option dicts aligned with *providers*.

    Returns
    -------
    tuple[list, list[dict] or None]
        The filtered providers and the matching option dicts.  When every
        requested provider is unavailable the inputs are returned unchanged so
        that onnxruntime raises its own (more precise) error.
    """
    try:
        available = set(onnxruntime.get_available_providers())
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("[OnnxSession] Could not query available providers: %s", exc)
        return list(providers), provider_options

    kept, kept_options, dropped = [], [], []
    for index, provider in enumerate(providers):
        options = provider_options[index] if provider_options is not None and index < len(provider_options) else {}
        if _provider_name(provider) in available:
            kept.append(provider)
            kept_options.append(options)
        else:
            dropped.append(_provider_name(provider))

    if not dropped:
        return list(providers), provider_options

    if not kept:
        # Nothing left to run on — let onnxruntime report the failure itself.
        return list(providers), provider_options

    if any(name in _GPU_PROVIDERS for name in dropped):
        logger.error(
            "[OnnxSession] GPU execution provider(s) %s were requested but are NOT "
            "available in this onnxruntime build (available: %s). Inference will run "
            "on %s instead, which is dramatically slower. Install the GPU runtime "
            "with: pip uninstall onnxruntime && pip install onnxruntime-gpu",
            dropped, sorted(available), [_provider_name(p) for p in kept],
        )
    else:
        logger.warning(
            "[OnnxSession] Execution provider(s) %s are not available; using %s.",
            dropped, [_provider_name(p) for p in kept],
        )

    return kept, (kept_options if provider_options is not None else None)


def _log_effective_providers(session, requested) -> None:
    """Warn when the created session did not pick up the requested GPU providers."""
    try:
        active = list(session.get_providers())
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("[OnnxSession] Could not query session providers: %s", exc)
        return

    requested_gpu = [
        _provider_name(p) for p in requested if _provider_name(p) in _GPU_PROVIDERS
    ]
    missing = [name for name in requested_gpu if name not in active]
    if missing:
        logger.error(
            "[OnnxSession] Session was created WITHOUT the requested GPU provider(s) %s "
            "— active providers: %s. Inference is running on the CPU. Check that "
            "onnxruntime-gpu is installed and that its CUDA/cuDNN versions match "
            "your driver.",
            missing, active,
        )
    else:
        logger.info("[OnnxSession] Active execution providers: %s", active)


def remove_initializers_from_inputs(model_proto) -> bool:
    """Drop initializers that are also declared as graph inputs.

    Such initializers trigger onnxruntime warnings like ``Initializer N appears
    in graph inputs and will not be treated as constant value/weight`` and can
    block graph optimizations (e.g. constant folding). This mirrors the
    ``onnxruntime/tools/python/remove_initializer_from_input.py`` tool.

    Only applied when the model IR version is >= 4: in earlier IR versions
    initializers are *required* to also be listed as graph inputs, so removing
    them would produce an invalid model.

    Parameters
    ----------
    model_proto : onnx.ModelProto
        Model to clean in place.

    Returns
    -------
    bool
        True when at least one input was removed (i.e. the proto was modified).
    """
    if model_proto.ir_version < 4:
        return False

    graph = model_proto.graph
    initializer_names = {init.name for init in graph.initializer}
    inputs_to_remove = [
        graph_input for graph_input in graph.input
        if graph_input.name in initializer_names
    ]
    for graph_input in inputs_to_remove:
        graph.input.remove(graph_input)
    return bool(inputs_to_remove)


def make_session(
    model_source: Union[str, bytes, bytearray],
    providers: List[str],
    disable_optimizations: bool = False,
    strip_initializer_inputs: bool = True,
    log_severity_level: int = 2,
    provider_options: Optional[List[dict]] = None,
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
    disable_optimizations : bool
        If True, disable all graph optimizations.  Required for QDQ models
        whose Gather nodes are broken by the optimizer.
    strip_initializer_inputs : bool
        If True (default), initializers that also appear as graph inputs are
        removed before the session is created. This silences onnxruntime's
        "Initializer ... appears in graph inputs" warnings and re-enables
        const-folding optimizations. Best-effort: any failure (e.g. ``onnx``
        not installed) leaves the original model untouched.
    log_severity_level : int
        OnnxRuntime log severity level (0=VERBOSE, 1=INFO, 2=WARNING,
        3=ERROR, 4=FATAL).  Defaults to 2 (WARNING).  Pass 3 to suppress
        expected per-frame warnings such as dynamic output shape mismatches.
    provider_options : list[dict] or None
        Per-provider option dicts, aligned with ``providers``.  When None the
        defaults are applied automatically (see below).

    Returns
    -------
    onnxruntime.InferenceSession
    """
    # Drop providers this onnxruntime build cannot offer *before* deciding on
    # session tuning: otherwise a CPU-only build silently inherits the CUDA
    # tuning below (1 thread, no CPU arena) and runs many times slower than a
    # plain CPU session.
    providers, provider_options = filter_available_providers(providers, provider_options)

    using_cuda = any(
        _provider_name(p) == "CUDAExecutionProvider" for p in providers
    )

    sess_options = onnxruntime.SessionOptions()
    sess_options.log_severity_level = log_severity_level
    if disable_optimizations:
        sess_options.graph_optimization_level = (
            onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
        )

    if using_cuda:
        # When CUDA handles inference, the ORT CPU thread-pool is used only for
        # host-side bookkeeping and any CPU-fallback operators.  Leaving it at
        # the default (all logical cores) causes 100 % CPU utilisation with near-
        # zero GPU utilisation because the OS scheduler fights over the same
        # cores that feed the GPU.  Capping to 1 thread each eliminates this.
        sess_options.intra_op_num_threads = 1
        sess_options.inter_op_num_threads = 1
        # Disable the CPU memory arena so ORT does not pre-allocate large CPU
        # buffers that are never used when running on the GPU.
        sess_options.enable_cpu_mem_arena = False
        logger.debug(
            "[OnnxSession] CUDA provider detected — "
            "CPU thread pool capped to 1 intra / 1 inter, CPU arena disabled."
        )

    # Build default CUDA provider options when none were supplied
    if provider_options is None:
        provider_options = []
        for p in providers:
            name = _provider_name(p)
            if name == "CUDAExecutionProvider":
                provider_options.append({
                    # Allocate only as much GPU memory as actually needed rather
                    # than doubling the arena on each growth event.
                    "arena_extend_strategy": "kSameAsRequested",
                })
            else:
                provider_options.append({})
    else:
        provider_options = list(provider_options)

    provider_options = _normalize_provider_options(providers, provider_options)

    if strip_initializer_inputs:
        model_source = _strip_initializer_inputs(model_source)

    try:
        session = onnxruntime.InferenceSession(
            model_source,
            sess_options=sess_options,
            providers=providers,
            provider_options=provider_options,
        )
        _log_effective_providers(session, providers)
        return session
    except Exception as exc:
        # onnxruntime does not expose stable public exception sub-types, so we
        # inspect the message to distinguish known recoverable errors from fatal
        # failures (e.g. corrupted file, missing op).
        err_str = str(exc)

        # TensorRT engine build failure (e.g. unsupported GPU SM version).
        # Drop TensorRT from the provider list and retry with the remaining
        # providers (typically CUDAExecutionProvider + CPUExecutionProvider).
        if _TRT_FAIL_RE.search(err_str):
            trt_name = "TensorrtExecutionProvider"
            fallback_providers = [
                p for p in providers
                if (p if isinstance(p, str) else p[0]) != trt_name
            ]
            if fallback_providers and len(fallback_providers) < len(providers):
                logger.warning(
                    "[ONNX] TensorRT engine build failed (%s). "
                    "Falling back to providers: %s",
                    err_str.split("\n")[0],
                    fallback_providers,
                )
                fallback_options = [
                    opt for p, opt in zip(providers, provider_options)
                    if (p if isinstance(p, str) else p[0]) != trt_name
                ]
                fallback_session = onnxruntime.InferenceSession(
                    model_source,
                    sess_options=sess_options,
                    providers=fallback_providers,
                    provider_options=fallback_options,
                )
                _log_effective_providers(fallback_session, fallback_providers)
                return fallback_session
            raise

        match = _IR_VERSION_ERROR_RE.search(err_str)
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
        clamped_session = onnxruntime.InferenceSession(
            model_proto.SerializeToString(),
            sess_options=sess_options,
            providers=providers,
            provider_options=provider_options,
        )
        _log_effective_providers(clamped_session, providers)
        return clamped_session


def _normalize_provider_options(
    providers: List[str],
    provider_options: Optional[List[dict]],
) -> List[dict]:
    """Normalize provider options for ORT execution providers."""
    normalized = list(provider_options or [])
    if len(normalized) < len(providers):
        normalized.extend({} for _ in range(len(providers) - len(normalized)))
    elif len(normalized) > len(providers):
        normalized = normalized[:len(providers)]

    for idx, provider in enumerate(providers):
        name = provider if isinstance(provider, str) else provider[0]
        options = dict(normalized[idx] or {})
        if name == "TensorrtExecutionProvider":
            for key in _TRT_BOOL_PROVIDER_OPTION_KEYS:
                if key in options:
                    options[key] = _normalize_trt_bool_option(options[key])
        normalized[idx] = options
    return normalized


def _normalize_trt_bool_option(value):
    """Return TensorRT boolean provider options in ORT's expected format."""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int) and not isinstance(value, bool):
        if value in (0, 1):
            return "True" if value else "False"
        raise ValueError(
            f"TensorRT boolean provider options must use 0 or 1, got: {value!r}"
        )
    if isinstance(value, str):
        stripped = value.strip()
        lowered = stripped.lower()
        if lowered in {"1", "true", "yes", "on"}:
            return "True"
        if lowered in {"0", "false", "no", "off"}:
            return "False"
        raise ValueError(
            "TensorRT boolean provider options must be recognizable true/false "
            f"strings, got: {value!r}"
        )
    raise ValueError(
        "TensorRT boolean provider options must be bool, int, or string values, "
        f"got: {value!r}"
    )


def _strip_initializer_inputs(
    model_source: Union[str, bytes, bytearray],
) -> Union[str, bytes, bytearray]:
    """Return a model source with initializers removed from graph inputs.

    Best-effort wrapper around :func:`remove_initializers_from_inputs`: loads the
    proto via ``onnx``, cleans it and returns the serialised bytes when anything
    changed. On any failure (``onnx`` missing, parse error, model with external
    data, …) the original ``model_source`` is returned unchanged so loading never
    breaks just because the cleanup could not run.
    """
    try:
        import onnx  # noqa: PLC0415 (deferred import keeps cv2/numpy import-free)
    except ImportError:
        return model_source

    try:
        if isinstance(model_source, (bytes, bytearray)):
            model_proto = onnx.load_from_string(bytes(model_source))
        else:
            model_proto = onnx.load(model_source)

        if remove_initializers_from_inputs(model_proto):
            logger.debug(
                "[ONNX] Removed initializers from graph inputs to silence "
                "onnxruntime warnings and re-enable const-folding."
            )
            return model_proto.SerializeToString()
    except Exception as exc:  # pragma: no cover - defensive, keep loading robust
        logger.debug(f"[ONNX] Could not strip initializer inputs: {exc}")

    return model_source
