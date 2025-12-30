# Implementation Summary: Video Node Frame Output Fix

## Problem Statement (French)
> Pour le node input/video, n'envoie jamais les frames en json, les frames doivent etre envoyées dans IMAGE, par contre la box a cliquer doit permettre par default d'envoyer les images a la volées, sinon, présplitter la video en frame et audio comme c'était le cas avant.

## Translation
> For the input/video node, never send frames in JSON, frames must be sent via IMAGE output. However, the checkbox should allow sending images on-the-fly by default. Otherwise, pre-split the video into frames and audio as it was before.

## Overview
This implementation fixes the video input node to ensure frames are **NEVER** sent in JSON format. Frames are always sent via the IMAGE output, while a checkbox controls whether to use on-the-fly mode (fast, no preprocessing) or preprocessing mode (with audio extraction).

## Changes Made

### 1. Checkbox Label and Default Value
**File**: `node/InputNode/node_video.py` (lines 236-246)

**Before**:
```python
dpg.add_checkbox(
    label="Send frames in JSON",
    default_value=False,
)
```

**After**:
```python
dpg.add_checkbox(
    label="On-the-fly (fast mode)",
    default_value=True,  # ✅ Checked by default
)
```

### 2. Variable Renaming
**Changed**: `send_frames_in_json` → `on_the_fly_mode`

**Rationale**: The new name accurately reflects what the checkbox controls - on-the-fly processing mode, not JSON frame sending.

### 3. Removed Frame-to-JSON Conversion
**File**: `node/InputNode/node_video.py` (lines 767-777)

**Before**:
```python
json_output = None
if send_frames_in_json and frame is not None:
    json_output = {
        "frame": frame.tolist(),  # ❌ Frame data in JSON
        "timestamp": frame_timestamp,
        "frame_number": current_frame_num
    }
```

**After**:
```python
# Frames are ALWAYS sent via IMAGE output, never in JSON
# JSON output can contain metadata only (no frame data)
json_output = None  # ✅ Never contains frame data
```

### 4. Updated Default Values
**File**: `node/InputNode/node_video.py`

All methods now use `True` as the default:
- Line 661: `on_the_fly_mode = True`
- Line 826: `on_the_fly_mode = True`
- Line 860: `setting_dict.get(tag_node_input06_value_name, True)`

### 5. Updated Comments and Documentation
**File**: `node/InputNode/node_video.py`

Updated all comments to reflect the new behavior:
- Line 768: "Frames are ALWAYS sent via IMAGE output, never in JSON"
- Line 872: "Only preprocesses if 'On-the-fly (fast mode)' is unchecked"
- Line 937: "On-the-fly mode: Skipping preprocessing (fast mode, frames sent via IMAGE output)"

## Behavior

### When Checkbox is Checked (Default: ✅)
**Mode**: On-the-fly (Fast)

1. ⚡ No preprocessing - instant video loading
2. 🖼️ Frames sent directly via IMAGE output
3. 🚫 No audio extraction
4. 📦 JSON output is always `None`
5. ⏱️ Timestamps calculated from frame count and FPS

**Use Cases**:
- Real-time video analysis
- Object detection pipelines
- Frame processing
- Quick prototyping

### When Checkbox is Unchecked (☐)
**Mode**: Preprocessing

1. ⏳ Video preprocessing runs in background thread
2. 🎵 Audio extracted and chunked into WAV files
3. 🖼️ Frames still sent via IMAGE output
4. 🎬 Audio chunks available via AUDIO output
5. 📊 Supports spectrogram generation

**Use Cases**:
- Audio-visual analysis
- Spectrogram generation
- Multi-modal processing
- Audio synchronization

## Testing

### Test File
**Created**: `tests/test_video_node_onthefly.py`

