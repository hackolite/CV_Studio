# CourtKeypointDeviation Algorithm - Implementation Summary

## Overview

This document describes the refactored `CourtKeypointDeviation` algorithm that implements robust scene cut detection for sports video analysis, particularly tennis and court sports.

## Problem Statement

The previous algorithm was not robust enough for detecting scene changes. The new algorithm needed to:

1. Define a **MASTER PLAN** based on the dominant court color from the first stable frame
2. Detect **scene cuts (CUT)** using grayscale histogram comparison
3. Maintain a **persistent trigger** until the court returns to the MASTER PLAN

## Algorithm Implementation

### 1. MASTER PLAN Definition

The algorithm identifies the dominant color of the court from the first stable frame:

- **Stability Check**: Waits for 5 frames (`STABLE_FRAME_COUNT`) before setting the master plan to avoid noise
- **Color Dominance**: Requires at least 75% (configurable) of pixels to be the dominant color
- **Color Quantization**: Groups similar colors using 32-level quantization (`COLOR_QUANTIZATION_STEP`)
- **Storage**: Stores both the dominant color (BGR) and the grayscale histogram

**Example**: A tennis court with green surface:
- Dominant color: [40, 150, 40] BGR
- Dominance ratio: 80%+ (exceeds 75% threshold)
- Master plan is set after 5 consecutive frames

### 2. Scene CUT Detection

The algorithm detects scene changes using histogram comparison:

- **Grayscale Conversion**: Converts each frame to grayscale for lighting-invariant detection
- **Histogram Calculation**: Computes normalized 256-bin histogram
- **Manhattan Distance (L1)**: Calculates sum of absolute differences between consecutive frame histograms
- **Threshold**: Triggers when distance exceeds `CUT_THRESHOLD` (default: 0.3, configurable: 0.1-1.0)

**Example Histogram Distances**:
- Similar frames (same scene): ~0.07
- Scene cut (different scene): ~2.0

### 3. Trigger Persistence

The trigger remains active until the court returns to the MASTER PLAN:

- **Activation**: Trigger activates when histogram distance > CUT_THRESHOLD
- **Persistence**: Trigger remains TRUE across subsequent frames
- **Deactivation Criteria** (both must be satisfied):
  1. Color similarity: Euclidean distance < 50 (`COLOR_SIMILARITY_THRESHOLD`)
  2. Histogram similarity: distance < CUT_THRESHOLD × 0.5 (`RETURN_THRESHOLD_FACTOR`)
- **Return Strictness**: Uses 0.5× factor to prevent false negatives and flickering

**Example Flow**:
1. Master plan: Green court (distance = 0)
2. Scene cut to replay: Blue background (distance = 2.0, **trigger = TRUE**)
3. Continue replay: Different angles (**trigger = TRUE**)
4. Return to court: Green court (distance = 0.12, color similar, **trigger = FALSE**)

## Configuration Parameters

### Algorithm Constants

These are defined as class constants and can be modified if needed:

```python
STABLE_FRAME_COUNT = 5              # Frames to wait before setting master plan
COURT_REGION_MARGIN = 10            # Margin around keypoints bounding box (pixels)
COLOR_QUANTIZATION_STEP = 32        # Color grouping step size (0-255)
COLOR_SIMILARITY_THRESHOLD = 50     # Maximum color distance for similarity
RETURN_THRESHOLD_FACTOR = 0.5       # Strictness factor for return detection
EPSILON = 1e-10                     # Small value to prevent division by zero
```

### User-Configurable Parameters

Adjustable via UI sliders:

1. **CUT Threshold** (default: 0.3, range: 0.1-1.0)
   - Lower values: More sensitive to small changes
   - Higher values: Only detects major scene cuts
   - Recommended: 0.2-0.4 for sports video

2. **Color Dominance %** (default: 0.75, range: 0.5-0.95)
   - Minimum ratio of dominant color to set master plan
   - Lower values: Accept more varied courts
   - Higher values: Only very uniform courts
   - Recommended: 0.70-0.80 for tennis

## Node Inputs and Outputs

### Inputs

1. **Court Image Input** (Input01, TYPE_IMAGE)
   - The video frame containing the court
   - Required for color and histogram analysis

2. **Keypoints JSON Input** (Input02, TYPE_JSON)
   - Optional: Court corner keypoints for region extraction
   - If provided, only analyzes the court region (more accurate)
   - If not provided, analyzes entire frame

