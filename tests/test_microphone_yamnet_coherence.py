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
    _YAMNET_N_FFT,
    _YAMNET_HOP_LENGTH,
    _YAMNET_N_MELS,
    _YAMNET_FIXED_TIME,
    _YAMNET_MEL_NORM,
    _YAMNET_OUTPUT_ACTIVATION,
    _DEFAULT_SR,
    _DEFAULT_N_FFT,
    _DEFAULT_HOP_LENGTH,
    audio_to_mel_array,
    inspect_audio_onnx,
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
        Node._model_n_fft = {}
        Node._model_hop_length = {}

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
        Node._model_n_fft = {}
        Node._model_hop_length = {}

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
            audio_to_mel_array,
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
        Node._model_n_fft = {}
        Node._model_hop_length = {}
        Node._model_mel_transpose = {}
        Node._model_mel_norm = {}
        Node._model_output_activation = {}

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_target_sr_saved_in_registry_entry(self, mock_dpg, mock_save):
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {
            "n_mels": _YAMNET_N_MELS,
            "num_classes": 521,
            "class_names": {},
            "model_type": "mel_cnn",
            "fixed_time": _YAMNET_FIXED_TIME,
            "target_sr": 16000,
            "n_fft": _YAMNET_N_FFT,
            "hop_length": _YAMNET_HOP_LENGTH,
            "mel_transpose": True,
            "mel_norm": _YAMNET_MEL_NORM,
            "output_activation": _YAMNET_OUTPUT_ACTIVATION,
        }
        node_inst = MagicMock()
        node_inst.tag_model_combo = "combo"

        Node._finalise_upload(node_inst, "/fake/yamnet.onnx", meta, {},
                              custom_name="YAMNet")

        mock_save.assert_called_once()
        entry = mock_save.call_args[0][0]
        self.assertEqual(entry.get("target_sr"), 16000)
        self.assertEqual(entry.get("n_fft"), _YAMNET_N_FFT)
        self.assertEqual(entry.get("hop_length"), _YAMNET_HOP_LENGTH)
        self.assertEqual(entry.get("mel_transpose"), True,
                         "mel_transpose must be persisted in the registry entry.")
        self.assertEqual(entry.get("mel_norm"), _YAMNET_MEL_NORM,
                         "mel_norm must be persisted in the registry entry.")
        self.assertEqual(entry.get("output_activation"), _YAMNET_OUTPUT_ACTIVATION,
                         "output_activation must be persisted in the registry entry.")

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
        self.assertEqual(entry.get("n_fft", 0), 0,
                         "n_fft must default to 0 when not in meta.")
        self.assertEqual(entry.get("hop_length", 0), 0,
                         "hop_length must default to 0 when not in meta.")
        self.assertFalse(entry.get("mel_transpose", False),
                         "mel_transpose must default to False for standard models.")
        self.assertEqual(entry.get("mel_norm", "power_to_db"), "power_to_db",
                         "mel_norm must default to 'power_to_db' for standard models.")
        self.assertEqual(entry.get("output_activation", "softmax"), "softmax",
                         "output_activation must default to 'softmax' for standard models.")


# ===========================================================================
# 8. YAMNet mel preprocessing: n_fft/hop_length in registry and inference
# ===========================================================================

