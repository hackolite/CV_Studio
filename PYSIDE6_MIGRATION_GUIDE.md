# PySide6 Migration Guide for CV_Studio

## Overview

This document outlines the comprehensive plan to migrate CV_Studio from DearPyGUI to PySide6. This is a **major undertaking** that effectively requires rewriting the entire UI layer of the application.

## Scope Assessment

### Current State
- **UI Framework**: DearPyGUI 2.0.0+
- **References**: 288 occurrences of DearPyGUI API calls across codebase
- **Node Files**: 79+ node implementation files
- **Core Framework**: ~925 lines in node_main.py alone
- **Total Impact**: Nearly every Python file that implements UI functionality

### Estimated Effort
**This is effectively a complete application rewrite of the UI layer**, estimated at:
- **Time**: 2-4 months of full-time development
- **Complexity**: High - requires deep understanding of both frameworks
- **Risk**: High - complete regression testing required

## Files Completed

### Phase 1: Foundation (Completed)
- [x] `requirements.txt` - Updated to use PySide6 instead of dearpygui
- [x] `node_editor/pyside6_adapter.py` - Basic compatibility layer for DPG API
- [x] `main_pyside6.py` - Proof-of-concept main application with PySide6

## Migration Strategy

### Approach 1: Complete Rewrite (Recommended)
Rewrite the node editor from scratch using PySide6 best practices:

**Advantages:**
- Clean architecture following Qt patterns
- Better performance and maintainability
- Modern Qt features (signals/slots, model-view)
- Better cross-platform support

**Disadvantages:**
- Longest development time
- Requires complete retesting
- Need to recreate all functionality

### Approach 2: Compatibility Layer (Attempted)
Create a compatibility layer that mimics DearPyGUI API:

**Advantages:**
- Potentially faster initial migration
- Less code to change upfront

**Disadvantages:**
- Complex abstraction layer to maintain
- Won't leverage Qt advantages
- Still requires extensive refactoring
- Current adapter is only ~10% complete

## Detailed Migration Checklist

### Core Framework Migration

#### 1. Node Editor Core (node_editor/node_main.py - 925 lines)
- [ ] Create QGraphicsScene-based node editor
- [ ] Implement node rendering using QGraphicsItem
- [ ] Create node connection system using QGraphicsPathItem
- [ ] Port zoom/pan functionality to QGraphicsView
- [ ] Migrate menu system to QMenuBar
- [ ] Implement file export/import dialogs
- [ ] Port node factory system
- [ ] Migrate node instance management
- [ ] Convert all DPG-specific callbacks to Qt signals/slots

#### 2. Style System (node_editor/style.py)
- [ ] Convert DPG themes to Qt stylesheets (QSS)
- [ ] Implement color theming for nodes
- [ ] Create widget styling for inputs, sliders, combos

#### 3. Utility Functions (node_editor/util.py)
- [ ] Replace dpg_get_value/dpg_set_value with Qt equivalents
- [ ] Port threading/locking mechanisms
- [ ] Update camera connection checks for Qt

### Node Type Migration (79+ files)

Each node category requires updating all files:

#### Input Nodes (~10 files)
- [ ] node/InputNode/node_webcam.py
- [ ] node/InputNode/node_video.py
- [ ] node/InputNode/node_image.py
- [ ] node/InputNode/node_rtsp.py
- [ ] node/InputNode/node_screen_capture.py
- [ ] ... (all other InputNode files)

**Per-node migration steps:**
1. Replace `import dearpygui.dearpygui as dpg` with PySide6 imports
2. Convert `dpg.node()` to QGraphicsItem subclass
3. Replace `dpg.node_attribute()` with custom attribute widgets
4. Convert `dpg.add_*()` calls to Qt widget creation
5. Replace `dpg_get_value()`/`dpg_set_value()` with Qt property access
6. Convert DPG textures to QPixmap/QImage
7. Update all callbacks to Qt signals

#### Process Nodes (~25 files)
- [ ] node/ProcessNode/node_grayscale.py
- [ ] node/ProcessNode/node_adaptive_threshold.py
- [ ] node/ProcessNode/node_blur.py
- [ ] node/ProcessNode/node_canny.py
- [ ] node/ProcessNode/node_clahe.py
- [ ] node/ProcessNode/node_crop.py
- [ ] node/ProcessNode/node_flip.py
- [ ] ... (all other ProcessNode files)

#### DL/ML Nodes (~15 files)
- [ ] node/DLNode/node_yolo.py
- [ ] node/DLNode/node_pose.py
- [ ] node/DLNode/node_segmentation.py
- [ ] ... (all other DLNode files)

#### Audio Nodes (~8 files)
- [ ] node/AudioProcessNode/node_microphone.py
- [ ] node/AudioProcessNode/node_spectrogram.py
- [ ] ... (all other AudioProcessNode files)

#### Tracker Nodes (~5 files)
- [ ] node/TrackerNode/node_mot.py
- [ ] node/TrackerNode/node_reid.py
- [ ] ... (all other TrackerNode files)

#### Other Node Categories (~16 files)
- [ ] StatsNode files
- [ ] TimeseriesNode files
- [ ] TriggerNode files
- [ ] RouterNode files
- [ ] ActionNode files
- [ ] OverlayNode files
- [ ] VisualNode files
- [ ] VideoNode files
- [ ] SystemNode files

### Widget Conversion Table

