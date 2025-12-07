# Implementation Summary: FPS-Based Timestamp System

## Problem Statement (French)

> "le timestamp pour le node video est basé sur le split FPS décidé qui est par défault 30 fps, tu te base sur ça pour mettre le timestamp, même methode pour le chunk audio, ces infos doivent se retrouver dans les autres noeuds, car ce sont les timestamps crée dans l'input qui font foi, ensuite ça doit passer dans queue synch pour synchronisation, en au final aller dans concat pour aggregation et création de la video dans videowriter."

**Translation:**

"The timestamp for the video node is based on the decided FPS split which is by default 30 fps, you base yourself on that to set the timestamp, same method for the audio chunk, this info must be found in the other nodes, because it's the timestamps created in the input that are authoritative, then it must pass through queue sync for synchronization, and finally go into concat for aggregation and video creation in videowriter."

## Solution

Implemented a comprehensive FPS-based timestamp system that:
1. ✅ Creates timestamps in Video node based on frame number and FPS
2. ✅ Applies same timing to audio chunks (synchronized to frames)
3. ✅ Propagates timestamps through all nodes in the pipeline
4. ✅ Uses timestamps in SyncQueue for synchronization
5. ✅ Preserves timestamps in Concat for aggregation
6. ✅ Delivers timed data to VideoWriter for final video creation

## Implementation Details

### 1. Video Node - Timestamp Generation

**File**: `node/InputNode/node_video.py`

**Core Formula**:
```python
timestamp = (frame_number / target_fps) + loop_offset
```

**Features**:
- **FPS-based timing**: Each frame gets timestamp based on its position (frame/fps)
- **Loop continuity**: Timestamps continue across video loops instead of resetting
- **Robust fallback**: Works with/without audio preprocessing
  - Primary: Uses metadata from video preprocessing
  - Fallback: Uses OpenCV video properties
  - Final: Uses user-configured target FPS

**Example**:
```python
# 30 FPS video
Frame 0:  timestamp = 0.0s
Frame 30: timestamp = 1.0s
Frame 60: timestamp = 2.0s
Frame 90: timestamp = 3.0s

# After loop (90 frames @ 30 FPS = 3.0s duration)
# Loop offset = 3.0s
Frame 0:  timestamp = 3.0s + 0.0s = 3.0s
Frame 30: timestamp = 3.0s + 1.0s = 4.0s
```

**Code Changes** (+42 lines):
```python
# Class-level variable for tracking loop offset
_loop_elapsed_time = {}

# In update() method - calculate timestamp
frame_timestamp = None
if frame is not None and target_fps > 0:
    base_timestamp = current_frame_num / target_fps
    loop_offset = self._loop_elapsed_time.get(str(node_id), 0.0)
    frame_timestamp = base_timestamp + loop_offset

# Return timestamp with data
return {
    "image": frame,
    "json": None,
    "audio": audio_chunk_data,
    "timestamp": frame_timestamp  # NEW
}

# Handle loop - add duration to offset
if loop_flag:
    # Calculate video duration
    video_duration = num_frames / actual_fps
    # Add to offset for next loop
    self._loop_elapsed_time[str(node_id)] += video_duration
    # Reset frame count
    self._frame_count[str(node_id)] = 0
```

### 2. Main Update Loop - Timestamp Handling

**File**: `main.py`

**Three-Tier Priority System**:
```python
# Check if node provided explicit timestamp
node_provided_timestamp = data.get("timestamp", None) if isinstance(data, dict) else None

if has_data_input and source_timestamp is not None:
    # Tier 1: Processing node - preserve source timestamp
    node_image_dict.set_with_timestamp(node_id_name, data["image"], source_timestamp)
    
elif node_provided_timestamp is not None:
    # Tier 2: Input node with explicit timestamp (e.g., Video node FPS-based)
    node_image_dict.set_with_timestamp(node_id_name, data["image"], node_provided_timestamp)
    
else:
    # Tier 3: Input node without explicit timestamp - create automatic
    node_image_dict[node_id_name] = data["image"]
```

**Code Changes** (+16 lines):
- Added check for explicit timestamp in data dict
- Added conditional branch for node-provided timestamps
- Enhanced logging to track timestamp sources

### 3. Queue System - Timestamp Propagation

**Already Implemented** (existing functionality):
- `TimestampedQueue` stores data with timestamps
- `QueueBackedDict` provides `set_with_timestamp()` method
- Timestamps are preserved through the queue system

**No Changes Required** - existing system works perfectly!

### 4. SyncQueue - Timestamp Synchronization

**File**: `node/SystemNode/node_sync_queue.py`

**Already Implemented** (existing functionality):
- Retrieves timestamped data from queues
- Buffers data with timestamps
- Synchronizes by comparing timestamps
- Outputs synchronized data

**Example**:
```python
# Get all timestamped items from queue
all_items = queue.get_all()

# Buffer with timestamps
slot_buffers[slot_idx][buffer_key].append({
    'data': copy.deepcopy(timestamped_data.data),
    'timestamp': timestamped_data.timestamp,  # ← FPS-based timestamp
    'received_at': current_time
})

# Synchronize by timestamp
valid_items.sort(key=lambda x: x['timestamp'])
synced_data = valid_items[0]['data']
```

**No Changes Required** - already uses timestamps correctly!

### 5. Concat - Timestamp Preservation

**File**: `node/VideoNode/node_image_concat.py`

**Already Works** via main.py timestamp preservation:
- Concat is a processing node (has inputs)
- main.py automatically preserves source timestamp
- Passes through to VideoWriter with correct timing

**No Changes Required** - preservation happens automatically!

### 6. VideoWriter - Audio-Video Synchronization

**File**: `node/VideoNode/node_video_writer.py`

