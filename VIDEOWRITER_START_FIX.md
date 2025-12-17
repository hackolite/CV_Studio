# VideoWriter Start Crash Fix

## Problem Statement (French)
> pourquoi quand je clique sur start (le record), sur le noeud videowriter, ça peut s"arréter brutalement ? corrige stp

**Translation:** "Why does it stop abruptly when I click on start (the record) on the videowriter node? Please fix it"

## Problem Analysis

When clicking "Start" (record) on the VideoWriter node, the recording could stop abruptly due to several issues:

1. **No validation of cv2.VideoWriter initialization**
   - If `cv2.VideoWriter` fails to initialize (invalid codec, disk space, permissions, etc.), the code continued silently
   - The `isOpened()` check was not performed after creating the VideoWriter
   - This led to silent failures where the node appeared to start recording but nothing was actually recorded

2. **No exception handling around legacy mode initialization**
   - The legacy mode VideoWriter creation had no try-except wrapper
   - Any exceptions during initialization would crash the entire node
   - No crash logs were created for diagnostics

3. **No user feedback on initialization failures**
   - Users received no indication that initialization failed
   - The button label changed to "Stop" even when recording never started
   - No progress bar updates to indicate errors

## Root Cause

The issue was in the `_recording_button` method in `node_video_writer.py`:

```python
# BEFORE (lines 1409-1448):
if not use_worker and tag_node_name not in self._video_writer_dict:
    temp_file_path = os.path.join(video_writer_directory, f'{startup_time_text}_temp{config["ext"]}')
    
    # Create video writer with temporary path
    self._video_writer_dict[tag_node_name] = cv2.VideoWriter(
        temp_file_path,
        cv2.VideoWriter_fourcc(*config['codec']),
        writer_fps,
        (writer_width, writer_height),
    )
    # ... rest of initialization ...
    # NO VALIDATION OR ERROR HANDLING!
```

## Solution

Added comprehensive error handling and validation:

### 1. VideoWriter Validation
```python
video_writer = cv2.VideoWriter(...)

# CRITICAL CHECK - Detect initialization failures immediately
if not video_writer.isOpened():
    error_msg = (
        f"Failed to initialize VideoWriter:\n"
        f"Format: {video_format}, Codec: {config['codec']}, "
        f"Resolution: {writer_width}x{writer_height}, FPS: {writer_fps}\n"
        f"Path: {temp_file_path}\n\n"
        f"Possible causes:\n"
        f"- Codec not available on your system\n"
        f"- Insufficient disk space\n"
        f"- Invalid output directory permissions\n"
        f"- Invalid video parameters"
    )
    logger.error(f"[VideoWriter] {error_msg}")
    
    # Create crash log for diagnostics
    create_crash_log("recording_start_videowriter_failed", 
                   RuntimeError(error_msg), 
                   tag_node_name)
    
    # Update progress bar to show error
    dpg.configure_item(tag_node_progress_name, overlay="Error: Failed to start")
    
    # Early return without changing button label (allows retry)
    return
```

### 2. Exception Handling
```python
try:
    # VideoWriter creation and initialization
    ...
except Exception as e:
    logger.error(f"[VideoWriter] Exception during recording start: {e}")
    create_crash_log("recording_start_exception", e, tag_node_name)
    
    # Update UI with error
    dpg.configure_item(tag_node_progress_name, overlay="Error: Exception occurred")
    
    # Clean up partial initialization
    if tag_node_name in self._video_writer_dict:
        try:
            self._video_writer_dict[tag_node_name].release()
        except Exception as release_error:
            logger.debug(f"[VideoWriter] Error releasing during cleanup: {release_error}")
        self._video_writer_dict.pop(tag_node_name, None)
    
    return  # Early return prevents state corruption
```

### 3. User Feedback
- Progress bar shows error message when initialization fails
- Button label remains "Start" (not changed to "Stop") on failure
- Users can retry after fixing the issue
- Crash logs provide detailed diagnostics

## Benefits

1. **No more silent failures** - All initialization failures are detected and reported
2. **Better diagnostics** - Crash logs provide detailed error information
3. **User-friendly** - Progress bar shows clear error messages
4. **Robust** - Exception handling prevents crashes
5. **Recoverable** - Button stays in "Start" state for easy retry

## Testing

Created comprehensive test suite (`test_videowriter_initialization_validation.py`) with 7 test cases:

1. ✅ VideoWriter `isOpened()` validation
2. ✅ Invalid codec handling
3. ✅ Invalid path handling
4. ✅ Zero FPS handling
5. ✅ Invalid dimensions handling
6. ✅ Success case validation
7. ✅ Complete error handling flow

All tests pass successfully.

## Common Failure Scenarios Now Handled

1. **Invalid Codec**
   - Example: FFMPEG not installed, codec not available
   - Detection: `isOpened()` returns False
   - Feedback: "Error: Failed to start" + crash log

2. **Disk Space Issues**
   - Example: Out of disk space
   - Detection: `isOpened()` returns False or exception raised
   - Feedback: Error message + crash log

3. **Permission Issues**
   - Example: Cannot write to output directory
   - Detection: Exception raised or `isOpened()` returns False
   - Feedback: Error message + crash log

4. **Invalid Parameters**
   - Example: Zero FPS, invalid dimensions
   - Detection: `isOpened()` returns False
   - Feedback: Error message + crash log

## Files Modified

1. `node/VideoNode/node_video_writer.py`
   - Added VideoWriter validation (line ~1418-1452)
   - Added exception handling (line ~1410, ~1493-1514)
   - Added crash logging integration
   - Added progress bar error feedback

2. `tests/test_videowriter_initialization_validation.py` (NEW)
   - Comprehensive test suite for validation logic
   - 7 test cases covering various failure scenarios

## Security Analysis

✅ CodeQL security scan: **0 alerts** - No security vulnerabilities introduced

## Backward Compatibility

✅ Fully backward compatible:
- Existing functionality unchanged
- Only adds validation and error handling
- No API changes
- No breaking changes to existing code

## Migration Notes

No migration needed. The fix is automatic and transparent to users.

## Future Improvements

Potential enhancements (not in this PR):

1. Add codec availability check before initialization
2. Add disk space check before starting recording
3. Add UI dialog with detailed error information
4. Add automatic codec fallback (try H.264 if MJPG fails)
5. Add retry mechanism with exponential backoff

## References

- Original issue: "pourquoi quand je clique sur start (le record), sur le noeud videowriter, ça peut s'arrêter brutalement?"
- Related files: `node/VideoNode/node_video_writer.py`, `node/VideoNode/video_worker.py`
- Test file: `tests/test_videowriter_initialization_validation.py`
