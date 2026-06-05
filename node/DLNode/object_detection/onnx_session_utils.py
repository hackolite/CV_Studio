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

    Returns
    -------
    onnxruntime.InferenceSession
    """
    sess_options = None
    if disable_optimizations:
        sess_options = onnxruntime.SessionOptions()
        sess_options.graph_optimization_level = (
            onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL
        )

    if strip_initializer_inputs:
        model_source = _strip_initializer_inputs(model_source)

    try:
        return onnxruntime.InferenceSession(
            model_source, sess_options=sess_options, providers=providers
        )
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
            model_proto.SerializeToString(),
            sess_options=sess_options,
            providers=providers,
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
