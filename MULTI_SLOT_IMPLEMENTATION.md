# Multi-Slot Concat and Video Writer Enhancement - Implementation Summary

## Overview
This implementation adds support for multiple slot types (IMAGE, AUDIO, JSON) to the ImageConcat node and enhances the VideoWriter node to support AVI and MKV formats with multi-track metadata storage.

## Changes Made

### 1. ImageConcat Node (`node/VideoNode/node_image_concat.py`)

#### New Features:
- **Multi-Type Slot Support**: Slots can now be IMAGE, AUDIO, or JSON type
- **Slot Type Selector**: UI combo box to select slot type before adding
- **Mixed Data Handling**: Processes and outputs IMAGE, AUDIO, and JSON data simultaneously
- **Settings Persistence**: Saves and restores slot type configuration

#### Implementation Details:
```python
# New class variable
_slot_types = {}  # Track the type of each slot (IMAGE, AUDIO, JSON)

# UI Enhancement - Slot type selector
dpg.add_combo(
    tag=node.tag_node_name + ':SlotType',
    items=['IMAGE', 'AUDIO', 'JSON'],
    default_value='IMAGE',
    label='Slot Type',
)
```

#### Data Flow:
1. User selects slot type from combo box
2. Clicks "Add Slot" to create a new slot of that type
3. Connects nodes to the slots (IMAGE nodes to IMAGE slots, etc.)
4. Update method collects data from all slot types
5. Returns combined data: `{"image": frame, "json": json_data, "audio": audio_data}`

### 2. VideoWriter Node (`node/VideoNode/node_video_writer.py`)

#### New Features:
- **Format Selection**: Choose between MP4, AVI, or MKV formats
- **Codec Mapping**:
  - MP4: mp4v (default, backward compatible)
  - AVI: MJPG (Motion JPEG, widely compatible)
  - MKV: FFV1 (lossless, archival quality)
- **MKV Metadata Tracks**: Stores audio and JSON data in separate track files
- **Dynamic Track Creation**: Creates track files as data arrives (supports variable slots)

#### Implementation Details:
```python
# Format selector UI
dpg.add_combo(
    tag=node.tag_node_name + ':Format',
    items=['MP4', 'AVI', 'MKV'],
    default_value='MP4',
    label='Format',
)

# MKV metadata structure
{
    'audio_handles': {slot_idx: file_handle},  # Per-slot audio files
    'json_handles': {slot_idx: file_handle},   # Per-slot JSON files
    'file_path': '/path/to/video.mkv',
}
```

#### MKV Metadata Storage:
When recording in MKV format, the following structure is created:
```
video_directory/
├── 20231206_120000.mkv           # Video file
└── 20231206_120000_metadata/     # Metadata directory
    ├── audio_slot_0.jsonl        # Audio data from slot 0
    ├── audio_slot_1.jsonl        # Audio data from slot 1
    ├── json_slot_0.jsonl         # JSON data from slot 0
    └── json_slot_1.jsonl         # JSON data from slot 1
```

Each `.jsonl` (JSON Lines) file contains one JSON object per line:
```json
{"slot": 0, "data": [0.1, 0.2, 0.3]}
{"slot": 0, "data": [0.4, 0.5, 0.6]}
```

### 3. Tests

Created comprehensive test suites:

#### `test_multi_slot_concat.py` (8 tests)
- Slot type initialization and storage
- Connection type handling
- Audio and JSON data collection
- Output data structure validation
- Settings persistence

#### `test_video_writer_formats.py` (10 tests)
- Format and codec selection
- File extension verification
- Metadata directory creation
- Audio and JSON track file creation
- Multiple slot handling

## Usage Examples

### Example 1: Mixed Slot Types in Concat Node
1. Create ImageConcat node
2. Add IMAGE slot (default)
3. Select "AUDIO" from combo, click "Add Slot"
4. Select "JSON" from combo, click "Add Slot"
5. Connect:
   - Camera → IMAGE slot
   - Microphone → AUDIO slot
   - Detector → JSON slot
6. Output includes all three data types

### Example 2: Recording MKV with Metadata
1. Create VideoWriter node
2. Select "MKV" from format combo
3. Connect ImageConcat output to VideoWriter
4. Click "Start" to begin recording
5. Video and metadata tracks are recorded in parallel
6. Click "Stop" to finalize recording

## Technical Notes

### Backward Compatibility
- Default slot type is IMAGE (maintains existing behavior)
- MP4 format is default (maintains existing behavior)
- Existing nodes and settings files continue to work
- Only IMAGE slots affect visual concat display

### Performance Considerations
- Metadata files are written incrementally (no memory buffering)
- File handles are flushed after each write
- Proper cleanup on stop/close to prevent file handle leaks

### Limitations
- MKV metadata is stored in separate files (not embedded in container)
- Audio data is serialized to JSON (not raw audio format)
- Maximum 9 slots (same as before)

## Future Enhancements

Possible improvements for future versions:
1. Embed metadata directly in MKV container using FFmpeg
2. Support raw audio encoding in MKV
3. Add slot type indicator in UI (color coding)
4. Support reordering slots
5. Add slot removal functionality

## Security Summary

CodeQL analysis completed with **0 alerts**. No security vulnerabilities detected in the implementation.

## Testing Results

All tests pass successfully:
- 4 existing concat text scaling tests ✓
- 8 new multi-slot concat tests ✓
- 10 new video writer format tests ✓

Total: **22/22 tests passing**