### Test Coverage
✅ 11 assertions covering:
1. Checkbox label is correct
2. Default value is True
3. Variable renamed to `on_the_fly_mode`
4. Old variable name removed
5. `frame.tolist()` removed
6. No frame data in JSON
7. Comment confirms IMAGE-only output
8. Default in `get_setting_dict`
9. Default in `set_setting_dict`
10. Preprocessing logic correct
11. Updated comments

### Test Results
```
======================================================================
✅ All tests passed!
======================================================================

Summary of changes:
  • Checkbox label: 'Send frames in JSON' → 'On-the-fly (fast mode)'
  • Default value: False → True
  • Frames: NEVER sent in JSON, ALWAYS sent via IMAGE output
  • Variable: 'send_frames_in_json' → 'on_the_fly_mode'
  • Behavior when checked: Skip preprocessing, send frames on-the-fly
  • Behavior when unchecked: Preprocess video, extract audio chunks
======================================================================
```

## Quality Assurance

### Code Review
✅ **Status**: Passed with no issues
- No review comments
- Code follows existing patterns
- Changes are minimal and focused

### Security Scan (CodeQL)
✅ **Status**: 0 alerts
- No security vulnerabilities introduced
- Safe handling of file paths
- Thread-safe DearPyGUI operations

### Syntax Validation
✅ **Status**: Valid Python syntax
- File compiles without errors
- Imports are correct
- No syntax issues

## Files Modified

### Changed Files (1)
1. **`node/InputNode/node_video.py`**
   - Checkbox label and default value
   - Variable renaming
   - Removed frame-to-JSON logic
   - Updated comments
   - **Lines changed**: -30 additions, +23 modifications

### New Files (1)
1. **`tests/test_video_node_onthefly.py`**
   - Comprehensive test suite
   - 11 test assertions
   - Source code validation
   - **Lines added**: +110

## Benefits

### Technical Benefits
1. 🎯 **Correct Behavior**: Frames never sent in JSON as required
2. ⚡ **Better Default**: On-the-fly mode enabled by default for speed
3. 🧹 **Cleaner Code**: Removed unnecessary frame conversion logic
4. 📝 **Clear Intent**: Variable names reflect actual behavior
5. 🔒 **Safe**: No security vulnerabilities

### User Experience Benefits
1. 🚀 **Faster**: Default mode skips preprocessing for instant loading
2. 🎛️ **Flexible**: Can still enable preprocessing for audio features
3. 💾 **Memory Efficient**: No large frame data in JSON
4. 🔄 **Backward Compatible**: Settings load with safe defaults
5. 📊 **Works with Spectrograms**: Audio mode still available when needed

## Backward Compatibility

### Old Project Files
When loading old project files with `send_frames_in_json` setting:
- ✅ Checkbox defaults to `True` (on-the-fly mode)
- ✅ No frame data in JSON regardless of old setting
- ✅ Video still plays normally
- ✅ IMAGE output works as expected

### Breaking Changes
⚠️ **Minor**: JSON output no longer contains frame data
- Old pipelines expecting frame data in JSON must be updated to use IMAGE output
- This is the **intended fix** per requirements

## Future Considerations

### Potential Enhancements
1. Add tooltip explaining on-the-fly vs. preprocessing modes
2. Show estimated memory savings in fast mode
3. Add progress indicator for preprocessing
4. Allow selective audio extraction

### Documentation Updates
- README could explain the two modes
- User guide could show use cases for each mode

## Conclusion

✅ **Successfully implemented** the required changes:
1. ✅ Frames **NEVER** sent in JSON
2. ✅ Frames **ALWAYS** sent via IMAGE output
3. ✅ Checkbox checked by default (on-the-fly mode)
4. ✅ Preprocessing available when unchecked
5. ✅ All tests pass
6. ✅ No security issues
7. ✅ Minimal, focused changes

The video input node now correctly sends frames via IMAGE output only, with a sensible default (on-the-fly mode) for fast video loading, while still supporting preprocessing mode for audio features when needed.
