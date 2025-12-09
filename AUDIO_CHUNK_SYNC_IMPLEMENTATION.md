# Audio Chunk Synchronization Implementation

## Overview

This implementation ensures that audio chunks from multiple sources maintain proper timestamp synchronization when flowing through the SyncQueue → ImageConcat → VideoWriter pipeline.

## Problem Statement (Original in French)

> "vérifie que le chunk de l'audio fusionne de façon synchronisé, quand on passe l'audio et la video au travzers de la syncQueue, tous cela au finale au traverse de imageconcat et videowriter"

**Translation:**
> "Verify that audio chunks merge synchronously when passing audio and video through the syncQueue, all ultimately through imageconcat and videowriter"

## Issue Description

Previously, when audio chunks from multiple sources (e.g., multiple video files) were passed through:
1. **SyncQueue** - Synchronized data by timestamp
2. **ImageConcat** - Collected audio from multiple slots
3. **VideoWriter** - Merged audio into final video

The VideoWriter would concatenate audio chunks **in slot order** (0, 1, 2...) rather than **timestamp order**. This could cause audio desynchronization if slots were added in a different order than their temporal sequence.

## Solution

### 1. ImageConcat Node Enhancement

**File:** `node/VideoNode/node_image_concat.py`

The ImageConcat node now preserves timestamps when collecting audio from multiple sources:

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

### 2. VideoWriter Node Enhancement

**File:** `node/VideoNode/node_video_writer.py`

The VideoWriter now synchronizes multi-slot audio by timestamp:

```python
# Extract chunks with timestamps
audio_chunks_with_ts = []
for slot_idx in sorted(audio_data.keys()):
    audio_chunk = audio_data[slot_idx]
    if isinstance(audio_chunk, dict) and 'data' in audio_chunk:
        timestamp = audio_chunk.get('timestamp', float('inf'))
        audio_chunks_with_ts.append({
            'data': audio_chunk['data'],
            'timestamp': timestamp,
            'slot': slot_idx
        })

# Sort by timestamp first (finite timestamps first), then by slot
audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))

# Concatenate in synchronized order
merged_chunk = np.concatenate([chunk['data'] for chunk in audio_chunks_with_ts])
```

## Data Flow

```
┌─────────────┐
│  Video Node │ 
│  (source 1) │ ─── timestamp: 100.0 ───┐
└─────────────┘                          │
                                         ├──> ┌────────────┐
┌─────────────┐                          │    │ SyncQueue  │
│  Video Node │                          ├──> │   Node     │
│  (source 2) │ ─── timestamp: 99.9 ────┤    └──────┬─────┘
└─────────────┘                          │           │
                                         │           │ Synchronized data
┌─────────────┐                          │           │
│  Video Node │                          │           ▼
│  (source 3) │ ─── timestamp: 100.1 ───┘    ┌─────────────┐
└─────────────┘                               │ ImageConcat │
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
                                                     ▼
                                              Synchronized
                                              Video + Audio
```

## Example Scenario

### Before Fix (Incorrect):
```
Slot 0: Audio chunk at timestamp 100.0
Slot 1: Audio chunk at timestamp 99.9
Slot 2: Audio chunk at timestamp 100.1

VideoWriter concatenates in slot order:
  → [chunk_0, chunk_1, chunk_2]
  → [100.0, 99.9, 100.1]  ❌ Out of temporal order!
```

### After Fix (Correct):
```
Slot 0: Audio chunk at timestamp 100.0
Slot 1: Audio chunk at timestamp 99.9
Slot 2: Audio chunk at timestamp 100.1

VideoWriter sorts by timestamp first:
  → [chunk_1, chunk_0, chunk_2]
  → [99.9, 100.0, 100.1]  ✓ Proper temporal order!
```

## Backward Compatibility

The implementation maintains full backward compatibility:

1. **Audio without timestamps**: Falls back to slot order (original behavior)
2. **Plain numpy arrays**: Treated as having no timestamp (sorted at end)
3. **Mixed formats**: Chunks with timestamps sorted first, then chunks without timestamps by slot order

## Testing

### Unit Tests
**File:** `tests/test_audio_chunk_sync.py`

Tests the synchronization logic in isolation:
- Timestamp-based vs slot-based ordering
- Audio chunks with and without timestamps
- Mixed audio formats

### Integration Tests
**File:** `tests/test_sync_audio_through_pipeline.py`

Tests the complete pipeline:
- SyncQueue → ImageConcat → VideoWriter data flow
- Timestamp preservation through each node
- Multi-source audio synchronization
- Backward compatibility

### Running Tests
```bash
# Unit tests
python tests/test_audio_chunk_sync.py

# Integration tests
python tests/test_sync_audio_through_pipeline.py

# Existing async merge tests (verify no regression)
python tests/test_async_merge.py
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

This fix ensures that:
1. ✅ Audio maintains proper temporal synchronization through the pipeline
2. ✅ Multi-source video/audio recordings have correctly aligned audio
3. ✅ SyncQueue synchronization is preserved all the way to VideoWriter
4. ✅ Backward compatibility is maintained for existing workflows

## Files Modified

1. `node/VideoNode/node_image_concat.py`
   - Added timestamp preservation in audio collection

2. `node/VideoNode/node_video_writer.py`
   - Added timestamp-based audio synchronization

3. `tests/test_audio_chunk_sync.py` (new)
   - Unit tests for synchronization logic

4. `tests/test_sync_audio_through_pipeline.py` (new)
   - Integration tests for complete pipeline

## Related Documentation

- `VIDEOWRITER_AUDIO_MERGE_IMPLEMENTATION.md` - Audio+video merging
- `SYNC_QUEUE_IMPLEMENTATION_SUMMARY.md` - SyncQueue node design
- `TIMESTAMPED_QUEUE_SYSTEM.md` - Timestamp queue architecture
