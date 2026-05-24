#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
set_onnx_audio_metadata.py
==========================
Inject class labels into the ONNX metadata of an audio classification model
so that CvStudio's AudioClassification node can read them automatically.

The node (node/AudioModelNode/node_audio_classification.py) looks for one of
three metadata keys (in order of preference): "names", "labels", "classes".
This script writes the selected key as a Python dict literal, which is the
format used by Ultralytics models and understood by CvStudio.

Supported label sources
-----------------------
  --labels esc50          Built-in ESC-50 dataset (50 classes)
  --labels yamnet         Built-in YAMNet/AudioSet ontology (521 classes)
  --labels path/to/file   Custom .txt (one label per line) or
                          .json ({int: str} or [str, ...])
  --labels "dog,cat,bird" Inline comma-separated list

Usage examples
--------------
  # Preview only (no file written)
  python tools/set_onnx_audio_metadata.py my_model.onnx --labels esc50 --dry-run

  # Write ESC-50 labels to the "names" key (default)
  python tools/set_onnx_audio_metadata.py my_model.onnx --labels esc50

  # Write custom labels from a JSON file to the "labels" key
  python tools/set_onnx_audio_metadata.py my_model.onnx \\
      --labels my_classes.json --key labels

  # Overwrite without confirmation prompt
  python tools/set_onnx_audio_metadata.py my_model.onnx --labels esc50 --force

  # Write to a separate output file (keeps original intact)
  python tools/set_onnx_audio_metadata.py my_model.onnx \\
      --labels esc50 --out my_model_with_meta.onnx
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys

# ---------------------------------------------------------------------------
# Optional dependency check
# ---------------------------------------------------------------------------
try:
    import onnx
except ImportError:
    sys.exit(
        "ERROR: 'onnx' package is required.\n"
        "Install it with:  pip install onnx"
    )

# ---------------------------------------------------------------------------
# Built-in label sets
# ---------------------------------------------------------------------------

def _load_esc50() -> dict[int, str]:
    """Return the ESC-50 class name dict {0: 'Dog', 1: 'Rooster', ...}."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_here)
    sys.path.insert(0, _repo_root)
    try:
        from node.DLNode.classification.esc50_class_names import esc50_class_names
        return dict(esc50_class_names)
    except Exception:
        pass
    # Fallback: hardcoded copy (always available)
    return {
        0: "Dog", 1: "Rooster", 2: "Pig", 3: "Cow", 4: "Frog",
        5: "Cat", 6: "Hen", 7: "Insects (flying)", 8: "Sheep", 9: "Crow",
        10: "Rain", 11: "Sea waves", 12: "Crackling fire", 13: "Crickets",
        14: "Chirping birds", 15: "Water drops", 16: "Wind",
        17: "Pouring water", 18: "Toilet flush", 19: "Thunderstorm",
        20: "Crying baby", 21: "Sneezing", 22: "Clapping", 23: "Breathing",
        24: "Coughing", 25: "Footsteps", 26: "Laughing",
        27: "Brushing teeth", 28: "Snoring", 29: "Drinking (sipping)",
        30: "Door knock", 31: "Mouse click", 32: "Keyboard typing",
        33: "Door, wood creaks", 34: "Can opening", 35: "Washing machine",
        36: "Vacuum cleaner", 37: "Clock alarm", 38: "Clock tick",
        39: "Glass breaking", 40: "Helicopter", 41: "Chainsaw",
        42: "Siren", 43: "Car horn", 44: "Engine", 45: "Train",
        46: "Church bells", 47: "Airplane", 48: "Fireworks", 49: "Hand saw",
    }


def _load_yamnet() -> dict[int, str]:
    """Return the YAMNet/AudioSet class name dict (521 classes)."""
    _here = os.path.dirname(os.path.abspath(__file__))
    _repo_root = os.path.dirname(_here)
    sys.path.insert(0, _repo_root)
    try:
        from node.DLNode.classification.yamnet_class_names import yamnet_class_names
        return dict(yamnet_class_names)
    except Exception:
        sys.exit(
            "ERROR: Could not import YAMNet class names.\n"
            "Run this script from the CV_Studio repository root."
        )


# ---------------------------------------------------------------------------
# Label loading helpers
# ---------------------------------------------------------------------------

def _load_from_txt(path: str) -> dict[int, str]:
    """Load one label per line from a .txt file."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f.readlines()]
    return {i: name for i, name in enumerate(lines) if name.strip()}


def _load_from_json(path: str) -> dict[int, str]:
    """Load labels from a JSON file ({int/str: str} or [str, ...])."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return {int(k): str(v) for k, v in data.items()}
    if isinstance(data, list):
        return {i: str(v) for i, v in enumerate(data)}
    raise ValueError(f"Unsupported JSON structure in '{path}'. Expected dict or list.")


def _load_from_inline(value: str) -> dict[int, str]:
    """Parse a comma-separated inline label string like 'dog,cat,bird'."""
    items = [s.strip() for s in value.split(",") if s.strip()]
    if not items:
        raise ValueError("Empty inline label list.")
    return {i: name for i, name in enumerate(items)}


def load_labels(labels_arg: str) -> dict[int, str]:
    """Resolve the --labels argument to a {int: str} dict."""
    lower = labels_arg.strip().lower()

    if lower == "esc50":
        return _load_esc50()

    if lower == "yamnet":
        return _load_yamnet()

    if os.path.isfile(labels_arg):
        ext = os.path.splitext(labels_arg)[1].lower()
        if ext == ".txt":
            return _load_from_txt(labels_arg)
        if ext == ".json":
            return _load_from_json(labels_arg)
        raise ValueError(
            f"Unsupported file extension '{ext}'. Use .txt or .json."
        )

    # Treat as inline comma-separated string
    return _load_from_inline(labels_arg)


# ---------------------------------------------------------------------------
# ONNX metadata helpers
# ---------------------------------------------------------------------------

def read_existing_metadata(model: onnx.ModelProto) -> dict[str, str]:
    """Return the model's custom_metadata_map as a plain dict."""
    return {prop.key: prop.value for prop in model.metadata_props}


