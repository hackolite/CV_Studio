#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for VideoWriter on-disk mode."""
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_frame(w=160, h=120):
    return (np.random.rand(h, w, 3) * 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Constants / module-level tests
# ---------------------------------------------------------------------------

def test_write_mode_constants_exist():
    from node.VideoNode.node_video_writer import (
        WRITE_MODE_STANDARD, WRITE_MODE_ON_DISK, WRITE_MODES,
    )
    assert WRITE_MODE_STANDARD in WRITE_MODES
    assert WRITE_MODE_ON_DISK in WRITE_MODES
    assert len(WRITE_MODES) == 2


def test_ondisk_writers_dict_exists():
    from node.VideoNode.node_video_writer import VideoWriterNode
    assert hasattr(VideoWriterNode, '_ondisk_writers_dict')
    assert isinstance(VideoWriterNode._ondisk_writers_dict, dict)


# ---------------------------------------------------------------------------
# PyAVEncoder: include_audio=False (video-only)
# ---------------------------------------------------------------------------

def test_pyavencoder_video_only_writes_file():
    """PyAVEncoder with include_audio=False should write a valid MP4."""
    try:
        from node.VideoNode.av_encoder import PyAVEncoder, _AV_AVAILABLE
    except ImportError:
        pytest.skip("av_encoder module not available")
    if not _AV_AVAILABLE:
        pytest.skip("PyAV not installed")

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        path = f.name
    try:
        encoder = PyAVEncoder(
            output_path=path,
            fps=25.0,
            frame_size=(160, 120),
            codec="libx264",
            include_audio=False,
        )
        for i in range(5):
            encoder.write_video_frame(_make_frame(), pts_ms=i * 40.0)
        encoder.close()
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_pyavencoder_write_audio_raises_when_no_audio_stream():
    """write_audio_chunk must raise SyncError when include_audio=False."""
    try:
        from node.VideoNode.av_encoder import PyAVEncoder, SyncError, _AV_AVAILABLE
    except ImportError:
        pytest.skip("av_encoder module not available")
    if not _AV_AVAILABLE:
        pytest.skip("PyAV not installed")

    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
        path = f.name
    try:
        encoder = PyAVEncoder(
            output_path=path,
            fps=25.0,
            frame_size=(160, 120),
            include_audio=False,
        )
        audio = np.zeros(1024, dtype=np.float32)
        with pytest.raises(SyncError):
            encoder.write_audio_chunk(audio, sample_rate=44100, pts_samples=0)
        encoder.close()
    finally:
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# VideoWriterNode on-disk recording (cv2 path — no PyAV required)
# ---------------------------------------------------------------------------

def test_ondisk_recording_cv2_roundtrip(monkeypatch, tmp_path):
    """On-disk recording must write frames via cv2 and create the output file."""
    import cv2
    from node.VideoNode import node_video_writer as nvw
    from node.VideoNode.node_video_writer import (
        VideoWriterNode, WRITE_MODE_ON_DISK,
    )

    node = VideoWriterNode()
    node._opencv_setting_dict = {
        'process_width': 160,
        'process_height': 120,
        'video_writer_width': 160,
        'video_writer_height': 120,
        'video_writer_fps': 25,
        'video_writer_directory': str(tmp_path),
    }
    tag = '99:VideoWriter'
    node.tag_node_name = tag

    # Stub DPG calls
    ui_state = {
        tag + ':Format': 'MP4',
        tag + ':WriteMode': WRITE_MODE_ON_DISK,
        tag + ':TEXT:ButtonValue': 'Start',
    }
    monkeypatch.setattr(nvw, 'dpg_get_value', lambda t: ui_state.get(t))
    monkeypatch.setattr(nvw, 'dpg_set_value', lambda *_a, **_kw: None)

    _labels = {tag + ':TEXT:ButtonValue': 'Start'}

    class _DPGStub:
        @staticmethod
        def get_item_label(t):
            return _labels.get(t, 'Start')
        @staticmethod
        def set_item_label(t, v):
            _labels[t] = v
        @staticmethod
        def does_item_exist(_t):
            return False

    monkeypatch.setattr(nvw, 'dpg', _DPGStub)

    # Force cv2 path (no PyAVEncoder)
    monkeypatch.setattr(nvw, '_AV_AVAILABLE', False)

    # Press Start
    node._recording_button(None, None, tag)

    assert tag in node._ondisk_writers_dict
    assert tag not in node._video_writer_dict  # standard dict must be empty

    # Feed 3 frames
    frame = _make_frame(160, 120)
    for _ in range(3):
        od = node._ondisk_writers_dict[tag]
        od.write(frame)

    # Press Stop
    _labels[tag + ':TEXT:ButtonValue'] = 'Stop'
    node._recording_button(None, None, tag)

    assert tag not in node._ondisk_writers_dict
    assert tag not in node._video_writer_dict
    # Output file must exist
    mp4s = list(tmp_path.glob('*.mp4'))
    assert len(mp4s) == 1
    assert mp4s[0].stat().st_size > 0


def test_ondisk_mode_skips_audio_collection(monkeypatch, tmp_path):
    """update() must not add audio to _audio_samples_dict in on-disk mode."""
    import cv2
    from node.VideoNode import node_video_writer as nvw
    from node.VideoNode.node_video_writer import (
        VideoWriterNode, WRITE_MODE_ON_DISK,
    )

    node = VideoWriterNode()
    node._opencv_setting_dict = {
        'process_width': 160,
        'process_height': 120,
        'video_writer_width': 160,
        'video_writer_height': 120,
        'video_writer_fps': 25,
        'video_writer_directory': str(tmp_path),
    }
    tag = '42:VideoWriter'
    node.tag_node_name = tag

    # Put a fake cv2 writer into ondisk dict to simulate active recording
    fake_cv2_writer = cv2.VideoWriter()  # closed writer — acts as placeholder
    node._ondisk_writers_dict[tag] = fake_cv2_writer
    node._frame_counter_dict[tag] = 0
    node._recording_metadata_dict[tag] = {
        'final_path': str(tmp_path / 'test.mp4'),
        'temp_path': None,
        'format': 'MP4',
        'fps': 25.0,
        'mode': WRITE_MODE_ON_DISK,
    }

    ui_state = {}
    monkeypatch.setattr(nvw, 'dpg_get_value', lambda t: ui_state.get(t))
    monkeypatch.setattr(nvw, 'dpg_set_value', lambda *_a, **_kw: None)

    class _DPGStub:
        @staticmethod
        def does_item_exist(_): return False
        @staticmethod
        def configure_item(*_a, **_kw): pass
        @staticmethod
        def set_value(*_a, **_kw): pass
        @staticmethod
        def get_item_label(_): return 'Stop'
        @staticmethod
        def set_item_label(*_a, **_kw): pass

    monkeypatch.setattr(nvw, 'dpg', _DPGStub)

    audio_chunk = {'data': np.zeros(1024, dtype=np.float32), 'sample_rate': 44100,
                   'chunk_index': 0}
    frame = _make_frame(160, 120)

    node.update(
        node_id=42,
        connection_list=[['42:FakeSource:IMAGE:Output01']],
        node_image_dict={'42:FakeSource': frame},
        node_result_dict={},
        node_audio_dict={'42:FakeSource': audio_chunk},
    )

    # No audio_samples_dict entry must have been created for on-disk mode
    assert tag not in node._audio_samples_dict

    # Clean up
    node._ondisk_writers_dict.pop(tag, None)
    node._frame_counter_dict.pop(tag, None)
    node._recording_metadata_dict.pop(tag, None)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
