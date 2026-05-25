#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for AudioClassification node inference pipeline.

Verifies that the mel-spectrogram preprocessing and ONNX inference setup
exactly match the ESC-50 training parameters:
  - sr=22050, n_mels=128, hop_length=512, n_fft=2048, max_sec=5
  - Input tensor shape: (1, 1, 128, 216) float32
  - Softmax applied to raw logits → probabilities sum to 1
  - Top-K predictions are sorted by descending score
  - add_model / _finalise_upload registers the model correctly
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Stub heavy GUI / vision dependencies before any project import so we can
# run tests headlessly without a display or full dependency stack.
# ---------------------------------------------------------------------------
for _mod in (
    "cv2", "dearpygui", "dearpygui.dearpygui",
    "onnxruntime", "onnxruntime.backend",
    "node.DLNode.object_detection.onnx_session_utils",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Stub make_session used by the module at import time
_mock_onnx_utils = MagicMock()
sys.modules["node.DLNode.object_detection.onnx_session_utils"] = _mock_onnx_utils

# Now numpy and librosa can be imported properly
import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
from node.AudioModelNode.node_audio_classification import (  # noqa: E402
    audio_to_mel_array,
    _DEFAULT_SR,
    _DEFAULT_N_MELS,
    _DEFAULT_MAX_SEC,
    _DEFAULT_HOP_LENGTH,
    _DEFAULT_N_FFT,
    _DEFAULT_TOP_K,
    _YAMNET_N_FFT,
    _YAMNET_WIN_LENGTH,
    _YAMNET_HOP_LENGTH,
    _YAMNET_TARGET_SR,
    _YAMNET_N_MELS,
    _YAMNET_FIXED_TIME,
    _YAMNET_MEL_NORM,
    _YAMNET_OUTPUT_ACTIVATION,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sine_audio(sr: int = _DEFAULT_SR, duration: float = _DEFAULT_MAX_SEC,
                     freq: float = 440.0) -> np.ndarray:
    """Return a float32 mono sine-wave array."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _expected_time_frames(sr: int, max_sec: int, hop_length: int) -> int:
    """Compute expected mel time-frames using librosa center=True convention."""
    n_samples = sr * max_sec
    return 1 + n_samples // hop_length


# ---------------------------------------------------------------------------
# 1. Mel-spectrogram shape
# ---------------------------------------------------------------------------

class TestMelSpectrogramShape(unittest.TestCase):

    def test_output_shape_5s_sr22050_128mels(self):
        """audio_to_mel_array must return (1, 128, 216) for the ESC-50 training config."""
        audio = _make_sine_audio(sr=_DEFAULT_SR, duration=_DEFAULT_MAX_SEC)
        mel = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)

        self.assertIsNotNone(mel, "audio_to_mel_array returned None (librosa missing?)")
        self.assertEqual(mel.ndim, 3, "Expected 3-D array (1, n_mels, T)")
        self.assertEqual(mel.shape[0], 1, "First dim should be 1 (channel)")
        self.assertEqual(mel.shape[1], _DEFAULT_N_MELS,
                         f"n_mels mismatch: {mel.shape[1]} != {_DEFAULT_N_MELS}")

        expected_T = _expected_time_frames(_DEFAULT_SR, _DEFAULT_MAX_SEC, _DEFAULT_HOP_LENGTH)
        self.assertEqual(
            mel.shape[2], expected_T,
            f"Time frames mismatch: got {mel.shape[2]}, expected {expected_T} "
            f"(sr={_DEFAULT_SR}, max_sec={_DEFAULT_MAX_SEC}, hop={_DEFAULT_HOP_LENGTH})"
        )

    def test_dtype_is_float32(self):
        """Mel array must be float32 to match ONNX model input type."""
        audio = _make_sine_audio()
        mel = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel)
        self.assertEqual(mel.dtype, np.float32, f"Expected float32, got {mel.dtype}")

    def test_short_audio_is_padded(self):
        """Audio shorter than max_sec must be zero-padded, not truncated."""
        short_audio = _make_sine_audio(duration=2.0)  # 2 s < 5 s
        mel = audio_to_mel_array(short_audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel)
        expected_T = _expected_time_frames(_DEFAULT_SR, _DEFAULT_MAX_SEC, _DEFAULT_HOP_LENGTH)
        self.assertEqual(mel.shape[2], expected_T,
                         "Padded audio should produce same T as full-length")

    def test_long_audio_is_cropped(self):
        """Audio longer than max_sec must be cropped, not padded."""
        long_audio = _make_sine_audio(duration=10.0)  # 10 s > 5 s
        mel = audio_to_mel_array(long_audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel)
        expected_T = _expected_time_frames(_DEFAULT_SR, _DEFAULT_MAX_SEC, _DEFAULT_HOP_LENGTH)
        self.assertEqual(mel.shape[2], expected_T,
                         "Cropped audio should produce same T as 5 s audio")

    def test_stereo_audio_is_converted_to_mono(self):
        """2-D stereo array must be averaged to mono before mel computation."""
        mono = _make_sine_audio()
        stereo = np.stack([mono, mono * 0.5], axis=-1)  # (N, 2)
        mel = audio_to_mel_array(stereo, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel)
        self.assertEqual(mel.ndim, 3, "Stereo input should still produce 3-D mel array")


# ---------------------------------------------------------------------------
# 2. ONNX input tensor shape
# ---------------------------------------------------------------------------

class TestOnnxInputTensorShape(unittest.TestCase):

    def test_batch_tensor_shape_is_1_1_128_216(self):
        """The batch tensor fed to onnxruntime must be (1, 1, 128, 216) float32."""
        audio = _make_sine_audio()
        mel_arr = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel_arr)

        # This is exactly what Node.update() does before calling session.run()
        x = mel_arr[np.newaxis].astype(np.float32)

        expected_T = _expected_time_frames(_DEFAULT_SR, _DEFAULT_MAX_SEC, _DEFAULT_HOP_LENGTH)
        expected_shape = (1, 1, _DEFAULT_N_MELS, expected_T)
        self.assertEqual(x.shape, expected_shape,
                         f"ONNX input shape {x.shape} != expected {expected_shape}")
        self.assertEqual(x.dtype, np.float32)


# ---------------------------------------------------------------------------
# 3. Softmax correctness
# ---------------------------------------------------------------------------

class TestSoftmaxInference(unittest.TestCase):
    """Verify the inline softmax used in Node.update() is numerically stable."""

    def _run_softmax(self, logits: np.ndarray) -> np.ndarray:
        """Reproduce the exact softmax from Node.update()."""
        logits = logits.copy().astype(np.float32)
        logits -= logits.max()          # numerical stability
        probs = np.exp(logits)
        probs /= probs.sum()
        return probs

    def test_probabilities_sum_to_one(self):
        logits = np.array([2.0, 1.0, 0.1, -0.5, 3.0] * 10, dtype=np.float32)
        probs = self._run_softmax(logits)
        self.assertAlmostEqual(float(probs.sum()), 1.0, places=5)

    def test_max_logit_gets_highest_prob(self):
        logits = np.zeros(50, dtype=np.float32)
        logits[7] = 10.0   # clear winner
        probs = self._run_softmax(logits)
        self.assertEqual(int(np.argmax(probs)), 7)

    def test_top_k_sorted_descending(self):
        rng = np.random.default_rng(42)
        logits = rng.standard_normal(50).astype(np.float32)
        probs = self._run_softmax(logits)
        top_k = 5
        top_ids = np.argsort(probs)[::-1][:top_k]
        top_scores = probs[top_ids]
        for i in range(len(top_scores) - 1):
            self.assertGreaterEqual(top_scores[i], top_scores[i + 1],
                                    "Top-K scores should be sorted in descending order")

    def test_uniform_logits_give_equal_probs(self):
        logits = np.zeros(50, dtype=np.float32)
        probs = self._run_softmax(logits)
        expected = 1.0 / 50
        np.testing.assert_allclose(probs, expected, atol=1e-6)

    def test_numerically_stable_with_large_logits(self):
        """Large logit values must not produce NaN/Inf (thanks to max shift)."""
        logits = np.array([1000.0, 999.0, 0.0, -500.0], dtype=np.float32)
        probs = self._run_softmax(logits)
        self.assertFalse(np.any(np.isnan(probs)), "Softmax produced NaN")
        self.assertFalse(np.any(np.isinf(probs)), "Softmax produced Inf")
        self.assertAlmostEqual(float(probs.sum()), 1.0, places=5)


# ---------------------------------------------------------------------------
# 4. Default hyper-parameters match training specification
# ---------------------------------------------------------------------------

class TestDefaultHyperParameters(unittest.TestCase):

    def test_sample_rate(self):
        self.assertEqual(_DEFAULT_SR, 22050,
                         "Sample rate must be 22050 Hz (ESC-50 training)")

    def test_n_mels(self):
        self.assertEqual(_DEFAULT_N_MELS, 128,
                         "n_mels must be 128 (ESC-50 training)")

    def test_max_sec(self):
        self.assertEqual(_DEFAULT_MAX_SEC, 5,
                         "max_sec must be 5 s (ESC-50 training)")

    def test_hop_length(self):
        self.assertEqual(_DEFAULT_HOP_LENGTH, 512,
                         "hop_length must be 512 (ESC-50 training)")

    def test_n_fft(self):
        self.assertEqual(_DEFAULT_N_FFT, 2048,
                         "n_fft must be 2048 (librosa/ESC-50 default)")

    def test_top_k_default_is_3(self):
        """Top-K default must be 3 so the node shows the top 3 predictions by default."""
        self.assertEqual(_DEFAULT_TOP_K, 3,
                         "Default Top-K should be 3 to display top 3 results")

    def test_expected_time_frames(self):
        """At sr=22050, 5 s, hop=512, T should be 216."""
        expected_T = _expected_time_frames(_DEFAULT_SR, _DEFAULT_MAX_SEC, _DEFAULT_HOP_LENGTH)
        self.assertEqual(expected_T, 216,
                         f"Expected 216 time frames, got {expected_T}")


# ---------------------------------------------------------------------------
# 5. _finalise_upload registers the model (mocked DPG)
# ---------------------------------------------------------------------------

class TestFinaliseUpload(unittest.TestCase):

    def setUp(self):
        from node.AudioModelNode.node_audio_classification import Node
        self.Node = Node
        # Reset class-level registry before each test
        Node._model_path_setting = {}
        Node._model_class_names = {}
        Node._model_n_mels = {}
        Node._model_type = {}
        Node._model_fixed_time = {}
        Node._model_target_sr = {}
        Node._model_n_fft = {}
        Node._model_hop_length = {}

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_model_registered_in_class_dicts(self, mock_dpg, mock_save):
        """After _finalise_upload, the model must appear in the class-level dicts."""
        mock_dpg.get_item_configuration.return_value = {"items": []}

        meta = {"n_mels": 128, "num_classes": 50, "class_names": {}}
        class_names = {i: f"cls_{i}" for i in range(50)}
        node_instance = MagicMock()
        node_instance.tag_model_combo = "combo_tag"

        self.Node._finalise_upload(node_instance, "/fake/model.onnx", meta,
                                   class_names, custom_name="test_model")

        self.assertIn("test_model", self.Node._model_path_setting)
        self.assertEqual(self.Node._model_path_setting["test_model"], "/fake/model.onnx")
        self.assertEqual(self.Node._model_n_mels["test_model"], 128)
        self.assertEqual(len(self.Node._model_class_names["test_model"]), 50)

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_duplicate_name_gets_suffix(self, mock_dpg, mock_save):
        """Adding a model with a taken name must append a counter suffix."""
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {"n_mels": 64, "num_classes": 10, "class_names": {}}
        class_names = {}
        node_instance = MagicMock()

        # Add "my_model" once
        self.Node._finalise_upload(node_instance, "/a.onnx", meta, class_names,
                                   custom_name="my_model")
        # Add "my_model" again
        self.Node._finalise_upload(node_instance, "/b.onnx", meta, class_names,
                                   custom_name="my_model")

        self.assertIn("my_model", self.Node._model_path_setting)
        self.assertIn("my_model_1", self.Node._model_path_setting)

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_registry_save_entry_called(self, mock_dpg, mock_save):
        """save_entry must be invoked so the model persists across restarts."""
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {"n_mels": 128, "num_classes": 50, "class_names": {}}
        node_instance = MagicMock()

        self.Node._finalise_upload(node_instance, "/c.onnx", meta, {},
                                   custom_name="persist_test")

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved["name"], "persist_test")
        self.assertEqual(saved["n_mels"], 128)
        self.assertEqual(saved["num_classes"], 50)


# ---------------------------------------------------------------------------
# 6. ESC-50 class names completeness
# ---------------------------------------------------------------------------

class TestEsc50ClassNames(unittest.TestCase):

    def test_50_classes_defined(self):
        from node.DLNode.classification.esc50_class_names import esc50_class_names
        self.assertEqual(len(esc50_class_names), 50)

    def test_keys_are_0_to_49(self):
        from node.DLNode.classification.esc50_class_names import esc50_class_names
        self.assertEqual(set(esc50_class_names.keys()), set(range(50)))

    def test_values_are_strings(self):
        from node.DLNode.classification.esc50_class_names import esc50_class_names
        for k, v in esc50_class_names.items():
            self.assertIsInstance(v, str, f"Class {k} name should be a string")



# ---------------------------------------------------------------------------
# 7. JSON output structure — classe + confiance
# ---------------------------------------------------------------------------

class TestJsonOutputStructure(unittest.TestCase):
    """Verify the result_json has the expected keys for downstream nodes."""

    def _build_result_json(self, logits: np.ndarray, class_names: dict,
                           top_k: int = 3) -> dict:
        """Reproduce the result_json construction from Node.update()."""
        logits = logits.copy().astype(np.float32)
        logits -= logits.max()
        probs = np.exp(logits)
        probs /= probs.sum()

        num_classes = len(probs)
        actual_k = min(top_k, num_classes)
        top_ids = np.argsort(probs)[::-1][:actual_k]
        top_scores = probs[top_ids]

        return {
            "predictions": [
                {
                    "rank": r + 1,
                    "class_id": int(top_ids[r]),
                    "class_name": class_names.get(int(top_ids[r]), f"class_{top_ids[r]}"),
                    "score": float(top_scores[r]),
                }
                for r in range(actual_k)
            ],
            "model": "test_model",
            "n_mels": 128,
            "sample_rate": 22050,
        }

    def test_top3_predictions_in_json(self):
        """Default top-3 must produce exactly 3 prediction entries."""
        logits = np.zeros(50, dtype=np.float32)
        logits[5] = 3.0
        logits[10] = 2.0
        logits[20] = 1.0
        class_names = {i: f"class_{i}" for i in range(50)}
        result = self._build_result_json(logits, class_names, top_k=_DEFAULT_TOP_K)
        self.assertEqual(len(result["predictions"]), 3,
                         f"Expected 3 predictions, got {len(result['predictions'])}")

    def test_predictions_have_class_name_and_score(self):
        """Each prediction must have 'class_name' (classe) and 'score' (confiance) keys."""
        rng = np.random.default_rng(0)
        logits = rng.standard_normal(50).astype(np.float32)
        class_names = {i: f"snd_{i}" for i in range(50)}
        result = self._build_result_json(logits, class_names, top_k=3)
        for pred in result["predictions"]:
            self.assertIn("class_name", pred, "Prediction must have 'class_name' key")
            self.assertIn("score", pred, "Prediction must have 'score' key (confidence)")
            self.assertIsInstance(pred["class_name"], str)
            self.assertIsInstance(pred["score"], float)
            self.assertGreaterEqual(pred["score"], 0.0)
            self.assertLessEqual(pred["score"], 1.0)

    def test_predictions_sorted_descending_by_score(self):
        """Predictions must appear in descending score order (best first)."""
        rng = np.random.default_rng(7)
        logits = rng.standard_normal(50).astype(np.float32)
        class_names = {i: f"c{i}" for i in range(50)}
        result = self._build_result_json(logits, class_names, top_k=3)
        scores = [p["score"] for p in result["predictions"]]
        for i in range(len(scores) - 1):
            self.assertGreaterEqual(scores[i], scores[i + 1],
                                    "Predictions should be sorted by descending confidence")

    def test_top1_label_format_for_json_button(self):
        """The JSON button label should be formatted as 'ClassName (0.XX)'."""
        logits = np.zeros(50, dtype=np.float32)
        logits[3] = 10.0   # clear winner: class 3
        class_names = {3: "Rain"}

        logits = logits.copy().astype(np.float32)
        logits -= logits.max()
        probs = np.exp(logits)
        probs /= probs.sum()
        top_ids = np.argsort(probs)[::-1][:1]
        top_scores = probs[top_ids]

        # This mirrors the label computation in Node.update()
        top_label = class_names.get(int(top_ids[0]), f"class_{top_ids[0]}")
        top_score = float(top_scores[0])
        label = f"{top_label} ({top_score:.2f})"

        self.assertTrue(label.startswith("Rain"), f"Label should start with class name: {label}")
        self.assertIn("(", label, "Label should include score in parentheses")

    def test_all_scores_sum_close_to_one_for_top3(self):
        """Scores of top-3 may not sum to 1.0, but each must be a valid probability."""
        rng = np.random.default_rng(99)
        logits = rng.standard_normal(50).astype(np.float32)
        class_names = {i: f"c{i}" for i in range(50)}
        result = self._build_result_json(logits, class_names, top_k=3)
        total = sum(p["score"] for p in result["predictions"])
        # total ≤ 1.0 since these are top-3 out of 50 probabilities
        self.assertLessEqual(total, 1.0 + 1e-5,
                             "Sum of top-3 scores should not exceed 1.0")


# ---------------------------------------------------------------------------
# 8. YAMNet mel preprocessing parameters
# ---------------------------------------------------------------------------

class TestYamnetMelPreprocessing(unittest.TestCase):
    """Verify that audio_to_mel_array honours per-model n_fft / hop_length
    overrides and that YAMNet uses the correct Qualcomm/Google parameters."""

    def test_yamnet_constants_are_correct(self):
        """YAMNet win_length=400 (25ms window), n_fft=512 (zero-padded FFT), hop_length=160 (10ms) at 16 kHz."""
        self.assertEqual(_YAMNET_WIN_LENGTH, 400,
                         "YAMNet win_length must be 400 (25 ms window at 16 kHz)")
        self.assertEqual(_YAMNET_N_FFT, 512,
                         "YAMNet n_fft must be 512 (zero-padded FFT, next power-of-two >= 400)")
        self.assertEqual(_YAMNET_HOP_LENGTH, 160,
                         "YAMNet hop_length must be 160 (10 ms stride at 16 kHz)")
        self.assertEqual(_YAMNET_TARGET_SR, 16000,
                         "YAMNet target sample rate must be 16000 Hz")
        # Architecture: input [1,1,96,64] → TIME-major (dim[2]=TIME, dim[3]=MELS)
        self.assertEqual(_YAMNET_N_MELS, 64,
                         "YAMNet n_mels must be 64 (not 96)")
        self.assertEqual(_YAMNET_FIXED_TIME, 96,
                         "YAMNet fixed_time must be 96 time frames per patch")
        # Mel normalisation: Google/Qualcomm YAMNet uses log(mel+0.001)
        self.assertEqual(_YAMNET_MEL_NORM, "log_offset",
                         "YAMNet mel_norm must be 'log_offset'")
        # Output: per-class sigmoid scores, not softmax logits
        self.assertEqual(_YAMNET_OUTPUT_ACTIVATION, "sigmoid",
                         "YAMNet output_activation must be 'sigmoid'")

    def test_custom_n_fft_changes_shape(self):
        """Passing n_fft overrides the default and is reflected in the output."""
        sr = 16000
        audio = _make_sine_audio(sr=sr, duration=1.0)
        mel_default = audio_to_mel_array(audio, sr, 96, 1)
        mel_yamnet = audio_to_mel_array(
            audio, sr, 96, 1,
            n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
        )
        self.assertIsNotNone(mel_default)
        self.assertIsNotNone(mel_yamnet)
        # Different hop produces different number of time frames
        self.assertNotEqual(
            mel_default.shape[2], mel_yamnet.shape[2],
            "YAMNet hop_length=160 must produce more frames than ESC-50 hop=512",
        )

    def test_yamnet_produces_more_frames_than_esc50(self):
        """hop_length=160 yields ~3.2x more frames than hop_length=512."""
        sr = 16000
        audio = _make_sine_audio(sr=sr, duration=5.0)
        mel_esc50 = audio_to_mel_array(audio, sr, 96, 5)
        mel_yamnet = audio_to_mel_array(
            audio, sr, 96, 5,
            n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
        )
        self.assertGreater(mel_yamnet.shape[2], mel_esc50.shape[2],
                           "YAMNet should produce more time frames due to smaller hop")

    def test_yamnet_mel_shape_at_16khz(self):
        """At 16 kHz, 5 s, hop=160, n_fft=400: T = 1 + (16000*5)//160 = 501."""
        sr = _YAMNET_TARGET_SR
        audio = _make_sine_audio(sr=sr, duration=5.0)
        mel = audio_to_mel_array(
            audio, sr, 96, 5,
            n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
        )
        self.assertIsNotNone(mel)
        expected_T = 1 + (sr * 5) // _YAMNET_HOP_LENGTH
        self.assertEqual(mel.shape[2], expected_T,
                         f"Expected T={expected_T}, got {mel.shape[2]}")

    def test_none_n_fft_falls_back_to_default(self):
        """Passing n_fft=None must use _DEFAULT_N_FFT unchanged."""
        sr = _DEFAULT_SR
        audio = _make_sine_audio(sr=sr)
        mel_none = audio_to_mel_array(audio, sr, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC, n_fft=None)
        mel_explicit = audio_to_mel_array(audio, sr, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC,
                                          n_fft=_DEFAULT_N_FFT)
        self.assertIsNotNone(mel_none)
        np.testing.assert_array_equal(mel_none, mel_explicit,
                                      "n_fft=None must behave the same as n_fft=_DEFAULT_N_FFT")

    def test_zero_n_fft_falls_back_to_default(self):
        """Passing n_fft=0 must use _DEFAULT_N_FFT unchanged."""
        sr = _DEFAULT_SR
        audio = _make_sine_audio(sr=sr)
        mel_zero = audio_to_mel_array(audio, sr, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC, n_fft=0)
        mel_explicit = audio_to_mel_array(audio, sr, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC,
                                          n_fft=_DEFAULT_N_FFT)
        self.assertIsNotNone(mel_zero)
        np.testing.assert_array_equal(mel_zero, mel_explicit,
                                      "n_fft=0 must behave the same as n_fft=_DEFAULT_N_FFT")

    def test_log_offset_norm_produces_different_values_than_power_to_db(self):
        """mel_norm='log_offset' must produce different values from 'power_to_db'."""
        sr = _YAMNET_TARGET_SR
        audio = _make_sine_audio(sr=sr, duration=1.0)
        mel_pdb = audio_to_mel_array(audio, sr, _YAMNET_N_MELS, 1,
                                     n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
                                     mel_norm="power_to_db")
        mel_log = audio_to_mel_array(audio, sr, _YAMNET_N_MELS, 1,
                                     n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
                                     mel_norm="log_offset")
        self.assertIsNotNone(mel_pdb)
        self.assertIsNotNone(mel_log)
        # log_offset values should be in [-7, 3] (natural log scale)
        # power_to_db values should be in [-80, 0] (dB scale)
        self.assertLess(mel_pdb.min(), -20.0,
                        "power_to_db should produce strongly negative dB values")
        self.assertGreater(mel_log.min(), -8.0,
                           "log_offset min should be ~log(0.001)=-6.9, not deeply negative")

    def test_log_offset_range_is_bounded(self):
        """log(mel + 0.001) output should be in [-6.9, ~3] range, not [-80, 0] dB."""
        sr = _YAMNET_TARGET_SR
        audio = _make_sine_audio(sr=sr, duration=1.0)
        mel_log = audio_to_mel_array(audio, sr, _YAMNET_N_MELS, 1,
                                     n_fft=_YAMNET_N_FFT, hop_length=_YAMNET_HOP_LENGTH,
                                     mel_norm="log_offset")
        self.assertIsNotNone(mel_log)
        self.assertGreaterEqual(mel_log.min(), -7.0,
                                "log_offset min should be bounded by log(0.001) ≈ -6.9")
        # max could be positive if mel energy > 1.0 (e.g. loud signal)
        self.assertLess(mel_log.max(), 30.0, "log_offset max should be reasonable")


if __name__ == "__main__":
    unittest.main(verbosity=2)
