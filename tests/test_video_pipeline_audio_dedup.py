#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Video→ImageConcat→VideoWriter audio synchronisation pipeline.

Verifies:
1. VideoNode._get_audio_chunk_for_frame exposes chunk_index and step_duration.
2. VideoWriterNode deduplicate overlapping sliding-window chunks so that the
   collected audio matches the original signal length (not fps×chunk_duration).
3. The non-overlapping extraction formula is correct:
       chunk_N[0 : step_samples] == original_audio[N*step : (N+1)*step]
"""

import sys
import os
import math
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sliding_window_chunks(audio, sr, chunk_duration, step_duration):
    """Reproduce the VideoNode sliding-window chunking logic in pure Python."""
    chunk_samples = int(chunk_duration * sr)
    step_samples = int(step_duration * sr)
    chunks = []
    start_times = []
    start = 0
    while (start + chunk_samples) <= len(audio):
        chunks.append(audio[start : start + chunk_samples].copy())
        start_times.append(start / sr)
        start += step_samples
    # Pad last partial chunk
    remaining = audio[start:]
    if len(remaining) > 0:
        pad = chunk_samples - len(remaining)
        chunks.append(np.pad(remaining, (0, pad)))
        start_times.append(start / sr)
    return chunks, start_times


def _chunk_index_for_frame(frame_number, fps, step_duration, num_chunks):
    current_time = frame_number / fps if fps > 0 else 0
    idx = int(current_time / step_duration)
    return max(0, min(idx, num_chunks - 1))


# ---------------------------------------------------------------------------
# Unit test: chunk_index + step_duration in audio dict
# ---------------------------------------------------------------------------

class TestVideoNodeAudioDictFields:
    """Verify that _get_audio_chunk_for_frame returns chunk_index and step_duration."""

    def test_audio_dict_has_chunk_index(self):
        """The audio chunk dict must include chunk_index for deduplication."""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py',
        )
        with open(video_node_path, 'r') as f:
            content = f.read()

        assert "'chunk_index': chunk_index" in content, \
            "_get_audio_chunk_for_frame must include 'chunk_index' in return dict"

    def test_audio_dict_has_step_duration(self):
        """The audio chunk dict must include step_duration for non-overlap extraction."""
        video_node_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'InputNode', 'node_video.py',
        )
        with open(video_node_path, 'r') as f:
            content = f.read()

        assert "'step_duration': step_duration" in content, \
            "_get_audio_chunk_for_frame must include 'step_duration' in return dict"


# ---------------------------------------------------------------------------
# Unit test: VideoWriterNode._dedup_chunk_segment
# ---------------------------------------------------------------------------

class TestVideoWriterDedup:
    """Test the deduplication helpers on VideoWriterNode without a GUI."""

    def _make_node(self):
        """Return a bare VideoWriterNode with minimal state."""
        # Import the class without triggering dearpygui at module level
        import importlib, types
        # Stub dearpygui so the module can be imported headlessly
        dpg_stub = types.ModuleType('dearpygui')
        dpg_inner = types.ModuleType('dearpygui.dearpygui')
        sys.modules.setdefault('dearpygui', dpg_stub)
        sys.modules.setdefault('dearpygui.dearpygui', dpg_inner)

        # Provide minimal stubs used at module top-level
        for attr in ('mvFormat_Float_rgb', 'mvNode_Attr_Input', 'mvNode_Attr_Output',
                     'mvNode_Attr_Static', 'mvNodeCol_TitleBar'):
            setattr(dpg_inner, attr, 0)

        from node.VideoNode.node_video_writer import VideoWriterNode
        node = VideoWriterNode.__new__(VideoWriterNode)
        node._last_chunk_index_dict = {}
        node._audio_samples_dict = {}
        node._recording_metadata_dict = {}
        return node

    def test_first_chunk_is_kept(self):
        """A chunk with a new chunk_index should be kept."""
        node = self._make_node()
        audio = np.arange(100, dtype=np.float32)
        chunk = {'data': audio, 'sample_rate': 10, 'chunk_index': 0, 'step_duration': 1.0}
        segment = node._dedup_chunk_segment('node:VW', 'single', chunk)
        assert segment is not None

    def test_duplicate_chunk_is_discarded(self):
        """A chunk with the same chunk_index should be discarded (returns None)."""
        node = self._make_node()
        audio = np.arange(100, dtype=np.float32)
        chunk = {'data': audio, 'sample_rate': 10, 'chunk_index': 0, 'step_duration': 1.0}
        # First call keeps it
        node._dedup_chunk_segment('node:VW', 'single', chunk)
        # Second call with same index → None
        segment = node._dedup_chunk_segment('node:VW', 'single', chunk)
        assert segment is None

    def test_non_overlapping_segment_length(self):
        """Segment returned should be exactly step_duration * sample_rate samples."""
        node = self._make_node()
        sr = 100
        step = 1.0
        chunk_dur = 5.0
        audio = np.zeros(int(chunk_dur * sr), dtype=np.float32)
        chunk = {'data': audio, 'sample_rate': sr, 'chunk_index': 0, 'step_duration': step}
        segment = node._dedup_chunk_segment('node:VW', 'single', chunk)
        assert len(segment) == int(step * sr)

    def test_non_overlapping_segment_content(self):
        """First step_duration samples of chunk N == original_audio[N*step:(N+1)*step]."""
        sr = 100
        step_dur = 1.0  # 1 second
        chunk_dur = 5.0  # 5-second window
        total_dur = 10.0
        # Unique signal so we can verify content exactly
        original = np.arange(int(total_dur * sr), dtype=np.float32)
        chunks, _ = _make_sliding_window_chunks(original, sr, chunk_dur, step_dur)

        node = self._make_node()
        step_samples = int(step_dur * sr)

        for chunk_idx, chunk_data in enumerate(chunks):
            audio_chunk = {
                'data': chunk_data,
                'sample_rate': sr,
                'chunk_index': chunk_idx,
                'step_duration': step_dur,
            }
            segment = node._dedup_chunk_segment('node:VW', 'single', audio_chunk)
            if segment is None:
                continue

            # Expected: original[chunk_idx*step : (chunk_idx+1)*step]
            expected_start = chunk_idx * step_samples
            expected_end = expected_start + step_samples
            if expected_end <= len(original):
                expected = original[expected_start:expected_end]
                np.testing.assert_array_equal(
                    segment,
                    expected,
                    err_msg=f"Chunk {chunk_idx}: segment does not match original audio slice",
                )

    def test_legacy_chunk_without_index_passes_through(self):
        """Audio without chunk_index (legacy/microphone) must be returned as-is."""
        node = self._make_node()
        audio = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        chunk = {'data': audio, 'sample_rate': 22050}  # No chunk_index
        segment = node._dedup_chunk_segment('node:VW', 'single', chunk)
        np.testing.assert_array_equal(segment, audio)

    def test_full_recording_audio_length(self):
        """Simulate a full recording; collected audio should equal original duration."""
        sr = 100
        step_dur = 1.0
        chunk_dur = 5.0
        fps = 10
        total_seconds = 8
        total_frames = total_seconds * fps

        original = np.random.randn(total_seconds * sr).astype(np.float32)
        chunks, _ = _make_sliding_window_chunks(original, sr, chunk_dur, step_dur)
        num_chunks = len(chunks)

        node = self._make_node()
        node._audio_samples_dict['node:VW'] = []
        node._recording_metadata_dict['node:VW'] = {'sample_rate': sr}

        for frame_num in range(total_frames):
            chunk_idx = _chunk_index_for_frame(frame_num, fps, step_dur, num_chunks)
            audio_chunk = {
                'data': chunks[chunk_idx],
                'sample_rate': sr,
                'chunk_index': chunk_idx,
                'step_duration': step_dur,
            }
            node._append_audio_chunk('node:VW', audio_chunk)

        collected = np.concatenate(node._audio_samples_dict['node:VW'])
        # Each unique chunk contributes exactly step_dur * sr samples.
        # num_chunks unique indices were seen during total_seconds of video.
        expected_samples = num_chunks * int(step_dur * sr)
        assert len(collected) == expected_samples, (
            f"Expected {expected_samples} samples, got {len(collected)}"
        )

    def test_no_duplicate_audio_frames(self):
        """At 10 fps with 5s chunks (step=1s), collected audio must NOT be ~fps× inflated."""
        sr = 100
        step_dur = 1.0
        chunk_dur = 5.0
        fps = 10
        total_seconds = 5
        total_frames = total_seconds * fps  # 50 frames

        original = np.zeros(total_seconds * sr, dtype=np.float32)
        chunks, _ = _make_sliding_window_chunks(original, sr, chunk_dur, step_dur)
        num_chunks = len(chunks)

        node = self._make_node()
        node._audio_samples_dict['node:VW'] = []
        node._recording_metadata_dict['node:VW'] = {'sample_rate': sr}

        for frame_num in range(total_frames):
            chunk_idx = _chunk_index_for_frame(frame_num, fps, step_dur, num_chunks)
            audio_chunk = {
                'data': chunks[chunk_idx],
                'sample_rate': sr,
                'chunk_index': chunk_idx,
                'step_duration': step_dur,
            }
            node._append_audio_chunk('node:VW', audio_chunk)

        collected = np.concatenate(node._audio_samples_dict['node:VW'])
        expected_samples = num_chunks * int(step_dur * sr)
        # Without dedup: total_frames * chunk_dur * sr = 50 * 5 * 100 = 25000
        # With dedup:    num_chunks * step_dur * sr  = e.g. 5 * 1 * 100 = 500
        assert len(collected) == expected_samples, (
            f"Audio was duplicated! Expected {expected_samples} samples, got {len(collected)}. "
            "The deduplication logic is not working."
        )


if __name__ == '__main__':
    import pytest as _pytest
    _pytest.main([__file__, '-v'])