3. **CUT Threshold** (Input03, TYPE_FLOAT)
   - Configurable threshold for scene cut detection

4. **Color Dominance %** (Input04, TYPE_FLOAT)
   - Minimum color dominance ratio for master plan

### Outputs

1. **Trigger** (Output01, TYPE_BOOLEAN)
   - TRUE when scene has cut away from master plan
   - FALSE when on master plan or returned to it

2. **Hist Dist** (Output02, TYPE_FLOAT)
   - Current histogram distance from previous frame
   - Useful for debugging and threshold adjustment

3. **Keypoints JSON Output** (Output03, TYPE_JSON)
   - Pass-through of input JSON
   - Enhanced with `trigger_info` metadata:
     ```json
     {
       "trigger_info": {
         "triggered": false,
         "histogram_distance": 0.08,
         "cut_threshold": 0.3,
         "master_plan_set": true,
         "frame_counter": 120,
         "master_color": [40, 150, 40]
       }
     }
     ```

4. **Elapsed time(ms)** (Output04, TYPE_TIME_MS)
   - Processing time for performance monitoring

## Helper Methods

### `_extract_court_region(frame, json_data)`
Extracts the court region from the frame using keypoint bounding box:
- If keypoints available: Returns region with 10-pixel margin
- If no keypoints: Returns entire frame
- Handles edge cases (boundaries, empty regions)

### `_get_dominant_color(image)`
Identifies the dominant color and its ratio:
- Quantizes colors to reduce complexity
- Counts pixel frequencies
- Returns (dominant_color, dominance_ratio)

### `_compute_histogram(image)`
Computes normalized grayscale histogram:
- Converts to grayscale
- Calculates 256-bin histogram
- Normalizes to probability distribution

### `_is_color_similar(color1, color2, threshold=None)`
Checks if two colors are similar:
- Uses Euclidean distance
- Default threshold: 50 (configurable)
- Returns boolean

## Use Cases

### Tennis Match Analysis
- Master plan: Green court
- Detects cuts to: Replay, crowd shots, scoreboard
- Returns to court: Resumes normal analysis

### Basketball Game
- Master plan: Orange court
- Detects cuts to: Timeout graphics, replays
- Returns to court: Resumes tracking

### Volleyball
- Master plan: Blue court
- Detects cuts to: Instant replay, statistics
- Returns to court: Resumes detection

## Testing

Comprehensive tests validate all algorithm components:

1. **Dominant Color Extraction**: 80%+ dominance for uniform courts ✓
2. **Histogram Distance**: 0.08 for similar, 2.0 for cuts ✓
3. **Color Similarity**: 8.66 for similar, 167.93 for different ✓
4. **Court Region Extraction**: Correct bounding box calculation ✓
5. **Trigger Persistence**: Activates on cut, deactivates on return ✓

All tests pass with expected values.

## Performance Considerations

- **Processing Time**: ~1-3ms per frame (on modern hardware)
- **Memory Usage**: Minimal (stores one histogram and one color)
- **Efficiency**: Uses optimized NumPy/OpenCV operations
- **Scalability**: Works with any resolution (analyzes court region only)

## Backward Compatibility Notes

### Breaking Changes
- Input order changed (Image is Input01, JSON is Input02)
- Algorithm completely different from previous version
- Output JSON structure changed

### Preserved
- Node label: `CourtKeypointDeviation`
- Node tag: `TriggerKeypointDeviation`
- Settings save/load functionality

### Migration Guide
Existing workflows need to:
1. Add image input connection to the node
2. Reconnect JSON input (now Input02 instead of Input01)
3. Adjust new parameters (CUT_THRESHOLD, Color Dominance %)

## Future Enhancements

Possible improvements for future versions:

1. **Adaptive Thresholds**: Auto-adjust based on video characteristics
2. **Multi-Court Support**: Track multiple courts in multi-camera setups
3. **Temporal Smoothing**: Average histogram over multiple frames
4. **GPU Acceleration**: Use CUDA for histogram calculations
5. **Learning Mode**: Learn court characteristics over time

## References

- Manhattan Distance (L1): More sensitive than Euclidean for histogram comparison
- Color Quantization: Reduces noise and improves dominant color detection
- Grayscale Histogram: Lighting-invariant scene representation

## Version History

- **v0.0.1**: Original keypoint-based deviation detection
- **v0.0.2**: Complete refactor with scene cut detection algorithm

## Security

CodeQL analysis: **0 alerts** (clean)

No security vulnerabilities detected in the implementation.
