#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke-tests for the piper-TTS live-streaming pipeline.

Tests verify:
  1. piper-tts Python package is importable.
  2. French ONNX model path constants are correct.
  3. sounddevice + numpy are importable (or gracefully absent).
  4. verify_piper() returns the expected result structure.
  5. _speak_piper() streams audio chunk-by-chunk via sounddevice.
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ---------------------------------------------------------------------------
# Pre-stub sounddevice so it can be imported even without PortAudio.
# Do this BEFORE loading the module under test so the module's lazy
# `import sounddevice as sd` resolves against our stub.
# ---------------------------------------------------------------------------
_sd_stub = MagicMock()
sys.modules['sounddevice'] = _sd_stub

# ---------------------------------------------------------------------------
# Other stubs needed to load node_text2speech.py without the full GUI stack.
# ---------------------------------------------------------------------------
sys.modules.setdefault('dearpygui', MagicMock())
sys.modules.setdefault('dearpygui.dearpygui', MagicMock())
sys.modules.setdefault('node_editor', MagicMock())
sys.modules.setdefault('node_editor.util', MagicMock())

_basenode_stub = MagicMock()
_basenode_stub.Node = object
sys.modules['node.basenode'] = _basenode_stub

# ---------------------------------------------------------------------------
# Load module under test via importlib to avoid `node` package conflict.
# ---------------------------------------------------------------------------
_NODE_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'node', 'ActionNode', 'node_text2speech.py'
)
_spec = importlib.util.spec_from_file_location('node_text2speech', _NODE_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_speak_piper = _mod._speak_piper
verify_piper = _mod.verify_piper
_FR_ONNX = _mod._FR_ONNX
_FR_JSON = _mod._FR_JSON


# ===========================================================================
# Tests
# ===========================================================================

class TestPiperInstallation(unittest.TestCase):
    """piper-tts Python package availability."""

    def test_piper_importable(self):
        try:
            from piper.voice import PiperVoice  # noqa: F401
        except ImportError as exc:
            self.fail(f'piper-tts not importable: {exc}')


class TestNumpyImport(unittest.TestCase):
    """numpy availability (required for audio arrays)."""

    def test_numpy_importable(self):
        try:
            import numpy  # noqa: F401
        except ImportError as exc:
            self.fail(f'numpy not importable: {exc}')


class TestVerifyPiper(unittest.TestCase):
    """verify_piper() returns the expected result structure."""

    def test_verify_piper_callable(self):
        self.assertTrue(callable(verify_piper))

    def test_verify_piper_has_required_keys(self):
        with patch.object(_mod, '_ensure_piper_model', return_value=_FR_ONNX), \
             patch.object(Path, 'exists', return_value=True):
            result = verify_piper()

        for key in ('piper_installed', 'onnx_model_ok', 'sounddevice_ok', 'errors'):
            self.assertIn(key, result, f'Missing key: {key}')
        self.assertIsInstance(result['errors'], list)

    def test_verify_piper_piper_installed_true(self):
        with patch.object(_mod, '_ensure_piper_model', return_value=_FR_ONNX):
            result = verify_piper()
        self.assertTrue(result['piper_installed'], msg=result['errors'])

    def test_verify_piper_sounddevice_ok_true(self):
        """sounddevice_ok is True when the stub is in sys.modules."""
        with patch.object(_mod, '_ensure_piper_model', return_value=_FR_ONNX):
            result = verify_piper()
        self.assertTrue(result['sounddevice_ok'], msg=result['errors'])


class TestSpeakPiperStreaming(unittest.TestCase):
    """_speak_piper streams audio sentence-by-sentence via sounddevice."""

    def _make_fake_chunk(self, sr=22050, n_samples=None):
        import numpy as np

        n = n_samples if n_samples is not None else sr
        chunk = MagicMock()
        chunk.audio_float_array = np.zeros(n, dtype=np.float32)
        chunk.sample_rate = sr
        return chunk

    def test_sd_play_called_once_per_chunk(self):
        """Each synthesized chunk triggers sounddevice.play(blocking=True)."""
        fake_chunks = [self._make_fake_chunk(), self._make_fake_chunk()]
        fake_voice = MagicMock()
        fake_voice.synthesize.return_value = iter(fake_chunks)

        with patch.object(_mod, '_get_piper_voice', return_value=fake_voice):
            _speak_piper('Bonjour le monde.', 1.0, 1.0, 0.8)

        # _sd_stub.play is the mock sd.play bound inside the module
        self.assertEqual(_sd_stub.play.call_count, len(fake_chunks))
        for call in _sd_stub.play.call_args_list:
            self.assertTrue(
                call.kwargs.get('blocking', False),
                'sd.play must be called with blocking=True for live streaming',
            )
        _sd_stub.play.reset_mock()

    def test_empty_chunk_not_played(self):
        """Chunks with zero samples must not call sd.play."""
        import numpy as np

        empty_chunk = MagicMock()
        empty_chunk.audio_float_array = np.array([], dtype=np.float32)
        empty_chunk.sample_rate = 22050

        fake_voice = MagicMock()
        fake_voice.synthesize.return_value = iter([empty_chunk])

        _sd_stub.play.reset_mock()
        with patch.object(_mod, '_get_piper_voice', return_value=fake_voice):
            _speak_piper('', 1.0, 1.0, 0.8)

        _sd_stub.play.assert_not_called()

    def test_voice_load_error_does_not_raise(self):
        """A voice-load failure must be swallowed, not propagate."""
        _sd_stub.play.reset_mock()
        with patch.object(_mod, '_get_piper_voice', side_effect=RuntimeError('model not found')):
            _speak_piper('Test.', 1.0, 1.0, 0.8)  # must not raise

        _sd_stub.play.assert_not_called()

    def test_synthesis_error_does_not_raise(self):
        """An error during synthesis iteration must be swallowed."""
        fake_voice = MagicMock()
        fake_voice.synthesize.side_effect = RuntimeError('synthesis failed')

        _sd_stub.play.reset_mock()
        with patch.object(_mod, '_get_piper_voice', return_value=fake_voice):
            _speak_piper('Hello.', 1.0, 1.0, 0.8)  # must not raise

        _sd_stub.play.assert_not_called()


if __name__ == '__main__':
    unittest.main()

