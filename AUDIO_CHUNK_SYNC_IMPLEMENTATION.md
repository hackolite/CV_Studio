# Audio Chunk Synchronization Implementation - FIXED

## Overview

This implementation ensures that audio chunks from multiple sources maintain proper timestamp synchronization when flowing through the SyncQueue → ImageConcat → VideoWriter pipeline.

## Problem Statement (Original in French)

> "le son ne marche pas lors de la fusion image son lors de ça ====> chunk de l'audio fusionne de façon synchronisé, quand on passe l'audio et la video au travzers de la syncQueue, tous cela au finale au traverse de imageconcat et videowriter. vérifie ça."

**Translation:**
> "The sound does not work during image-sound fusion ===> audio chunks merge synchronously when passing audio and video through syncQueue, all ultimately through imageconcat and videowriter. Check this."

## Issue Description

When audio chunks from multiple sources (e.g., multiple video files) were passed through:
1. **SyncQueue** - Synchronized data by timestamp
2. **ImageConcat** - Collected audio from multiple slots
3. **VideoWriter** - Merged audio into final video

The VideoWriter had a critical bug: it was merging audio chunks **per-frame** instead of **per-slot**. This caused audio from different video sources to be incorrectly interleaved, resulting in garbled audio output.

### The Bug

**Previous (Incorrect) Behavior:**
- For each video frame received, VideoWriter would:
  1. Sort all slot audio chunks by timestamp
  2. Merge them into a single chunk
  3. Append to the audio samples list
- This caused audio to be interleaved frame-by-frame instead of playing each source sequentially

**Example of Bug:**
```
Frame 1: Slot 0 [1, 2] (ts=100.0), Slot 1 [3, 4] (ts=99.9)
  → Merged per frame: [3, 4, 1, 2]  (sorted by timestamp)

Frame 2: Slot 0 [5, 6] (ts=100.0), Slot 1 [7, 8] (ts=99.9)
  → Merged per frame: [7, 8, 5, 6]  (sorted by timestamp)

Final audio: [3, 4, 1, 2, 7, 8, 5, 6]  ❌ WRONG - interleaved!
```

**Correct Behavior:**
```
Collect all frames per slot:
  Slot 0 (ts=100.0): [1, 2] + [5, 6] = [1, 2, 5, 6]
  Slot 1 (ts=99.9): [3, 4] + [7, 8] = [3, 4, 7, 8]

Sort slots by timestamp and concatenate:
  Final audio: [3, 4, 7, 8, 1, 2, 5, 6]  ✓ CORRECT - slot 1 then slot 0
```

## Solution

### 1. ImageConcat Node Enhancement

**File:** `node/VideoNode/node_image_concat.py`

The ImageConcat node preserves timestamps when collecting audio from multiple sources:

```python
# Get audio from node_audio_dict
audio_chunk = node_audio_dict.get(slot_info['source'], None)
if audio_chunk is not None:
    # Also retrieve timestamp for synchronization
    timestamp = node_audio_dict.get_timestamp(slot_info['source'])
    
    # Preserve timestamp in audio chunk for downstream synchronization
    if isinstance(audio_chunk, dict):
        if 'timestamp' not in audio_chunk and timestamp is not None:
            audio_chunk = audio_chunk.copy()
            audio_chunk['timestamp'] = timestamp
    elif timestamp is not None:
        audio_chunk = {
            'data': audio_chunk,
            'timestamp': timestamp
        }
    
    audio_chunks[slot_idx] = audio_chunk
```

### 2. VideoWriter Node Fix

**File:** `node/VideoNode/node_video_writer.py`

The VideoWriter now correctly collects audio **per-slot** during recording and merges by timestamp at the end:

#### Changes to Audio Collection Structure

**Before:**
```python
_audio_samples_dict = {}  # {node: [merged_chunks]}
```

**After:**
```python
_audio_samples_dict = {}  # {node: {slot_idx: {'samples': [], 'timestamp': float, 'sample_rate': int}}}
```

#### Audio Collection During Recording