class TestYamnetMelPreprocessingParams(unittest.TestCase):
    """Verify that the YAMNet-specific mel parameters are correctly wired
    through the registry and _register_model so the node uses them at
    inference time instead of the ESC-50 defaults."""

    def setUp(self):
        Node._model_path_setting = {}
        Node._model_class_names = {}
        Node._model_n_mels = {}
        Node._model_type = {}
        Node._model_fixed_time = {}
        Node._model_target_sr = {}
        Node._model_n_fft = {}
        Node._model_hop_length = {}
        Node._model_mel_transpose = {}
        Node._model_mel_norm = {}
        Node._model_output_activation = {}

    def test_register_model_stores_n_fft(self):
        Node._register_model(
            "YAMNet", "/fake/yamnet.onnx", {}, _YAMNET_N_MELS,
            model_type="mel_cnn", fixed_time=_YAMNET_FIXED_TIME,
            target_sr=_YAMNET_TARGET_SR,
            n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
            mel_transpose=True, mel_norm=_YAMNET_MEL_NORM,
            output_activation=_YAMNET_OUTPUT_ACTIVATION,
        )
        self.assertEqual(Node._model_n_fft.get("YAMNet"), _YAMNET_N_FFT)
        self.assertEqual(Node._model_hop_length.get("YAMNet"), _YAMNET_HOP_LENGTH)
        self.assertTrue(Node._model_mel_transpose.get("YAMNet"),
                        "mel_transpose must be stored True for YAMNet")
        self.assertEqual(Node._model_mel_norm.get("YAMNet"), _YAMNET_MEL_NORM,
                         "mel_norm must be stored correctly for YAMNet")
        self.assertEqual(Node._model_output_activation.get("YAMNet"), _YAMNET_OUTPUT_ACTIVATION,
                         "output_activation must be stored correctly for YAMNet")
        self.assertEqual(Node._model_n_mels.get("YAMNet"), _YAMNET_N_MELS,
                         "n_mels must be stored correctly for YAMNet")
        self.assertEqual(Node._model_fixed_time.get("YAMNet"), _YAMNET_FIXED_TIME,
                         "fixed_time must be stored correctly for YAMNet")

    def test_register_model_n_fft_defaults_to_zero(self):
        """n_fft/hop_length/mel_transpose/mel_norm/output_activation default when omitted."""
        Node._register_model("ESC50", "/fake/esc50.onnx", {}, 128)
        self.assertEqual(Node._model_n_fft.get("ESC50"), 0)
        self.assertEqual(Node._model_hop_length.get("ESC50"), 0)
        self.assertFalse(Node._model_mel_transpose.get("ESC50"),
                         "mel_transpose must default to False")
        self.assertEqual(Node._model_mel_norm.get("ESC50"), "power_to_db",
                         "mel_norm must default to 'power_to_db'")
        self.assertEqual(Node._model_output_activation.get("ESC50"), "softmax",
                         "output_activation must default to 'softmax'")

    def test_yamnet_uses_different_params_than_esc50_defaults(self):
        """YAMNet n_fft and hop_length must differ from the ESC-50/librosa defaults."""
        self.assertNotEqual(_YAMNET_N_FFT, _DEFAULT_N_FFT,
                            "YAMNet n_fft should differ from ESC-50 default")
        self.assertNotEqual(_YAMNET_HOP_LENGTH, _DEFAULT_HOP_LENGTH,
                            "YAMNet hop_length should differ from ESC-50 default")
        self.assertNotEqual(_YAMNET_MEL_NORM, "power_to_db",
                            "YAMNet mel_norm should differ from ESC-50 default")
        self.assertNotEqual(_YAMNET_OUTPUT_ACTIVATION, "softmax",
                            "YAMNet output_activation should differ from ESC-50 default")

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.load_registry")
    def test_n_fft_hop_loaded_from_registry(self, mock_load):
        """All YAMNet params are loaded from the registry into Node dicts."""
        mock_load.return_value = [
            {
                "name": "YAMNet",
                "path": "/fake/yamnet.onnx",
                "class_names": {},
                "n_mels": _YAMNET_N_MELS,
                "model_type": "mel_cnn",
                "fixed_time": _YAMNET_FIXED_TIME,
                "target_sr": 16000,
                "n_fft": _YAMNET_N_FFT,
                "hop_length": _YAMNET_HOP_LENGTH,
                "mel_transpose": True,
                "mel_norm": _YAMNET_MEL_NORM,
                "output_activation": _YAMNET_OUTPUT_ACTIVATION,
            }
        ]
        with patch("os.path.isfile", return_value=True):
            Node._load_models_from_registry()

        self.assertEqual(Node._model_n_fft.get("YAMNet"), _YAMNET_N_FFT)
        self.assertEqual(Node._model_hop_length.get("YAMNet"), _YAMNET_HOP_LENGTH)
        self.assertTrue(Node._model_mel_transpose.get("YAMNet"))
        self.assertEqual(Node._model_mel_norm.get("YAMNet"), _YAMNET_MEL_NORM)
        self.assertEqual(Node._model_output_activation.get("YAMNet"), _YAMNET_OUTPUT_ACTIVATION)

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.load_registry")
    def test_missing_n_fft_defaults_to_zero(self, mock_load):
        """Old registry entries without n_fft/hop_length/mel_transpose etc. must default."""
        mock_load.return_value = [
            {
                "name": "OldModel",
                "path": "/fake/old.onnx",
                "class_names": {},
                "n_mels": 128,
                "model_type": "mel_cnn",
                "fixed_time": 0,
                # All new fields intentionally absent → test backward compat
            }
        ]
        with patch("os.path.isfile", return_value=True):
            Node._load_models_from_registry()

        self.assertEqual(Node._model_n_fft.get("OldModel", 0), 0)
        self.assertEqual(Node._model_hop_length.get("OldModel", 0), 0)
        self.assertFalse(Node._model_mel_transpose.get("OldModel", False))
        self.assertEqual(Node._model_mel_norm.get("OldModel", "power_to_db"), "power_to_db")
        self.assertEqual(Node._model_output_activation.get("OldModel", "softmax"), "softmax")

    def test_yamnet_hop_produces_more_frames_than_esc50(self):
        """YAMNet hop=160 at 16 kHz produces ~3.2x more frames than ESC-50 hop=512."""
        try:
            import librosa  # noqa: F401
        except ImportError:
            self.skipTest("librosa not installed")

        sr = _YAMNET_TARGET_SR
        duration = 3.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        mel_esc50 = audio_to_mel_array(y, sr, _YAMNET_N_MELS, int(duration))
        mel_yamnet = audio_to_mel_array(
            y, sr, _YAMNET_N_MELS, int(duration),
            n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
        )
        self.assertIsNotNone(mel_esc50)
        self.assertIsNotNone(mel_yamnet)
        self.assertGreater(
            mel_yamnet.shape[2], mel_esc50.shape[2],
            f"YAMNet (hop=160) should give more frames "
            f"({mel_yamnet.shape[2]}) than ESC-50 (hop=512) "
            f"({mel_esc50.shape[2]})"
        )


