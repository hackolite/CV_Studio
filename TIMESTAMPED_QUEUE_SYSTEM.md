# Timestamped Buffer System for Node Data Communication

## Overview

This document describes the timestamped buffer system implemented for CV_Studio's node-based data communication architecture. The system ensures that data passed between nodes is timestamped and maintained in a rolling buffer of 10 items, with each element accessible via its timestamp for synchronization purposes.

## Problem Statement (French)

> "alors je ne veux pas fifo mais plutôt un tampon qui prend en mémoire 10 valeur en tampon chaque element possede un timestamp pour pouvoir synchroniser plus tard, verifier que ça fonctionne"

**Translation:**

"so I don't want FIFO but rather a buffer that holds 10 values in memory buffer, each element has a timestamp to be able to synchronize later, verify that it works"

## Architecture

### Core Components

#### 1. `TimestampedData` (dataclass)

A container for data with timestamp information:
- `data`: The actual payload (image, audio, json, etc.)
- `timestamp`: Unix timestamp when the data was created
- `node_id`: Identifier of the node that produced this data

#### 2. `TimestampedQueue` (class)

A thread-safe buffer that stores timestamped data:
- Automatically timestamps data when added
- Maintains chronological order
- Supports non-consuming retrieval (latest or oldest data)
- Thread-safe for concurrent access
- Configurable maximum size (default: 10) with automatic oldest-item removal when full

**Key Methods:**
- `put(data, timestamp=None)`: Add data with automatic or custom timestamp
- `get_oldest()`: Retrieve oldest data **without removing it**
- `get_latest()`: Retrieve newest data **without removing it**
- `pop_oldest()`: Remove and return oldest data (for cleanup if needed)
- `get_all()`: Get all buffered items with timestamps
- `size()`, `is_empty()`, `clear()`: Buffer management

#### 3. `NodeDataQueueManager` (class)

Centralized manager for all node buffers:
- Maintains one buffer per node per data type (image, audio, json)
- Default buffer size: 10 items per buffer
- Thread-safe buffer creation and access
- Provides high-level data operations
- Manages buffer lifecycle

**Key Methods:**
- `get_queue(node_id_name, data_type)`: Get or create a buffer
- `put_data(node_id_name, data_type, data, timestamp)`: Add data to a node's buffer
- `get_oldest_data(node_id_name, data_type)`: Get oldest data (without removing)
- `get_latest_data(node_id_name, data_type)`: Get newest data (without removing)
- `clear_node_queues(node_id_name)`: Clear all buffers for a node
- `get_queue_info(node_id_name, data_type)`: Get buffer statistics

#### 4. `QueueBackedDict` (class)

Backward-compatible dictionary interface backed by timestamped buffers:
- Maintains the old dict-based API (`node_image_dict`, etc.)
- Uses buffers internally for data storage
- Returns the **latest** value when accessed (buffer behavior)
- Caches latest values for immediate access
- Transparent to existing code

**Usage:**
```python
# Create buffer-backed dictionaries
queue_manager = NodeDataQueueManager()  # Default: 10 items per buffer
node_image_dict = QueueBackedDict(queue_manager, "image")
node_audio_dict = QueueBackedDict(queue_manager, "audio")

# Use like regular dicts
node_image_dict["1:Webcam"] = image_data  # Adds to buffer with timestamp
image = node_image_dict["1:Webcam"]       # Gets latest from buffer (doesn't remove)

# Access all buffered items with timestamps for synchronization
queue = queue_manager.get_queue("1:Webcam", "image")
all_items = queue.get_all()  # Returns list of TimestampedData objects
for item in all_items:
    print(f"Data: {item.data}, Timestamp: {item.timestamp}")
```

## Implementation Details

### Data Flow

1. **Node produces data** → Data is assigned to `node_image_dict[node_id_name]`
2. **QueueBackedDict** → Intercepts the assignment and:
   - Caches the value for immediate retrieval
   - Adds to the timestamped buffer with current timestamp
