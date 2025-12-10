# CV_Studio Architecture Documentation

## Overview

CV_Studio is a node-based visual programming environment for computer vision and audio processing. This document explains the data flow architecture, particularly the video pipeline that processes input video through queues to the final video output.

## Data Flow Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           VIDEO PIPELINE FLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌─────────────────────┐     ┌───────────────┐     ┌──────────────┐
│  VideoNode   │────▶│  TimestampedQueue   │────▶│  ImageConcat  │────▶│ VideoWriter  │
│ (node_video) │     │   (queue_adapter)   │     │   (concat)    │     │   (output)   │
└──────────────┘     └─────────────────────┘     └───────────────┘     └──────────────┘
       │                      │                         │                      │
       │                      │                         │                      │
   ┌───▼───┐              ┌───▼───┐                ┌───▼───┐              ┌───▼───┐
   │ Frame │              │ FIFO  │                │ Multi │              │ ffmpeg│
   │ Audio │              │Buffer │                │ Slot  │              │ merge │
   │ Chunk │              │  800  │                │ Merge │              │ video │
   └───────┘              └───────┘                └───────┘              └───────┘
```

## Component Details

### 1. VideoNode (`node/InputNode/node_video.py`)

**Purpose**: Read video files and extract frames + audio chunks.

**Data Output**:
```python
{
    "image": frame,           # numpy array (H, W, 3) BGR
    "json": None,             # metadata (unused)
    "audio": audio_chunk,     # dict with 'data' and 'sample_rate'
    "timestamp": frame_ts     # FPS-based timestamp for sync
}
```

**Key Operations**:
1. Extract video frames using OpenCV
2. Pre-process audio using ffmpeg → WAV chunks (5s default)
3. Map frame numbers to audio chunks
4. Provide FPS-based timestamps for synchronization

**Potential Issues**:
- Audio chunk duration mismatch with frame timing
- Memory usage from WAV file storage
- ffmpeg extraction failures

### 2. TimestampedQueue (`node/timestamped_queue.py` + `queue_adapter.py`)

**Purpose**: FIFO buffer for node-to-node communication with timestamps.

**Architecture**:
```
┌────────────────────────────────────────────────┐
│            NodeDataQueueManager                 │
├────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐  │
│  │  Per-Node Queues (default: 800 items)    │  │
│  │  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │ image queue │  │ audio queue │  ...   │  │
│  │  └─────────────┘  └─────────────┘        │  │
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

**Queue Size Calculation**:
```
DEFAULT_QUEUE_SIZE = 800 items
Reasoning:
- SyncQueue max retention time: 10s
- Buffer overhead: 1s
- Max buffer age: 11s
- At 60 FPS: 11s × 60 = 660 frames minimum
- With 20% safety margin: 800 frames
```

**Data Structure**:
```python
@dataclass
class TimestampedData:
    data: Any           # Frame, audio chunk, or JSON
    timestamp: float    # Unix timestamp
    node_id: str        # Source node identifier
```

**Potential Issues**:
- Queue overflow when processing is slower than input
- Timestamp drift between audio and video
- Memory pressure from 800-item buffer per node

### 3. ImageConcat (`node/VideoNode/node_image_concat.py`)

**Purpose**: Concatenate multiple video/audio streams into a single output.

**Slot System**:
```
┌────────────────────────────────────────────────┐
│               ImageConcat Node                  │
├────────────────────────────────────────────────┤
│  Slot 1: IMAGE ──────────┐                     │
│  Slot 2: IMAGE ──────────┼─▶ Concatenated      │
│  Slot 3: AUDIO ──────────┤   Frame + Audio     │
│  Slot 4: JSON ───────────┘   Dictionary        │
└────────────────────────────────────────────────┘
```

**Output Format**:
```python
{
    "image": concatenated_frame,   # Combined frames
    "json": json_chunks,           # {slot_idx: json_data}
    "audio": audio_chunks          # {slot_idx: audio_chunk}
}
```

**Grid Layout**:
```
Slots 1-2:  [1][2]       (horizontal)
Slots 3-4:  [1][2]       (2x2 grid)
            [3][4]
Slots 5-6:  [1][2][3]    (2x3 grid)
            [4][5][6]
```

**Potential Issues**:
- Frame resize inconsistencies
- Audio timestamp ordering when merging slots
- TYPE mismatch between slots

### 4. VideoWriter (`node/VideoNode/node_video_writer.py` + `video_worker.py`)

**Purpose**: Encode frames + audio to video file using background threads.

**Thread Architecture**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    VideoBackgroundWorker                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐  │
│  │  Main Thread │─────▶│  Frame Queue │─────▶│   Encoder    │  │
│  │ push_frame() │      │ (150-300)    │      │   Thread     │  │
│  └──────────────┘      └──────────────┘      └──────────────┘  │
│                                                      │          │
│                                                      ▼          │
│                                               ┌──────────────┐  │
│                                               │    Muxer     │  │
│                                               │   Thread     │  │
│                                               └──────────────┘  │
│                                                      │          │
│                                                      ▼          │
│                                               ┌──────────────┐  │
│                                               │   Output     │  │
│                                               │   (ffmpeg)   │  │
│                                               └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Queue Sizing**:
```python
# Frame queue size = fps × chunk_duration
# Clamped to MIN_FRAME_QUEUE_SIZE (50) and MAX_FRAME_QUEUE_SIZE (300)
frame_queue_size = max(50, min(int(fps * chunk_duration), 300))
```

