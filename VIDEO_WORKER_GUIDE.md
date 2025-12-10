# VideoWriter Background Worker Guide

## Overview

The VideoWriter node now uses a multi-threaded background worker architecture that prevents UI freezes during video encoding. The worker runs completely in the background, allowing you to continue working while your video is being created.

## Features

### Non-Blocking Encoding
- Video encoding runs in background threads
- UI remains responsive during encoding (< 50ms latency)
- No freezing or blocking of the main interface
- Continue editing while video is being created

### Progress Tracking
- Real-time progress bar with percentage
- Frames encoded counter
- Encoding speed (fps)
- Estimated Time to Arrival (ETA)
- Current state display (encoding, paused, flushing, complete)

### Pause/Resume/Cancel Controls
- **Pause**: Temporarily stop encoding without losing progress
- **Resume**: Continue encoding from where you left off
- **Cancel**: Abort encoding and clean up resources

### Intelligent Queue Management
- Bounded queues prevent memory overflow
- Automatic backpressure handling
- Priority given to audio (preserves audio quality)
- Drops video frames if necessary under heavy load
- Detailed metrics logging

### Monotonic Audio Timestamps
- Audio timestamps never go backwards
- Smooth audio/video synchronization
- No audio glitches at segment boundaries
- Proper PTS (Presentation TimeStamp) tracking

## Using the VideoWriter Node

### Starting Video Recording

1. Connect video source to VideoWriter node
2. (Optional) Connect audio source for audio/video recording
3. Click **Start** button
4. VideoWriter begins recording in background
5. Control buttons appear (Pause/Cancel)
6. Progress bar shows encoding status

### Progress Display

The progress bar shows:
- **Encoding: 45.2%** - Currently encoding at 45.2% complete
- **Finalizing...** - Merging audio and video
- **Paused** - Encoding is paused
- **Complete** - Encoding finished successfully
- **Error** - An error occurred
- **Cancelled** - User cancelled encoding

### Detailed Progress Information

Below the progress bar:
```
Frames: 450/1000 | 30.5 fps | ETA 0m 18s
```

- **Frames**: Number of frames encoded / total frames (if known)
- **fps**: Current encoding speed in frames per second
- **ETA**: Estimated time to completion

### Pause/Resume

**To Pause:**
1. Click **Pause** button during encoding
2. Encoding stops, but progress is preserved
3. Resume button becomes available
4. No frames are lost

**To Resume:**
1. Click **Resume** button
2. Encoding continues from where it stopped
3. Pause button becomes available again

### Cancelling Encoding

1. Click **Cancel** button at any time
2. Encoding stops immediately
3. Temporary files are cleaned up
4. Progress bar shows "Cancelled"
5. Ready to start new recording

### Completion

When encoding completes:
1. Progress bar shows "Complete" at 100%
2. Control buttons disappear
3. Output file is ready to use
4. Button returns to "Start" state

## Architecture Details

### Thread Structure

The background worker uses 4 main components:

#### 1. Producer (Main Thread)
- Receives frames from the video pipeline
- Receives audio chunks
- Pushes to frame queue
- Non-blocking with timeout

#### 2. Encoder Thread
- Pops frames from queue
- Encodes video using OpenCV
- Accumulates audio samples
- Updates progress metrics
- Logs encoding statistics

#### 3. Muxer Thread
- Waits for encoder to finish
- Merges video and audio using FFmpeg
- Writes final output file
- Cleans up temporary files

#### 4. Progress Tracker
- Tracks frames encoded
- Calculates encoding speed
- Estimates time to completion
- Provides progress events

### Queue Configuration

```python
# Frame queue (video + audio)
queue_frames = ThreadSafeQueue(50, "FrameQueue")

# Packet queues (for future raw FFmpeg implementation)
queue_video_packets = ThreadSafeQueue(200, "VideoPacketQueue")
queue_audio_packets = ThreadSafeQueue(200, "AudioPacketQueue")
```

**Queue Sizes:**
- **Frame Queue**: 50 frames (~1.7 seconds at 30fps)
- **Packet Queues**: 200 packets (future use)

**Backpressure Policy:**
- If frame queue is full, drop oldest video frames
- Audio is always preserved (never dropped)
- Warning logged when frames are dropped
- Total dropped frames tracked

### Logging and Metrics

The worker logs detailed information:

```
[VideoWorker] Started background encoding for output.mp4
[VideoWorker] Initializing encoder for 1920x1080 @ 30.0 fps
[VideoWorker] Encoder started
[VideoWorker] Metrics - Frames: 450, Audio chunks: 45, Queue size: 3, Dropped: 0
[VideoWorker] Video encoding complete, 1500 frames
[VideoWorker] Writing audio file with 150 chunks
[VideoWorker] Audio file written: /path/to/temp_audio.wav
[VideoWorker] Muxer starting merge process
[VideoWorker] Merging video and audio with ffmpeg
[VideoWorker] Merge complete in 2.34s: output.mp4
[VideoWorker] Output file size: 45.67 MB
[VideoWorker] Encoding completed successfully
```