| DearPyGUI Widget | PySide6 Equivalent | Notes |
|------------------|-------------------|-------|
| `dpg.add_text()` | `QLabel` | Direct mapping |
| `dpg.add_button()` | `QPushButton` | Direct mapping |
| `dpg.add_checkbox()` | `QCheckBox` | Direct mapping |
| `dpg.add_slider_int()` | `QSlider` | Needs value scaling |
| `dpg.add_slider_float()` | `QSlider` | Needs value scaling |
| `dpg.add_input_int()` | `QSpinBox` | Direct mapping |
| `dpg.add_input_float()` | `QDoubleSpinBox` | Direct mapping |
| `dpg.add_input_text()` | `QLineEdit` | Direct mapping |
| `dpg.add_combo()` | `QComboBox` | Direct mapping |
| `dpg.add_image()` | `QLabel` with `QPixmap` | Different approach |
| `dpg.add_raw_texture()` | `QImage`/`QPixmap` | Texture handling differs |
| `dpg.node()` | Custom `QGraphicsItem` | Complex custom implementation |
| `dpg.node_attribute()` | Custom widget layout | No direct equivalent |

### Testing Requirements

Each migrated component requires:
- [ ] Unit tests for basic functionality
- [ ] Integration tests with other nodes
- [ ] Performance testing
- [ ] Visual regression testing
- [ ] Cross-platform testing (Windows, Linux, macOS)

### Documentation Updates

- [ ] README.md - Update framework requirements
- [ ] INSTALLATION.md - Update installation instructions
- [ ] INSTALLATION_WINDOWS.md - Update Windows-specific instructions
- [ ] INSTALLATION_WINDOWS_FR.md - Update French instructions
- [ ] BUILD_GUIDE.md - Update build instructions for PySide6
- [ ] All other build/installation guides

## Technical Challenges

### 1. Node Editor Implementation
**Challenge**: DearPyGUI has built-in node editor support. PySide6 requires custom implementation.

**Solution**: Use QGraphicsScene/QGraphicsView with custom QGraphicsItem subclasses for nodes and connections.

**Example Libraries for Reference:**
- pyqtgraph's flowchart module
- nodeeditor (ryven project)
- Custom implementation from scratch

### 2. Real-time Image Display
**Challenge**: Converting OpenCV frames to Qt format efficiently.

**Current DPG Approach:**
```python
texture = convert_cv_to_dpg(frame, width, height)
dpg_set_value(output_tag, texture)
```

**PySide6 Approach:**
```python
height, width, channels = frame.shape
bytes_per_line = channels * width
qimage = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
pixmap = QPixmap.fromImage(qimage)
qlabel.setPixmap(pixmap)
```

### 3. Threading and Async Updates
**Challenge**: DPG uses `dpg.render_dearpygui_frame()` for manual updates.

**PySide6 Approach:**
- Use `QTimer` for periodic updates
- Use `QThread` for background processing
- Emit Qt signals for cross-thread communication

### 4. Node Connection Rendering
**Challenge**: Visual connection lines between nodes.

**Solution**: Use `QGraphicsPathItem` with `QPainterPath` to draw Bezier curves between node attributes.

## Current Progress Status

### ✅ Completed
1. **requirements.txt** - PySide6 dependency added
2. **node_editor/pyside6_adapter.py** - Basic compatibility layer (partial)
3. **main_pyside6.py** - Proof-of-concept main window

### 🚧 In Progress
Nothing currently in progress - foundation laid only

### ❌ Not Started
- Complete node editor implementation
- All 79+ node file conversions
- Widget system conversions
- Testing infrastructure
- Documentation updates

## Recommendations

### Short Term (If Continuing)
1. **Decide on approach**: Full rewrite vs. compatibility layer
2. **Create node editor prototype**: Build a working node editor with 2-3 sample nodes
3. **Validate approach**: Ensure the architecture works before converting all nodes
4. **Set up automated testing**: Critical for preventing regressions

### Long Term
1. **Incremental migration**: Convert node categories one at a time
2. **Parallel development**: Keep DPG version working while building PySide6 version
3. **Community involvement**: This is too large for one developer
4. **Consider alternatives**: Evaluate if the migration is truly necessary

## Alternative Approaches

### Keep DearPyGUI
**Pros:**
- No migration needed
- Working solution
- Specialized for this use case

**Cons:**
- Less mature than Qt
- Smaller community
- Limited customization

### Hybrid Approach
**Pros:**
- Use PySide6 for main window/menus
- Keep DPG for node editor embedded in Qt
- Gradual migration path

**Cons:**
- Complex integration
- Two UI frameworks to maintain
- Potential performance issues

## Estimated Timeline (Full Migration)

### Phase 1: Core Framework (4-6 weeks)
- Week 1-2: Node editor architecture
- Week 3-4: Basic node rendering and connections
- Week 5-6: Menu system, file I/O, zoom/pan

### Phase 2: Node Migration (8-12 weeks)
- Week 7-9: Input nodes (10 files)
- Week 10-13: Process nodes (25 files)
- Week 14-16: DL/ML nodes (15 files)
- Week 17-18: Audio, Tracker, Other nodes (29 files)

### Phase 3: Testing & Polish (2-4 weeks)
- Week 19-20: Integration testing
- Week 21-22: Bug fixes, optimization

### Phase 4: Documentation (1-2 weeks)
- Week 23-24: Update all documentation

**Total: 15-24 weeks (4-6 months) of full-time development**

## Conclusion

Converting CV_Studio from DearPyGUI to PySide6 is a **major undertaking** that requires significant time and resources. The foundation has been laid with:

1. Updated dependencies (PySide6 in requirements.txt)
2. Basic compatibility adapter module
3. Proof-of-concept main window

However, the bulk of the work remains:
- Complete node editor implementation
- Converting all 79+ node files
- Extensive testing and validation
- Documentation updates

**Recommendation**: Carefully evaluate if this migration is necessary, considering the substantial effort required and the fact that DearPyGUI is currently working well for this application.
