# UI Element Coloring - Visual Guide

## Overview
This guide provides a visual reference for how UI elements are now colored to match their parent node's category.

## Node Categories and Colors

### 1. Input Nodes - Yellow Pastel
**Color:** RGB(255, 255, 153, 255) - Soft yellow

**Example Nodes:**
- WebCam
- Video
- YouTube
- RTSP
- WebRTC
- API
- MQTT
- Microphone

**UI Elements Affected:**
- URL input fields (yellow background, black text)
- Frame position sliders (yellow track and handle)
- Quality/resolution sliders (yellow)
- Start/Stop buttons (yellow)

### 2. VisionProcess Nodes - Green Pastel
**Color:** RGB(144, 238, 144, 255) - Light green

**Example Nodes:**
- Resize
- Crop
- Zoom
- Grayscale
- Blur
- Canny
- Threshold
- Brightness
- Contrast

**UI Elements Affected:**
- Width/Height input fields (green background)
- Threshold sliders (green track)
- Zoom factor sliders (green)
- Parameter adjustment fields (green)

### 3. VisionModel Nodes - Peach Puff Pastel
**Color:** RGB(255, 218, 185, 255) - Soft peach

**Example Nodes:**
- Classification
- ObjectDetection
- PoseEstimation
- SemanticSegmentation
- FaceDetection
- LLIE (Low Light Image Enhancement)
- MonocularDepthEstimation

**UI Elements Affected:**
- Model selection combos (peach background)
- Confidence threshold sliders (peach)
- Configuration buttons (peach)
- Parameter input fields (peach)

### 4. AudioProcess Nodes - Powder Blue Pastel
**Color:** RGB(176, 224, 230, 255) - Light blue

**Example Nodes:**
- Spectrogram
- Equalizer

**UI Elements Affected:**
- Frequency band sliders (powder blue)
- Window size inputs (powder blue)
- Audio parameter fields (powder blue)
- Control buttons (powder blue)

### 5. AudioModel Nodes - Pink Pastel
**Color:** RGB(255, 192, 203, 255) - Soft pink

**Example Nodes:**
- Audio classification models (if any)

**UI Elements Affected:**
- All controls in pink pastel

### 6. Visual Nodes - Light Pink
**Color:** RGB(255, 182, 193, 255) - Light pink

**Example Nodes:**
- Heatmap
- ObjHeatmap
- ObjChart
- Visual

**UI Elements Affected:**
- Alpha sliders (light pink)
- Radius sliders (light pink)
- Configuration inputs (light pink)
- Update buttons (light pink)

### 7. Video Nodes - Very Light Green Pastel
**Color:** RGB(193, 255, 193, 255) - Very light green

**Example Nodes:**
- ImageConcat
- VideoWriter
- ScreenCapture
- DynamicPlay

**UI Elements Affected:**
- Layout selection buttons (light green)
- Recording start/stop buttons (light green)
- Quality sliders (light green)
- FPS input fields (light green)

### 8. Trigger Nodes - Violet/Plum Pastel
**Color:** RGB(221, 160, 221, 255) - Light violet

**Example Nodes:**
- Count
- OnOffSwitch

**UI Elements Affected:**
- Threshold sliders (violet)
- Counter inputs (violet)
- Toggle buttons (violet)

### 9. System Nodes - Silver Gray Pastel
**Color:** RGB(192, 192, 192, 255) - Light gray

**Example Nodes:**
- SyncQueue

**UI Elements Affected:**
- Queue size inputs (light gray)
- Timeout sliders (light gray)
- System control buttons (light gray)

### 10. Tracking Nodes - Blue Pastel
**Color:** RGB(173, 216, 230, 255) - Light blue

**Example Nodes:**
- MultiObjectTracking

**UI Elements Affected:**
- Tracker parameter sliders (light blue)
- Configuration inputs (light blue)

### 11. Overlay Nodes - Very Light Gray (Almost White)
**Color:** RGB(245, 245, 245, 255) - Nearly white

**Example Nodes:**
- DrawInformation
- PutText

**UI Elements Affected:**
- Text input fields (very light gray)
- Position inputs (very light gray)
- Size/scale sliders (very light gray)

### 12. Action Nodes - Orange Pastel
**Color:** RGB(255, 204, 153, 255) - Soft orange

**Example Nodes:**
- MongoDB operations

**UI Elements Affected:**
- Database URL inputs (orange)
- Action buttons (orange)
- Configuration fields (orange)

### 13. DataProcess Nodes - Light Blue Pastel
**Color:** RGB(173, 216, 230, 255) - Light blue

**Example Nodes:**
- Statistical processing nodes

**UI Elements Affected:**
- Data input fields (light blue)
- Processing parameter sliders (light blue)

### 14. DataModel Nodes - Very Soft Pink Pastel
**Color:** RGB(255, 222, 243, 255) - Very soft pink

