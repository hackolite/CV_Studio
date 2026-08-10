#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Speech2Text node — live microphone transcription via Vosk.

Architecture overview
---------------------
Vosk was selected as the speech-recognition backend for several compelling
reasons:

  • *Fully offline* — the entire inference graph runs on-device; no audio
    data is transmitted to any cloud service, preserving privacy and
    guaranteeing operation in air-gapped environments.
  • *Low latency* — Vosk uses a streaming recogniser that emits partial
    results in real time and a final result as soon as the speaker pauses,
    enabling near-instant prompt delivery to the downstream agent.
  • *Lightweight footprint* — small models (≈ 40 MB for French) run
    comfortably on CPU, leaving GPU resources free for the vision pipeline.
  • *Broad language support* — dozens of pre-trained models are available
    at https://alphacephei.com/vosk/models, configurable via the
    ``VOSK_MODEL_PATH`` environment variable.

Data flow
---------
Microphone → SoundDevice (16 kHz, mono, int16) → Vosk KaldiRecogniser
  → final text → JSON output ``{"prompt": "<transcribed text>"}``

The JSON output is compatible with the AgentNode prompt input: connect the
Speech2Text output to any AgentNode JSON input slot.  The agent will find
the ``prompt`` key inside the aggregated ``input_N`` dict and can use it as
the user instruction driving ambiance, security, or comfort decisions.
"""

import json
import logging
import os
import pathlib
import queue
import threading
import urllib.request
import zipfile
import tempfile

import dearpygui.dearpygui as dpg

from node_editor.util import dpg_set_value
from node.basenode import Node as BaseNode

_LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vosk model — small French model bundled by default.
# Override model directory/name/URL with env vars:
#   VOSK_MODEL_PATH — path to an already-extracted model directory (highest priority)
#   VOSK_MODEL_NAME — model archive name without .zip (default: vosk-model-small-fr-0.22)
#   VOSK_MODEL_URL  — full URL to the model zip archive (overrides VOSK_MODEL_NAME)
# ---------------------------------------------------------------------------
_VOSK_MODELS_DIR = pathlib.Path(
    os.environ.get(
        'VOSK_MODELS_DIR',
        pathlib.Path.home() / '.local' / 'share' / 'vosk' / 'models',
    )
)
_DEFAULT_MODEL_NAME = 'vosk-model-small-fr-0.22'
_FR_MODEL_NAME = os.environ.get('VOSK_MODEL_NAME', _DEFAULT_MODEL_NAME)
_FR_MODEL_DIR  = _VOSK_MODELS_DIR / _FR_MODEL_NAME
_DEFAULT_MODEL_URL = f'https://alphacephei.com/vosk/models/{_FR_MODEL_NAME}.zip'
_FR_MODEL_URL  = os.environ.get('VOSK_MODEL_URL', _DEFAULT_MODEL_URL)

# Audio parameters — Vosk expects 16 kHz mono int16.
_SAMPLE_RATE = 16000
_BLOCK_SIZE  = 8000   # ~500 ms per block

# ---------------------------------------------------------------------------
# Model download helper
# ---------------------------------------------------------------------------

def _ensure_vosk_model() -> pathlib.Path:
    """Return path to the Vosk model directory, downloading/extracting if needed."""
    _VOSK_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if _FR_MODEL_DIR.exists():
        return _FR_MODEL_DIR

    _LOG.info('Downloading Vosk model: %s', _FR_MODEL_URL)
    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix='.zip', dir=_VOSK_MODELS_DIR)
        os.close(tmp_fd)
        urllib.request.urlretrieve(_FR_MODEL_URL, tmp_path)
        with zipfile.ZipFile(tmp_path, 'r') as zf:
            zf.extractall(_VOSK_MODELS_DIR)
        pathlib.Path(tmp_path).unlink(missing_ok=True)
    except Exception as exc:
        pathlib.Path(tmp_path).unlink(missing_ok=True)
        _LOG.error('Failed to download Vosk model: %s', exc)
        raise RuntimeError(f'Cannot download Vosk model: {exc}') from exc

    return _FR_MODEL_DIR


# ---------------------------------------------------------------------------
# Background recording / recognition thread
# ---------------------------------------------------------------------------

class _RecognitionWorker:
    """Runs a Vosk KaldiRecogniser on a background thread.

    Partial results are discarded; only *final* results (triggered by a pause
    in speech) are placed on ``result_queue`` as plain strings.
    """

    def __init__(self, result_queue: queue.Queue):
        self._q = result_queue
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        try:
            import sounddevice as sd
            from vosk import Model, KaldiRecognizer
        except ImportError as exc:
            _LOG.error('[Speech2Text] Missing dependency: %s', exc)
            return

        try:
            model_path = os.environ.get('VOSK_MODEL_PATH', str(_ensure_vosk_model()))
            model = Model(model_path)
            rec = KaldiRecognizer(model, _SAMPLE_RATE)
        except Exception as exc:
            _LOG.error('[Speech2Text] Could not load Vosk model: %s', exc)
            return

        _LOG.info('[Speech2Text] Listening on default microphone (16 kHz mono)…')
        try:
            with sd.RawInputStream(
                samplerate=_SAMPLE_RATE,
                blocksize=_BLOCK_SIZE,
                dtype='int16',
                channels=1,
            ) as stream:
                while not self._stop.is_set():
                    data, _ = stream.read(_BLOCK_SIZE)
                    if rec.AcceptWaveform(bytes(data)):
                        result = json.loads(rec.Result())
                        text = result.get('text', '').strip()
                        if text:
                            self._q.put(text)
        except Exception as exc:
            _LOG.error('[Speech2Text] Recording error: %s', exc)


# ---------------------------------------------------------------------------
# DearPyGui node
# ---------------------------------------------------------------------------

class FactoryNode:
    node_label = 'Speech2Text'
    node_tag = 'Speech2Text'

    def __init__(self):
        pass

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        node = Node()
        return node.add_node(parent, node_id, pos, opencv_setting_dict, callback)


class Node(BaseNode):
    _ver = '0.0.1'
    node_label = 'Speech2Text'
    node_tag = 'Speech2Text'

    def __init__(self):
        self._opencv_setting_dict = {}
        self._last_output = {}
        self._result_queue: queue.Queue = queue.Queue()
        self._worker = _RecognitionWorker(self._result_queue)

    def add_node(self, parent, node_id, pos=None, opencv_setting_dict=None, callback=None):
        if pos is None:
            pos = [0, 0]
        self._opencv_setting_dict = opencv_setting_dict or {}
        w = self._opencv_setting_dict.get('process_width', 280)

        tag = str(node_id) + ':' + self.node_tag
        self.tag_node_name = tag

        tag_out     = tag + ':' + self.TYPE_JSON + ':Output01'
        tag_out_val = tag + ':' + self.TYPE_JSON + ':Output01Value'
        tag_in_bool      = tag + ':' + self.TYPE_JSON + ':InputEnable'
        tag_in_bool_val  = tag + ':' + self.TYPE_JSON + ':InputEnableValue'

        self._tag_transcript = tag + ':TranscriptValue'
        self._tag_status     = tag + ':StatusValue'
        self._tag_out_val    = tag_out_val
        self._tag_in_bool    = tag_in_bool

        with dpg.node(tag=tag, parent=parent, label=self.node_label, pos=pos):

            # ── Boolean enable input ──────────────────────────────────────
            with dpg.node_attribute(
                tag=tag_in_bool,
                attribute_type=dpg.mvNode_Attr_Input,
            ):
                dpg.add_text(tag=tag_in_bool_val, default_value='Enable (boolean JSON)')

            # ── Controls ──────────────────────────────────────────────────
            with dpg.node_attribute(
                tag=tag + ':ControlAttr',
                attribute_type=dpg.mvNode_Attr_Static,
            ):
                dpg.add_text(tag=self._tag_status, default_value='[*] idle')
                dpg.add_text(default_value='Transcript')
                dpg.add_input_text(
                    tag=self._tag_transcript,
                    default_value='',
                    multiline=True,
                    width=w,
                    height=80,
                    readonly=True,
                )

            # ── JSON output ───────────────────────────────────────────────
            with dpg.node_attribute(tag=tag_out, attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text(tag=tag_out_val, default_value='JSON (prompt)')

        return self

    def update(self, node_id, connection_list, node_image_dict, node_result_dict, node_audio_dict):
        # Read boolean enable input from connected source (e.g., Text2Speech idle output).
        # Default to True (listen) when no boolean input is connected.
        enable_listen = True
        for conn in connection_list:
            if conn[1] == self._tag_in_bool:
                src_key = ':'.join(conn[0].split(':')[:2])
                json_data = node_result_dict.get(src_key)
                if isinstance(json_data, dict):
                    enable_listen = bool(json_data.get('enabled', True))
                break

        if enable_listen:
            self._worker.start()
            try:
                dpg_set_value(self._tag_status, '[>] listening…')
            except (SystemError, AttributeError):
                pass
        else:
            self._worker.stop()
            try:
                dpg_set_value(self._tag_status, '[~] muted (TTS speaking)')
            except (SystemError, AttributeError):
                pass

        # Drain the result queue — keep only the most recent utterance.
        latest_text = None
        while True:
            try:
                latest_text = self._result_queue.get_nowait()
            except queue.Empty:
                break

        if latest_text is not None:
            self._last_output = {'prompt': latest_text}
            try:
                dpg_set_value(self._tag_transcript, latest_text)
                dpg_set_value(self._tag_status, '[✓] captured')
            except (SystemError, AttributeError):
                pass

        return {'image': None, 'json': self._last_output, 'audio': None}

    def close(self, node_id):
        self._worker.stop()

    def get_setting_dict(self, node_id):
        tag = self.tag_node_name
        pos = dpg.get_item_pos(tag)
        d = {'ver': self._ver, 'pos': pos}
        return d

    def set_setting_dict(self, node_id, setting_dict):
        pass
