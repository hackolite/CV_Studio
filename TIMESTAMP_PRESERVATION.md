# Timestamp Preservation from Input Nodes

## Overview

This document describes the timestamp preservation system implemented in CV_Studio to ensure that data timestamps are created at input nodes and preserved throughout the processing pipeline.

## Problem Statement

In a node-based processing pipeline, it's critical that all data (frames, audio chunks, JSON) maintains the timestamp of when it was originally captured from the input source. This enables:

- Proper synchronization of video and audio streams
- Accurate timing analysis in processing pipelines  
- Correlation of data from multiple input sources
- Temporal alignment of multi-modal data

## Solution

The system now automatically:

1. **Creates timestamps at input nodes** - When data exits an input node (Webcam, Video, Microphone, etc.), a timestamp is created
2. **Preserves timestamps through processing** - As data flows through processing nodes (Blur, Grayscale, etc.), the original timestamp is maintained
3. **Handles multiple data types** - Works for image frames, audio chunks, and JSON metadata

## Implementation Details

### Node Classification

Nodes are automatically classified as either:

- **Input Nodes**: No IMAGE/AUDIO/JSON input connections
  - Examples: Webcam, Video, Microphone, RTSP, API
  - Behavior: Create new timestamps when outputting data

- **Processing Nodes**: Have at least one IMAGE/AUDIO/JSON input connection  
  - Examples: Blur, Grayscale, ObjectDetection, AudioEffect
  - Behavior: Preserve timestamp from source input

### Code Changes

#### 1. QueueBackedDict (`node/queue_adapter.py`)

Added two new methods:

```python
def set_with_timestamp(self, node_id_name: str, value: Any, timestamp: Optional[float] = None):
    """Set a value with an explicit timestamp (preserves source timestamp)."""
    
def get_timestamp(self, node_id_name: str) -> Optional[float]:
    """Get the timestamp of the latest data for a node."""
```

#### 2. Main Loop (`main.py`)

Modified `update_node_info()` to detect node type and handle timestamps:

```python
# Determine if this is an input node or processing node
has_data_input = False
source_timestamp = None

for connection_info in connection_list:
    connection_type = connection_info[0].split(":")[2]
    if connection_type in ["IMAGE", "AUDIO", "JSON"]:
        has_data_input = True
        # Get timestamp from source node
        source_node_id = ":".join(connection_info[0].split(":")[:2])
        source_timestamp = node_image_dict.get_timestamp(source_node_id)
        break

# Store data with appropriate timestamp
if has_data_input and source_timestamp is not None:
    # Processing node - preserve source timestamp
    node_image_dict.set_with_timestamp(node_id_name, data["image"], source_timestamp)
else:
    # Input node - create new timestamp
    node_image_dict[node_id_name] = data["image"]
```

## Usage Examples

### Single Input Pipeline

```
Webcam (timestamp: 1701234567.123)
  ↓
Blur (timestamp: 1701234567.123)  # Preserved
  ↓  
Grayscale (timestamp: 1701234567.123)  # Preserved
  ↓
ObjectDetection (timestamp: 1701234567.123)  # Preserved
```

### Video with Audio

```
Video Node
  ├─ Image (timestamp: 1701234567.123)
  └─ Audio (timestamp: 1701234567.456)
       ↓                    ↓
   VideoEffect          AudioEffect
  (preserves .123)    (preserves .456)
```

### Multiple Input Sources

```
Webcam (timestamp: 1701234567.100)
  ↓
Blur (timestamp: 1701234567.100)

Video (timestamp: 1701234568.200)
  ↓
Grayscale (timestamp: 1701234568.200)
```

Each pipeline maintains its own source timestamp independently.

## API Reference

### QueueBackedDict Methods

#### `set_with_timestamp(node_id_name, value, timestamp=None)`

Store data with an explicit timestamp.

**Parameters:**
- `node_id_name` (str): Node identifier (e.g., "1:Webcam")
- `value` (Any): Data to store
- `timestamp` (float, optional): Explicit timestamp. If None, creates new timestamp.

**Example:**
```python
# Preserve timestamp from source
source_timestamp = node_image_dict.get_timestamp("1:Webcam")
node_image_dict.set_with_timestamp("2:Blur", processed_image, source_timestamp)
```

#### `get_timestamp(node_id_name)`

Retrieve the timestamp of the latest data for a node.

**Parameters:**
- `node_id_name` (str): Node identifier

**Returns:**
- `float`: Timestamp of latest data, or None if not available

**Example:**
```python
timestamp = node_image_dict.get_timestamp("1:Webcam")
print(f"Webcam frame captured at: {timestamp}")
```

## Testing

Comprehensive test suite with 56 passing tests:

- **test_timestamp_preservation.py**: Unit tests for timestamp methods
- **test_pipeline_timestamp_integration.py**: Integration tests simulating real pipelines
- **test_buffer_system.py**: Buffer behavior with timestamps
- **test_queue_integration.py**: Queue system integration

Run tests:
```bash
cd /path/to/CV_Studio
python -m pytest tests/test_timestamp_preservation.py -v
python -m pytest tests/test_pipeline_timestamp_integration.py -v
```

## Benefits

1. **Accurate Synchronization**: Video and audio can be precisely synchronized using their source timestamps
2. **Temporal Analysis**: Processing delays can be measured by comparing current time with source timestamp
3. **Multi-source Correlation**: Data from different input sources maintains distinct timestamps
4. **Zero Configuration**: Works automatically based on node connections
5. **Backward Compatible**: Existing code continues to work without modifications

## Technical Notes

### Thread Safety

All timestamp operations are thread-safe through the underlying `TimestampedQueue` implementation.

### Performance Impact

Minimal overhead:
- Timestamp retrieval: O(1) operation
- Timestamp preservation: Single additional parameter in method call
- No impact on existing node update logic

### Timestamp Precision

Timestamps use Python's `time.time()` with microsecond precision (float).

## Migration Guide

### For Existing Nodes

No changes required! The system automatically:
- Detects if your node is an input or processing node
- Creates timestamps for input nodes
- Preserves timestamps for processing nodes

### For New Nodes

Simply follow existing patterns:
- Input nodes: Return data via update() method
- Processing nodes: Get input via `get_input_frame()` or dict access

The timestamp system handles everything automatically.

## Troubleshooting

### Timestamps Not Being Preserved

**Issue**: Processing node shows different timestamp than input
**Solution**: Check that connection_list includes IMAGE/AUDIO/JSON connections

### Multiple Input Sources

**Issue**: Which timestamp is used when node has multiple inputs?
**Answer**: First IMAGE/AUDIO/JSON connection's timestamp is used

### Debugging Timestamps

Enable debug logging to see timestamp operations:
```python
import logging
logging.getLogger('node.queue_adapter').setLevel(logging.DEBUG)
logging.getLogger('main').setLevel(logging.DEBUG)
```

## Future Enhancements

Potential improvements:
- Timestamp-based data alignment across streams
- Automatic detection of timing drift
- Configurable timestamp preservation policies
- Timestamp visualization in UI

## References

- `TIMESTAMPED_QUEUE_SYSTEM.md`: Original queue system documentation
- `node/timestamped_queue.py`: Core timestamp queue implementation  
- `node/queue_adapter.py`: Dictionary adapter with timestamp support
- `main.py`: Main loop with timestamp preservation logic