**Example Nodes:**
- PositionPrediction (Timeseries)

**UI Elements Affected:**
- Model configuration inputs (soft pink)
- Prediction parameter sliders (soft pink)

### 15. Router Nodes - Lavender Pastel
**Color:** RGB(216, 191, 216, 255) - Lavender

**Example Nodes:**
- Routing nodes (if any)

**UI Elements Affected:**
- Route selection combos (lavender)
- Configuration buttons (lavender)

## Visual Consistency Features

### Text Readability
All UI elements maintain **black text** (RGB 0, 0, 0) on pastel backgrounds for optimal readability.

### State Indicators
- **Normal State**: Pastel color background
- **Hover State**: Same pastel color (maintains consistency)
- **Active State**: Same pastel color (maintains consistency)

### Slider Specifics
- **Track Background**: Node category color
- **Grab Handle**: Node category color
- **Active Grab**: Node category color (same for consistency)

### Button Specifics
- **Idle**: Node category color
- **Hover**: Node category color (same for visual stability)
- **Pressed**: Node category color (same for consistency)

## Benefits of This Color Scheme

1. **Category Recognition**: Instantly identify which category a node belongs to
2. **Visual Grouping**: Related nodes have similar colors in the workflow
3. **Professional Appearance**: Cohesive color scheme across all UI elements
4. **Accessibility**: Pastel colors with black text ensure readability
5. **Consistency**: Same coloring system for all interactive elements

## Usage Tips

### For Users
1. **Quick Identification**: Use colors to quickly find nodes of a specific category
2. **Visual Debugging**: Easily trace data flow by following color-coded nodes
3. **Workflow Organization**: Group similar-colored nodes for logical sections

### For Developers
1. **Easy Customization**: All colors defined in `node_editor/style.py`
2. **Adding New Categories**: Simply add to STYLE dictionary with a color tuple
3. **Maintaining Consistency**: Theme automatically applies to all UI element types

## Technical Notes

### Color Format
All colors are RGBA tuples: (Red, Green, Blue, Alpha)
- Values range from 0-255
- Alpha is always 255 (fully opaque) for UI elements

### DearPyGUI Theming
The implementation uses DearPyGUI's native theming system:
- `mvThemeCol_FrameBg`: Normal state background
- `mvThemeCol_FrameBgHovered`: Hover state background
- `mvThemeCol_FrameBgActive`: Active/editing state background
- `mvThemeCol_Button`: Button normal state
- `mvThemeCol_ButtonHovered`: Button hover state
- `mvThemeCol_ButtonActive`: Button pressed state
- `mvThemeCol_SliderGrab`: Slider handle
- `mvThemeCol_SliderGrabActive`: Slider handle when dragging
- `mvThemeCol_Text`: Text color (black for all)

## Comparison with Previous Version

### Before This Implementation
- ✓ Node title bars: Colored
- ✓ Combo boxes: Colored (added in previous PR)
- ✗ Input fields: Default gray/white
- ✗ Sliders: Default gray
- ✗ Buttons: Default colors

### After This Implementation
- ✓ Node title bars: Colored
- ✓ Combo boxes: Colored
- ✓ Input fields: **Now colored to match node**
- ✓ Sliders: **Now colored to match node**
- ✓ Buttons: **Now colored to match node**

## Examples in Practice

### Example 1: Video Input Node (Yellow)
```
┌─────────────────────────────┐
│ Video (Yellow title bar)    │
├─────────────────────────────┤
│ [Yellow input: filename.mp4]│
│ Frame: [▬▬▬▬▬▬▬▬▬] (Yellow) │
│ FPS:   [▬▬▬▬▬▬▬▬▬] (Yellow) │
│ [Yellow Button: Load]       │
└─────────────────────────────┘
```

### Example 2: Resize Node (Green)
```
┌─────────────────────────────┐
│ Resize (Green title bar)    │
├─────────────────────────────┤
│ Width:  [Green input: 1920] │
│ Height: [Green input: 1080] │
│ Method: [Green combo: ▼]    │
└─────────────────────────────┘
```

### Example 3: Classification Node (Peach)
```
┌─────────────────────────────┐
│ Classification (Peach bar)  │
├─────────────────────────────┤
│ Model: [Peach combo: ▼]     │
│ Confidence: [▬▬▬▬] (Peach)  │
│ [Peach Button: Process]     │
└─────────────────────────────┘
```

## Future Enhancements

Potential additions:
1. User-customizable color schemes
2. Dark mode support with adjusted colors
3. Colorblind-friendly palette option
4. High-contrast mode for accessibility
5. Theme export/import functionality

## Conclusion

The UI element coloring system provides a professional, cohesive visual experience that makes CV Studio more intuitive and easier to use. Every interactive element now communicates its category through consistent color coding while maintaining excellent readability.
