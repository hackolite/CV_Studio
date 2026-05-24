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
    _DEFAULT_MEL_MEAN,
    _DEFAULT_MEL_STD,
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

    def test_mel_mean(self):
        self.assertEqual(_DEFAULT_MEL_MEAN, -40.0,
                         "MEL_MEAN must be -40.0 (ESC-50 training z-score)")

    def test_mel_std(self):
        self.assertEqual(_DEFAULT_MEL_STD, 20.0,
                         "MEL_STD must be 20.0 (ESC-50 training z-score)")


# ---------------------------------------------------------------------------
# 4b. Z-score normalization in audio_to_mel_array
# ---------------------------------------------------------------------------

class TestMelNormalization(unittest.TestCase):
    """Verify audio_to_mel_array applies z-score normalization matching training."""

    def test_default_normalization_applied(self):
        """With default mel_mean/mel_std the output must NOT equal the raw dB values."""
        audio = _make_sine_audio()
        # unnormalized (bypass via extreme values that wouldn't overlap with normalized)
        mel_norm = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel_norm)
        # After z-score with mean=-40, std=20 a typical dB range of ~-80..0 maps to ~-2..2
        # Raw power_to_db output is typically in the range -80..0 dB;
        # after normalization the mean should be near 0 (not near -40).
        mean_val = float(mel_norm.mean())
        self.assertLess(abs(mean_val), 5.0,
                        f"Normalized mel mean {mean_val:.2f} is too far from 0; "
                        "normalization may not be applied")

    def test_custom_normalization_applied(self):
        """Passing custom mel_mean/mel_std must shift and scale the output."""
        audio = _make_sine_audio()
        # Use extreme values so the effect is obvious
        mel_zero_mean = audio_to_mel_array(
            audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC,
            mel_mean=0.0, mel_std=1.0,
        )
        mel_default = audio_to_mel_array(
            audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC,
        )
        self.assertIsNotNone(mel_zero_mean)
        self.assertIsNotNone(mel_default)
        # They should differ because the normalization constants are different
        self.assertFalse(
            np.allclose(mel_zero_mean, mel_default, atol=1e-3),
            "Different normalization constants should produce different outputs",
        )

    def test_normalization_constants_used_correctly(self):
        """The formula (mel_db - mel_mean) / mel_std must be exact."""
        audio = _make_sine_audio()

        import librosa as _librosa_check  # noqa: F401 — skip if not available
        import librosa

        y = np.asarray(audio, dtype=np.float32)
        if len(y) < _DEFAULT_SR * _DEFAULT_MAX_SEC:
            y = np.pad(y, (0, _DEFAULT_SR * _DEFAULT_MAX_SEC - len(y)))
        else:
            y = y[:_DEFAULT_SR * _DEFAULT_MAX_SEC]

        raw_mel = librosa.feature.melspectrogram(
            y=y, sr=_DEFAULT_SR, n_mels=_DEFAULT_N_MELS,
            n_fft=2048, hop_length=512,
        )
        raw_db = librosa.power_to_db(raw_mel).astype(np.float32)
        expected = ((raw_db - _DEFAULT_MEL_MEAN) / _DEFAULT_MEL_STD)[np.newaxis]

        result = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS, _DEFAULT_MAX_SEC)
        np.testing.assert_allclose(result, expected, atol=1e-5,
                                   err_msg="Normalization formula mismatch")


# ---------------------------------------------------------------------------
# 4c. Sample-rate resampling in audio_to_mel_array
# ---------------------------------------------------------------------------

class TestMelResampling(unittest.TestCase):
    """Verify audio_to_mel_array resamples audio to target_sr before computing mel."""

    def test_resampled_output_same_shape_as_native_sr(self):
        """Audio at 44100 Hz resampled to 22050 must give same T as native 22050 audio."""
        # Native 22050 audio
        audio_22050 = _make_sine_audio(sr=_DEFAULT_SR, duration=_DEFAULT_MAX_SEC)
        mel_native = audio_to_mel_array(audio_22050, _DEFAULT_SR, _DEFAULT_N_MELS,
                                        _DEFAULT_MAX_SEC)

        # 44100 Hz audio (same signal, twice as many samples)
        audio_44100 = _make_sine_audio(sr=44100, duration=_DEFAULT_MAX_SEC)
        mel_resampled = audio_to_mel_array(audio_44100, 44100, _DEFAULT_N_MELS,
                                           _DEFAULT_MAX_SEC, target_sr=_DEFAULT_SR)

        self.assertIsNotNone(mel_native)
        self.assertIsNotNone(mel_resampled)
        self.assertEqual(mel_native.shape, mel_resampled.shape,
                         f"Resampled shape {mel_resampled.shape} != native shape "
                         f"{mel_native.shape}")

    def test_no_resample_when_sr_equals_target(self):
        """When sample_rate == target_sr, result must be identical to no-resampling path."""
        audio = _make_sine_audio(sr=_DEFAULT_SR)
        mel_explicit = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS,
                                          _DEFAULT_MAX_SEC, target_sr=_DEFAULT_SR)
        mel_default = audio_to_mel_array(audio, _DEFAULT_SR, _DEFAULT_N_MELS,
                                         _DEFAULT_MAX_SEC)
        self.assertIsNotNone(mel_explicit)
        np.testing.assert_array_equal(mel_explicit, mel_default,
                                      err_msg="Same-SR path should give identical output")


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
        Node._model_input_sr = {}
        Node._model_mel_mean = {}
        Node._model_mel_std = {}

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

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_normalization_params_stored_in_registry(self, mock_dpg, mock_save):
        """Registry entry must include input_sr, mel_mean, mel_std from model metadata."""
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {
            "n_mels": 128, "num_classes": 50, "class_names": {},
            "input_sr": 22050, "mel_mean": -40.0, "mel_std": 20.0,
        }
        node_instance = MagicMock()

        self.Node._finalise_upload(node_instance, "/d.onnx", meta, {},
                                   custom_name="norm_test")

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        self.assertEqual(saved["input_sr"], 22050)
        self.assertAlmostEqual(saved["mel_mean"], -40.0)
        self.assertAlmostEqual(saved["mel_std"], 20.0)

    @patch("node.AudioModelNode.node_audio_classification.audio_models_registry.save_entry")
    @patch("node.AudioModelNode.node_audio_classification.dpg")
    def test_normalization_params_in_class_dicts(self, mock_dpg, mock_save):
        """Class-level dicts _model_input_sr/mel_mean/mel_std must be set after upload."""
        mock_dpg.get_item_configuration.return_value = {"items": []}
        meta = {
            "n_mels": 64, "num_classes": 10, "class_names": {},
            "input_sr": 44100, "mel_mean": -30.0, "mel_std": 15.0,
        }
        node_instance = MagicMock()

        self.Node._finalise_upload(node_instance, "/e.onnx", meta, {},
                                   custom_name="custom_sr_model")

        self.assertEqual(self.Node._model_input_sr["custom_sr_model"], 44100)
        self.assertAlmostEqual(self.Node._model_mel_mean["custom_sr_model"], -30.0)
        self.assertAlmostEqual(self.Node._model_mel_std["custom_sr_model"], 15.0)


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


if __name__ == "__main__":
    unittest.main(verbosity=2)

