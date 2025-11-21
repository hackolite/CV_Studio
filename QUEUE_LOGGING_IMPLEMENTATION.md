# Buffer Queue Logging Implementation

## Overview
This implementation adds comprehensive logging to the CV_Studio buffer queue system to track all data insertions with timestamp and data type information.

## Problem Statement (French)
"Affiche dans les logs, les données insérées dans les queues tampon avec les données timestamp et le type de donnée dont il s'agit"

Translation: "Display in the logs the data inserted in the buffer queues with the timestamp data and the type of data involved"

## Solution
The solution adds logging at three levels:

### 1. TimestampedQueue Level (node/timestamped_queue.py)
Every time data is inserted into a queue, a log entry is created showing:
- Queue identifier (node_id)
- Data type (Python type name)
- Precise timestamp (6 decimal places)
- Current queue size vs maximum size

**Example:**
```
Queue [Camera:1] - Inserted data: type=str, timestamp=1763751256.570693, queue_size=1/5
```

### 2. NodeDataQueueManager Level (node/timestamped_queue.py)
When data is inserted through the manager, it logs:
- Node identifier
- Data type classification (image, audio, json, etc.)
- Timestamp

**Example:**
```
Manager - Node [Webcam:1] received image data at timestamp=1763751256.570916
```

### 3. QueueBackedDict Adapter Level (node/queue_adapter.py)
When data is set through the dictionary-like interface, it logs:
- Data type classification
- Node identifier
- Value type

**Example:**
```
QueueAdapter [image] - Node [ProcessingNode:1] set value of type=str
```

## Files Modified

1. **node/timestamped_queue.py**
   - Added logging module import
   - Enhanced `TimestampedQueue.put()` method with logging
   - Enhanced `NodeDataQueueManager.put_data()` method with logging
   - Ensured timestamp consistency across log entries

2. **node/queue_adapter.py**
   - Added logging module import
   - Enhanced `QueueBackedDict.__setitem__()` method with logging

## Files Created

1. **tests/test_queue_logging.py**
   - 7 comprehensive tests for logging functionality
   - Tests verify timestamps, data types, and queue states
   - All tests pass (100% success rate)

2. **tests/demo_queue_logging.py**
   - Demonstration script showing logging in various scenarios
   - Can be run to see actual log output
   - Includes realistic multi-stream synchronization example

## Usage

To see the logging in action, you can:

1. **Run the demonstration script:**
   ```bash
   PYTHONPATH=/home/runner/work/CV_Studio/CV_Studio python tests/demo_queue_logging.py
   ```

2. **Run the tests:**
   ```bash
   python -m pytest tests/test_queue_logging.py -v
   ```

3. **Use in your code:**
   ```python
   import logging
   from node.timestamped_queue import NodeDataQueueManager
   
   # Configure logging to see the output
   logging.basicConfig(level=logging.INFO)
   
   # Create manager and use it
   manager = NodeDataQueueManager()
   manager.put_data("MyNode:1", "image", frame_data)
   # Logs: Manager - Node [MyNode:1] received image data at timestamp=...
   ```

## Log Configuration

The logging uses Python's standard `logging` module with logger names:
- `node.timestamped_queue` - For TimestampedQueue and NodeDataQueueManager
- `node.queue_adapter` - For QueueBackedDict

To configure logging in your application:
```python
import logging

# Basic configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Or use the CV_Studio logging utility
from src.utils.logging import setup_logging
setup_logging(level=logging.INFO)
```

## Test Results

All tests pass successfully:
- **Existing tests**: 42/42 ✅
- **New logging tests**: 7/7 ✅
- **Total**: 49/49 tests ✅

## Security

CodeQL security analysis completed with **0 alerts**.
No security vulnerabilities introduced.

## Performance Impact

The logging overhead is minimal:
- Only executed when data is inserted (not on reads)
- Uses standard Python logging (efficient and well-optimized)
- Can be disabled by setting logging level to WARNING or higher
- Thread-safe (uses existing queue locks)

## Timestamp Precision

Timestamps are logged with 6 decimal places (microsecond precision):
- Format: `timestamp=1763751256.570693`
- Consistent across all log levels (manager and queue use same timestamp)
- Suitable for synchronization analysis

## Data Types Logged

The system automatically detects and logs Python type names:
- Primitives: `str`, `int`, `float`, `bool`
- Collections: `list`, `dict`, `tuple`, `set`
- Custom objects: Full class name (e.g., `numpy.ndarray`)
- None: `NoneType`

## Integration Notes

The logging is fully backward compatible:
- No changes required to existing code
- Works with all three interfaces (TimestampedQueue, NodeDataQueueManager, QueueBackedDict)
- Logging can be enabled/disabled via logging configuration
- No performance impact when logging is disabled
