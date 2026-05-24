#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
training_scripts — CV Studio AudioModelNode training module
============================================================

This package contains Jupyter/Colab notebooks that train ONNX audio
classification models fully compatible with the CV Studio
**AudioClassification** node (node/AudioModelNode).

Available notebooks
-------------------
train_esc50.ipynb
    Train a mel-CNN on the ESC-50 dataset (50 environmental sound classes).
    Exports an ONNX model with input shape (1, 1, 128, 216) and embeds
    class names as ONNX metadata (key "names").

train_fsd50k.ipynb
    Train a mel-CNN on FSD50K (200 AudioSet classes, ~51 k clips from Zenodo).
    Exports an ONNX model with a user-chosen fixed time axis.

train_yamnet_qualcomm.ipynb
    Fine-tune YAMNet (521 AudioSet classes) and export an ONNX model with
    fixed input shape (1, 1, 96, 64) ready for upload to Qualcomm AI Hub
    or direct use in the AudioClassification node.

Preprocessing contract (must match the CV Studio node)
------------------------------------------------------
All scripts use the **exact same** mel-spectrogram hyper-parameters that
``node_audio_classification.py`` applies at inference time:

    SR          = 22 050 Hz
    N_MELS      = 128   (96 for YAMNet / Qualcomm)
    N_FFT       = 2 048
    HOP_LENGTH  = 512
    MAX_SEC     = 5     (configurable)

ONNX compatibility checklist
-----------------------------
- Input  : float32  shape (1, 1, N_MELS, T)  — 4-D mel_cnn format
- Output : float32  shape (1, N_CLASSES)      — softmax scores
- Metadata key "names" : JSON string ``{"0": "label0", "1": "label1", …}``
- Fixed time axis (T) embedded in the ONNX graph so the node
  auto-detects ``fixed_time`` and crops / pads accordingly.

Usage
-----
Open any notebook in Google Colab or Jupyter, run all cells,
then upload the exported ``*.onnx`` file via the yellow **📂 Add Model**
button on the AudioClassification node in CV Studio.
"""

import os as _os

# ---------------------------------------------------------------------------
# Public catalogue of available training scripts
# ---------------------------------------------------------------------------

_SCRIPT_DIR = _os.path.dirname(_os.path.abspath(__file__))

TRAINING_SCRIPTS: dict = {
    "esc50": {
        "notebook": _os.path.join(_SCRIPT_DIR, "train_esc50.ipynb"),
        "description": "ESC-50: 50-class environmental sound dataset (train from scratch).",
        "dataset_url": "https://github.com/karoldvl/ESC-50/archive/master.zip",
        "n_classes": 50,
        "n_mels": 128,
        "fixed_time": 216,  # 5 s × 22 050 Hz / 512 hop + 1, center=True
        "onnx_input_shape": [1, 1, 128, 216],
    },
    "fsd50k": {
        "notebook": _os.path.join(_SCRIPT_DIR, "train_fsd50k.ipynb"),
        "description": "FSD50K: 200-class AudioSet subset from Zenodo (~51 k clips).",
        "dataset_url": "https://zenodo.org/record/4060432",
        "n_classes": 200,
        "n_mels": 128,
        "fixed_time": None,  # user-configurable
        "onnx_input_shape": [1, 1, 128, "T"],
    },
    "yamnet_qualcomm": {
        "notebook": _os.path.join(_SCRIPT_DIR, "train_yamnet_qualcomm.ipynb"),
        "description": (
            "YAMNet (521 AudioSet classes) fine-tuned and exported with fixed "
            "shape (1,1,96,64) for Qualcomm AI Hub deployment."
        ),
        "dataset_url": "https://tfhub.dev/google/yamnet/1",
        "n_classes": 521,
        "n_mels": 96,
        "fixed_time": 64,
        "onnx_input_shape": [1, 1, 96, 64],
    },
}


def list_scripts() -> list:
    """Return the names of all available training scripts."""
    return list(TRAINING_SCRIPTS.keys())


def get_script_info(name: str) -> dict:
    """Return metadata dict for the named training script.

    Parameters
    ----------
    name : str
        One of ``"esc50"``, ``"fsd50k"``, ``"yamnet_qualcomm"``.

    Returns
    -------
    dict
        Metadata including notebook path, dataset URL, ONNX input shape, etc.

    Raises
    ------
    KeyError
        If *name* is not a recognised training script.
    """
    if name not in TRAINING_SCRIPTS:
        raise KeyError(
            f"Unknown script '{name}'. Available: {list_scripts()}"
        )
    return dict(TRAINING_SCRIPTS[name])


def print_summary() -> None:
    """Print a human-readable summary of all available training scripts."""
    print("CV Studio — AudioModelNode training scripts\n" + "=" * 50)
    for key, info in TRAINING_SCRIPTS.items():
        nb = info["notebook"]
        exists = "✓" if _os.path.isfile(nb) else "✗"
        print(f"\n[{exists}] {key}")
        print(f"    {info['description']}")
        print(f"    Notebook   : {nb}")
        print(f"    ONNX shape : {info['onnx_input_shape']}")
        print(f"    Dataset    : {info['dataset_url']}")
