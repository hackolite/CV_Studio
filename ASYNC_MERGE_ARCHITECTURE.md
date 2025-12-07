# VideoWriter Async Merge Architecture

## Architecture Overview

This document describes the architecture of the async video/audio merge implementation in the VideoWriter node.

## Before (Synchronous - Causes Freeze)

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Thread                             │
│                                                              │
│  User clicks "Stop" → Release video writer                  │
│            ↓                                                 │
│  Call _merge_audio_video_ffmpeg() [BLOCKS UI!]             │
│            ↓                                                 │
│  Concatenate audio (slow)                                   │
│            ↓                                                 │
│  Write WAV file (slow)                                      │
│            ↓                                                 │
│  Run ffmpeg merge (VERY SLOW!)  ⚠️ UI FROZEN HERE          │
│            ↓                                                 │
│  Clean up files                                             │
│            ↓                                                 │
│  Return control to user (UI unfreezes)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## After (Asynchronous - UI Stays Responsive)

```
┌──────────────────────────────┐    ┌────────────────────────────────┐
│         UI Thread            │    │      Merge Thread              │
│                              │    │                                │
│  User clicks "Stop"          │    │                                │
│         ↓                    │    │                                │
│  Release video writer        │    │                                │
│         ↓                    │    │                                │
│  Copy audio samples          │    │                                │
│         ↓                    │    │                                │
│  Start merge thread ─────────┼───→│  Receive audio samples         │
│         ↓                    │    │         ↓                      │
│  Return immediately ✅       │    │  Progress → 10%                │
│         ↓                    │    │         ↓                      │
│  Continue UI updates         │    │  Concatenate audio             │
│         ↓                    │    │         ↓                      │
│  Monitor progress ←──────────┼────│  Progress → 30%                │
│         ↓                    │    │         ↓                      │
│  Update progress bar         │    │  Write WAV file                │
│         ↓                    │    │         ↓                      │
│  User can interact! ✅       │    │  Progress → 50%                │
│         ↓                    │    │         ↓                      │
│  Update progress bar         │    │  Run ffmpeg merge              │
│         ↓                    │    │         ↓                      │
│  User can interact! ✅       │    │  Progress → 70%                │
│         ↓                    │    │         ↓                      │
│  Update progress bar         │    │  Complete merge                │
│         ↓                    │    │         ↓                      │
│  Detect thread done ←────────┼────│  Progress → 100%               │
│         ↓                    │    │         ↓                      │
│  Hide progress bar           │    │  Clean up files                │
│         ↓                    │    │         ↓                      │
│  Continue UI updates ✅      │    │  Thread exits                  │
│                              │    │                                │
└──────────────────────────────┘    └────────────────────────────────┘
```

## Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    Recording Phase                              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Video Frame ──→ VideoWriter.write()                           │
│                                                                 │
│  Audio Chunk ──→ _audio_samples_dict[node_tag].append()       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    Stop Button Clicked                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Release VideoWriter                                        │
│  2. Deep copy audio samples                                    │
│  3. Start merge thread with copies                             │
│  4. Return to UI immediately                                   │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    Merge Thread (Async)                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Progress: 0.0 ──→ _merge_progress_dict[node_tag]             │
│         ↓                                                       │
│  Concatenate audio samples                                     │
│         ↓                                                       │
│  Progress: 0.3 ──→ _merge_progress_dict[node_tag]             │
│         ↓                                                       │
│  Write temporary WAV file                                      │
│         ↓                                                       │
│  Progress: 0.5 ──→ _merge_progress_dict[node_tag]             │
│         ↓                                                       │
│  Run ffmpeg to merge video + audio                            │
│         ↓                                                       │
│  Progress: 0.7 ──→ _merge_progress_dict[node_tag]             │
│         ↓                                                       │
│  Complete merge                                                │
│         ↓                                                       │
│  Progress: 1.0 ──→ _merge_progress_dict[node_tag]             │
│         ↓                                                       │
│  Clean up temporary files                                      │
│         ↓                                                       │
│  Thread exits                                                  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    UI Thread (Monitoring)                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Every frame in update():                                      │
│    1. Check _merge_progress_dict[node_tag]                    │
│    2. Update progress bar value                               │
│    3. Update progress bar label                               │
│    4. If thread.is_alive() == False:                          │
│       - Clean up dictionaries                                 │
│       - Hide progress bar                                     │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Thread Synchronization

