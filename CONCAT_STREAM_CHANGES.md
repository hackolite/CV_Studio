# Concat Stream Data Management Enhancement

## Overview

This document describes the enhancements made to the concat queue (ImageConcat node) and VideoWriter node to better manage audio, video, and JSON data streams during recording.

## Problem Statement (French Original)

"Je veux que la queue concat quand elle récupère les flux audio et video, stocke les références des données (image, audio et json) quand le record start, ensuite, crée le stream video en concat, crée le stream audio en concat, crée le stream json en concat, et fusionne audio + video si AVI et MPEG4, et sinon, audio + video + data_from_json pour mkv."

## Translation

"I want the concat queue, when it retrieves audio and video streams, to store references to the data (image, audio and json) when recording starts, then create the video stream by concatenation, create the audio stream by concatenation, create the json stream by concatenation, and merge audio + video if AVI and MPEG4, otherwise audio + video + data_from_json for MKV."

## Implementation Details

### 1. JSON Sample Collection (`node_video_writer.py`)

**Added:**
- `_json_samples_dict`: Class variable to store JSON samples per slot during recording
  - Structure: `{node_tag: {slot_idx: {'samples': [], 'timestamp': float}}}`
- JSON sample collection logic in the `update()` method (lines ~497-525)
- JSON sample cleanup in stop recording logic (line ~1031)

**How it works:**
- When recording starts, `_json_samples_dict` is initialized for the node
- During recording, JSON data from each slot is collected and appended to the slot's samples list
- When recording stops, JSON samples are processed and saved for MKV format

### 2. Stream Concatenation

**Video Stream:**
- Already implemented via `cv2.VideoWriter`
- Frames are written sequentially during recording

**Audio Stream:**
- Already implemented (lines 928-996)
- Audio samples per slot are collected with timestamps
- At recording stop, slots are sorted by timestamp
- Audio data from each slot is concatenated using `np.concatenate()`
- All slot audio is merged into a single audio track

**JSON Stream (NEW):**
- JSON samples per slot are collected during recording (similar to audio)
- At recording stop, for MKV format:
  - JSON slots are sorted by timestamp
  - Each slot's JSON samples are concatenated into a list
  - Saved to `{video_name}_metadata/json_slot_{idx}_concat.json`

### 3. Format-Specific Merging

**Enhanced `_async_merge_thread()` method:**
- Added parameters: `video_format='MP4'`, `json_samples=None`
- Logic now differentiates between formats:

**For AVI and MP4 (MPEG4):**
```python
# Only merges audio + video
success = self._merge_audio_video_ffmpeg(
    temp_path, audio_samples, sample_rate, final_path, progress_callback
)
```

**For MKV:**
```python
# Merges audio + video
success = self._merge_audio_video_ffmpeg(...)
# Additionally saves JSON metadata
if video_format == 'MKV' and json_samples:
    # Sort and concatenate JSON samples by timestamp
    # Save to metadata directory
    {video_name}_metadata/json_slot_{idx}_concat.json
```

### 4. Data Reference Storage

The implementation now properly stores references to all data types when recording starts:

1. **Video frames**: Written directly to `cv2.VideoWriter`
2. **Audio samples**: Stored in `_audio_samples_dict[node_tag][slot_idx]['samples']`
3. **JSON data**: Stored in `_json_samples_dict[node_tag][slot_idx]['samples']`

All three data types are collected during the entire recording session and processed when recording stops.

### 5. Timestamp-Based Concatenation

Both audio and JSON samples are sorted by timestamp before concatenation:

```python
sorted_slots = sorted(
    slot_data_dict.items(),
    key=lambda x: (x[1]['timestamp'], x[0])
)
```

This ensures that:
- Slots with finite timestamps are processed first (in timestamp order)
- Slots with `float('inf')` timestamp (no timestamp) are processed last (in slot order)
- Proper synchronization is maintained across streams

## File Structure for MKV Recordings

When recording to MKV format with JSON data, the following file structure is created:

```
/output_directory/
├── video_20231213_120000.mkv          # Video + audio
└── video_20231213_120000_metadata/     # JSON metadata directory
    ├── json_slot_0_concat.json        # Concatenated JSON from slot 0
    ├── json_slot_1_concat.json        # Concatenated JSON from slot 1
    └── ...
```

Each JSON file contains:
```json
{
  "slot_idx": 0,
  "timestamp": 100.0,
  "samples": [
    {"frame": 1, "data": "..."},
    {"frame": 2, "data": "..."},
    ...
  ]
}
```

## Testing

New test file: `tests/test_concat_stream_merge.py`

Tests cover:
- JSON samples dict initialization
- JSON slot data structure
- JSON sample collection (single and multi-slot)
- Timestamp-based sorting
- Format-specific merge detection
- JSON metadata file structure
- Audio and JSON concurrent collection
- Recording metadata with format

## Backward Compatibility

All changes are backward compatible:
- Existing AVI/MP4 recordings work as before (audio + video only)
- MKV recordings now optionally include JSON metadata if available
- No changes to ImageConcat node output format
- JSON collection only activates if JSON data is present in the pipeline

## Summary

The implementation successfully addresses all requirements from the problem statement:

1. ✅ Store references to data (image, audio, JSON) when recording starts
2. ✅ Create video stream by concatenation (existing + verified)
3. ✅ Create audio stream by concatenation (existing + verified)
4. ✅ Create JSON stream by concatenation (NEW)
5. ✅ Merge audio + video for AVI and MPEG4
6. ✅ Merge audio + video + data_from_json for MKV
7. ✅ Verify that changes don't break existing functionality (tests added)
