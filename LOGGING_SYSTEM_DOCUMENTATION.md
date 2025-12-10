# Logging System Documentation

## Overview

CV Studio now includes a comprehensive logging system that provides:
- **Automatic log file creation** with timestamps
- **Log rotation** to prevent disk space issues
- **Multiple log levels** for different verbosity needs
- **Structured logging** across all modules
- **Automatic cleanup** of old log files

## Quick Start

The logging system is automatically initialized when CV Studio starts. By default:
- Logs are written to the `logs/` directory in the project root
- Default log level is **ERROR** (only critical issues are logged)
- Log files are automatically rotated when they reach 10 MB
- Up to 5 backup log files are kept
- Log files older than 30 days are automatically cleaned up

## Log Levels

The logging system supports standard Python log levels:

| Level | Description | Use Case |
|-------|-------------|----------|
| DEBUG | Detailed diagnostic information | Development and debugging |
| INFO | General informational messages | Normal operation tracking |
| WARNING | Warning messages for non-critical issues | Potential problems |
| ERROR | Error messages for serious problems | **Default level** |
| CRITICAL | Critical errors that may cause crashes | System failures |

## Configuration

### Changing Log Level

To change the log level, modify the `setup_logging()` call in `main.py`:

```python
from src.utils.logging import setup_logging
import logging

# For production (default)
setup_logging(level=logging.ERROR)

# For development
setup_logging(level=logging.DEBUG)

# For normal operation tracking
setup_logging(level=logging.INFO)
```

### Custom Log File Location

```python
from src.utils.logging import setup_logging

# Specify custom log file
setup_logging(
    level=logging.INFO,
    log_file="/path/to/custom/logfile.log"
)
```

### Disabling File Logging

```python
from src.utils.logging import setup_logging

# Console only (no file logging)
setup_logging(
    level=logging.INFO,
    enable_file_logging=False
)
```

### Adjusting Rotation Settings

```python
from src.utils.logging import setup_logging

# Larger log files, more backups
setup_logging(
    level=logging.INFO,
    max_bytes=50 * 1024 * 1024,  # 50 MB
    backup_count=10
)
```

## Log File Location

Log files are stored in the `logs/` directory in the project root:

```
CV_Studio/
├── logs/
│   ├── cv_studio_20231210_143022.log      # Current log
│   ├── cv_studio_20231210_143022.log.1    # Backup 1
│   ├── cv_studio_20231210_143022.log.2    # Backup 2
│   └── ...
├── main.py
└── ...
```

### Log File Naming

Log files are automatically named with timestamps:
- Format: `cv_studio_YYYYMMDD_HHMMSS.log`
- Example: `cv_studio_20231210_143022.log` (Dec 10, 2023 at 14:30:22)

## Using Logging in Your Code

### Getting a Logger

```python
from src.utils.logging import get_logger

logger = get_logger(__name__)
```

### Logging Messages

```python
# Debug level - detailed diagnostic info
logger.debug("Processing frame 123 with dimensions 1920x1080")

# Info level - general information
logger.info("Video encoding started for output.mp4")

# Warning level - potential issues
logger.warning("Queue is 80% full, may drop frames soon")

# Error level - serious problems
logger.error("Failed to write video frame: disk full")

# Critical level - system failures
logger.critical("FFmpeg process crashed, cannot continue")
```

### Logging Exceptions

```python
try:
    # Some operation
    process_video()
except Exception as e:
    logger.error(f"Video processing failed: {e}")
    logger.error(traceback.format_exc())  # Include stack trace
```

## Log Cleanup

Old log files are automatically cleaned up at startup:
- Default retention: 30 days
- Runs automatically when CV Studio starts
- Can be manually triggered

### Manual Cleanup

```python
from src.utils.logging import cleanup_old_logs

# Clean up logs older than 30 days
cleanup_old_logs(max_age_days=30)

# More aggressive cleanup
cleanup_old_logs(max_age_days=7)
```

## Module-Specific Logging

### Video Worker