```python
# For each frame received with multi-slot audio
if isinstance(audio_data, dict) and 'data' not in audio_data:
    # Multi-slot concat output: {slot_idx: audio_chunk}
    for slot_idx in audio_data.keys():
        audio_chunk = audio_data[slot_idx]
        
        if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
            timestamp = audio_chunk.get('timestamp', float('inf'))
            sample_rate = audio_chunk.get('sample_rate', 22050)
            
            # Initialize slot if not exists
            if slot_idx not in self._audio_samples_dict[tag_node_name]:
                self._audio_samples_dict[tag_node_name][slot_idx] = {
                    'samples': [],
                    'timestamp': timestamp,
                    'sample_rate': sample_rate
                }
            
            # Append this frame's audio to the slot
            self._audio_samples_dict[tag_node_name][slot_idx]['samples'].append(audio_chunk['data'])
```

#### Audio Merge at Recording End

```python
# When recording stops, process collected audio
slot_audio_dict = self._audio_samples_dict[tag_node_name]

# Sort slots by timestamp (finite timestamps first), then by slot index
sorted_slots = sorted(
    slot_audio_dict.items(),
    key=lambda x: (x[1]['timestamp'], x[0])
)

# Build final audio sample list in timestamp order
audio_samples_list = []
for slot_idx, slot_data in sorted_slots:
    # Concatenate all samples for this slot
    if slot_data['samples']:
        slot_concatenated = np.concatenate(slot_data['samples'])
        audio_samples_list.append(slot_concatenated)

# Final audio is passed to ffmpeg merge
```

## Data Flow

```
┌─────────────┐
│  Video Node │ 
│  (source 1) │ ─── timestamp: 100.0, audio: [frame1, frame2, ...] ───┐
└─────────────┘                                                        │
                                                                       ├──> ┌────────────┐
┌─────────────┐                                                        │    │ SyncQueue  │
│  Video Node │                                                        ├──> │   Node     │
│  (source 2) │ ─── timestamp: 99.9, audio: [frame1, frame2, ...] ───┤    └──────┬─────┘
└─────────────┘                                                        │           │
                                                                       │           │ Synchronized
┌─────────────┐                                                        │           │ by timestamp
│  Video Node │                                                        │           ▼
│  (source 3) │ ─── timestamp: 100.1, audio: [frame1, frame2, ...] ──┘    ┌─────────────┐
└─────────────┘                                                             │ ImageConcat │
                                                                            │    Node     │
                                                                            └──────┬──────┘
                                                                                   │
                                                                                   │ Multi-slot audio
                                                                                   │ with timestamps
                                                                                   ▼
                                                                            ┌─────────────┐
                                                                            │ VideoWriter │
                                                                            │    Node     │
                                                                            └──────┬──────┘
                                                                                   │
                                                                                   │ During Recording:
                                                                                   │ Collect per slot
                                                                                   │
                                                                                   │ At Recording End:
                                                                                   │ Sort slots by ts
                                                                                   │ Concatenate
                                                                                   ▼
                                                                            Synchronized
                                                                            Video + Audio
```

## Example Scenario (Fixed)

### Recording Scenario:
```
3 video sources connected to ImageConcat, then to VideoWriter
Recording 2 frames from each source

Source 0 (Slot 0): timestamp 100.0
Source 1 (Slot 1): timestamp 99.9  (earlier)
Source 2 (Slot 2): timestamp 100.1 (later)
```

### During Recording (Frame-by-Frame):

**Frame 1 arrives from all sources:**
```python
audio_data = {
    0: {'data': [10, 11], 'timestamp': 100.0},
    1: {'data': [20, 21], 'timestamp': 99.9},
    2: {'data': [30, 31], 'timestamp': 100.1},
}

# VideoWriter collects per slot:
_audio_samples_dict[node] = {
    0: {'samples': [[10, 11]], 'timestamp': 100.0},
    1: {'samples': [[20, 21]], 'timestamp': 99.9},
    2: {'samples': [[30, 31]], 'timestamp': 100.1},
}
```

**Frame 2 arrives from all sources:**
```python
audio_data = {
    0: {'data': [12, 13], 'timestamp': 100.0},
    1: {'data': [22, 23], 'timestamp': 99.9},
    2: {'data': [32, 33], 'timestamp': 100.1},
}

# VideoWriter appends to each slot:
_audio_samples_dict[node] = {
    0: {'samples': [[10, 11], [12, 13]], 'timestamp': 100.0},
    1: {'samples': [[20, 21], [22, 23]], 'timestamp': 99.9},
    2: {'samples': [[30, 31], [32, 33]], 'timestamp': 100.1},
}
```