**Worker States**:
```
IDLE → STARTING → ENCODING → FLUSHING → COMPLETED
                     ↓           ↓
                  PAUSED      ERROR
                     ↓
                 CANCELLED
```

## Crash Causes Analysis

### 1. Queue Backpressure Crash

**Symptom**: Application freezes or crashes during recording.

**Cause**: VideoWriter queue is full, main thread blocks on `push_frame()`.

**Root Cause**:
```
Frame Queue Size: fps × chunk_duration = 24 × 5 = 120 frames
If encoding is slower than input → queue fills up
drop_on_full=True drops frames → video/audio desync
```

**Solution**:
- Increase queue size or use adaptive backpressure
- Add logging for dropped frames
- Implement frame skipping strategy

### 2. Audio/Video Sync Crash

**Symptom**: Output video has audio drift or crash during ffmpeg merge.

**Cause**: Audio timestamps don't match video frame timestamps.

**Root Cause**:
```python
# Video: FPS-based timestamps
frame_timestamp = frame_number / target_fps

# Audio: Sample-based timestamps
audio_timestamp = samples_written / sample_rate

# Drift accumulates over time
```

**Solution**:
- Use monotonic timestamps from same source
- Implement audio resampling to match video duration
- Add timestamp validation before merge

### 3. Memory Exhaustion Crash

**Symptom**: Python memory error or system OOM.

**Cause**: Large queue buffers × number of nodes.

**Root Cause**:
```
Per node memory = 800 items × frame_size
Frame size = 1920 × 1080 × 3 = 6.2 MB
Per node = 800 × 6.2 MB = 4.96 GB ❌
```

**Solution**:
- Reduce queue size for high-resolution video
- Use frame references instead of copies
- Implement lazy loading for audio chunks

### 4. Thread Race Condition Crash

**Symptom**: Sporadic crashes with "NoneType has no attribute" errors.

**Cause**: Encoder thread accesses data while muxer modifies it.

**Root Cause**:
```python
# Encoder thread
video_writer.write(frame)  # frame might be None

# Muxer thread
self._temp_video_path = None  # cleanup while encoder running
```

**Solution**:
- Use proper locks around shared state
- Add null checks before operations
- Implement proper shutdown sequence

### 5. FFmpeg Subprocess Crash

**Symptom**: "ffmpeg.run() failed" or corrupted output file.

**Cause**: FFmpeg process killed or input files incomplete.

**Root Cause**:
```python
# Video file not fully flushed
video_writer.release()
time.sleep(0.1)  # Insufficient delay
ffmpeg.run(...)  # Video file still being written
```

**Solution**:
- Wait for video file size to stabilize
- Use file locks or explicit flush
- Add retry logic for ffmpeg operations

## Logging Strategy

### Current Logging Points

```python
# node_video.py
logger.info("🎬 Pre-processing video: {movie_path}")
logger.info("✅ Video metadata extracted")
logger.info("🎵 Extracting audio with ffmpeg")

# timestamped_queue.py
logger.info(f"Queue [{node_id}] - Inserted data: type={data_type}, timestamp={ts}")

# video_worker.py
logger.info(f"[VideoWorker] Metrics - Frames: {frames}, Queue size: {size}")
logger.warning(f"[{name}] Queue full, dropped item")
```

### Recommended Additional Logging

```python
# Add to node_video_writer.py
logger.debug(f"[VideoWriter] Frame {frame_num} pushed, queue={queue.size()}")
logger.warning(f"[VideoWriter] Frame drop detected, buffer={queue.size()}/{queue.max_size}")
logger.error(f"[VideoWriter] Audio/video sync drift: {drift_ms}ms")

# Add to node_image_concat.py  
logger.debug(f"[ImageConcat] Slot {slot_idx} received {data_type}")
logger.warning(f"[ImageConcat] Missing slot {slot_idx} data, using black frame")

# Add to video_worker.py
logger.info(f"[Encoder] FPS: {actual_fps:.1f}, Queue health: {queue.size()}/{queue.max_size}")
logger.error(f"[Muxer] FFmpeg failed: {stderr}")
```

## Robustness Improvements

### 1. Graceful Degradation

```python
# Instead of crashing, drop frames and continue
if queue.full():
    logger.warning("Queue full, dropping oldest frame")
    queue.pop()  # Make room
    queue.push(frame)
```

### 2. Health Monitoring

```python
class PipelineHealthMonitor:
    def check_queue_health(self, queue):
        if queue.size() > queue.max_size * 0.9:
            self.emit_warning("Queue near capacity")
        if queue.dropped_count > 10:
            self.emit_error("Excessive frame drops")
```

### 3. Automatic Recovery

```python
try:
    ffmpeg.run(output)
except Exception as e:
    logger.error(f"FFmpeg failed: {e}, retrying...")
    time.sleep(1)
    ffmpeg.run(output)  # Retry once
```

## Configuration Recommendations

```json
{
    "queue_size": 400,
    "video_writer_fps": 30,
    "audio_chunk_duration": 5.0,
    "max_frame_queue": 150,
    "enable_frame_drop": true,
    "ffmpeg_timeout": 30
}
```

## Conclusion

The video pipeline is complex due to:
1. Multiple asynchronous data streams (video, audio, JSON)
2. Timestamp synchronization requirements
3. Background thread coordination
4. Memory management for large buffers

Crashes typically occur due to:
- Queue overflow (backpressure)
- Thread synchronization issues
- Audio/video timestamp drift
- FFmpeg subprocess failures

Robustness can be improved by:
- Better logging at critical points
- Graceful degradation when queues fill
- Proper error handling in threads
- Monitoring queue health metrics