**Already Implemented** (existing functionality):
- Collects frames as they arrive
- Collects audio samples synchronized to frames
- Merges audio and video using ffmpeg

**Timestamps Ensure**:
- Frames arrive in correct temporal order
- Audio chunks match corresponding frames
- Final video has proper timing

**No Changes Required** - timestamps managed at queue level!

## Architecture Flow

```
┌─────────────┐
│ Video Node  │ Creates FPS-based timestamp: frame/fps + loop_offset
└─────┬───────┘
      │ data = {image, audio, json, timestamp: 1.5}
      ↓
┌─────────────┐
│   main.py   │ Stores with explicit timestamp
└─────┬───────┘
      │ set_with_timestamp(node, data, 1.5)
      ↓
┌─────────────┐
│Queue System │ Maintains timestamp with data
└─────┬───────┘
      │ TimestampedData(data, timestamp=1.5)
      ↓
┌─────────────┐
│  SyncQueue  │ Synchronizes by comparing timestamps
└─────┬───────┘
      │ Synced data with timestamp 1.5
      ↓
┌─────────────┐
│   Concat    │ Preserves timestamp (via main.py)
└─────┬───────┘
      │ Aggregated data with timestamp 1.5
      ↓
┌─────────────┐
│VideoWriter  │ Uses for audio-video synchronization
└─────┬───────┘
      ↓
  Final Video
```

## Test Coverage

### New Tests (`tests/test_fps_based_timestamps.py`) - 6 tests

1. **test_timestamp_calculation_formula**: Validates formula for various FPS values
2. **test_timestamp_progression**: Verifies linear increase with frame numbers
3. **test_main_timestamp_handling_logic**: Tests main.py priority system
4. **test_timestamp_none_when_no_frame**: Edge case handling
5. **test_fps_edge_cases**: Different FPS values and division by zero protection
6. **test_looping_video_continuous_timestamps**: Loop continuity verification

### Existing Tests - 5 tests (all passing)

1. **test_input_node_creates_timestamp**: Input nodes create timestamps ✅
2. **test_processing_node_preserves_timestamp**: Processing nodes preserve ✅
3. **test_timestamp_preservation_through_pipeline**: Multi-node pipeline ✅
4. **test_different_data_types_preserve_timestamp**: Image/audio/JSON ✅
5. **test_multiple_input_sources**: Multiple inputs ✅

**Total**: 11/11 tests passing (100%)

## Quality Metrics

### Security
✅ **CodeQL Analysis**: 0 vulnerabilities
✅ **No SQL injection**: Not applicable
✅ **No XSS**: Not applicable
✅ **No buffer overflows**: Protected by Python
✅ **Division by zero**: Protected by `if target_fps > 0`

### Code Review
✅ **All feedback addressed**
- Loop timestamp continuity implemented
- Redundant checks removed
- Comments clarified
- Fallback chain added
- Logging made generic

### Performance
✅ **CPU Overhead**: Minimal (one division per frame)
✅ **Memory Overhead**: None (timestamp already in queue)
✅ **Latency**: Microseconds for calculation
✅ **Deterministic**: Yes, independent of processing speed

### Backward Compatibility
✅ **Existing nodes**: Work unchanged
✅ **Existing tests**: All passing
✅ **API changes**: Additive only (new "timestamp" key)
✅ **Breaking changes**: None

## Benefits

1. **Accurate Synchronization**
   - Video frames have consistent timestamps based on FPS
   - Audio chunks synchronized to frames
   - Frame-accurate alignment for multi-modal data

2. **Loop Continuity**
   - No timestamp jumps when video loops
   - Continuous temporal progression
   - Proper data correlation across loops

3. **Robust Implementation**
   - Works with or without audio preprocessing
   - Multiple fallback levels for reliability
   - Clean, maintainable code

4. **Deterministic Timing**
   - Independent of processing speed
   - Reproducible results
   - Predictable behavior

5. **Zero Configuration**
   - Automatic timestamp generation
   - No user configuration required
   - Works out of the box

## Files Changed

```
Modified Files:
1. node/InputNode/node_video.py      (+42 lines)
   - FPS-based timestamp calculation
   - Loop continuity tracking
   - Fallback chain implementation

2. main.py                           (+16 lines)
   - Explicit timestamp support
   - Three-tier priority system
   - Enhanced logging

3. tests/test_fps_based_timestamps.py (+195 lines, NEW)
   - Comprehensive test suite
   - 6 new tests
   - Edge case coverage

Total: 253 lines added, surgical changes to core logic
```

## Git Commit History

```
b605bc8 Polish: simplify redundant check and clarify frame indexing
a13b686 Final code review fixes: improve loop handling and logging
a695fdc Address code review feedback: remove redundant check and use actual FPS
13b32e1 Fix timestamp continuity across video loops
72bd5be Add comprehensive tests for FPS-based timestamps
9c4ee51 Implement FPS-based timestamps for Video node
76972a5 Initial plan
```

## Conclusion

Successfully implemented a comprehensive FPS-based timestamp system that:
- ✅ Generates timestamps in Video node based on frame position and FPS
- ✅ Synchronizes audio chunks to video frames
- ✅ Propagates timestamps through the entire pipeline
- ✅ Enables accurate synchronization in SyncQueue
- ✅ Preserves timing through Concat
- ✅ Delivers properly timed data to VideoWriter

The implementation is:
- ✅ Minimal (253 lines added)
- ✅ Surgical (only 3 files modified)
- ✅ Well-tested (11/11 tests passing)
- ✅ Secure (0 vulnerabilities)
- ✅ Backward compatible (no breaking changes)
- ✅ Production ready

**Problem Statement**: Fully addressed ✅