```
┌─────────────────────────────────────────────────────────────────┐
│                    Shared Resources                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  _merge_threads_dict = {                                        │
│    'node_id:VideoWriter': <Thread object>                      │
│  }                                                              │
│                                                                  │
│  _merge_progress_dict = {                                       │
│    'node_id:VideoWriter': 0.75  # Current progress (0.0-1.0)   │
│  }                                                              │
│                                                                  │
│  Access Pattern:                                                │
│    - UI Thread: READ progress, WRITE thread ref                │
│    - Merge Thread: WRITE progress                              │
│                                                                  │
│  Thread Safety:                                                 │
│    - Python GIL protects dict operations                       │
│    - No explicit locks needed                                  │
│    - Deep copy prevents data races                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Progress Bar States

```
┌─────────────────────┐
│   Initial State     │
│   (Hidden)          │
│   show=False        │
│   value=0.0         │
└──────────┬──────────┘
           │
           │ Stop recording with audio
           ↓
┌─────────────────────┐
│   Merging State     │
│   (Visible)         │
│   show=True         │
│   value=0.0→1.0     │
│   overlay="X%"      │
└──────────┬──────────┘
           │
           │ Merge complete
           ↓
┌─────────────────────┐
│   Complete State    │
│   (Hidden)          │
│   show=False        │
│   value=0.0         │
└─────────────────────┘
```

## Error Handling

```
┌─────────────────────────────────────────────────────────────────┐
│                    Merge Thread Error Handling                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  try:                                                           │
│    Initialize progress (0.0)                                   │
│    Perform merge with progress callbacks                       │
│    If success:                                                 │
│      - Delete temp video file                                 │
│      - Print success message                                  │
│    If failure:                                                 │
│      - Rename temp file to final name                         │
│      - Print warning message                                  │
│                                                                  │
│  except Exception as e:                                        │
│    Print error                                                 │
│    Try to save temp file as final                             │
│                                                                  │
│  finally:                                                       │
│    Set progress to 1.0 (indicates completion)                 │
│    Allow cleanup to proceed                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Cleanup Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    Node Close Sequence                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Check for ongoing merge thread                             │
│     ↓                                                           │
│  2. If thread exists and is alive:                             │
│     - Print waiting message                                    │
│     - Wait up to 30 seconds                                    │
│     ↓                                                           │
│  3. Remove from _merge_threads_dict                            │
│     ↓                                                           │
│  4. Remove from _merge_progress_dict                           │
│     ↓                                                           │
│  5. Release any active video writers                           │
│     ↓                                                           │
│  6. Close MKV metadata handles                                 │
│     ↓                                                           │
│  7. Node cleanup complete                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Benefits of This Architecture

### ✅ Performance
- UI remains responsive during merge
- No blocking operations in main thread
- Progress feedback keeps user informed

### ✅ Safety
- Deep copy prevents race conditions
- Try-except-finally ensures cleanup
- Daemon threads auto-cleanup on exit

### ✅ Usability
- Visual progress indicator
- Clear status messages
- Graceful error handling

### ✅ Maintainability
- Clean separation of concerns
- Well-defined interfaces
- Comprehensive error handling

## Key Design Decisions

1. **Daemon Threads**: Threads don't block application exit
2. **Deep Copy**: Prevents data races with minimal overhead
3. **Progress Dict**: Simple shared state for UI updates
4. **No Locks**: Python GIL provides sufficient protection
5. **Timeout**: 30-second wait ensures timely cleanup
6. **Progress Callback**: Clean interface for progress reporting

## Future Enhancements

Potential improvements:
1. Cancellable merge operations
2. Multiple concurrent merges
3. More granular progress (frame-by-frame)
4. Estimated time remaining
5. Merge queue for multiple recordings

---

**Architecture Version**: 1.0
**Date**: 2025-12-07
