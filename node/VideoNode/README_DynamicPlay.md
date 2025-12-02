# DynamicPlay Node Documentation

## Overview

The **DynamicPlay** node is an interactive video node that allows you to:
- Display multiple video/image streams
- Switch between streams using hand pointing gestures
- Zoom in/out using pinch gestures with your thumb and index finger

This node combines computer vision (MediaPipe Hands) with interactive controls to create a hands-free video player interface.

## Features

### Multiple Input Streams
- Supports up to 9 simultaneous video/image streams
- Dynamic slot addition (like ImageConcat node)
- Grid layout automatically adjusts based on number of streams

### Hand Gesture Controls

#### Stream Selection
- Use your **index finger pointing gesture** to select a stream
- Point at the numbered button overlay on the screen
- Selected stream is highlighted in green
- Other streams shown with white borders

#### Pinch-to-Zoom
- Use **thumb and index finger pinch** to zoom
- Closer fingers = less zoom (1x)
- Wider fingers = more zoom (up to 3x)
- Zoom center follows your index finger position

## Node Interface

### Inputs
- **Input01-Input09**: Multiple BGR image inputs (add slots as needed)
- Each input can receive a video stream or static image

### Outputs
- **Output01**: The currently selected and zoomed video stream with overlay

### Controls
- **Add Slot Button**: Click to add more input slots (up to 9)

## Usage Example

### Basic Setup
1. Add the DynamicPlay node from the **Video** menu
2. Connect video sources to the input slots
   - Example: Connect WebCam nodes, Video nodes, or any image-producing nodes
3. The node will display a grid of buttons numbered 1-9

### Gesture Controls
1. **Selecting a Stream**:
   - Extend your index finger
   - Point at the numbered button corresponding to the stream you want to view
   - The selected stream will be displayed full-screen with zoom controls

2. **Zooming**:
   - Make a pinch gesture with thumb and index finger
   - Adjust the distance between your fingers:
     - Close together: Zoom out (1x)
     - Far apart: Zoom in (up to 3x)
   - Move your index finger to change the zoom center

## Visual Indicators

### On-Screen Display
- **Stream Number**: Shows current stream (e.g., "Stream: 1/4")
- **Zoom Level**: Shows current zoom factor (e.g., "Zoom: 2.5x")
- **Button Grid**: Numbered buttons overlay (1-9)
  - Green border: Currently selected stream
  - White border: Available streams
  - Red border: Button being pointed at

### Hand Visualization
- **Yellow circles**: Thumb tip and index finger tip (key tracking points)
- **Green circles**: Other hand landmarks

## Technical Details

### Grid Layout
The button grid automatically adjusts based on the number of input streams:

| Streams | Grid Layout |
|---------|-------------|
| 1       | 1x1         |
| 2       | 2x1         |
| 3-4     | 2x2         |
| 5-6     | 3x2         |
| 7-9     | 3x3         |

### Zoom Parameters
- **Minimum Zoom**: 1.0x (no zoom)
- **Maximum Zoom**: 3.0x
- **Base Pinch Distance**: 100 pixels (for 1x zoom)
- Zoom is proportional to pinch distance

### Hand Detection
- Uses **MediaPipe Hands** (Complexity 0)
- Detects up to 1 hand
- Minimum detection confidence: 0.7
- Minimum tracking confidence: 0.5

## Requirements

### Dependencies
- `mediapipe`: For hand pose estimation
- `opencv-contrib-python`: For image processing
- `numpy`: For numerical operations
- `dearpygui`: For UI rendering

### Hardware
- Webcam or video input device (for hand detection)
- Sufficient lighting for hand tracking

## Performance Considerations

- Hand detection runs on each frame of the selected stream
- For better performance:
  - Use lower resolution input streams
  - Reduce the number of concurrent streams
  - Ensure good lighting conditions for hand tracking

## Troubleshooting

### Hand Not Detected
- **Check lighting**: Ensure adequate lighting on your hand
- **Check camera**: Make sure the hand is visible in the camera frame
- **Check distance**: Hand should be at a reasonable distance from camera (30cm-1m)

### Gestures Not Responding
- **Point clearly**: Extend index finger fully for pointing
- **Pinch clearly**: Make distinct pinch gesture with thumb and index
- **Avoid fast movements**: Keep hand movements smooth and steady

### Performance Issues
- Reduce input stream resolution
- Reduce number of input streams
- Close other resource-intensive applications

## Example Workflow

```
[WebCam] → [DynamicPlay]
[Video1] → [Input01]   
[Video2] → [Input02]    → [Output] → [Display/VideoWriter]
[Video3] → [Input03]    
```

This setup allows you to:
1. Select between webcam and multiple video sources
2. Zoom into specific areas of interest
3. Record the selected and zoomed output

## Limitations

- Maximum 9 input streams
- Single hand tracking only
- Zoom range limited to 1x-3x
- Requires MediaPipe installation

## Future Enhancements

Potential improvements could include:
- Multi-hand gesture support
- Custom gesture mapping
- Adjustable zoom limits
- Picture-in-picture mode
- Gesture-based rotation
- Two-hand zoom (like touchscreen pinch)

## License

This node is part of the CV_Studio project and follows the same license terms.
