#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Persistent registry for user-uploaded custom ONNX models (pose_estimation)."""

import json
import os
import sys

def _get_registry_path():
    """Return the registry path – writable location in frozen (onefile) mode."""
    if getattr(sys, "frozen", False):
        from src.utils.paths import get_registry_path
        return get_registry_path("pose_custom_models_registry.json")
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "custom_models_registry.json"
    )

_REGISTRY_PATH = _get_registry_path()


def _load_raw() -> list:
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
    entries = _load_raw()
    valid = []
    for e in entries:
        if isinstance(e, dict) and "name" in e and "path" in e:
            if os.path.isfile(e["path"]):
                valid.append(e)
    return valid


def save_entry(entry: dict) -> None:
    entries = _load_raw()
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
    entries = _load_raw()
    entries = [e for e in entries if not (isinstance(e, dict) and e.get("name") == name)]
    _save_raw(entries)
