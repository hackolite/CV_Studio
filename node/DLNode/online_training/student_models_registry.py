#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Persistent registry for student ONNX models used in online training (distillation).

The registry is stored as a JSON file alongside this module.
Each entry contains everything needed to load and use the student model.

Entry schema
------------
{
    "name":          str   – display name shown in the model dropdown
    "path":          str   – absolute path to the .onnx file
    "class_names":   dict  – {str_id: str_name}  (e.g. {"0": "cat", "1": "dog"})
    "output_format": str   – "nanodet" | "yolo11" | "yolox" | "unknown"
    "input_width":   int
    "input_height":  int
    "num_classes":   int
}
"""

import json
import os
import sys


def _get_registry_path():
    """Return the registry path – writable location in frozen (onefile) mode."""
    if getattr(sys, "frozen", False):
        from src.utils.paths import get_registry_path
        return get_registry_path("student_models_registry.json")
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "student_models_registry.json"
    )


_REGISTRY_PATH = _get_registry_path()


def _load_raw() -> list:
    """Return the raw list from the JSON file (no validation)."""
    if not os.path.isfile(_REGISTRY_PATH):
        return []
    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_raw(entries: list) -> None:
    with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def load_registry() -> list:
    """Return a list of valid registry entries (path still exists)."""
    entries = _load_raw()
    valid = []
    for e in entries:
        if isinstance(e, dict) and "name" in e and "path" in e:
            if os.path.isfile(e["path"]):
                valid.append(e)
    return valid


def save_entry(entry: dict) -> None:
    """Add or update an entry (matched by name) and persist to disk."""
    entries = _load_raw()
    # Replace existing entry with same name
    updated = False
    for i, e in enumerate(entries):
        if isinstance(e, dict) and e.get("name") == entry.get("name"):
            entries[i] = entry
            updated = True
            break
    if not updated:
        entries.append(entry)
    _save_raw(entries)


def remove_entry(name: str) -> None:
    """Remove entry by name and persist."""
    entries = _load_raw()
    entries = [e for e in entries if not (isinstance(e, dict) and e.get("name") == name)]
    _save_raw(entries)


def get_entry(name: str) -> dict | None:
    """Return entry dict for given name, or None."""
    for e in _load_raw():
        if isinstance(e, dict) and e.get("name") == name:
            return e
    return None


# ---------------------------------------------------------------------------
# Catalog of pre-validated student models available for download.
#
# Populate ``download_url`` when the ONNX files are hosted (e.g. a GitHub
# Release asset).  Until then the download infrastructure is in place but
# :func:`download_model` will log a warning for models with an empty URL.
#
# Each entry follows the same schema as :func:`save_entry`; the ``path``
# key is omitted here (it is filled in after the file is downloaded).
# ---------------------------------------------------------------------------
DOWNLOADABLE_MODELS = [
    {
        "name": "yolov8n-coco",
        "description": (
            "YOLOv8 nano — 80 COCO classes, 640×640 input. "
            "Compatible with PyTorch backprop (onnx2torch ≥ 0.0.30). "
            "Export yourself: yolo export model=yolov8n.pt format=onnx opset=12"
        ),
        "output_format": "yolo11",
        "num_classes": 80,
        "input_width": 640,
        "input_height": 640,
        "download_url": "",   # set when hosted
    },
    {
        "name": "yolov8s-coco",
        "description": (
            "YOLOv8 small — 80 COCO classes, 640×640 input. "
            "Compatible with PyTorch backprop (onnx2torch ≥ 0.0.30). "
            "Export yourself: yolo export model=yolov8s.pt format=onnx opset=12"
        ),
        "output_format": "yolo11",
        "num_classes": 80,
        "input_width": 640,
        "input_height": 640,
        "download_url": "",
    },
    {
        "name": "nanodet-plus-m_416",
        "description": (
            "NanoDet-Plus-m — 80 COCO classes, 416×416 input. "
            "Compatible with PyTorch backprop (onnx2torch ≥ 0.0.30). "
            "Download from: github.com/RangiLyu/nanodet/releases"
        ),
        "output_format": "nanodet",
        "num_classes": 80,
        "input_width": 416,
        "input_height": 416,
        "download_url": "",
    },
]


def download_model(
    url: str,
    dest_path: str,
    progress_callback=None,
) -> bool:
    """Download a model ONNX file from *url* to *dest_path*.

    Parameters
    ----------
    url : str
        Direct download URL for the ``.onnx`` file.
    dest_path : str
        Local file path where the downloaded model will be saved.
    progress_callback : callable | None
        Optional ``callback(percent: float)`` invoked during download.

    Returns
    -------
    bool
        ``True`` on success, ``False`` on any error.
    """
    import urllib.request

    if not url:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "[StudentRegistry] download_model: empty URL — nothing to download."
        )
        return False

    try:
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)

        def _reporthook(block_num, block_size, total_size):
            if progress_callback is not None and total_size > 0:
                pct = min(100.0, block_num * block_size / total_size * 100)
                try:
                    progress_callback(pct)
                except Exception:
                    pass

        urllib.request.urlretrieve(url, dest_path, reporthook=_reporthook)
        if progress_callback is not None:
            try:
                progress_callback(100.0)
            except Exception:
                pass
        return True
    except Exception as exc:
        import logging as _logging
        _logging.getLogger(__name__).error(
            "[StudentRegistry] download_model failed (%s → %s): %s",
            url, dest_path, exc,
        )
        return False