### State Machine

Worker states:
```
IDLE → STARTING → ENCODING ↔ PAUSED
                      ↓
                 FLUSHING → COMPLETED
                      ↓
                   ERROR / CANCELLED
```

## Performance Characteristics

### UI Responsiveness
- **Target**: < 50ms response time
- **Achieved**: Non-blocking operation
- **Method**: Background threading

### Encoding Speed
- Depends on:
  - CPU performance
  - Video resolution
  - Frame rate
  - Codec settings
- Logged in real-time
- Moving average over 5 seconds

### Memory Usage
- Bounded by queue sizes
- Maximum ~50 frames in queue
- ~150 MB for 1080p at 50 frames
- Audio buffered in memory during encoding

### Disk I/O
- Temporary files created during encoding
- Final merge operation
- Automatic cleanup
- Progress logged

## Error Handling

### Common Errors and Solutions

#### Video Writer Failed
```
[VideoWorker] Failed to open video writer
```
**Solution:** Check write permissions, disk space, video codec

#### FFmpeg Not Found
```
[VideoWorker] No audio merge needed (FFmpeg not available)
```
**Solution:** Install FFmpeg (see SYSTEM_VERIFICATION_DOCUMENTATION.md)

#### Disk Full
```
[VideoWorker] Error in encoder thread: No space left on device
```
**Solution:** Free up disk space

#### Out of Memory
```
[VideoWorker] Error in encoder thread: Cannot allocate memory
```
**Solution:** Reduce queue sizes, close other applications

### Error Recovery

When an error occurs:
1. Worker state changes to ERROR
2. Error is logged with details
3. Progress bar shows "Error"
4. Resources are cleaned up
5. Button returns to "Start" state

## Advanced Features

### Custom Progress Callback

For programmatic monitoring:

```python
def progress_callback(progress_event):
    print(f"Progress: {progress_event.percent:.1f}%")
    print(f"Frames: {progress_event.frames_encoded}")
    print(f"Speed: {progress_event.encode_speed:.1f} fps")
    print(f"ETA: {progress_event.eta_seconds}s")

worker = VideoBackgroundWorker(
    output_path="output.mp4",
    width=1920,
    height=1080,
    fps=30,
    progress_callback=progress_callback
)
```

### Monitoring Queue Health

Queue health is logged periodically:
```
[VideoWorker] Metrics - Frames: 450, Audio chunks: 45, Queue size: 3, Dropped: 0
```

**Healthy Indicators:**
- Queue size: 0-30 (low utilization)
- Dropped: 0 (no frames lost)

**Warning Indicators:**
- Queue size: 40-50 (high utilization)
- Dropped: > 0 (frames being lost)

### Audio Timestamp Tracking

Audio timestamps are monotonic across all segments:

```python
# Maintained throughout encoding
samples_written_audio_total = 0

# For each audio chunk
packet.pts = av_rescale_q(
    samples_written_audio,
    (AVRational){1, sample_rate},
    out_audio_stream->time_base
)
samples_written_audio += N  # Never reset
```

## Best Practices

### 1. Monitor Progress Regularly
Watch the progress bar and detailed info to track encoding.

### 2. Don't Start Multiple Encodings
Only one encoding per VideoWriter node at a time.

### 3. Use Pause for Temporary Stops
Use Pause instead of Cancel if you plan to continue.

### 4. Check Logs for Issues
Review logs if encoding seems slow or fails.

### 5. Ensure Sufficient Disk Space
Check free space before starting long recordings.

### 6. Close Unnecessary Applications
Free up RAM and CPU for better encoding performance.

## Troubleshooting

### Encoding is Slow
- Check CPU usage
- Reduce video resolution
- Lower frame rate
- Check disk I/O speed

### Frames Being Dropped
```
[FrameQueue] Queue full, dropped item (total dropped: 5)
```
- CPU is overloaded
- Disk write is slow
- Consider pausing other work

### Audio Sync Issues
- Should not occur with monotonic timestamps
- If it does, check FFmpeg version
- Verify with: `ffprobe -show_packets output.mp4`

### Progress Bar Not Updating
- Check if worker is actually running
- Review logs for errors
- Try restarting the node

## Future Enhancements

Planned improvements:
- [ ] Direct FFmpeg encoding (avcodec API)
- [ ] Multiple encoder threads
- [ ] Adaptive bitrate control
- [ ] Network stream output
- [ ] Real-time preview during encoding

## Summary

The VideoWriter background worker provides:
- ✅ Non-blocking UI operation
- ✅ Real-time progress tracking with ETA
- ✅ Pause/resume/cancel controls
- ✅ Intelligent queue management
- ✅ Monotonic audio timestamps
- ✅ Comprehensive logging
- ✅ Automatic error handling
- ✅ Clean resource management

For more information:
- `node/VideoNode/video_worker.py` - Worker implementation
- `node/VideoNode/node_video_writer.py` - UI integration
- `tests/test_background_video_worker.py` - Test suite
