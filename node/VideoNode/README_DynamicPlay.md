# DynamicPlay Node Documentation

## Overview

The **DynamicPlay** node is an interactive video node that allows you to:
- Display a master video stream (background) with hand detection
- Activate overlay video streams (picture-in-picture) using pointing gestures
- Move and resize the overlay using pinch gestures with thumb and index finger

This node combines computer vision (MediaPipe Hands) with interactive controls to create a hands-free video player interface with overlay management.

## Features

### Master Stream + Overlay Architecture
- **Master Stream** (Input01): Background video stream that always runs hand detection
- **Overlay Streams** (Input02-Input09): Video streams that can be activated as picture-in-picture
- Up to 8 overlay streams available simultaneously
- Grid layout automatically adjusts based on number of streams

### Hand Gesture Controls

#### Overlay Activation
- Use your **index finger pointing gesture** to activate an overlay stream
- Point at the numbered button overlay on the screen
- The activated overlay stream appears as picture-in-picture on the master stream
- Point at the same button again to deactivate the overlay

#### Overlay Movement (Drag)
- Use **thumb and index finger pinch** to grab the overlay
- Hold the pinch and move your hand to move the overlay
- The overlay follows your hand position in real-time

#### Overlay Resizing
- Use **thumb-index distance** to resize the overlay
- Closer fingers = smaller overlay (100px minimum)
- Wider fingers = larger overlay (800px maximum)
- Resizing maintains the overlay's aspect ratio

## Node Interface

### Inputs
- **Input01**: Master stream (background) - Always visible with hand detection
- **Input02-Input09**: Overlay streams (add slots as needed)
- Each input can receive a video stream or static image

### Outputs
- **Output01**: The master stream with embedded overlay and visual controls

### Controls
- **Add Slot Button**: Click to add more overlay slots (up to 8 overlays)

## Usage Example

### Basic Setup
1. Add the DynamicPlay node from the **Video** menu
2. Connect a master stream to Input01 (e.g., a WebCam)
3. Connect overlay streams to Input02, Input03, etc. (e.g., Video nodes)
4. The node will display a grid of buttons on the master stream

### Gesture Controls
1. **Activating an Overlay**:
   - Extend your index finger
   - Point at the numbered button corresponding to the overlay stream you want to activate
   - The overlay will appear as picture-in-picture on the master stream
   - Point at the same button again to deactivate it

2. **Moving the Overlay**:
   - Pinch with thumb and index finger (bring them within 40 pixels)
   - Hold the pinch and move your hand
   - The overlay follows your hand in real-time
   - Release the pinch to stop moving

3. **Resizing the Overlay**:
   - While holding the pinch, vary the distance between thumb and index finger
   - Wider fingers = larger overlay (up to 800px)
   - Closer fingers = smaller overlay (minimum 100px)
   - Aspect ratio is maintained automatically

## Visual Indicators

### On-Screen Display
- **Overlay Info**: Shows active overlay and its size (e.g., "Overlay: 2 | Size: 320x240")
- **Button Grid**: Numbered buttons overlay (1-8)
  - Green border: Currently active overlay
  - White border: Available overlays
  - Red border: Button being pointed at
- **Cyan Border**: Border around the active overlay to make it visible

### Hand Visualization
- **Yellow circles**: Thumb tip and index finger tip (key tracking points)
- **Green circles**: Other hand landmarks

## Technical Details

### Architecture
- **Slot 0 (Input01)**: Master stream (always visible)
- **Slots 1-8 (Input02-09)**: Overlay streams (activatable)
- Only one overlay can be active at a time

### Grid Layout
The button grid automatically adjusts based on the number of overlay streams:

| Overlays | Grid Layout |
|----------|-------------|
| 1        | 1x1         |
| 2        | 2x1         |
| 3-4      | 2x2         |
| 5-6      | 3x2         |
| 7-8      | 3x3         |

### Overlay Parameters
- **Minimum Size**: 100x100 pixels
- **Maximum Size**: 800x800 pixels
- **Default Size**: 320x240 pixels
- **Base Pinch Distance**: 100 pixels (for reference)
- **Pinch Threshold**: 40 pixels (to detect pinching)
- Resizing maintains the source aspect ratio

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

- Hand detection runs on each frame of the master stream
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
[WebCam]    → [Input01 - Master Stream]
[Video1]    → [Input02]   
[Video2]    → [Input03]    → [DynamicPlay] → [Output] → [Display/VideoWriter]
[Video3]    → [Input04]    
```

This setup allows you to:
1. Always see the webcam stream (with hand detection)
2. Activate videos as overlays using pointing gestures
3. Move and resize the overlay using pinch gestures
4. Record the composite output (master + overlay)

## Limitations

- Maximum 1 master stream + 8 overlay streams
- Only one overlay active at a time
- Single hand tracking
- Overlay size limited to 100-800 pixels
- Requires MediaPipe installation

## Future Enhancements

Potential improvements could include:
- Support for multiple simultaneous overlays
- Custom gestures for different actions
- Multiple picture-in-picture mode
- Overlay rotation based on gestures
- Adjustable overlay transparency
- Zoom within the overlay itself

## License

This node is part of the CV_Studio project and follows the same license terms.
