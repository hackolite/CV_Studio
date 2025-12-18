# VideoWriter Async Release - Manual Verification Guide

## Purpose
This guide helps verify that the VideoWriter async release fix works correctly and prevents UI freezing.

## Test Scenarios

### Test 1: Short Recording (< 5 seconds)
**Expected behavior:** Fast finalization, minimal UI delay

1. Open CV Studio
2. Create VideoWriter node
3. Select MP4 format
4. Connect video source
5. Click "Start" recording
6. Record for 3-5 seconds
7. Click "Stop"
8. **Verify:**
   - Button immediately changes to "Finalizing..."
   - UI remains responsive (can move nodes, interact with other controls)
   - Recording indicator (red circle) disappears immediately
   - Button changes back to "Start" within 1-2 seconds
   - Video file is created and playable

### Test 2: Long Recording (30+ seconds)
**Expected behavior:** Longer finalization, but UI stays responsive

1. Open CV Studio
2. Create VideoWriter node
3. Select AVI format (MJPEG codec - slower to finalize)
4. Connect video source
5. Click "Start" recording
6. Record for 30-60 seconds
7. Click "Stop"
8. **Verify:**
   - Button immediately changes to "Finalizing..."
   - UI remains responsive (can move nodes, interact with other controls)
   - Recording indicator (red circle) disappears immediately
   - No frames are written during finalization
   - Button changes back to "Start" after 5-15 seconds
   - Video file is created and playable
   - No crash or freeze occurs

### Test 3: MKV Format (FFV1 codec)
**Expected behavior:** Similar to AVI, potentially slower finalization

1. Open CV Studio
2. Create VideoWriter node
3. Select MKV format (FFV1 codec - lossless, can be slow)
4. Connect video source
5. Click "Start" recording
6. Record for 20-30 seconds
7. Click "Stop"
8. **Verify:**
   - Button immediately changes to "Finalizing..."
   - UI remains responsive
   - No freeze during finalization
   - Video file is created and playable

### Test 4: Multiple VideoWriter Nodes
**Expected behavior:** Each node finalizes independently

1. Open CV Studio
2. Create 2-3 VideoWriter nodes
3. Connect video sources to all nodes
4. Start recording on all nodes
5. Stop recording on all nodes (with small delays between stops)
6. **Verify:**
   - Each button shows "Finalizing..." independently
   - All nodes finalize without interfering with each other
   - UI remains responsive throughout
   - All video files are created successfully

### Test 5: Node Deletion During Finalization
**Expected behavior:** Graceful cleanup

1. Open CV Studio
2. Create VideoWriter node
3. Start recording for 20+ seconds
4. Stop recording (button shows "Finalizing...")
5. Try to delete the node while finalization is in progress
6. **Verify:**
   - Node deletion waits for finalization to complete (up to 60 seconds)
   - No crash occurs
   - Video file is properly finalized
   - Logs show: "Waiting for background finalization to complete"

### Test 6: Close Application During Finalization
**Expected behavior:** Graceful shutdown

1. Open CV Studio
2. Start and stop a long recording
3. While button shows "Finalizing...", close the application
4. **Verify:**
   - Application waits for finalization (up to 60 seconds)
   - Video file is properly created
   - No corruption in video file
   - Clean shutdown

## Log Messages to Check

When stopping a recording, you should see:
```
[VideoWriter] Stopped recording, finalizing in background
[VideoWriter] Starting background finalization for <node_name>
[VideoWriter] Background finalization completed for <node_name>
```

When closing a node during finalization:
```
[VideoWriter] Waiting for background finalization to complete for <node_name>
```

## Memory Behavior

### Before Fix:
- UI freezes for 10-30+ seconds when stopping
- System becomes unresponsive
- High risk of crash/timeout
- Memory spike during synchronous release

### After Fix:
- UI remains responsive when stopping
- Button shows "Finalizing..." feedback
- Background thread handles release
- No UI freeze or crash
- Minimal memory overhead (one thread per finalization)

## Performance Expectations

| Video Format | Codec | Typical Finalization Time (30s recording) |
|--------------|-------|-------------------------------------------|
| MP4          | mp4v  | 1-3 seconds                               |
| AVI          | MJPEG | 5-15 seconds                              |
| MKV          | FFV1  | 5-20 seconds (depends on compression)     |

Note: Finalization time depends on:
- Video resolution (1080p vs 720p vs 4K)
- Recording duration
- Codec complexity
- Disk write speed
- System resources

## Troubleshooting

### Issue: Button stays "Finalizing..." for too long
- Check disk space
- Check logs for errors
- Verify video file is being written
- Consider system I/O performance

### Issue: Video file is corrupted
- Check logs for errors during finalization
- Verify no exceptions in `_release_video_writer_async`
- Check disk space and write permissions

### Issue: Application won't close
- Check if finalization threads are stuck
- Look for "Waiting for background finalization" in logs
- After 60 seconds, threads should timeout

## Success Criteria

✅ All test scenarios pass without UI freeze
✅ Video files are created and playable
✅ No crashes during finalization
✅ Button properly shows "Finalizing..." state
✅ Recording indicator disappears immediately on stop
✅ Logs show correct async finalization messages
✅ Multiple nodes can finalize simultaneously
✅ Graceful cleanup on node deletion
✅ Clean application shutdown
