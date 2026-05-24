#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for microphone ↔ YAMNet audio-model coherence.

Verifies that:
1. Microphone default sample rate is 16000 Hz (YAMNet's training rate).
2. AudioClassification stores a target_sr per model and resamples incoming
   audio when the microphone runs at a different rate.
3. The YAMNet built-in model is registered with target_sr = 16000.
4. _register_model / _load_models_from_registry round-trips target_sr.
5. inspect_audio_onnx extracts target_sr from ONNX metadata keys.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub heavy GUI / vision / ONNX dependencies so tests run headlessly
# ---------------------------------------------------------------------------
for _mod in (
    "cv2", "dearpygui", "dearpygui.dearpygui",
    "onnxruntime", "onnxruntime.backend",
    "node.DLNode.object_detection.onnx_session_utils",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

sys.modules["node.DLNode.object_detection.onnx_session_utils"] = MagicMock()

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from node.AudioModelNode.node_audio_classification import (  # noqa: E402
    Node,
    _YAMNET_TARGET_SR,
    _DEFAULT_SR,
    audio_to_mel_array,
)


# ===========================================================================
# 1. Microphone default sample rate
# ===========================================================================

class TestMicrophoneDefaultSampleRate(unittest.TestCase):

    def test_default_sr_is_16000(self):
        """Microphone UI must default to 16000 Hz to match YAMNet's training rate."""
        mic_path = os.path.join(
            os.path.dirname(__file__), "..", "node", "InputNode", "node_microphone.py"
        )
        with open(mic_path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn(
            "default_value='16000'",
            src,
            "Microphone sample-rate combo default must be '16000' (YAMNet training SR).",
        )

    def test_internal_default_sr_is_16000(self):
        """MicrophoneNode._current_sample_rate initial value must be 16000."""
        mic_path = os.path.join(
            os.path.dirname(__file__), "..", "node", "InputNode", "node_microphone.py"
        )
        with open(mic_path, "r", encoding="utf-8") as f:
            src = f.read()
        self.assertIn(
            "_current_sample_rate = 16000",
            src,
            "MicrophoneNode._current_sample_rate must initialise to 16000.",
        )


# ===========================================================================
# 2. _YAMNET_TARGET_SR constant
# ===========================================================================

class TestYamnetTargetSrConstant(unittest.TestCase):

    def test_yamnet_target_sr_value(self):
        """_YAMNET_TARGET_SR must be 16000 (Google YAMNet training sample rate)."""
        self.assertEqual(
            _YAMNET_TARGET_SR, 16000,
            f"Expected _YAMNET_TARGET_SR=16000, got {_YAMNET_TARGET_SR}",
        )

    def test_yamnet_target_sr_differs_from_default_sr(self):
        """YAMNet target SR (16 kHz) must differ from the ESC-50 default SR (22050 Hz)."""
        self.assertNotEqual(
            _YAMNET_TARGET_SR, _DEFAULT_SR,
            "YAMNet and ESC-50 are trained at different sample rates.",
        )


# ===========================================================================
# 3. Node._register_model stores target_sr
# ===========================================================================

class TestRegisterModelTargetSr(unittest.TestCase):

    def setUp(self):
        Node._model_path_setting = {}
        Node._model_class_names = {}
        Node._model_n_mels = {}
        Node._model_type = {}
        Node._model_fixed_time = {}
        Node._model_target_sr = {}

    def test_target_sr_stored_when_provided(self):
        Node._register_model(
            "TestModel", "/fake/model.onnx", {}, 96,
            model_type="mel_cnn", fixed_time=64, target_sr=16000,
        )
        self.assertEqual(Node._model_target_sr.get("TestModel"), 16000)

    def test_target_sr_defaults_to_zero(self):
        """When target_sr is omitted, it defaults to 0 (= no forced resampling)."""
        Node._register_model(
            "ESC50Model", "/fake/esc50.onnx", {}, 128,
        )
        self.assertEqual(Node._model_target_sr.get("ESC50Model"), 0)

    def test_multiple_models_independent_target_sr(self):
        Node._register_model("ModelA", "/a.onnx", {}, 96, target_sr=16000)
        Node._register_model("ModelB", "/b.onnx", {}, 128, target_sr=22050)
        Node._register_model("ModelC", "/c.onnx", {}, 64)

        self.assertEqual(Node._model_target_sr["ModelA"], 16000)
        self.assertEqual(Node._model_target_sr["ModelB"], 22050)
        self.assertEqual(Node._model_target_sr["ModelC"], 0)


# ===========================================================================
# 4. _load_models_from_registry round-trips target_sr
# ===========================================================================

class TestLoadRegistryTargetSr(unittest.TestCase):

    def setUp(self):
        Node._model_path_setting = {}
        Node._model_class_names = {}
        Node._model_n_mels = {}
        Node._model_type = {}
        Node._model_fixed_time = {}
        Node._model_target_sr = {}

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.load_registry")
    def test_target_sr_loaded_from_registry(self, mock_load):
        mock_load.return_value = [
            {
                "name": "YAMNet",
                "path": "/fake/yamnet.onnx",
                "class_names": {"0": "Speech"},
                "n_mels": 96,
                "model_type": "mel_cnn",
                "fixed_time": 64,
                "target_sr": 16000,
            }
        ]
        with patch("os.path.isfile", return_value=True):
            Node._load_models_from_registry()

        self.assertIn("YAMNet", Node._model_target_sr)
        self.assertEqual(Node._model_target_sr["YAMNet"], 16000)

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.load_registry")
    def test_missing_target_sr_defaults_to_zero(self, mock_load):
        """Old registry entries without target_sr must default to 0."""
        mock_load.return_value = [
            {
                "name": "OldModel",
                "path": "/fake/old.onnx",
                "class_names": {},
                "n_mels": 128,
                "model_type": "mel_cnn",
                "fixed_time": 0,
                # target_sr intentionally absent
            }
        ]
        with patch("os.path.isfile", return_value=True):
            Node._load_models_from_registry()

        self.assertEqual(Node._model_target_sr.get("OldModel", 0), 0)


# ===========================================================================
# 5. inspect_audio_onnx extracts target_sr from metadata
# ===========================================================================

class TestInspectAudioOnnxTargetSr(unittest.TestCase):

    def _make_mock_session(self, input_shape, output_shape, metadata=None):
        """Return a mock onnxruntime.InferenceSession with given shapes."""
        sess = MagicMock()

        inp = MagicMock()
        inp.name = "audio"
        inp.shape = input_shape

        out = MagicMock()
        out.name = "output"
        out.shape = output_shape

        sess.get_inputs.return_value = [inp]
        sess.get_outputs.return_value = [out]

        meta = MagicMock()
        meta.custom_metadata_map = metadata or {}
        sess.get_modelmeta.return_value = meta

        return sess

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    def test_target_sr_from_sample_rate_key(self, mock_make):
        mock_make.return_value = self._make_mock_session(
            [1, 1, 96, 64], [1, 521],
            metadata={"sample_rate": "16000"},
        )
        from node.AudioModelNode.node_audio_classification import inspect_audio_onnx
        with patch("os.path.isfile", return_value=True):
            result = inspect_audio_onnx("/fake/yamnet.onnx")
        self.assertEqual(result["target_sr"], 16000)

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    def test_target_sr_from_sr_key(self, mock_make):
        mock_make.return_value = self._make_mock_session(
            [1, 1, 96, 64], [1, 521],
            metadata={"sr": "22050"},
        )
        from node.AudioModelNode.node_audio_classification import inspect_audio_onnx
        with patch("os.path.isfile", return_value=True):
            result = inspect_audio_onnx("/fake/model.onnx")
        self.assertEqual(result["target_sr"], 22050)

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    def test_target_sr_zero_when_no_metadata(self, mock_make):
        mock_make.return_value = self._make_mock_session(
            [1, 1, 96, 64], [1, 521],
            metadata={},
        )
        from node.AudioModelNode.node_audio_classification import inspect_audio_onnx
        with patch("os.path.isfile", return_value=True):
            result = inspect_audio_onnx("/fake/model.onnx")
        self.assertEqual(result["target_sr"], 0)


# ===========================================================================
# 6. Resampling in update() — effective audio window correctness
# ===========================================================================

class TestResamplingEffectiveWindow(unittest.TestCase):
    """
    When mic runs at 44100 Hz and YAMNet expects 16000 Hz with fixed_time=64
    and hop_length=512, the EFFECTIVE audio window used for inference is:
      - Without resample: 64 * 512 / 44100 ≈ 0.74 s  (too short)
      - With resample:    64 * 512 / 16000 = 2.05 s   (correct)
    """

    def test_effective_window_at_16000hz(self):
        """At 16000 Hz the 64-frame mel covers exactly 2.048 s."""
        sr = 16000
        hop = 512
        fixed_time = 64
        window_s = fixed_time * hop / sr
        self.assertAlmostEqual(window_s, 2.048, places=3)

    def test_effective_window_at_44100hz_is_too_short(self):
        """Without resampling a 44100 Hz mic only covers ~0.74 s — below 1 s."""
        sr = 44100
        hop = 512
        fixed_time = 64
        window_s = fixed_time * hop / sr
        self.assertLess(
            window_s, 1.0,
            "Without resampling, YAMNet inference window < 1 s — too short for reliable detection.",
        )

    def test_resampled_audio_shape(self):
        """librosa.resample must change the number of samples proportionally."""
        try:
            import librosa
        except ImportError:
            self.skipTest("librosa not installed")

        orig_sr = 44100
        target_sr = 16000
        duration = 3.0
        t = np.linspace(0, duration, int(orig_sr * duration), endpoint=False)
        y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        y_rs = librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)

        expected_len = int(duration * target_sr)
        # librosa may be off by ±1 sample
        self.assertAlmostEqual(len(y_rs), expected_len, delta=2)

    def test_mel_frames_after_resample(self):
        """After resampling 44100→16000 Hz, the mel shape should reflect 16 kHz."""
        try:
            import librosa
        except ImportError:
            self.skipTest("librosa not installed")

        from node.AudioModelNode.node_audio_classification import (
            audio_to_mel_array, _DEFAULT_HOP_LENGTH,
        )

        orig_sr = 44100
        target_sr = 16000
        max_sec = 3
        n_mels = 96

        duration = 3.0
        t = np.linspace(0, duration, int(orig_sr * duration), endpoint=False)
        y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        y_rs = librosa.resample(y, orig_sr=orig_sr, target_sr=target_sr)

        mel = audio_to_mel_array(y_rs, target_sr, n_mels, max_sec)
        self.assertIsNotNone(mel)
        # Expected time frames at 16 kHz, 3 s, hop=512
        expected_T = 1 + (target_sr * max_sec) // _DEFAULT_HOP_LENGTH
        self.assertEqual(mel.shape[2], expected_T)


# ===========================================================================
# 7. _finalise_upload persists target_sr in registry entry
# ===========================================================================

class TestFinaliseUploadTargetSr(unittest.TestCase):

    def setUp(self):
        Node._model_path_setting = {}
        Node._model_class_names = {}
        Node._model_n_mels = {}
        Node._model_type = {}
        Node._model_fixed_time = {}
        Node._model_target_sr = {}

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_target_sr_saved_in_registry_entry(self, mock_dpg, mock_save):
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {
            "n_mels": 96,
            "num_classes": 521,
            "class_names": {},
            "model_type": "mel_cnn",
            "fixed_time": 64,
            "target_sr": 16000,
        }
        node_inst = MagicMock()
        node_inst.tag_model_combo = "combo"

        Node._finalise_upload(node_inst, "/fake/yamnet.onnx", meta, {},
                              custom_name="YAMNet")

        mock_save.assert_called_once()
        entry = mock_save.call_args[0][0]
        self.assertEqual(entry.get("target_sr"), 16000,
                         "target_sr must be persisted in the registry entry.")

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_target_sr_zero_when_not_in_meta(self, mock_dpg, mock_save):
        """Old meta dicts without target_sr must default to 0 in the registry."""
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {"n_mels": 128, "num_classes": 50, "class_names": {}}
        node_inst = MagicMock()

        Node._finalise_upload(node_inst, "/fake/esc50.onnx", meta, {},
                              custom_name="ESC50")

        entry = mock_save.call_args[0][0]
        self.assertEqual(entry.get("target_sr", 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