The video worker logs detailed information about encoding:

```
[VideoWorker] Started background encoding for output.mp4
[VideoWorker] Encoder started
[VideoWorker] Metrics - Frames: 450, Audio chunks: 45, Queue size: 3, Dropped: 0
[VideoWorker] Video encoding complete, 1500 frames
[VideoWorker] Writing audio file with 150 chunks
[VideoWorker] Merging video and audio with ffmpeg
[VideoWorker] Merge complete in 2.34s: output.mp4
[VideoWorker] Output file size: 45.67 MB
[VideoWorker] Encoding completed successfully
```

### System Verification

System verification logs all checks at startup:

```
Running system verification...
[OK        ] FFmpeg: FFmpeg is installed and working
[OK        ] Package: opencv-contrib-python is installed
[OK        ] OpenCV: OpenCV 4.8.0 with required modules
Summary - OK: 8, Warnings: 2, Errors: 0, Not Found: 0
```

## Best Practices

### 1. Use Appropriate Log Levels

```python
# ❌ Don't use ERROR for informational messages
logger.error("Video encoding started")

# ✅ Use INFO for normal operation
logger.info("Video encoding started")

# ❌ Don't use DEBUG for errors
logger.debug("Failed to open file")

# ✅ Use ERROR for failures
logger.error("Failed to open file: permission denied")
```

### 2. Include Context in Messages

```python
# ❌ Vague message
logger.error("Operation failed")

# ✅ Specific message with context
logger.error(f"Failed to encode frame {frame_num} for {output_path}: {error}")
```

### 3. Use String Formatting

```python
# ❌ String concatenation
logger.info("Processing " + str(count) + " frames")

# ✅ f-strings or % formatting
logger.info(f"Processing {count} frames")
logger.info("Processing %d frames", count)
```

### 4. Log Performance Metrics

```python
import time

start = time.time()
# ... operation ...
elapsed = time.time() - start

logger.info(f"Operation completed in {elapsed:.2f}s")
```

## Troubleshooting

### Log File Not Created

Check that:
1. The `logs/` directory exists (it should be created automatically)
2. You have write permissions to the project directory
3. File logging is enabled: `enable_file_logging=True`

### Disk Space Issues

If logs are consuming too much disk space:
1. Reduce `max_bytes` to create smaller log files
2. Reduce `backup_count` to keep fewer backups
3. Run `cleanup_old_logs()` with a shorter retention period
4. Consider raising the default log level to ERROR or CRITICAL

### Missing Log Messages

If expected messages don't appear:
1. Check the log level - messages below the set level won't appear
2. Ensure the logger is properly initialized
3. Check that the module is using `get_logger(__name__)`

## Advanced Features

### Custom Formatters

```python
from src.utils.logging import setup_logging

# Custom format with more detail
custom_format = '%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s'

setup_logging(
    level=logging.INFO,
    format_string=custom_format
)
```

### Multiple Loggers

Different modules automatically get their own loggers:

```python
# In video_worker.py
logger = get_logger(__name__)  # Logger name: "node.VideoNode.video_worker"

# In main.py
logger = get_logger(__name__)  # Logger name: "__main__"
```

### Filtering by Module

Since each module has its own logger, you can filter log files:

```bash
# Show only video worker logs
grep "video_worker" logs/cv_studio_*.log

# Show only errors
grep "ERROR" logs/cv_studio_*.log

# Show errors from video worker
grep "video_worker.*ERROR" logs/cv_studio_*.log
```

## Summary

The logging system provides:
- ✅ Automatic file logging with rotation
- ✅ Structured, module-specific logs
- ✅ Multiple log levels for different needs
- ✅ Automatic cleanup of old logs
- ✅ Easy integration in new modules
- ✅ Performance metrics and diagnostics
- ✅ Comprehensive error tracking

For more information, see:
- `src/utils/logging.py` - Logging implementation
- `src/utils/system_verification.py` - System verification logging
- `node/VideoNode/video_worker.py` - Video worker logging examples
