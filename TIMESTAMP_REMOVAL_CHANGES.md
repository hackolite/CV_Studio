# Timestamp Removal - Slot-Based Stream Ordering

## Overview

This document describes the changes made to remove timestamp-based ordering in ImageConcat and VideoWriter nodes. Timestamps are now maintained for informational purposes only, and all stream creation is based on actual data accumulation and slot ordering.

## Problem Statement (French Original)

"il ne faut plus se baser sur les timestamp, les timestamps sont a titre indicatif pour le moment, dans la fabrication des stream dans imageconcate et videowriter, il faut fabriquer la video basé sur la taille de l'audio issus de la concatenation des éléments dans le stream, et l'accumulation des images dans sont stream, pareil pour les jsons quand il y en a tous ça pour chacun des stream crées basées sur les données qui rentrent dans imageconcat."

## Translation

"We must no longer rely on timestamps, timestamps are for informational purposes only for the moment. In the creation of streams in imageconcat and videowriter, the video must be created based on the size of the audio from the concatenation of elements in the stream, and the accumulation of images in the stream, same for JSONs when there are any, all this for each stream created based on the data entering imageconcat."

## Key Changes

### 1. VideoWriter - Background Worker Mode (`node_video_writer.py`)

**Before:**
```python
# Sort by timestamp
audio_chunks_with_ts.sort(key=lambda x: (x['timestamp'], x['slot']))
```

**After:**
```python
# Sort by slot index only (timestamps are indicative only)
for slot_idx in sorted(audio_data.keys()):
    # Process in slot order
```

**Location:** Lines 471-490

**Impact:** Audio chunks from multiple slots are now concatenated in slot index order (0, 1, 2, ...) rather than timestamp order.

### 2. VideoWriter - Legacy Mode Audio Merging (`node_video_writer.py`)

**Before:**
```python
# Sort slots by timestamp (finite timestamps first), then by slot index
sorted_slots = sorted(
    slot_audio_dict.items(),
    key=lambda x: (x[1]['timestamp'], x[0])
)
```

**After:**
```python
# Sort slots by slot index only (timestamps are indicative only)
sorted_slots = sorted(
    slot_audio_dict.items(),
    key=lambda x: x[0]  # Sort by slot_idx only
)
```

**Location:** Lines 1263-1272

**Impact:** When recording stops, audio samples from all slots are sorted and merged based on slot index only, not timestamps.

### 3. VideoWriter - JSON Merging for MKV (`node_video_writer.py`)

**Before:**
```python
# Sort and concatenate JSON samples by timestamp
sorted_json_slots = sorted(
    json_samples.items(),
    key=lambda x: (x[1]['timestamp'], x[0])
)
```

**After:**
```python
# Sort JSON samples by slot index only (timestamps are indicative only)
sorted_json_slots = sorted(
    json_samples.items(),
    key=lambda x: x[0]  # Sort by slot_idx only
)
```

**Location:** Lines 1030-1035

**Impact:** JSON metadata for MKV files is now ordered by slot index, not timestamp.

### 4. ImageConcat - Audio Timestamp Handling (`node_image_concat.py`)

**Before:**
```python
# Preserve timestamp in audio chunk for downstream synchronization
```

**After:**
```python
# Preserve timestamp in audio chunk (indicative only, not used for ordering)
```

**Location:** Line 561

**Impact:** Clarified that timestamps are preserved but not used for ordering decisions.

### 5. Data Structure Comments

Updated comments throughout to clarify timestamp usage:

```python
_audio_samples_dict = {}  # Store audio samples per slot: {node: {slot_idx: {'samples': [], 'timestamp': float (indicative), 'sample_rate': int}}}
_json_samples_dict = {}  # Store JSON samples per slot: {node: {slot_idx: {'samples': [], 'timestamp': float (indicative)}}}
```

## Stream Creation Logic

### Video Stream
- Created by accumulating images in the order they arrive
- Based on the number of frames collected, not timestamps
- Each frame is written sequentially to cv2.VideoWriter

### Audio Stream
- Created by concatenating audio samples from all slots
- **Ordering:** Slot index (0, 1, 2, ...)
- **Duration:** Based on the actual size of concatenated audio data
- **Sample Rate:** Detected from first slot with valid sample rate
- Formula: `audio_duration = total_samples / sample_rate`

### JSON Stream
- Created by aggregating JSON samples from all slots
- **Ordering:** Slot index (0, 1, 2, ...)
- **Structure:** Each slot's samples are concatenated into a list
- **Output:** Saved to `{video_name}_metadata/json_slot_{idx}_concat.json` for MKV

## Timestamp Preservation

While timestamps are no longer used for ordering, they are still preserved in the data structures for:

1. **Debugging:** Helping developers understand data flow
2. **Logging:** Providing context in log messages
3. **Future Features:** Potential use in analytics or post-processing
4. **Documentation:** Showing when data was captured

## Testing

Updated tests in `tests/test_stream_aggregation_by_timestamp.py`:

- ✅ `test_audio_slots_sorted_by_slot_index()` - Verifies slot index ordering
- ✅ `test_audio_concatenation_preserves_order()` - Verifies concatenation order
- ✅ `test_json_slots_sorted_by_slot_index()` - Verifies JSON slot ordering
- ✅ `test_slot_ordering_by_index()` - Verifies ordering with various timestamps
- ✅ `test_slot_index_as_primary_sort()` - Verifies slot index is primary sort key
- ✅ `test_audio_duration_calculation_from_samples()` - Verifies duration calculation
- ✅ `test_multiple_slot_audio_merge_realistic()` - Verifies realistic merge scenario

All tests pass successfully.

## Backward Compatibility

These changes are backward compatible:

- ✅ Timestamps are still collected and stored (just not used for ordering)
- ✅ Existing code that reads timestamps will continue to work
- ✅ Data structure formats remain unchanged
- ✅ File output formats (AVI, MP4, MKV) remain unchanged
- ✅ Metadata structure for MKV remains unchanged

## Migration Guide

For users upgrading to this version:

1. **No code changes required** - The API remains the same
2. **Behavior change:** Streams are now ordered by slot index instead of timestamp
3. **Expected impact:** More predictable ordering based on slot configuration
4. **Recommendation:** If specific ordering is needed, assign slots in the desired order

## Benefits

1. **Simplicity:** Slot-based ordering is simpler and more predictable
2. **Data-Driven:** Stream creation is based on actual accumulated data size
3. **Consistency:** All data types (image, audio, JSON) use the same ordering logic
4. **Performance:** Eliminates timestamp comparison overhead
5. **Debugging:** Easier to understand and debug slot-based ordering

## Summary

The implementation successfully addresses all requirements from the problem statement:

1. ✅ Timestamps are now indicative only (not used for ordering)
2. ✅ Video creation based on image accumulation in slot order
3. ✅ Audio stream based on actual audio size from concatenated elements
4. ✅ JSON stream based on actual JSON accumulation from slots
5. ✅ All streams created based on data entering ImageConcat in slot order
6. ✅ Tests updated and passing
7. ✅ Documentation updated
8. ✅ Backward compatibility maintained