# ===========================================================================
# 9. inspect_audio_onnx: time-major layout detection
# ===========================================================================

class TestInspectAudioOnnxLayout(unittest.TestCase):
    """Verify that inspect_audio_onnx correctly detects time-major vs mels-first
    tensor layouts by checking the relative sizes of input dimensions."""

    def _make_mock_session(self, input_shape):
        """Build a minimal ort session mock with the given 4-D input shape."""
        inp = MagicMock()
        inp.name = "audio"
        inp.shape = input_shape
        out = MagicMock()
        out.name = "class_scores"
        out.shape = [1, 521]

        sess = MagicMock()
        sess.get_inputs.return_value = [inp]
        sess.get_outputs.return_value = [out]
        sess.get_modelmeta.return_value.custom_metadata_map = {}
        return sess

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    @patch("os.path.isfile", return_value=True)
    def test_yamnet_shape_96x64_is_time_major(self, mock_isfile, mock_make):
        """Input [1,1,96,64]: dim[2]=96 > dim[3]=64 → time-major (transpose=True)."""
        mock_make.return_value = self._make_mock_session([1, 1, 96, 64])
        info = inspect_audio_onnx("/fake/yamnet.onnx")
        self.assertEqual(info["n_mels"], 64,
                         "n_mels must be dim[3]=64 for time-major layout")
        self.assertEqual(info["fixed_time"], 96,
                         "fixed_time must be dim[2]=96 for time-major layout")
        self.assertTrue(info["mel_transpose"],
                        "mel_transpose must be True for time-major layout")

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    @patch("os.path.isfile", return_value=True)
    def test_esc50_shape_128x216_is_mels_first(self, mock_isfile, mock_make):
        """Input [1,1,128,216]: dim[2]=128 < dim[3]=216 → mels-first (transpose=False)."""
        mock_make.return_value = self._make_mock_session([1, 1, 128, 216])
        info = inspect_audio_onnx("/fake/esc50.onnx")
        self.assertEqual(info["n_mels"], 128,
                         "n_mels must be dim[2]=128 for mels-first layout")
        self.assertEqual(info["fixed_time"], 216,
                         "fixed_time must be dim[3]=216 for mels-first layout")
        self.assertFalse(info["mel_transpose"],
                         "mel_transpose must be False for mels-first layout")

    @patch("node.AudioModelNode.node_audio_classification.make_session")
    @patch("os.path.isfile", return_value=True)
    def test_equal_dims_treated_as_mels_first(self, mock_isfile, mock_make):
        """Input [1,1,64,64]: equal dims → mels-first (no transpose)."""
        mock_make.return_value = self._make_mock_session([1, 1, 64, 64])
        info = inspect_audio_onnx("/fake/square.onnx")
        self.assertFalse(info["mel_transpose"],
                         "Equal dims should not trigger transpose")


if __name__ == "__main__":
    unittest.main(verbosity=2)