def set_metadata_key(model: onnx.ModelProto, key: str, value: str) -> None:
    """Set (or replace) a single key in the model's metadata_props."""
    # Remove any existing entry for this key
    to_remove = [p for p in model.metadata_props if p.key == key]
    for p in to_remove:
        model.metadata_props.remove(p)
    # Add the new entry
    prop = model.metadata_props.add()
    prop.key = key
    prop.value = value


def class_names_to_metadata_value(class_names: dict[int, str]) -> str:
    """Serialise {int: str} as a Python dict literal (Ultralytics / CvStudio format).

    Example output: "{0: 'Dog', 1: 'Rooster', 2: 'Pig'}"

    CvStudio's inspect_audio_onnx() parses this with ast.literal_eval().
    """
    items = ", ".join(
        f"{k}: {repr(v)}"
        for k, v in sorted(class_names.items())
    )
    return "{" + items + "}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Inject class labels into ONNX metadata for CvStudio AudioClassification."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "model",
        help="Path to the input .onnx file.",
    )
    p.add_argument(
        "--labels",
        required=True,
        metavar="SOURCE",
        help=(
            "Label source. One of:\n"
            "  esc50        — built-in ESC-50 (50 classes)\n"
            "  yamnet       — built-in YAMNet (521 classes)\n"
            "  path/to/file — custom .txt or .json file\n"
            "  'dog,cat,…'  — inline comma-separated list"
        ),
    )
    p.add_argument(
        "--key",
        default="names",
        choices=["names", "labels", "classes"],
        help=(
            "Metadata key to write (default: 'names'). "
            "CvStudio checks 'names' first, then 'labels', then 'classes'."
        ),
    )
    p.add_argument(
        "--out",
        default=None,
        metavar="OUTPUT",
        help=(
            "Path for the modified .onnx file. "
            "If omitted, the input file is overwritten in-place."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be written without modifying any file.",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite without asking for confirmation.",
    )
    return p


def _confirm(prompt: str) -> bool:
    try:
        answer = input(prompt + " [y/N] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("y", "yes")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # ---- Validate input file -----------------------------------------------
    model_path = os.path.abspath(args.model)
    if not os.path.isfile(model_path):
        print(f"ERROR: Model file not found: '{model_path}'", file=sys.stderr)
        return 1

    # ---- Load labels --------------------------------------------------------
    try:
        class_names = load_labels(args.labels)
    except Exception as exc:
        print(f"ERROR: Could not load labels: {exc}", file=sys.stderr)
        return 1

    if not class_names:
        print("ERROR: Label set is empty.", file=sys.stderr)
        return 1

    # ---- Load ONNX model ----------------------------------------------------
    try:
        model = onnx.load(model_path)
    except Exception as exc:
        print(f"ERROR: Could not load ONNX model: {exc}", file=sys.stderr)
        return 1

    existing_meta = read_existing_metadata(model)

    # ---- Prepare new metadata value ----------------------------------------
    meta_value = class_names_to_metadata_value(class_names)

    # ---- Preview -----------------------------------------------------------
    print("=" * 60)
    print(f"  Model   : {model_path}")
    print(f"  Key     : '{args.key}'")
    print(f"  Classes : {len(class_names)}")
    print()

    if args.key in existing_meta:
        old_val = existing_meta[args.key]
        try:
            old_parsed = ast.literal_eval(old_val)
            old_count = len(old_parsed) if isinstance(old_parsed, (dict, list)) else "?"
        except Exception:
            old_count = "?"
        print(f"  Existing '{args.key}' metadata: {old_count} entries — will be replaced.")
    else:
        print(f"  No existing '{args.key}' metadata found — will be added.")

    print()
    print("  First 10 classes to be written:")
    for idx, (k, v) in enumerate(sorted(class_names.items())):
        if idx >= 10:
            print(f"    … and {len(class_names) - 10} more")
            break
        print(f"    {k:>4}: {v}")
    print("=" * 60)

    if args.dry_run:
        print("\n[dry-run] No file was modified.")
        return 0

    # ---- Confirm ------------------------------------------------------------
    out_path = os.path.abspath(args.out) if args.out else model_path
    in_place = (out_path == model_path)

    if not args.force:
        action = "overwrite in-place" if in_place else f"save to '{out_path}'"
        if not _confirm(f"\nProceed and {action}?"):
            print("Aborted.")
            return 0

    # ---- Write metadata -----------------------------------------------------
    set_metadata_key(model, args.key, meta_value)

    try:
        onnx.save(model, out_path)
    except Exception as exc:
        print(f"ERROR: Could not save ONNX model: {exc}", file=sys.stderr)
        return 1

    action_msg = "updated in-place" if in_place else f"saved to '{out_path}'"
    print(f"\n✓ Done — model {action_msg}.")
    print(f"  Wrote {len(class_names)} class labels under metadata key '{args.key}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
