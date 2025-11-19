# Timestamped FIFO Queue System for Node Data Communication

## Overview

This document describes the timestamped queue system implemented for CV_Studio's node-based data communication architecture. The system ensures that data passed between nodes is timestamped and retrieved in FIFO (First-In-First-Out) order, with the oldest data being retrieved first.

## Problem Statement (French)

> "Chaque noeud qui renvoie des données aux autres noeuds le fait par une queue de sa propre classe, la donnée est timestampé, et le noeud qui récupère la data récupère la plus ancienne issus de la fifo."

**Translation:**

"Each node that sends data to other nodes does so through a queue of its own class, the data is timestamped, and the node that retrieves the data gets the oldest one from the FIFO."

## Architecture

### Core Components

#### 1. `TimestampedData` (dataclass)

A container for data with timestamp information:
- `data`: The actual payload (image, audio, json, etc.)
- `timestamp`: Unix timestamp when the data was created
- `node_id`: Identifier of the node that produced this data

#### 2. `TimestampedQueue` (class)

A thread-safe FIFO queue that stores timestamped data:
- Automatically timestamps data when added
- Maintains chronological order
- Supports FIFO retrieval (oldest data first)
- Thread-safe for concurrent access
- Configurable maximum size with automatic oldest-item removal

**Key Methods:**
- `put(data, timestamp=None)`: Add data with automatic or custom timestamp
- `get_oldest()`: Retrieve oldest data without removing it
- `get_latest()`: Retrieve newest data without removing it
- `pop_oldest()`: Remove and return oldest data (FIFO)
- `size()`, `is_empty()`, `clear()`: Queue management

#### 3. `NodeDataQueueManager` (class)

Centralized manager for all node queues:
- Maintains one queue per node per data type (image, audio, json)
- Thread-safe queue creation and access
- Provides high-level data operations
- Manages queue lifecycle

**Key Methods:**
- `get_queue(node_id_name, data_type)`: Get or create a queue
- `put_data(node_id_name, data_type, data, timestamp)`: Add data to a node's queue
- `get_oldest_data(node_id_name, data_type)`: Get oldest data (FIFO)
- `get_latest_data(node_id_name, data_type)`: Get newest data
- `clear_node_queues(node_id_name)`: Clear all queues for a node
- `get_queue_info(node_id_name, data_type)`: Get queue statistics

#### 4. `QueueBackedDict` (class)

Backward-compatible dictionary interface backed by timestamped queues:
- Maintains the old dict-based API (`node_image_dict`, etc.)
- Uses queues internally for FIFO behavior
- Caches latest values for immediate access
- Transparent to existing code

**Usage:**
```python
# Create queue-backed dictionaries
queue_manager = NodeDataQueueManager()
node_image_dict = QueueBackedDict(queue_manager, "image")
node_audio_dict = QueueBackedDict(queue_manager, "audio")

# Use like regular dicts
node_image_dict["1:Webcam"] = image_data  # Adds to queue with timestamp
image = node_image_dict["1:Webcam"]        # Gets oldest from queue (FIFO)
```

## Implementation Details

### Data Flow

1. **Node produces data** → Data is assigned to `node_image_dict[node_id_name]`
2. **QueueBackedDict** → Intercepts the assignment and:
   - Caches the value for immediate retrieval
   - Adds to the timestamped queue with current timestamp
3. **Node retrieves data** → Requests data via `node_image_dict[source_node_id]`
4. **QueueBackedDict** → Returns the **oldest data** from the queue (FIFO)
5. **Fallback** → If queue is empty, returns cached value

### Thread Safety

All queue operations are protected by thread locks (`threading.RLock()`):
- Multiple threads can safely read/write to queues
- No race conditions during concurrent access
- Consistent state even under high load

### Queue Size Management

Each queue has a configurable maximum size (default: 100):
- When full, oldest items are automatically removed
- Prevents memory overflow in long-running applications
- Ensures recent data is always available

## Integration with CV_Studio

### Changes to `main.py`

```python
# Import the queue system
from node.timestamped_queue import NodeDataQueueManager
from node.queue_adapter import QueueBackedDict

# Initialize the queue manager
queue_manager = NodeDataQueueManager(default_maxsize=100)

# Create queue-backed dictionaries
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
1. Access queue information:
   ```python
   info = node_image_dict.get_queue_info("1:Webcam")
   print(f"Queue size: {info['size']}")
   print(f"Oldest timestamp: {info['oldest_timestamp']}")
   ```

2. Get the latest data explicitly:
   ```python
   latest_image = node_image_dict.get_latest("1:Webcam")
   ```

3. Monitor queue status:
   ```python
   if info['size'] > 50:
       logger.warning("Queue is getting full!")
   ```

## Testing

Comprehensive test suites ensure correct behavior:

### Test Files

1. **`tests/test_timestamped_queue.py`** (17 tests)
   - TimestampedData creation and comparison
   - TimestampedQueue FIFO behavior
   - Thread safety
   - Queue size limits
   - NodeDataQueueManager operations

2. **`tests/test_queue_adapter.py`** (12 tests)
   - QueueBackedDict dict-like interface
   - FIFO retrieval
   - Cache fallback
   - Multiple data types
   - None value handling

### Running Tests

```bash
# Run all queue tests
python -m pytest tests/test_timestamped_queue.py tests/test_queue_adapter.py -v

# Run with coverage
python -m pytest tests/test_timestamped_queue.py tests/test_queue_adapter.py --cov=node --cov-report=html
```

## Performance Considerations

### Memory Usage
- Each queue stores up to 100 items by default
- Old items automatically removed when limit reached
- Typical node: ~3 queues × 100 items = 300 data items max

### CPU Usage
- Lock contention minimal (very fast lock operations)
- O(1) operations for put/get (deque is efficient)
- No significant overhead compared to dict-based approach

### Latency
- Negligible added latency (~microseconds for queue operations)
- Thread-safe operations are highly optimized
- No blocking except during brief lock acquisition

## Future Enhancements

Potential improvements:
1. **Time-based cleanup**: Remove data older than X seconds
2. **Priority queues**: Support for prioritized data retrieval
3. **Queue persistence**: Save/load queue state
4. **Statistics**: Throughput, latency, queue depth metrics
5. **Visualization**: Real-time queue status in UI

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
    # Get oldest image from connected node (FIFO)
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
# Check queue status
info = node_image_dict.get_queue_info(source_node)
if info['exists'] and not info['is_empty']:
    logger.info(f"Queue has {info['size']} items")
    logger.info(f"Age of oldest data: {time.time() - info['oldest_timestamp']:.2f}s")

# Get latest instead of oldest if needed
latest_image = node_image_dict.get_latest(source_node)
```

## Summary

The timestamped queue system provides:
- ✅ **FIFO data retrieval** - Oldest data retrieved first
- ✅ **Automatic timestamping** - All data timestamped on creation
- ✅ **Thread safety** - Safe concurrent access
- ✅ **Backward compatibility** - Works with existing code
- ✅ **Queue management** - Automatic size limits and cleanup
- ✅ **Comprehensive testing** - 29 passing tests
- ✅ **Documentation** - Complete API and usage guide

The implementation fulfills the requirement: "Each node that sends data to other nodes does so through a queue of its own class, the data is timestamped, and the node that retrieves the data gets the oldest one from the FIFO."
