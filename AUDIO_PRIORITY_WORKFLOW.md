# Audio Priority Workflow Documentation

## Problem Statement (French)

> "vérifie que dans le workflow input/video ----> concat [audio, video] ----> videowriter  
> quand on arrete l'enregistrement on construit d'abord l'audio, en garantissant sa qualité,  
> et ensuite on mélange avec la video. l'audio est prioritaire pour la qualité."

## Translation

"Verify that in the workflow input/video -> concat [audio, video] -> videowriter,  
when we stop recording, we first build the audio, guaranteeing its quality,  
and then we mix it with the video. Audio is priority for quality."

## Implementation Status

✅ **VERIFIED**: The current implementation correctly prioritizes audio quality and builds audio before video merging.

## Audio Priority Workflow

### 1. Recording Stop Trigger

When the user clicks the "Stop" button in VideoWriter node:

**Legacy Mode** (`node_video_writer.py`, lines 1411-1492):
1. Stop button click detected
2. Calculate audio duration from collected samples
3. Determine if more video frames are needed to match audio duration
4. Enter "stopping state" if needed (continue collecting frames, stop collecting audio)
5. When frame count matches audio duration, call `_finalize_recording()`

**Worker Mode** (`video_worker.py`, lines 441-451):
1. Stop signal sent to worker
2. Worker flushes remaining frames and audio
3. Encoder completes and transitions to FLUSHING state
4. Muxer starts merge process

### 2. Audio Building Phase (Priority Step)

**THIS IS WHERE AUDIO GETS PRIORITY**

**Legacy Mode** (`node_video_writer.py`, `_finalize_recording` method, lines 1174-1220):

```python
# Step 1: Release video writer (video file is closed)
self._video_writer_dict[tag_node_name].release()

# Step 2: Process audio samples (AUDIO BUILDS FIRST)
slot_audio_dict = self._audio_samples_dict[tag_node_name]
sorted_slots = sorted(slot_audio_dict.items(), key=lambda x: x[0])

# Step 3: Concatenate audio per slot
audio_samples_list = []
for slot_idx, slot_data in sorted_slots:
    if slot_data['samples']:
        slot_concatenated = np.concatenate(slot_data['samples'])
        audio_samples_list.append(slot_concatenated)

# Step 4: Start merge thread with audio-first workflow
merge_thread = threading.Thread(target=self._async_merge_thread, ...)
```

**Worker Mode** (`video_worker.py`, `_encoder_worker` method, lines 588-597):

```python
# Step 1: Video encoding completes
video_writer.release()
logger.info("Video encoding complete")

# Step 2: Write audio file (AUDIO BUILDS FIRST)
if audio_samples:
    logger.info("Writing audio file")
    full_audio = np.concatenate(audio_samples)
    sf.write(self._temp_audio_path, full_audio, self.sample_rate)
    logger.info("Audio file written")

# Step 3: Signal muxer to start (after audio is ready)
self._set_state(WorkerState.FLUSHING)
```

### 3. Audio File Creation (Quality Guarantee)

**Both Modes** - Audio is written with high quality:

**Method**: `_merge_audio_video_ffmpeg` (`node_video_writer.py`, lines 867-893)

```python
# Step 1: Filter and validate audio samples
valid_samples = [sample for sample in audio_samples 
                if isinstance(sample, np.ndarray) and sample.size > 0]

# Step 2: Concatenate all audio (COMPLETE AUDIO ASSEMBLY)
full_audio = np.concatenate(valid_samples)
total_duration = len(full_audio) / sample_rate

# Step 3: Write audio to WAV file with native sample rate
# NO CONVERSION, NO COMPRESSION - GUARANTEED QUALITY
sf.write(temp_audio_path, full_audio, sample_rate)
```

**Quality Guarantees**:
- ✅ Native sample rate preserved (44100 Hz, 22050 Hz, etc.)
- ✅ No sample rate conversion (prevents quality degradation)
- ✅ WAV format (lossless, uncompressed)
- ✅ Full precision numpy arrays (float32/float64)

### 4. Video Adaptation (Audio Determines Length)

**AUDIO HAS PRIORITY** - Video is adapted to match audio duration:

**Method**: `_adapt_video_to_audio_duration` (`node_video_writer.py`, lines 713-818)

```python
# Step 1: Calculate required video duration from audio
total_audio_samples = sum(len(samples) for samples in audio_samples)
audio_duration = total_audio_samples / sample_rate

# Step 2: Calculate required video frames
required_frames = int(audio_duration * fps)

# Step 3: If video is shorter, duplicate last frame
if frames_to_add > 0:
    for _ in range(frames_to_add):
        out.write(last_frame)  # Duplicate last frame to match audio
```

**This ensures**: Audio duration always determines the final video length.

### 5. Audio/Video Merge (High Quality Settings)

**Final merge** with FFmpeg using high-quality audio parameters:

**Method**: `_merge_audio_video_ffmpeg` (`node_video_writer.py`, lines 926-945)

