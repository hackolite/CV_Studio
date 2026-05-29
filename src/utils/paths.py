#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Path utilities for CV_Studio – PyInstaller onefile compatibility.

In **onefile** mode, PyInstaller extracts everything to a temporary folder
(``sys._MEIPASS``).  That folder is **read-only** and deleted on exit.

For any runtime data that must persist (video recordings, user-uploaded
models, registry JSON files), we use the directory where the ``.exe``
resides (``APP_DIR``).

Layout next to the ``.exe``::

    CV_Studio.exe
    CV_Studio_data/
    ├── _VideoWriter/        ← video recordings
    ├── models/              ← user-uploaded ONNX models (all node types)
    │   ├── object_detection/
    │   ├── classification/
    │   ├── face_detection/
    │   ├── pose_estimation/
    │   ├── semantic_segmentation/
    │   ├── monocular_depth_estimation/
    │   └── audio/
    └── registries/          ← persistent JSON registries
        ├── od_custom_models_registry.json
        ├── cls_custom_models_registry.json
        ├── fd_custom_models_registry.json
        ├── pose_custom_models_registry.json
        ├── seg_custom_models_registry.json
        ├── depth_custom_models_registry.json
        └── audio_models_registry.json

In **development** (non-frozen) mode, ``get_app_dir()`` simply returns the
repository root so existing relative paths keep working unchanged.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_DATA_FOLDER_NAME = "CV_Studio_data"


def is_frozen() -> bool:
    """Return True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_exe_dir() -> str:
    """Return the directory containing the running .exe (or script)."""
    if is_frozen():
        # sys.executable is the .exe itself
        return os.path.dirname(os.path.abspath(sys.executable))
    # Dev mode: repository root (where main.py lives)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_app_dir() -> str:
    """
    Return the persistent, writable data directory for CV_Studio.

    - Frozen (onefile): ``<exe_dir>/CV_Studio_data/``
    - Dev mode: repository root (unchanged behaviour)
    """
    if is_frozen():
        app_dir = os.path.join(get_exe_dir(), _DATA_FOLDER_NAME)
        os.makedirs(app_dir, exist_ok=True)
        return app_dir
    return get_exe_dir()


def get_bundle_dir() -> str:
    """
    Return the read-only bundle directory (where PyInstaller extracts files).

    In dev mode this is just the repository root.
    """
    if is_frozen():
        return sys._MEIPASS  # type: ignore[attr-defined]
    return get_exe_dir()


def get_videowriter_dir() -> str:
    """Return the default VideoWriter output directory."""
    return os.path.join(get_app_dir(), "_VideoWriter")


def get_models_dir(node_type: str) -> str:
    """
    Return the writable models directory for a given node type.

    Args:
        node_type: One of 'object_detection', 'classification',
                   'face_detection', 'pose_estimation',
                   'semantic_segmentation', 'monocular_depth_estimation',
                   'audio'.
    """
    d = os.path.join(get_app_dir(), "models", node_type)
    os.makedirs(d, exist_ok=True)
    return d


def get_registry_path(filename: str) -> str:
    """
    Return the path to a writable registry JSON file.

    Args:
        filename: e.g. 'od_custom_models_registry.json'
    """
    d = os.path.join(get_app_dir(), "registries")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, filename)
