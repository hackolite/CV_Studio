# VideoRecorder Node

## Description

The VideoRecorder node is an action node that records video when triggered by a boolean value in JSON data. It supports multiple video formats (AVI, MP4, MKV) and can store frame-by-frame JSON metadata alongside MKV recordings.

## Location

**Menu:** Action → VideoRecorder

## Inputs

### 1. Trigger JSON (Required)
- **Type:** JSON
- **Purpose:** Controls when to start recording
- **Trigger Logic:**
  - Priority 1: `{"record": true}` - Recommended field name
  - Priority 2: `{"trigger": true}` - Alternative field name
  - Priority 3: Any boolean field set to `true` - Fallback behavior

### 2. Image (Required)
- **Type:** IMAGE
- **Purpose:** Video frames to record
- **Note:** Shows a preview of the current frame

### 3. Metadata JSON (Optional)
- **Type:** JSON
- **Purpose:** Frame-by-frame metadata to store with MKV files
- **Format:** Any JSON object that will be stored alongside each frame

## Configuration

### Duration Slider
- **Range:** 1-300 seconds
- **Default:** 10 seconds
- **Purpose:** Sets the recording duration once triggered

### Format Dropdown
- **Options:** avi, mp4, mkv
- **Default:** mp4
- **Notes:**
  - **AVI:** Uses XVID codec (widely supported)
  - **MP4:** Uses mp4v codec (good compatibility)
  - **MKV:** Uses X264 codec with XVID fallback (supports metadata)

### Status Indicator
- **WAIT (Gray):** Ready to record, waiting for trigger
- **RECORD (Red):** Currently recording with countdown timer

## Output

- **Video files** are saved to the directory specified in settings (default: `./_VideoRecorder`)
- **Filename format:** `recording_YYYYMMDD_HHMMSS.{format}`
- **MKV metadata** is saved as `recording_YYYYMMDD_HHMMSS_metadata.json` (only for MKV format with metadata input)

## Behavior

1. **Trigger:** When the boolean in the trigger JSON becomes `true`, recording starts
2. **Recording:** Records frames for the specified duration
3. **Auto-stop:** Automatically stops after the duration expires
4. **State:** Returns to WAIT state after recording completes
5. **Metadata:** For MKV format, stores JSON data frame-by-frame in a separate file

## Example Usage

### Basic Recording
```
Input Trigger JSON: {"record": true}
Duration: 5 seconds
Format: mp4
Result: Records 5 seconds of video as mp4
```

### Recording with Metadata
```
Input Trigger JSON: {"detected": true}
Input Metadata JSON: {"object": "person", "confidence": 0.95}
Duration: 10 seconds
Format: mkv
Result: Records 10 seconds of video with frame-by-frame metadata
```

## Technical Notes

- **FPS:** Uses the `video_writer_fps` setting from the application configuration (default: 30 fps)
- **Resolution:** Records at the original frame resolution
- **Codec Fallback:** If X264 is not available for MKV, falls back to XVID
- **Error Handling:** Logs errors to console if codec initialization fails

## Settings Persistence

The node saves and restores:
- Duration value
- Format selection

## Tips

1. Use the `record` field in your trigger JSON for clearest intent
2. Choose MKV format if you need to store metadata
3. Ensure sufficient disk space for recordings
4. Check console output for codec-related errors
5. Install ffmpeg for better codec support on your system