```python
output_params = {
    'vcodec': vcodec,           # Copy or re-encode (format dependent)
    'acodec': 'aac',            # AAC codec
    'audio_bitrate': '192k',    # HIGH QUALITY (no artifacts)
    'shortest': None,           # Stop when shortest stream ends
    'vsync': 'cfr',             # Constant frame rate
    'avoid_negative_ts': 'make_zero',  # Timestamp alignment
    'loglevel': 'error'
}

output = ffmpeg.output(video_input, audio_input, output_path, **output_params)
ffmpeg.run(output)
```

**Quality Parameters**:
- ✅ `audio_bitrate='192k'`: High quality AAC (prevents compression artifacts)
- ✅ `acodec='aac'`: AAC codec (industry standard for quality)
- ✅ `avoid_negative_ts='make_zero'`: Perfect audio/video synchronization
- ✅ `vsync='cfr'`: Constant frame rate (no drift)

### 6. Stopping State (Audio-First Logic)

When stop button is pressed but not enough video frames exist:

**Method**: `_recording_button` (`node_video_writer.py`, lines 1421-1490)

```python
# Step 1: Count total audio samples
for slot_idx, slot_data in slot_audio_dict.items():
    for audio_chunk in slot_data['samples']:
        total_audio_samples += len(audio_chunk)

# Step 2: Calculate audio duration
audio_duration = total_audio_samples / sample_rate

# Step 3: Calculate required frames FROM AUDIO DURATION
required_frames = int(audio_duration * fps)

# Step 4: Enter stopping state if not enough frames
if current_frames < required_frames:
    self._stopping_state_dict[tag_node_name] = {
        'stopping': True,
        'required_frames': required_frames,  # Based on audio!
        'audio_chunks': total_audio_chunks
    }
    # Stop collecting audio, continue collecting video frames
    # until we have enough frames to match audio duration
```

**Key Point**: Audio collection stops immediately, but collected audio determines how many more video frames are needed.

## Workflow Diagrams

### Legacy Mode Workflow

```
User clicks Stop
    ↓
Calculate audio duration
    ↓
Determine required video frames (based on audio)
    ↓
[Stopping State if needed]
    ↓
_finalize_recording()
    ↓
1. Release video writer
    ↓
2. Concatenate audio samples (AUDIO BUILD)
    ↓
3. Start async merge thread
    ↓
_async_merge_thread()
    ↓
4. Filter and validate audio
    ↓
5. Concatenate all audio
    ↓
6. Write audio to WAV file (QUALITY GUARANTEED)
    ↓
7. Adapt video to match audio duration (if needed)
    ↓
8. Run FFmpeg merge (192k bitrate, AAC)
    ↓
Final output with high-quality audio
```

### Worker Mode Workflow

```
User clicks Stop
    ↓
Worker.stop() called
    ↓
_encoder_worker() finishes
    ↓
1. Video writer released
    ↓
2. Concatenate audio samples (AUDIO BUILD)
    ↓
3. Write audio to WAV file (QUALITY GUARANTEED)
    ↓
4. Set state to FLUSHING
    ↓
_muxer_worker() starts
    ↓
5. Wait for video file
    ↓
6. Check for audio file
    ↓
7. Run FFmpeg merge (192k bitrate, AAC)
    ↓
Final output with high-quality audio
```

## Test Validation

Created `tests/test_audio_priority_workflow.py` which validates:

1. ✅ Audio concatenation happens before video merge
2. ✅ Audio quality parameters are correct (192k bitrate)
3. ✅ Audio sample rate is preserved (no conversion)
4. ✅ Video is adapted to match audio duration (not vice versa)
5. ✅ In stopping state, audio determines required video length
6. ✅ Worker mode also follows audio-first priority

All tests pass, confirming the implementation is correct.

## Summary

### Audio Priority Guarantees

1. **Audio is built first**
   - Audio samples are concatenated before video merge starts
   - Audio file is written to disk before FFmpeg merge

2. **Audio quality is guaranteed**
   - Native sample rate preserved (no conversion)
   - WAV format used (lossless, uncompressed)
   - FFmpeg merge uses 192k AAC bitrate (high quality)
   - No audio compression during collection

3. **Audio has priority over video**
   - Audio duration determines final video length
   - Video is adapted to match audio (not vice versa)
   - In stopping state, audio determines required video frames

### Implementation Details

- **Files**: `node/VideoNode/node_video_writer.py`, `node/VideoNode/video_worker.py`
- **Methods**: `_finalize_recording()`, `_merge_audio_video_ffmpeg()`, `_encoder_worker()`, `_muxer_worker()`
- **Test**: `tests/test_audio_priority_workflow.py`

### Conclusion

✅ The current implementation **correctly implements audio priority**.

The workflow ensures:
- Audio is built completely before merging with video
- Audio quality is guaranteed through high-quality settings
- Audio duration determines the final video length
- Both legacy and worker modes follow the same audio-first approach

No changes are needed to the implementation. This document serves as verification and documentation of the audio priority workflow.