### At Recording End:

```python
# Sort slots by timestamp
sorted_slots = [(1, {...}), (0, {...}), (2, {...})]  # ts: 99.9, 100.0, 100.1

# Concatenate each slot
slot_1_audio = [20, 21, 22, 23]  # All frames from slot 1
slot_0_audio = [10, 11, 12, 13]  # All frames from slot 0
slot_2_audio = [30, 31, 32, 33]  # All frames from slot 2

# Final audio in timestamp order
final_audio = [20, 21, 22, 23, 10, 11, 12, 13, 30, 31, 32, 33]  ✓ CORRECT!
```

## Backward Compatibility

The implementation maintains full backward compatibility:

1. **Audio without timestamps**: Falls back to slot order (original behavior)
2. **Plain numpy arrays**: Treated as having no timestamp (sorted at end)
3. **Mixed formats**: Chunks with timestamps sorted first, then chunks without timestamps by slot order

## Testing

### Unit Tests

**File:** `tests/test_audio_chunk_sync.py`
Tests the synchronization logic concepts in isolation.

**File:** `tests/test_video_writer_audio_slot_merge.py` (NEW)
Tests the actual VideoWriter collection and merge logic:
- Audio collection per slot across frames
- Slot merge by timestamp at recording end
- Single-slot audio (backward compatibility)
- Multi-slot with mixed timestamps
- Fallback behavior when timestamps missing

### Integration Tests

**File:** `tests/test_sync_audio_through_pipeline.py`
Tests the complete pipeline:
- SyncQueue → ImageConcat → VideoWriter data flow
- Timestamp preservation through each node
- Multi-source audio synchronization

### Running Tests
```bash
# Unit tests for VideoWriter slot merging
python tests/test_video_writer_audio_slot_merge.py

# Unit tests for chunk sync concepts
python tests/test_audio_chunk_sync.py

# Integration tests
python tests/test_sync_audio_through_pipeline.py
```

## Technical Details

### Timestamp Format
Audio chunks can contain timestamps in the following formats:

```python
# Dict format with timestamp
{'data': numpy_array, 'sample_rate': 22050, 'timestamp': 100.0}

# Dict format without timestamp (uses slot order)
{'data': numpy_array, 'sample_rate': 22050}

# Plain numpy array (uses slot order)
numpy_array
```

### Synchronization Priority
When merging multi-slot audio, the sort key is:
```python
(timestamp, slot_index)
```

This means:
1. Chunks with timestamps are ordered by their timestamp value
2. Chunks without timestamps (infinity) come last
3. Within the same timestamp value (or infinity), ordered by slot index

## Impact

This fix resolves the audio synchronization issue:
1. ✅ Audio from multiple video sources is no longer garbled
2. ✅ Each source's audio plays sequentially in correct timestamp order
3. ✅ Multi-source video/audio recordings have properly aligned audio
4. ✅ SyncQueue synchronization is preserved all the way to final output
5. ✅ Backward compatibility is maintained for single-slot workflows

## Files Modified

1. `node/VideoNode/node_video_writer.py`
   - Changed `_audio_samples_dict` structure from list to dict
   - Modified audio collection to store per-slot during recording
   - Added slot sorting by timestamp at recording end
   - Preserves sample rate and timestamp information per slot

2. `tests/test_video_writer_audio_slot_merge.py` (new)
   - Comprehensive unit tests for slot collection and merging
   - Tests multi-slot, single-slot, and edge cases

3. `AUDIO_CHUNK_SYNC_IMPLEMENTATION.md`
   - Updated documentation to reflect the actual bug and fix

## Related Documentation

- `VIDEOWRITER_AUDIO_MERGE_IMPLEMENTATION.md` - Audio+video merging
- `SYNC_QUEUE_IMPLEMENTATION_SUMMARY.md` - SyncQueue node design
- `TIMESTAMPED_QUEUE_SYSTEM.md` - Timestamp queue architecture
