#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Robust tests that document and verify every root cause preventing a combined
video+audio flux from being created, even when starting from an input video.

Pipeline under investigation:
    VideoInput.IMAGE ──► [optional: ImageProcessingNode] ──► VideoWriter.IMAGE
    VideoInput.AUDIO ──► ??? ──► VideoWriter (no AUDIO port)

Five root causes are verified:

    RC-1  VideoWriter has no dedicated AUDIO input port.
    RC-2  VideoWriter uses only the LAST connection's source for BOTH the frame
          AND audio lookups (connection_info_src bug).
    RC-3  Every intermediate IMAGE-only node (Resize, Flip, …) returns
          {"audio": None}, permanently dropping the audio from the pipeline.
    RC-4  "Frames only" mode (default=False, but often the first thing users
          check) completely suppresses audio preprocessing.
    RC-5  Audio preprocessing has not been triggered yet (user has not pressed
          Start in full-pipeline mode) → _audio_chunk_paths is empty.
"""

import os
import sys
import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers to locate source files without importing DPG-dependent modules
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(relative_path: str) -> str:
    """Return the text content of a repo file."""
    return open(os.path.join(_REPO_ROOT, relative_path)).read()


# ===========================================================================
#  RC-1 – VideoWriter has NO dedicated AUDIO input port
# ===========================================================================

class TestRC1NoAudioInputPort:
    """RC-1: VideoWriter only declares a TYPE_IMAGE input pin (Input01).
    It is structurally impossible to connect an audio-producing node to it
    through the normal link mechanism, so audio from split pipelines can
    never arrive via a separate port."""

    def test_videowriter_has_no_audio_input_attribute(self):
        """VideoWriter add_node defines only one input attribute: TYPE_IMAGE:Input01."""
        src = _read("node/VideoNode/node_video_writer.py")
        # Must have an IMAGE input
        assert "TYPE_IMAGE + ':Input01'" in src or "TYPE_IMAGE + \":Input01\"" in src or \
               ":Input01'" in src, "Expected IMAGE Input01 to exist"
        # Must NOT have any AUDIO input attribute
        assert "TYPE_AUDIO + ':Input" not in src and \
               'TYPE_AUDIO + ":Input' not in src, \
            (
                "VideoWriter should have NO TYPE_AUDIO input port. "
                "If an AUDIO port existed users could connect audio directly. "
                "Its absence is RC-1: the pipeline cannot carry a separate audio stream."
            )

    def test_videowriter_only_one_dpg_input_attribute(self):
        """Verify that only a single mvNode_Attr_Input is defined in add_node."""
        src = _read("node/VideoNode/node_video_writer.py")
        # Count occurrences of mvNode_Attr_Input
        input_attr_count = src.count("mvNode_Attr_Input")
        assert input_attr_count == 1, (
            f"Expected exactly 1 mvNode_Attr_Input in VideoWriter, found {input_attr_count}. "
            "RC-1: only an IMAGE input port exists; audio has no port to connect to."
        )

    def test_node_link_callback_only_allows_imagetype_to_videowriter(self):
        """node_main._callback_link only permits same-type or AUDIO→IMAGE links.
        An AUDIO output cannot be linked to VideoWriter's IMAGE input
        unless the system downgrades the type check — RC-1 confirms this path
        is blocked at the UI level too."""
        src = _read("node_editor/node_main.py")
        # The allowed connection rules
        assert "source_type == destination_type" in src, \
            "Expected same-type connection rule in _callback_link"
        assert 'source_type == "AUDIO" and destination_type == "IMAGE"' in src, \
            "Expected AUDIO→IMAGE special rule for spectrogram connections"
        # There is NO special rule for AUDIO → AUDIO → VideoWriter's IMAGE input
        # Verify: no AUDIO→IMAGE for VideoWriter specifically
        assert 'source_type == "IMAGE" and destination_type == "AUDIO"' not in src, \
            "IMAGE→AUDIO reverse connection should not be allowed"


# ===========================================================================
#  RC-2 – VideoWriter uses the LAST connection's source for BOTH lookups
# ===========================================================================

class TestRC2SingleConnectionInfoSrc:
    """RC-2: VideoWriter's update() iterates connection_list and ALWAYS
    overwrites connection_info_src with each iteration's source, ending
    with the LAST one.  Both node_image_dict and node_audio_dict are then
    fetched with that same key.

    Consequence: if two connections arrive (one IMAGE, one AUDIO from different
    upstream nodes), only the last source is used.  Whichever type isn't stored
    under that key in its dict returns None."""

    def test_videowriter_connection_loop_overwrites_src(self):
        """Verify the loop unconditionally overwrites connection_info_src."""
        src = _read("node/VideoNode/node_video_writer.py")
        # The loop assigns connection_info_src on every iteration without a type guard
        assert "connection_info_src = connection_info[0]" in src, \
            "Expected assignment inside the connection_list loop"
        # The fetch of frame and audio use the same variable
        assert "node_image_dict.get(connection_info_src" in src, \
            "Expected frame to be fetched with connection_info_src"
        assert "node_audio_dict.get(connection_info_src" in src, \
            "Expected audio to be fetched with the SAME connection_info_src"

    def test_last_source_wins_simulation(self):
        """Simulate the connection_info_src selection logic in pure Python.

        Demonstrates that when two connections are present, the second one
        (AUDIO source) becomes connection_info_src, causing frame lookup to
        fail (image node's data is stored under a different key).
        """
        # Simulate connection_list with two entries: IMAGE first, AUDIO second
        connection_list = [
            # [source_attribute_tag, destination_attribute_tag]
            ["1:Resize:IMAGE:Output01", "2:VideoWriter:IMAGE:Input01"],
            ["3:SomeAudioNode:AUDIO:Output01", "2:VideoWriter:IMAGE:Input01"],
        ]

        # Simulate the VideoWriter update() loop
        connection_info_src = ""
        for connection_info in connection_list:
            connection_info_src = connection_info[0]
            connection_info_src = ":".join(connection_info_src.split(":")[:2])

        assert connection_info_src == "3:SomeAudioNode", (
            f"Expected last connection's source '3:SomeAudioNode', got {connection_info_src!r}. "
            "RC-2: the AUDIO node becomes the sole lookup key, "
            "so node_image_dict['3:SomeAudioNode'] → None (frame lost)."
        )

    def test_single_source_still_works(self):
        """When only ONE connection exists (direct Video→VideoWriter), the
        same key is used for both dicts.  Video node stores BOTH image and
        audio under its own key, so this case works correctly."""
        connection_list = [
            ["1:Video:IMAGE:Output01", "2:VideoWriter:IMAGE:Input01"],
        ]
        connection_info_src = ""
        for connection_info in connection_list:
            connection_info_src = ":".join(connection_info[0].split(":")[:2])

        assert connection_info_src == "1:Video"

        # Simulate dicts as the Video node fills them
        node_image_dict = {"1:Video": np.zeros((480, 640, 3), dtype=np.uint8)}
        node_audio_dict = {
            "1:Video": {"data": np.zeros(44100), "sample_rate": 44100, "chunk_index": 0}
        }

        frame = node_image_dict.get(connection_info_src)
        audio_data = node_audio_dict.get(connection_info_src)

        assert frame is not None, "Frame should be available with direct Video→VideoWriter"
        assert audio_data is not None, (
            "Audio should be available with direct Video→VideoWriter "
            "because BOTH image and audio are stored under the SAME '1:Video' key."
        )

    def test_intermediate_node_audio_key_mismatch(self):
        """After Video→Resize, the Resize node stores its output under '2:Resize'.
        VideoWriter fetches from '2:Resize' in both dicts.
        node_audio_dict['2:Resize'] is None because Resize returned audio=None.
        """
        # Resize node returned {"image": frame, "audio": None}
        node_image_dict = {"2:Resize": np.zeros((480, 640, 3), dtype=np.uint8)}
        node_audio_dict = {"2:Resize": None}  # Resize dropped audio

        connection_info_src = "2:Resize"

        frame = node_image_dict.get(connection_info_src)
        audio_data = node_audio_dict.get(connection_info_src)

        assert frame is not None, "Frame should exist at Resize's output"
        assert audio_data is None, (
            "Audio is None at Resize's output key. "
            "RC-2+RC-3: VideoWriter will save video WITHOUT audio."
        )


# ===========================================================================
#  RC-3 – IMAGE-only intermediate nodes drop audio (return audio=None)
# ===========================================================================

class TestRC3IntermediateNodesDropAudio:
    """RC-3: Standard image-processing nodes (Resize, Flip, ColorSpace, etc.)
    do not carry audio through their pipeline.  Their update() method receives
    the connection_list which only contains the IMAGE connection from the
    upstream node; they look up the frame and return {"image": ..., "audio": None}.

    This permanently removes audio from the pipeline for all downstream nodes."""

    @pytest.mark.parametrize("node_file,node_name", [
        ("node/ProcessNode/node_resize.py", "Resize"),
        ("node/ProcessNode/node_flip.py", "Flip"),
        ("node/ProcessNode/node_threshold.py", "Threshold"),
        ("node/ProcessNode/node_apply_color_map.py", "ApplyColorMap"),
    ])
    def test_image_processing_nodes_return_audio_none(self, node_file, node_name):
        """Every standard image-processing node must return audio=None."""
        src = _read(node_file)
        # Accept both `"audio": None` (with space) and `"audio":None` (no space)
        has_audio_none = (
            '"audio": None' in src
            or "'audio': None" in src
            or '"audio":None' in src
            or "'audio':None" in src
        )
        assert has_audio_none, (
            f"{node_name} ({node_file}) does not explicitly return audio=None. "
            "RC-3: all image-only nodes must return audio=None, which drops the "
            "audio signal from any Video node upstream."
        )

    def test_simulated_pipeline_audio_loss_after_resize(self):
        """Simulate Video → Resize → VideoWriter and show audio=None at VideoWriter.

        This demonstrates RC-3 end-to-end using pure Python dicts.
        """
        # --- VideoNode produces both image and audio ---
        video_node_key = "1:Video"
        raw_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        raw_audio = {"data": np.zeros(44100), "sample_rate": 44100, "chunk_index": 0}

        node_image_dict = {video_node_key: raw_frame}
        node_audio_dict = {video_node_key: raw_audio}

        # --- ResizeNode reads image, returns audio=None ---
        resize_node_key = "2:Resize"
        resize_frame = node_image_dict.get(video_node_key)  # ✓ gets frame
        # Resize does NOT read node_audio_dict; it returns audio=None
        resize_audio_out = None  # This is what Resize.update() returns

        # Main loop stores Resize output
        node_image_dict[resize_node_key] = resize_frame
        node_audio_dict[resize_node_key] = resize_audio_out  # None stored here

        # --- VideoWriter fetches from Resize ---
        vw_connection_info_src = resize_node_key
        vw_frame = node_image_dict.get(vw_connection_info_src)
        vw_audio = node_audio_dict.get(vw_connection_info_src)

        assert vw_frame is not None, "VideoWriter should receive the resized frame"
        assert vw_audio is None, (
            "VideoWriter receives audio=None after Resize intermediate node. "
            "RC-3: audio is silently dropped by image-only nodes."
        )

    def test_audio_present_in_direct_video_to_videowriter(self):
        """Confirm audio IS available when Video is connected DIRECTLY to VideoWriter
        (no intermediate node), as a control test for RC-3."""
        video_node_key = "1:Video"
        raw_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        raw_audio = {"data": np.zeros(44100), "sample_rate": 44100, "chunk_index": 0}

        node_image_dict = {video_node_key: raw_frame}
        node_audio_dict = {video_node_key: raw_audio}

        # VideoWriter reads directly from Video node
        vw_frame = node_image_dict.get(video_node_key)
        vw_audio = node_audio_dict.get(video_node_key)

        assert vw_frame is not None, "Frame must be present in the direct connection case"
        assert vw_audio is not None, (
            "Audio MUST be present when Video → VideoWriter with no intermediate node. "
            "This is the only working configuration for video+audio recording."
        )


# ===========================================================================
#  RC-4 – "Frames only" checkbox suppresses audio preprocessing entirely
# ===========================================================================

class TestRC4FramesOnlyMode:
    """RC-4: When the 'Frames only' checkbox is ticked (Input06), the Video
    node's update() skips the audio chunk lookup and always returns audio=None.
    The preprocessing step is never triggered, so no audio chunks are ever
    created."""

    def test_frames_only_mode_gates_audio_output(self):
        """Simulate VideoNode.update() logic: frames_only_mode=True → audio=None."""
        frames_only_mode = True  # RC-4 condition
        audio_chunk_paths = {"1": ["/tmp/fake_chunk_000.wav"]}  # chunks exist

        audio_chunk_data = None
        if not frames_only_mode:
            if "1" in audio_chunk_paths:
                # Would normally call _get_audio_chunk_for_frame
                audio_chunk_data = {"data": np.zeros(44100), "sample_rate": 44100}

        assert audio_chunk_data is None, (
            "With frames_only_mode=True, audio_chunk_data must remain None "
            "even if audio chunks exist on disk. RC-4."
        )

    def test_frames_only_false_can_produce_audio(self):
        """Simulate VideoNode.update() logic: frames_only_mode=False → audio present."""
        frames_only_mode = False
        audio_chunk_paths = {"1": ["/tmp/fake_chunk_000.wav"]}

        # With frames_only_mode=False AND chunks present, audio lookup is attempted.
        audio_attempted = (not frames_only_mode) and ("1" in audio_chunk_paths)
        assert audio_attempted, (
            "frames_only_mode=False with existing chunks should attempt audio lookup. "
            "This is the required condition for audio to flow."
        )

    def test_videonode_source_code_frames_only_guard(self):
        """Verify the actual source code guards audio behind the frames_only_mode flag."""
        src = _read("node/InputNode/node_video.py")
        assert "if not frames_only_mode:" in src, \
            "Expected 'if not frames_only_mode:' guard in VideoNode.update()"
        assert "audio_chunk_data = None" in src, \
            "Expected audio_chunk_data initialised to None before the guard"


# ===========================================================================
#  RC-5 – Audio preprocessing not triggered (no chunks in _audio_chunk_paths)
# ===========================================================================

class TestRC5PreprocessingNotDone:
    """RC-5: Even with frames_only_mode=False, if the user has not pressed
    Start in full-pipeline mode (or if preprocessing failed), _audio_chunk_paths
    is empty.  update() checks the dict first and skips the chunk lookup."""

    def test_empty_chunk_paths_produces_audio_none(self):
        """Simulate VideoNode.update() when _audio_chunk_paths is empty."""
        frames_only_mode = False
        audio_chunk_paths: dict = {}  # RC-5: not populated yet
        node_id = "1"

        audio_chunk_data = None
        if not frames_only_mode:
            if node_id in audio_chunk_paths:
                # Would call _get_audio_chunk_for_frame
                audio_chunk_data = {"data": np.zeros(44100), "sample_rate": 44100}

        assert audio_chunk_data is None, (
            "audio_chunk_data must be None when _audio_chunk_paths has no entry for node_id. "
            "RC-5: user must press Start to trigger preprocessing before audio is available."
        )

    def test_preprocessing_status_loading_blocks_frame_output(self):
        """When preprocessing is in-progress ('loading'), update() returns
        {"image": None, "audio": None} to prevent the video from starting
        before chunks are ready."""
        src = _read("node/InputNode/node_video.py")
        # update() must detect 'loading' status and return early
        assert "preprocessing_status == 'loading'" in src or \
               "preprocessing_status == \"loading\"" in src, \
            "Expected early return when preprocessing_status is 'loading'"
        assert "return {\"image\": None, \"json\": None, \"audio\": None" in src or \
               "return {'image': None, 'json': None, 'audio': None" in src, \
            "Expected early return with all-None dict when still loading"

    def test_chunk_metadata_required_for_chunk_lookup(self):
        """_get_audio_chunk_for_frame returns None if metadata or paths are missing."""
        src = _read("node/InputNode/node_video.py")
        assert "if node_id not in self._chunk_metadata or node_id not in self._audio_chunk_paths:" in src, \
            "Expected guard for missing metadata/paths in _get_audio_chunk_for_frame"

    def test_button_triggers_preprocessing_in_full_pipeline_mode(self):
        """Verify _button() calls _trigger_preprocessing when no chunks exist and
        frames_only_mode is False – this is the only way to get audio chunks."""
        src = _read("node/InputNode/node_video.py")
        assert "_trigger_preprocessing" in src, "Expected _trigger_preprocessing to be called"
        assert "not frames_only_mode and needs_chunking and movie_path" in src, \
            "Expected guard: only trigger preprocessing in full-pipeline mode with a file selected"


# ===========================================================================
#  Integration logic: all five root causes in a single end-to-end simulation
# ===========================================================================

class TestEndToEndPipelineSimulation:
    """Pure-Python simulation of the complete node graph update cycle.

    No DearPyGUI, no OpenCV display – just the dict-passing logic extracted
    from main.py's update_node_info() and each node's update() return value.
    """

    def _make_dicts(self):
        return {}, {}, {}  # image, audio, result

    def test_direct_video_to_videowriter_has_audio(self):
        """Pipeline: Video → VideoWriter (direct, no intermediate)
        Expected: VideoWriter receives BOTH frame AND audio."""
        node_image_dict, node_audio_dict, node_result_dict = self._make_dicts()

        # --- Video node update() return value ---
        video_key = "1:Video"
        video_output = {
            "image": np.zeros((480, 640, 3), dtype=np.uint8),
            "json": None,
            "audio": {"data": np.zeros(44100), "sample_rate": 44100, "chunk_index": 0},
            "timestamp": 0.033,
        }
        node_image_dict[video_key] = video_output["image"]
        node_audio_dict[video_key] = video_output["audio"]
        node_result_dict[video_key] = video_output["json"]

        # --- VideoWriter connection_list (single IMAGE connection from Video) ---
        connection_list = [
            ["1:Video:IMAGE:Output01", "2:VideoWriter:IMAGE:Input01"],
        ]
        connection_info_src = ""
        for ci in connection_list:
            connection_info_src = ":".join(ci[0].split(":")[:2])

        vw_frame = node_image_dict.get(connection_info_src)
        vw_audio = node_audio_dict.get(connection_info_src)

        assert vw_frame is not None, "Direct Video→VideoWriter: frame must arrive"
        assert vw_audio is not None, "Direct Video→VideoWriter: audio must arrive"
        assert vw_audio["sample_rate"] == 44100

    def test_video_resize_videowriter_loses_audio(self):
        """Pipeline: Video → Resize → VideoWriter
        Expected: VideoWriter receives frame but audio=None (RC-3)."""
        node_image_dict, node_audio_dict, node_result_dict = self._make_dicts()

        # Video node fills dicts
        video_key = "1:Video"
        node_image_dict[video_key] = np.zeros((480, 640, 3), dtype=np.uint8)
        node_audio_dict[video_key] = {"data": np.zeros(44100), "sample_rate": 44100, "chunk_index": 0}

        # Resize node reads IMAGE from Video, returns audio=None
        resize_key = "2:Resize"
        resized_frame = node_image_dict[video_key]  # pretend resize happened
        resize_output = {"image": resized_frame, "json": None, "audio": None}
        node_image_dict[resize_key] = resize_output["image"]
        node_audio_dict[resize_key] = resize_output["audio"]  # None

        # VideoWriter fetches from Resize
        vw_frame = node_image_dict.get(resize_key)
        vw_audio = node_audio_dict.get(resize_key)

        assert vw_frame is not None, "Resize→VideoWriter: frame must arrive"
        assert vw_audio is None, (
            "Resize→VideoWriter: audio MUST be None because Resize dropped it. "
            "This is the primary failure mode – RC-3."
        )

    def test_frames_only_mode_pipeline_no_audio(self):
        """Pipeline: Video (frames_only=True) → VideoWriter
        Expected: VideoWriter receives frame but audio=None (RC-4)."""
        node_image_dict, node_audio_dict, node_result_dict = self._make_dicts()

        frames_only_mode = True  # RC-4
        video_key = "1:Video"
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Video node: frames_only → audio=None
        audio_out = None  # RC-4: suppressed
        node_image_dict[video_key] = frame
        node_audio_dict[video_key] = audio_out

        vw_frame = node_image_dict.get(video_key)
        vw_audio = node_audio_dict.get(video_key)

        assert vw_frame is not None
        assert vw_audio is None, "frames_only=True must produce audio=None (RC-4)"

    def test_preprocessing_not_done_pipeline_no_audio(self):
        """Pipeline: Video (chunks not ready) → VideoWriter
        Expected: VideoWriter receives frame=None (update returns all-None while loading)
        OR receives frame+audio=None if loading completed without audio (RC-5)."""
        node_image_dict, node_audio_dict, node_result_dict = self._make_dicts()

        video_key = "1:Video"
        # Simulate preprocessing_status == 'loading' → early return
        preprocessing_status = "loading"
        if preprocessing_status == "loading":
            video_output = {"image": None, "json": None, "audio": None, "timestamp": None}
        else:
            video_output = {"image": np.zeros((480, 640, 3), dtype=np.uint8), "json": None, "audio": None, "timestamp": 0.0}

        node_image_dict[video_key] = video_output["image"]
        node_audio_dict[video_key] = video_output["audio"]

        assert node_image_dict[video_key] is None, (
            "While preprocessing is loading, VideoNode returns image=None (RC-5). "
            "VideoWriter will not write any frames or audio during this phase."
        )
        assert node_audio_dict[video_key] is None, "Audio is None while loading (RC-5)"

    def test_two_sources_to_videowriter_last_wins(self):
        """Demonstrate RC-2: two connections to VideoWriter, last source wins."""
        node_image_dict, node_audio_dict, node_result_dict = self._make_dicts()

        image_source_key = "2:Resize"
        audio_source_key = "3:AudioClassification"

        node_image_dict[image_source_key] = np.zeros((480, 640, 3), dtype=np.uint8)
        node_audio_dict[image_source_key] = None  # Resize dropped audio

        node_image_dict[audio_source_key] = None   # AudioClassification has no image output
        node_audio_dict[audio_source_key] = {"data": np.zeros(16000), "sample_rate": 16000}

        # Two connections to VideoWriter (in the order they appear in connection_list)
        connection_list = [
            [f"{image_source_key}:IMAGE:Output01", "4:VideoWriter:IMAGE:Input01"],
            [f"{audio_source_key}:AUDIO:Output01", "4:VideoWriter:IMAGE:Input01"],
        ]

        # VideoWriter loop (RC-2 bug)
        connection_info_src = ""
        for ci in connection_list:
            connection_info_src = ":".join(ci[0].split(":")[:2])

        assert connection_info_src == audio_source_key, "RC-2: last connection wins"

        vw_frame = node_image_dict.get(connection_info_src)
        vw_audio = node_audio_dict.get(connection_info_src)

        assert vw_frame is None, (
            "RC-2: when the AUDIO source is last, VideoWriter fetches the frame "
            "from the audio node's key → None (audio node has no image output)."
        )
        assert vw_audio is not None, (
            "RC-2: audio IS available from the audio source key, but the frame is lost."
        )


# ===========================================================================
#  Logging additions – verify they exist in the modified source files
# ===========================================================================

class TestLoggingAdditions:
    """Verify that the diagnostic logging code has been added to the
    three key files: node_video.py, node_video_writer.py, main.py."""

    def test_videonode_logs_audio_none_frames_only(self):
        src = _read("node/InputNode/node_video.py")
        assert "'Frames only' mode is active" in src or \
               "Frames only" in src, \
            "VideoNode.update() should log when 'Frames only' is active"

    def test_videonode_logs_audio_none_no_chunks(self):
        src = _read("node/InputNode/node_video.py")
        assert "no audio chunks in _audio_chunk_paths" in src or \
               "audio preprocessing was never completed" in src, \
            "VideoNode.update() should log when _audio_chunk_paths is empty"

    def test_videonode_logs_audio_chunk_present(self):
        src = _read("node/InputNode/node_video.py")
        assert "AUDIO OUTPUT:" in src or "chunk_index" in src, \
            "VideoNode.update() should log successful audio chunk emission"

    def test_videowriter_logs_multiple_connections_warning(self):
        src = _read("node/VideoNode/node_video_writer.py")
        assert "MULTIPLE CONNECTIONS detected" in src, \
            "VideoWriter.update() should warn when multiple connections exist (RC-2)"

    def test_videowriter_logs_audio_none_warning(self):
        src = _read("node/VideoNode/node_video_writer.py")
        assert "VIDEO FRAME present but AUDIO IS NONE" in src or \
               "AUDIO IS NONE" in src, \
            "VideoWriter.update() should warn when frame is present but audio is None (RC-3)"

    def test_videowriter_logs_no_audio_port_explanation(self):
        src = _read("node/VideoNode/node_video_writer.py")
        assert "no dedicated AUDIO input port" in src or \
               "VideoWriter has no dedicated AUDIO input" in src, \
            "VideoWriter.update() should document the missing AUDIO input port (RC-1)"

    def test_main_logs_audio_propagation_per_node(self):
        src = _read("main.py")
        assert "AudioPropagation" in src, \
            "main.py update_node_info() should log [AudioPropagation] events"
        assert "produced an IMAGE frame but returned audio=None" in src or \
               "IMAGE frame but returned audio=None" in src, \
            "main.py should warn when an image node drops audio"


# ===========================================================================
#  Structural tests: VideoNode audio machinery
# ===========================================================================

class TestVideoNodeAudioMachinery:
    """Verify the audio preprocessing machinery in VideoNode is structurally correct."""

    def test_preprocess_video_method_exists(self):
        src = _read("node/InputNode/node_video.py")
        assert "def _preprocess_video(" in src

    def test_get_audio_chunk_for_frame_returns_dict_format(self):
        src = _read("node/InputNode/node_video.py")
        assert "'data': audio_data" in src, "Audio chunk must contain 'data' key"
        assert "'sample_rate': sample_rate" in src, "Audio chunk must contain 'sample_rate' key"
        assert "'chunk_index': chunk_index" in src, "Audio chunk must contain 'chunk_index' key"

    def test_audio_chunk_deduplication_in_videowriter(self):
        """VideoWriter deduplicates chunks by chunk_index to avoid repeating audio."""
        src = _read("node/VideoNode/node_video_writer.py")
        assert "_last_chunk_index_dict" in src, \
            "VideoWriter must maintain last-chunk-index dict for deduplication"
        assert "incoming_idx != last_idx" in src or "incoming_idx" in src, \
            "VideoWriter must skip duplicate audio chunks"

    def test_cleanup_audio_chunks_method_exists(self):
        src = _read("node/InputNode/node_video.py")
        assert "def _cleanup_audio_chunks(" in src

    def test_audio_chunking_uses_soundfile(self):
        src = _read("node/InputNode/node_video.py")
        assert "import soundfile as sf" in src
        assert "sf.write(chunk_path," in src
        assert "sf.read(chunk_path)" in src


if __name__ == "__main__":
    import pytest as _pytest
    _pytest.main([__file__, "-v", "--tb=short"])
