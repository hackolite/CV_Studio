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