3. **Node retrieves data** → Requests data via `node_image_dict[source_node_id]`
4. **QueueBackedDict** → Returns the **latest data** from the buffer (buffer behavior, doesn't remove)
5. **Fallback** → If buffer is empty, returns cached value
6. **Synchronization** → All buffered items remain accessible with timestamps via `get_all()`

### Thread Safety

All queue operations are protected by thread locks (`threading.RLock()`):
- Multiple threads can safely read/write to queues
- No race conditions during concurrent access
- Consistent state even under high load

### Buffer Size Management

Each buffer has a configurable maximum size (default: 10):
- When full, oldest items are automatically removed (rolling buffer)
- Maintains the most recent 10 items with their timestamps
- All items remain accessible for synchronization purposes
- Ensures predictable memory usage

## Integration with CV_Studio

### Changes to `main.py`

```python
# Import the buffer system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Initialize the buffer manager
queue_manager = NodeDataQueueManager(default_maxsize=10)

# Create buffer-backed dictionaries
node_image_dict = QueueBackedDict(queue_manager, "image")
node_result_dict = QueueBackedDict(queue_manager, "json")
node_audio_dict = QueueBackedDict(queue_manager, "audio")

# Use normally - no other changes needed!
```

### Backward Compatibility

✅ **Fully backward compatible** with existing code:
- Existing nodes work without modifications
- Dictionary interface unchanged
- No breaking changes to the API
- Optional: Nodes can use new queue features if needed

### New Capabilities

Nodes can now:
1. Access buffer information:
   ```python
   info = node_image_dict.get_queue_info("1:Webcam")
   print(f"Buffer size: {info['size']}")
   print(f"Oldest timestamp: {info['oldest_timestamp']}")
   print(f"Latest timestamp: {info['latest_timestamp']}")
   ```

2. Get the latest data explicitly:
   ```python
   latest_image = node_image_dict.get_latest("1:Webcam")
   ```

3. Access all buffered items for synchronization:
   ```python
   queue = queue_manager.get_queue("1:Webcam", "image")
   all_items = queue.get_all()  # Get all 10 buffered items with timestamps
   
   # Synchronize with audio based on timestamps
   for video_item in all_items:
       # Find matching audio by timestamp
       matching_audio = find_audio_by_timestamp(video_item.timestamp)
   ```

4. Monitor buffer status:
   ```python
   if info['size'] >= 10:
       logger.warning("Buffer is full!")
   ```

## Testing

Comprehensive test suites ensure correct buffer behavior:

### Test Files

1. **`tests/test_timestamped_queue.py`** (17 tests)
   - TimestampedData creation and comparison
   - TimestampedQueue buffer behavior
   - Thread safety
   - Buffer size limits (10 items)
   - NodeDataQueueManager operations

2. **`tests/test_queue_adapter.py`** (12 tests)
   - QueueBackedDict dict-like interface
   - Buffer retrieval (latest data)
   - Cache fallback
   - Multiple data types
   - None value handling

3. **`tests/test_buffer_system.py`** (13 tests)
   - Buffer maintains 10 items maximum
   - Non-consuming reads (data not removed on access)
   - All items accessible with timestamps
   - Multi-stream synchronization
   - Timestamp ordering

4. **`tests/test_queue_integration.py`** (6 tests)
   - Integration with CV_Studio nodes
   - Buffer behavior in pipelines
   - Concurrent node updates

### Running Tests

```bash
# Run all buffer tests
python -m pytest tests/test_timestamped_queue.py tests/test_queue_adapter.py tests/test_buffer_system.py tests/test_queue_integration.py -v

# Run with PYTHONPATH
cd /path/to/CV_Studio
PYTHONPATH=. python tests/test_buffer_system.py
```

## Performance Considerations

### Memory Usage
- Each buffer stores up to 10 items by default
- Old items automatically removed when limit reached
- Typical node: ~3 buffers × 10 items = 30 data items max per node
- Predictable and minimal memory footprint

### CPU Usage
- Lock contention minimal (very fast lock operations)
- O(1) operations for put/get (deque is efficient)
- No significant overhead compared to dict-based approach

### Latency
- Negligible added latency (~microseconds for buffer operations)
- Thread-safe operations are highly optimized
- No blocking except during brief lock acquisition
- Reading doesn't remove items, so synchronization is efficient

## Future Enhancements

Potential improvements:
1. **Time-based cleanup**: Remove data older than X seconds
2. **Configurable buffer sizes per node**: Allow different buffer sizes for different nodes
3. **Buffer persistence**: Save/load buffer state
4. **Statistics**: Throughput, latency, buffer depth metrics
5. **Visualization**: Real-time buffer status in UI
6. **Timestamp-based queries**: Find items by timestamp range

## Examples

### Basic Usage

```python
# Producer node
def update(self, node_id, connection_list, node_image_dict, node_result_dict):
    image = capture_image()
    node_image_dict[f"{node_id}:{self.node_tag}"] = image
    return {"image": image, "json": None}
```

### Consumer node

```python
def update(self, node_id, connection_list, node_image_dict, node_result_dict):
    # Get latest image from connected node (buffer behavior)
    source_node = connection_list[0][0].split(":")[:2]
    source_node = ":".join(source_node)
    
    input_image = node_image_dict.get(source_node)
    if input_image is None:
        return {"image": None, "json": None}
    
    processed = process_image(input_image)
    return {"image": processed, "json": None}
```

### Advanced Usage

```python
# Check buffer status
info = node_image_dict.get_queue_info(source_node)
if info['exists'] and not info['is_empty']:
    logger.info(f"Buffer has {info['size']} items")
    logger.info(f"Age of oldest data: {time.time() - info['oldest_timestamp']:.2f}s")

# Get latest instead of using default dict access
latest_image = node_image_dict.get_latest(source_node)

# Access all buffered items for synchronization
queue = queue_manager.get_queue(source_node, "image")
all_items = queue.get_all()  # Returns up to 10 items with timestamps

# Synchronize video and audio by timestamps
for video_item in all_items:
    timestamp = video_item.timestamp
    # Find matching audio
    audio_queue = queue_manager.get_queue(audio_source, "audio")
    audio_items = audio_queue.get_all()
    
    # Find closest audio by timestamp
    closest_audio = min(audio_items, key=lambda x: abs(x.timestamp - timestamp))
    process_synced(video_item.data, closest_audio.data)
```

## Summary

The timestamped buffer system provides:
- ✅ **Buffer storage** - Maintains last 10 timestamped items per node
- ✅ **Non-consuming reads** - Reading data doesn't remove it from buffer
- ✅ **Automatic timestamping** - All data timestamped on creation
- ✅ **Timestamp synchronization** - All buffered items accessible with timestamps for sync
- ✅ **Thread safety** - Safe concurrent access
- ✅ **Backward compatibility** - Works with existing code
- ✅ **Automatic size management** - Rolling buffer removes oldest when full
- ✅ **Comprehensive testing** - 48 passing tests across 4 test suites
- ✅ **Documentation** - Complete API and usage guide

The implementation fulfills the requirement: "a buffer that holds 10 values in memory buffer, each element has a timestamp to be able to synchronize later"
