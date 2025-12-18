 # CV Studio

> A professional node-based image processing application for computer vision development, verification, and comparison.

<img src="https://user-images.githubusercontent.com/37477845/172011014-23fb025e-68a5-4cb7-925f-c4417029966c.gif" loading="lazy" width="100%">

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.5.5%2B-green.svg)](https://opencv.org/)

## 🎯 Overview

CV Studio is an advanced node-based image processing application that allows you to visually create computer vision pipelines through an intuitive drag-and-drop interface. Perfect for:

- **Prototyping** - Quickly test and compare different CV algorithms
- **Education** - Learn computer vision concepts interactively
- **Development** - Build and validate processing pipelines before production
- **Research** - Experiment with ML models and traditional CV techniques

## ✨ Key Features

- 🎨 **Visual Node Editor** - Intuitive drag-and-drop interface powered by DearPyGUI
- 🔄 **Real-time Processing** - See results instantly as you build your pipeline
- 🧩 **100+ Built-in Nodes** - Input, processing, ML/DL, analysis, and visualization nodes
- 🤖 **ML/DL Integration** - Support for ONNX models, MediaPipe, and custom models
- 📹 **Multiple Input Sources** - Webcam, video files, images, RTSP streams, screen capture
- 💾 **Save & Load** - Export and import your processing graphs as JSON
- 🏗️ **Modern Architecture** - Professional codebase with proper error handling, logging, and testing
- 🔌 **Extensible** - Easy to add custom nodes and processing algorithms

## 📋 Requirements

```
Python          3.7 or later
opencv-python   4.5.5.64 or later
onnxruntime-gpu 1.12.0 or later
dearpygui       1.11.0 or later
mediapipe       0.8.10 or later  ※ Required for MediaPipe nodes
protobuf        3.20.0 or later  ※ Required for MediaPipe nodes
filterpy        1.4.5 or later   ※ Required for MOT (Multi-Object Tracking) nodes
```

## 🚀 Installation

### Method 1: Direct Installation (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/hackolite/CV_Studio.git
   cd CV_Studio
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python main.py
   ```

### Method 2: Using Virtual Environment (Recommended for Development)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Method 3: Pip Installation

```bash
# Install build tools first
# Windows: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Ubuntu: sudo apt-get install build-essential libssl-dev libffi-dev python3-dev

# Install required packages
pip install Cython numpy wheel

# Install from GitHub
pip install git+https://github.com/hackolite/CV_Studio.git

# Run the application
ipn-editor
```

### Method 4: Docker

See [Image-Processing-Node-Editor/docker/nvidia-gpu](https://github.com/Kazuhito00/Image-Processing-Node-Editor/tree/main/docker/nvidia-gpu) for Docker setup instructions.  

### Method 5: Standalone Executable (Windows)

For Windows users who want a standalone .exe file that doesn't require Python installation:

#### 📋 Prérequis / Prerequisites

Before building the executable, ensure you have:
- **Python 3.7+** installed (tested with Python 3.12)
- **Git** for cloning the repository
- **Windows OS** (for building Windows executables)

#### 🔧 Étapes de création du .exe / Step-by-Step Build Instructions

**Étape 1 : Cloner le dépôt / Step 1: Clone the repository**

```bash
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

**Étape 2 : Installer les dépendances principales / Step 2: Install main dependencies**

```bash
# Install main dependencies
pip install -r requirements.txt
```

**Étape 3 : Installer les dépendances de build / Step 3: Install build dependencies**

```bash
# Install PyInstaller and build tools
pip install -r requirements-build.txt
# Or manually: pip install pyinstaller
```

**Étape 4 : Construire l'exécutable / Step 4: Build the executable**

```bash
# Standard build with clean
python build_exe.py --clean

# Alternative: Build without console window (GUI only)
python build_exe.py --clean --windowed

# Alternative: With custom icon
python build_exe.py --clean --icon your_icon.ico

# Alternative: Build + Windows installer (requires Inno Setup)
python build_exe.py --clean --installer
```

The build process will:
1. ✅ Verify all dependencies are installed
2. ✅ Clean previous build artifacts (if --clean flag used)
3. ✅ Package all Python dependencies
4. ✅ Include all nodes (Input, Process, DL, Audio, etc.)
5. ✅ Bundle all ONNX models for object detection
6. ✅ Create the standalone executable
7. ✅ Create Windows installer (if --installer flag used)

**Build time:** Approximately 5-15 minutes depending on your system.

**Étape 5 : Localiser l'exécutable / Step 5: Locate your executable**

Your .exe file is ready at:
```
dist/CV_Studio/CV_Studio.exe
```

The `dist/CV_Studio/` folder contains:
- `CV_Studio.exe` - Main executable
- `node/` - All node implementations and ONNX models
- `node_editor/` - Editor core and settings
- `src/` - Source utilities
- `_internal/` - Python runtime and dependencies

**Étape 6 : Tester l'exécutable / Step 6: Test the executable**

```bash
# Navigate to the dist folder
cd dist/CV_Studio

# Run the executable
CV_Studio.exe

# Or run with debug output
CV_Studio.exe --use_debug_print
```

**Étape 7 : Vérifier les fonctionnalités / Step 7: Verify functionality**

Test that everything works:
1. Open the application
2. Add an **Image** node (Input → Image)
3. Add an **Object Detection** node (VisionModel → Object Detection)
4. Select a YOLOX model
5. Add a **Result Image** node
6. Connect the nodes and verify object detection works

**Étape 8 : Distribution / Step 8: Distribution**

You have two distribution options:

**Option A: ZIP Archive (Portable)**
```bash
# Create a ZIP archive
cd dist
# On Windows PowerShell:
Compress-Archive -Path CV_Studio -DestinationPath CV_Studio_v1.0.zip

# Or use 7-Zip (if installed):
7z a CV_Studio_v1.0.zip CV_Studio
```

The ZIP file can be distributed to users who just need to:
1. Extract the ZIP file
2. Run `CV_Studio.exe`
3. No Python installation required!

**Option B: Windows Installer (Professional)**

If you used the `--installer` flag or want to create an installer:

```bash
# Install Inno Setup from: https://jrsoftware.org/isdl.php

# Compile the installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
# Or just: iscc installer.iss (if in PATH)
```

The installer will be created in `installer_output/CV_Studio_Setup_v1.0.0.exe` and provides:
- ✅ Professional installation wizard
- ✅ Start Menu shortcuts
- ✅ Desktop shortcut (optional)
- ✅ Clean uninstallation
- ✅ Multi-language support (EN/FR)

#### 📦 What's included in the executable

- ✅ All nodes (Input, Process, DL, Audio, etc.)
- ✅ All ONNX models for object detection (YOLOX, YOLO, FreeYOLO, etc.)
- ✅ Complete Python runtime (no separate Python installation needed)
- ✅ All required libraries (OpenCV, DearPyGUI, ONNX Runtime, etc.)
- ✅ Configuration files and fonts

**Size:** Approximately 800 MB - 1.5 GB

#### 🔍 Options de build avancées / Advanced Build Options

```bash
# Clean build (recommended)
python build_exe.py --clean

# GUI mode without console window
python build_exe.py --windowed

# Debug mode with detailed logging
python build_exe.py --debug

# Custom icon (if you have an icon file)
python build_exe.py --icon your_icon.ico

# Create Windows installer (requires Inno Setup)
python build_exe.py --clean --installer

# Combine options
python build_exe.py --clean --windowed --icon your_icon.ico --installer
```

**Note about PyTorch and ONNX:**
- CV Studio uses **ONNX Runtime** (included) for AI model inference
- **PyTorch is NOT required** for the executable to work
- PyTorch is only needed if you want to:
  - Train new models
  - Convert PyTorch models to ONNX
  - Develop custom PyTorch-based nodes
- ONNX Runtime provides fast inference with GPU support (CUDA)
- See the detailed guides for more information on dependencies

#### ⚠️ Dépannage / Troubleshooting

**Problem:** PyInstaller not found
```bash
pip install pyinstaller
```

**Problem:** Missing dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-build.txt
```

**Problem:** Exe doesn't start
- Install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Run from command line to see error messages: `CV_Studio.exe --use_debug_print`
- Check antivirus isn't blocking the executable

**Problem:** ONNX models not found
- Verify the `dist/CV_Studio/node/DLNode/` directory structure is intact
- Rebuild with `python build_exe.py --clean`

#### 📚 Documentation détaillée / Detailed Documentation

**For comprehensive guides, see:**
- [Quick Reference](BUILD_EXE_QUICKREF.md) - Quick start guide
- [Full Guide (English)](BUILD_EXE_GUIDE.md) - Complete documentation with all options
- [Guide complet (Français)](BUILD_EXE_GUIDE_FR.md) - Documentation complète en français

## 💡 Usage

### Basic Usage

Start the application with:
```bash
python main.py
```

#### Command Line Options

- `--setting <path>` - Specify custom configuration file (default: `node_editor/setting/setting.json`)
- `--unuse_async_draw` - Disable asynchronous drawing for debugging
- `--use_debug_print` - Enable debug output

**Example:**
```bash
python main.py --setting custom_config.json --use_debug_print
```

### Quick Start Guide

#### 1. Create a Node
Select a node from the menu and click to add it to the canvas.

<img src="https://user-images.githubusercontent.com/37477845/172030402-80d3d14e-d0c8-464f-bb0c-139bfe676845.gif" loading="lazy" width="60%">

#### 2. Connect Nodes
Drag from an output terminal to an input terminal to create connections. Only compatible terminal types can be connected.

<img src="https://user-images.githubusercontent.com/37477845/172030403-ec4f0a89-22d5-4467-9b11-c8e595e65997.gif" loading="lazy" width="60%">

#### 3. Delete a Node
Select the node and press the **Delete** key.

<img src="https://user-images.githubusercontent.com/37477845/172030418-201d7df5-1984-4fa7-8e47-9264c5dcb6cf.gif" loading="lazy" width="60%">

#### 4. Export Your Graph
Save your processing pipeline as a JSON file via the **Export** menu option.

<img src="https://user-images.githubusercontent.com/37477845/172030429-9c6c453c-b8b0-4ccf-b36e-eb666c2d919f.gif" loading="lazy" width="60%">

#### 5. Import a Graph
Load a previously saved processing pipeline from a JSON file.

<img src="https://user-images.githubusercontent.com/37477845/172030433-8a07b702-9ba4-43e7-9f2f-f0885f472c44.gif" loading="lazy" width="60%">

### Workflow Examples

Here are some practical examples to help you get started with common computer vision tasks:

#### Example 1: Basic Image Processing Pipeline

**Task:** Apply blur and edge detection to an image

1. Add an **Image** node (Input → Image)
2. Add a **Blur** node (VisionProcess → Blur)
3. Add a **Canny** node (VisionProcess → Canny)
4. Add a **Result Image** node (Visual → Result Image)
5. Connect: Image → Blur → Canny → Result Image
6. Click "Select Image" in the Image node to load your image
7. Adjust blur and Canny parameters using the sliders

**Result:** You'll see real-time edge detection applied to your blurred image.

#### Example 2: Webcam Object Detection

**Task:** Detect objects in real-time from your webcam

1. Add a **WebCam** node (Input → WebCam)
2. Add an **Object Detection** node (VisionModel → Object Detection)
3. Add a **Draw Information** node (Overlay → Draw Information)
4. Add a **Result Image** node (Visual → Result Image)
5. Connect: WebCam → Object Detection → Draw Information → Result Image
6. Select your camera device in the WebCam node
7. Choose a detection model in the Object Detection node

**Result:** Real-time object detection with bounding boxes drawn on your webcam feed.

#### Example 3: Video Processing with Multiple Effects

**Task:** Process a video file with multiple filters

1. Add a **Video** node (Input → Video)
2. Add multiple processing nodes (e.g., **Brightness**, **Contrast**, **Grayscale**)
3. Add an **Image Concat** node (Overlay → Image Concat) to compare results
4. Add a **Result Image** node (Visual → Result Image)
5. Connect the Video node to each processing node
6. Connect all processing outputs to the Image Concat node
7. Connect Image Concat to Result Image

**Result:** Side-by-side comparison of different processing effects on your video.

#### Example 4: Face Detection and Analysis

**Task:** Detect faces and apply effects

1. Add an **Image** or **WebCam** node
2. Add a **Face Detection** node (VisionModel → Face Detection)
3. Add a **Draw Information** node (Overlay → Draw Information)
4. Add a **Crop** node (VisionProcess → Crop) - optional, to extract faces
5. Connect nodes in sequence
6. Use the Draw Information node to visualize detected faces

**Result:** Automatic face detection with bounding boxes and optional face extraction.

### Tips & Best Practices

#### Working with Nodes

- **Organize Your Workspace:** Arrange nodes logically from left (inputs) to right (outputs) for better readability
- **Use Image Concat:** Compare different processing approaches side-by-side using the Image Concat node
- **Check Terminal Colors:** Nodes can only connect if terminal types match (indicated by color)
- **Start Simple:** Begin with a basic pipeline and add complexity incrementally
- **Save Frequently:** Use Export to save your work regularly

#### Performance Optimization

- **Reduce Resolution:** Use the **Resize** node early in your pipeline to speed up processing
- **Toggle Nodes:** Use the **ON/OFF Switch** node to temporarily disable expensive operations
- **Limit Video FPS:** Adjust skip rate in Video nodes to process fewer frames
- **GPU Acceleration:** Enable GPU in Deep Learning nodes when available (requires ONNX Runtime GPU)

#### Debugging and Testing

- **Use Debug Print:** Launch with `--use_debug_print` to see detailed node execution logs
- **Disable Async Draw:** Use `--unuse_async_draw` if you experience UI issues
- **Check Connections:** Verify all node connections are properly established (no red indicators)
- **Monitor Performance:** Use the **FPS** node to track processing speed
- **Test Incrementally:** Add one node at a time and verify it works before adding more

#### Node Selection Tips

- **Input Nodes:** 
  - Use **Image** for static images and prototyping
  - Use **WebCam** for real-time testing
  - Use **Video** for batch processing and testing on recorded content
  - Use **RTSP** for network camera streams

- **Processing Nodes:**
  - Start with basic nodes (Brightness, Contrast, Blur) before complex ones
  - Chain multiple processing nodes to create sophisticated effects
  - Use **Grayscale** before **Threshold** for better results

- **ML/DL Nodes:**
  - Check GPU availability before enabling GPU inference
  - Different models have different performance characteristics - experiment!
  - Combine detection nodes with tracking for smoother results

- **Visualization:**
  - Use **Result Image** for final output
  - Use **Result Image (Large)** when you need more detail
  - Use **PutText** to add custom labels and timing information
  - Use **RGB Histogram** for color analysis

### Keyboard Shortcuts & UI Interactions

| Action | Shortcut/Method |
|--------|----------------|
| **Add Node** | Click menu item, then click on canvas |
| **Delete Node** | Select node, press `Delete` key |
| **Pan Canvas** | Middle mouse button drag or `Ctrl` + Left mouse drag |
| **Connect Nodes** | Drag from output terminal to input terminal |
| **Disconnect Nodes** | Right-click on connection line, select delete |
| **Select Multiple** | `Ctrl` + Click on nodes |
| **Minimap** | Click minimap in bottom-right to navigate large graphs |

### Troubleshooting

#### Common Issues and Solutions

**Problem:** Application crashes on startup
- **Solution:** Check if required dependencies are installed: `pip install -r requirements.txt`
- **Solution:** Ensure you have a compatible Python version (3.7+)
- **Solution:** Try disabling async drawing: `python main.py --unuse_async_draw`

**Problem:** Webcam not detected
- **Solution:** Close other applications using the webcam
- **Solution:** Check camera permissions in your OS settings
- **Solution:** Try different device numbers in the WebCam node dropdown

**Problem:** Cannot connect two nodes
- **Solution:** Verify terminal types match (same color)
- **Solution:** Check that output terminal connects to input terminal (not output to output)
- **Solution:** Some nodes require specific input types - check node documentation

**Problem:** Deep Learning node shows "Model not found" error
- **Solution:** Download the required model files (see node-specific README files)
- **Solution:** Check the model path in the node configuration
- **Solution:** Verify you have the correct ONNX runtime installed

**Problem:** Low FPS / Slow processing
- **Solution:** Add a **Resize** node to reduce image resolution
- **Solution:** Enable GPU acceleration in DL nodes if available
- **Solution:** Reduce video skip rate or use lower resolution input
- **Solution:** Close unnecessary nodes and connections

**Problem:** Export/Import doesn't work
- **Solution:** Ensure you're saving to a writable location
- **Solution:** Check that the JSON file is valid and not corrupted
- **Solution:** Import files should be loaded before adding new nodes

**Problem:** Node parameters don't update
- **Solution:** Try reconnecting the node connections
- **Solution:** Restart the application
- **Solution:** Check if the node is receiving valid input data

### Advanced Usage

#### Custom Configuration Files

Create custom configuration files to save your preferred settings:

```bash
# Create a custom config
cp node_editor/setting/setting.json my_config.json

# Edit my_config.json to set your preferences
# - webcam_width/height: Camera resolution
# - process_width/height: Processing resolution  
# - editor_width/height: Window size
# - use_gpu: Enable GPU acceleration
# - use_pref_counter: Enable performance monitoring

# Run with custom config
python main.py --setting my_config.json
```

#### Working with Multiple Cameras

CV Studio supports multiple cameras simultaneously:

1. The application automatically detects available cameras on startup
2. Each **WebCam** node can select a different camera device
3. Use multiple WebCam nodes to process multiple camera feeds in parallel
4. Combine feeds using **Image Concat** for multi-camera display

#### Creating Custom Nodes

Extend CV Studio with your own nodes:

```python
# Create a new node file in node/ProcessNode/
from node.ProcessNode.node_abc import ProcessNodeABC

class MyCustomNode(ProcessNodeABC):
    node_label = 'My Custom Filter'
    node_tag = 'MyCustomFilter'
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        # Your processing logic here
        input_image = self._get_input_image(node_image_dict, connection_list)
        # Process input_image...
        output_image = input_image  # Replace with your processing
        
        return {"image": output_image, "json": None}
```

See the [Development](#-development) section for more details on creating custom nodes.

#### Batch Processing

Process multiple files efficiently:

1. Create your processing pipeline using an **Image** node
2. Test with a single image
3. Export the graph configuration
4. Modify the exported JSON to point to different images
5. Import and process each configuration

For video batch processing:
1. Use the **Video** node with your pipeline
2. Add a **Video Writer** node to save output
3. Configure output settings in `setting.json`
4. Process multiple videos by changing the input file

#### Integration with External Systems

CV Studio supports integration with external systems:

- **API Integration:** Use API input nodes to receive data from REST endpoints
- **WebSocket Streaming:** Real-time data streaming for live applications
- **RTSP Streams:** Connect to IP cameras and network video sources
- **Serial Communication:** Interface with Arduino and other embedded devices (enable in settings)

See [tests/dummy_servers/README.md](tests/dummy_servers/README.md) for examples of external server integration.

## 🏗️ Architecture

CV Studio features a modern, professional architecture designed for scalability and maintainability.

### Timestamped FIFO Queue System

**New in this version**: CV Studio now implements a timestamped queue system for node data communication that ensures:
- ✅ **FIFO Data Retrieval** - Oldest data is retrieved first from node queues
- ✅ **Automatic Timestamping** - All data automatically timestamped when created
- ✅ **Thread-Safe Operations** - Safe concurrent access across all nodes
- ✅ **Backward Compatibility** - Existing nodes work without modifications
- ✅ **Queue Management** - Automatic size limits prevent memory overflow

Each node that sends data to other nodes does so through its own timestamped queue. When nodes retrieve data, they get the oldest data from the FIFO queue, ensuring chronological processing order. See [TIMESTAMPED_QUEUE_SYSTEM.md](TIMESTAMPED_QUEUE_SYSTEM.md) for detailed documentation.

**Benefits:**
- Proper temporal ordering of video frames and audio data
- Prevention of data race conditions
- Better synchronization between nodes
- Monitoring and debugging capabilities

### Project Structure

```
CV_Studio/
├── src/                    # New professional architecture
│   ├── core/              # Core business logic
│   │   ├── nodes/         # Node abstractions (BaseNode, NodeFactory, EnhancedNode)
│   │   ├── config/        # Settings management
│   │   └── pipeline/      # Processing pipeline (future)
│   ├── nodes/             # Node implementations with adapters
│   │   ├── input/         # Input node adapters
│   │   ├── process/       # Processing node adapters
│   │   ├── ml/            # ML/DL node adapters
│   │   └── examples/      # Example implementations
│   ├── utils/             # Reusable utilities
│   │   ├── exceptions.py  # Custom exception hierarchy
│   │   ├── logging.py     # Centralized logging
│   │   └── resource_manager.py  # Resource lifecycle management
│   └── gui/               # GUI components (future)
│
├── node/                  # Original node implementations (fully compatible)
│   ├── InputNode/         # Input sources (webcam, video, images)
│   ├── ProcessNode/       # Image processing nodes
│   ├── DLNode/            # Deep learning nodes
│   ├── ActionNode/        # Action/control nodes
│   ├── OverlayNode/       # Drawing and overlay nodes
│   ├── timestamped_queue.py  # Timestamped FIFO queue system (NEW)
│   ├── queue_adapter.py   # Backward-compatible queue adapter (NEW)
│   └── ...                # Other node categories
│
├── node_editor/           # Node editor core and UI
├── tests/                 # Test suite (52+ tests, including queue system)
├── main.py               # Application entry point
└── requirements.txt      # Python dependencies
```

### New Features in src/ Directory

The `src/` directory introduces professional development practices:

#### 1. **Exception Hierarchy**
```python
from src.utils.exceptions import NodeExecutionError, NodeConfigurationError

# Clear, structured error handling
raise NodeExecutionError(node_id, "Processing failed", original_exception)
```

#### 2. **Centralized Logging**
```python
from src.utils.logging import get_logger

logger = get_logger(__name__)
logger.info("Processing node...")
logger.error("Node failed", exc_info=True)
```

#### 3. **Resource Management**
```python
from src.utils.resource_manager import get_resource_manager

manager = get_resource_manager()
manager.register('video_capture', video_cap, cleanup_func=lambda v: v.release())
```

#### 4. **Settings Management**
```python
from src.core.config import Settings

settings = Settings('config.json')
width = settings.get('webcam_width', 640)
settings.set('use_gpu', True)
```

#### 5. **Enhanced Node Development**
```python
from src.core.nodes import EnhancedNode

class MyNode(EnhancedNode):
    node_label = 'My Custom Node'
    node_tag = 'MyNode'
    
    # Built-in logging, error handling, resource management
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        result = self.safe_execute(self.process_image, node_image_dict)
        return {"image": result, "json": None}
```

### Backward Compatibility

**100% backward compatible** - All existing code in the `node/` and `node_editor/` directories continues to work unchanged. The new architecture in `src/` provides optional enhancements for future development.

### Documentation

- **[Architecture Details](ARCHITECTURE.md)** - Complete architecture overview
- **[Migration Guide](MIGRATION_GUIDE.md)** - How to use new features
- **[src/README.md](src/README.md)** - Technical architecture documentation
- **[Restructuring Summary](RESTRUCTURING_SUMMARY.md)** - Changes and improvements
- **[Timestamped Queue System](TIMESTAMPED_QUEUE_SYSTEM.md)** - FIFO queue documentation (NEW) 🆕

#### Video-Audio Synchronization Documentation

Comprehensive guides explaining how the Video Node synchronizes audio spectrograms with video playback:

- **[📑 Documentation Index](VIDEO_AUDIO_SYNC_INDEX.md)** - Complete index of all documentation (START HERE!) 🌟
- **[📖 Documentation Guide](VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md)** - Navigate all documentation 🎯
- **[📄 Simple Summary](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md)** - One-page visual overview 🎨
- **[Quick Reference](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md)** - Quick overview and key formulas ⚡
- **[Video-Audio Synchronization Explained](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)** - Complete technical explanation in English
- **[Synchronisation Vidéo-Audio Expliquée](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md)** - Explication complète en français
- **[Visual Sync Diagrams](VISUAL_SYNC_DIAGRAMS.md)** - Visual diagrams and flowcharts
- **[VFR to CFR Conversion](VFR_TO_CFR_CONVERSION.md)** - Automatic variable frame rate to constant frame rate conversion 🆕

## 🧪 Testing

CV Studio includes comprehensive test coverage (52+ tests).

### Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_utils/ -v
python -m pytest tests/test_core/ -v

# Run queue system tests (NEW)
python -m pytest tests/test_timestamped_queue.py tests/test_queue_adapter.py tests/test_queue_integration.py -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov=node --cov-report=html
```

### Test Coverage

- ✅ Exception hierarchy (7 tests)
- ✅ Logging utilities (6 tests)
- ✅ Resource management (8 tests)
- ✅ Node factory (7 tests)
- ✅ Settings management (10 tests)
- ✅ **Timestamped queue system (35 tests)** ← NEW
  - Core queue functionality (17 tests)
  - Backward compatibility adapter (12 tests)
  - Integration with node system (6 tests)

## 📚 Available Nodes

# Node
<details>
<summary>Input Node</summary>

<table>
    <tr>
        <td width="200">
            Image
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031017-fd0107a5-2a33-4e47-a18b-ea53213f65e1.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that reads still images (bmp, jpg, png, gif) and outputs images<br>
            Open the file dialog with the "Select Image" button
        </td>
    </tr>
    <tr>
        <td width="200">
            Video
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031118-9382a9f6-d45c-4d39-ae82-59575a109664.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that reads a video (mp4, avi) and outputs an image for each frame<br>
            Open the file dialog with the "Select Movie" button<br>
            Check "Loop" to play the video in a loop<br>
            "Skip rate" sets the interval for skipping the output image.
        </td>
    </tr>
    <tr>
        <td width="200">
            Video(Set Frame Position)
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/211860076-00b700a5-18e1-46cc-ae30-376976d54f63.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that reads a video (mp4, avi) and outputs an image at the specified frame position<br>
            Open the file dialog with "Select Movie" button
        </td>
    </tr>
    <tr>
        <td width="200">
            WebCam
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031202-2ec0e976-12c7-41a9-94e4-ef162302f0b1.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that reads a webcam and outputs an image for each frame<br>
            Specify the camera number in the Device No drop-down list<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            RTSP
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/178135453-293836c2-e38d-476f-9b64-ea654470ba2e.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that reads the RTSP input of a network camera and outputs an image for each frame<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Microphone
        </td>
        <td width="320">
            (Audio Input Node)
        </td>
        <td width="760">
            A node that captures real-time audio from a microphone and outputs audio data<br>
            Select audio device from the dropdown list<br>
            Configure sample rate (8kHz to 48kHz) and chunk duration (0.1s to 5.0s)<br>
            Click "Start" to begin recording, "Stop" to pause<br>
            Outputs audio data compatible with Spectrogram and other audio processing nodes<br>
            See <a href="node/InputNode/README_Microphone.md">README_Microphone.md</a> for details
        </td>
    </tr>
    <tr>
        <td width="200">
            Int Value
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031284-95255053-6eaf-4298-a392-062129e698f6.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that outputs an integer value<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Float Value
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031323-98ae0273-7083-48d0-9ef2-f02af7fde482.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that outputs the float value<br>
        </td>
    </tr>
</table>
</details>

<details>
<summary>Process Node</summary>

<table>
    <tr>
        <td width="200">
            ApplyColorMap
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031657-81e70c61-05a3-4bff-9423-67ac9e486f5c.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that applies pseudo color to the input image and outputs a pseudo color image
        </td>
    </tr>
    <tr>
        <td width="200">
            Blur
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031667-399472c9-7731-4cc2-8258-6879a1836b66.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that executes smoothing processing on the input image and outputs the smoothed image
        </td>
    </tr>
    <tr>
        <td width="200">
            Brightness
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031761-9ab8d83d-9bac-4854-9a6d-44c34692a002.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that executes brightness adjustment processing on the input image and outputs the brightness adjustment image<br>
            Brightness adjustment value can be changed with the "alpha" slide bar<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Canny
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172032723-df30d0bb-ed24-4909-afee-c3a78f66dad9.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that executes edge detection processing using the Canny method on the input image and outputs the edge detection image.<br>
           Specify the minimum and maximum thresholds with the slider
        </td>
    </tr>
    <tr>
        <td width="200">
            Contrast
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042432-dab55644-f95f-4854-bcc4-45bb54d9c5bd.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that executes contrast adjustment processing on the input image and outputs the contrast adjustment image.<br>
           Contrast adjustment value can be changed with the "beta" slide bar<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Crop
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042627-1c90f1ca-2d57-45b4-8dbe-ce0e4917d08e.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs cropping of the input image and outputs the cropped image<br>
            Upper left coordinates(x1, y1) and upper right coordinates(x2, y2) can be changed with the slider<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            EqualizeHist
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042718-4f14021f-c29e-4886-b44f-46af644a74fe.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs histogram flattening of the brightness part of the input image and outputs the image<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Flip
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042828-62d5ba24-69f9-4d6b-b3f9-322f43af0284.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs horizontal/vertical inversion to the input image and outputs the image<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Gamma Correction
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042880-7804d210-72f7-4977-ac11-41f9e7883a65.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs gamma correction on the input image and outputs the image<br>
            Gamma value can be changed with the slider
        </td>
    </tr>
    <tr>
        <td width="200">
            Grayscale
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042929-1501d980-b00b-42f7-bbb3-a078d95be5ff.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that grayscales the input image and outputs the image<br>
        </td>
    </tr>
    <tr>
        <td width="200">
            Threshold
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042985-3e7908cc-f485-4684-884c-8cfe3d020004.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that binarizes the input image and outputs the image<br>
            Specify the binarization algorithm with "type"<br>
            Change threshold with "threshold"<br><br>
            In "type", "Otsu binarization (THRESH_OTSU)" is an automatic threshold determination algorithm, so the "threshold" value is ignored.
        </td>
    </tr>
    <tr>
        <td width="200">
            Simple Filter
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/178098739-ee15159c-d66f-4b5d-822d-dbaf686448d6.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs 3x3 2D filtering processing on the input image and outputs the image
        </td>
    </tr>
    <tr>
        <td width="200">
            Omnidirectional Viewer
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/182130848-fff3d053-6c21-4a03-9e96-371111112226.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that transforms an input image(360-degree image) with the specified roll, pitch, and yaw axes and outputs the image<br>
            The input image is assumed to be an equirectangular projection image
        </td>
    </tr>
    <tr>
        <td width="200">
            Resize
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/210739536-5f70e55a-3433-4325-81e2-79619943bd9f.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that resizes the input image with the specified height, width and interpolation method and outputs the image.
        </td>
    </tr>
</table>
</details>


<details>
<summary>Deep Learning Node</summary>

You can specify the model in the drop-down list and change the device at the time of inference with the CPU / GPU checkbox.<br>
* If the model does not support GPU inference, checking GPU will still result in CPU inference<br>
Refer to each directory of "node/deep_learning_node/XXXXXXXX" for the license of the model used by the node.
<table>
    <tr>
        <td width="200">
            Classification
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172043243-2c037f0b-e1ba-4e3b-96a8-b0e3358f6616.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs classification on the input image<br>
            The output image is a raw image<br><br>
            Performs classification on the bounding box when an Object Detection node is connected
        </td>
    </tr>
    <tr>
        <td width="200">
            Face Detection
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045704-23c00432-90b1-4a53-b621-6413ba8f18dd.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs face detection on the input image<br>
            The output image is a raw image
        </td>
    </tr>
    <tr>
        <td width="200">
            Low-Light Image Enhancement
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045825-8ad902e0-d11d-44b7-8390-bb3e7ab12622.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs Low-Light Image Enhancement on the input image<br>
            The output image is an image with Low-Light Image Enhancement applied.
        </td>
    </tr>
    <tr>
        <td width="200">
            Monocular Depth Estimation
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045864-8e249b46-d5bf-4d48-b540-2e5102afbe21.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that performs monocular depth estimation on the input image<br>
            The output image is a grayscale image to which monocular depth estimation is applied.
        </td>
    </tr>
    <tr>
        <td width="200">
            Object Detection
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172044154-1ef0a081-0e1e-4e3f-8d0d-599b73ee895d.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs object detection on the input image<br>
            The output image is a raw image
        </td>
    </tr>
    <tr>
        <td width="200">
            Pose Estimation
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045920-cf18889d-d2f8-43ba-b3a5-773fd8df7eec.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs attitude estimation for the input image<br>
            The output image is a raw image
        </td>
    </tr>
    <tr>
        <td width="200">
            Semantic Segmentation
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045965-6d77f4ef-d208-40c9-a335-25a9d1d07acc.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that performs semantic segmentation on the input image<br>
            The output image is a raw image
        </td>
    </tr>
    <tr>
        <td width="200">
            QR Code Detection
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/174199447-f92a18ef-cc76-46a3-abf5-314f8f9e01fe.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that executes QR code detection for the input image<br>
            The output image is a raw image
        </td>
    </tr>
</table>
</details>

<details>
<summary>Analysis Node</summary>

<table>
    <tr>
        <td width="200">
            FPS
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046425-ad00b7ea-b91b-4542-81d2-c92002f8a925.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that calculates FPS based on the processing time(ms) of the node<br>
           Processing time input terminal can be added with "Add Slot"
        </td>
    </tr>
    <tr>
        <td width="200">
            RGB Histgram
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046609-45ce392e-cbf1-4f14-b4eb-ee6b3fe7cc80.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that calculates the histogram of each RGB channel of the input image and displays it in the graph
        </td>
    </tr>
    <tr>
        <td width="200">
            BRISQUE
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/173472170-cc47e04e-80e7-4126-949f-a0f034b9f0b8.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that evaluates image quality using BRISQUE<br>
            * The higher the number, the worse
        </td>
    </tr>
</table>
</details>

<details>
<summary>Draw Node</summary>

<table>
    <tr>
        <td width="200">
            Draw Information
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046789-0d43ca22-b202-404a-ba01-dd80a01d01e5.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Draw the analysis result for the image of the node that outputs the raw image such as Classification node and Object Detection node.
        </td>
    </tr>
    <tr>
        <td width="200">
            Image Concat
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046873-1bb27261-160a-452e-b454-05d249ec1aca.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that displays multiple input images side by side<br>
           Image input terminal can be added with "Add Slot"
        </td>
    </tr>
    <tr>
        <td width="200">
            PutText
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046942-7d004807-348d-4576-bac5-f4da27f0e5ed.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            A node that draws text in the upper left of the input image<br>
            Drawing color can be selected in the color map<br>
            By connecting the processing time input terminal, the processing time is also drawn.
        </td>
    </tr>
    <tr>
        <td width="200">
            Result Image
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047088-eb867eab-98bf-4f46-8435-533f03a8f9b0.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node to display the image<br>
            Display larger than the processing node<br>
            Also, if you connect a node that outputs raw images such as a Classification node or Object Detection node, the analysis result will be added and drawn.
        </td>
    </tr>
    <tr>
        <td width="200">
            Result Image(Large)
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047088-eb867eab-98bf-4f46-8435-533f03a8f9b0.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Larger than the Result Image node
        </td>
    </tr>
</table>
</details>

<details>
<summary>Other Node</summary>

<table>
    <tr>
        <td width="200">
            ON/OFF Switch
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047545-e0887c75-16d0-450e-8cc2-50f4065173e0.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node to switch whether to output the input image or not
        </td>
    </tr>
    <tr>
        <td width="200">
            Video Writer
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047578-7ee450ff-0816-4006-814f-55f854ca921a.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node to export the input image as a video<br>
            Output destination, output size, FPS are specified in "setting.json"
        </td>
    </tr>
</table>
</details>

<details>
<summary>Preview Release Node</summary>

Nodes whose specifications may change significantly in the future
<table>
    <tr>
        <td width="200">
            MOT
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172049681-67df2cc3-3db3-4766-a96e-f7c557e4a5b9.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that inputs an Object Detection node and executes MOT(Multi Object Tracking)
        </td>
    </tr>
    <tr>
        <td width="200">
            Exec Python Code
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/179454389-7b707584-ef3b-43f2-8e99-db74005c76e8.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that executes Python code <br>
            The variable for the input image is "input_image" <br>
            The variable for the output image is "output_image"
        </td>
    </tr>
    <tr>
        <td width="200">
            Screen Capture
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/216200610-5a5714c0-99ac-4ec9-a56e-90ae99088815.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that captures and outputs the desktop full screen<br>
        </td>
    </tr>
</table>
</details>

# Node(Other repository)
It is a node published in other repositories.<br>
To use it with Image-Processing-Node-Editor, follow the installation instructions for each repository.

<details>
<summary>Input Node</summary>

<table>
    <tr>
        <td width="200">
            <a href=https://github.com/Kazuhito00/IPNE-YouTube-Input-Node>YouTube</a> 
        </td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/179450682-f7cc8237-e9d8-4c0f-b5d8-d2caac453f04.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Node that reads YouTube and outputs images<br>
            Please specify the URL of the YouTube video in the URL field and press the "Start" button<br>
            It will take some time before playback starts<br>
            Specify the YouTube loading interval with "Interval(ms)"
        </td>
    </tr>
</table>

</details>

---

## 🛠️ Development

### Creating Custom Nodes

You can extend CV Studio by creating custom nodes. Use the new architecture for enhanced development experience:

```python
from src.core.nodes import EnhancedNode
from src.utils.logging import get_logger
import cv2

logger = get_logger(__name__)

class MyCustomNode(EnhancedNode):
    """Example custom node with enhanced features"""
    
    node_label = 'My Custom Node'
    node_tag = 'CustomNode'
    _ver = '1.0.0'
    
    def __init__(self):
        super().__init__()
        logger.info(f"Initialized {self.node_tag}")
    
    def add_node(self, parent, node_id, pos, opencv_setting_dict=None):
        """Add node to GUI"""
        # Implement your GUI setup here
        pass
    
    def update(self, node_id, connection_list, node_image_dict, node_result_dict):
        """Process the node"""
        try:
            # Your processing logic here
            input_image = self._get_input_image(node_image_dict, connection_list)
            output_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
            
            return {"image": output_image, "json": None}
        except Exception as e:
            logger.error(f"Node processing failed: {e}", exc_info=True)
            return {"image": None, "json": None}
```

See [src/nodes/examples/example_enhanced_node.py](src/nodes/examples/example_enhanced_node.py) for a complete example.

### Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes** using the new architecture in `src/`
4. **Add tests** for new functionality
5. **Ensure tests pass** (`python -m pytest tests/`)
6. **Commit your changes** (`git commit -m 'Add amazing feature'`)
7. **Push to the branch** (`git push origin feature/amazing-feature`)
8. **Open a Pull Request**

#### Contribution Guidelines

- Use the new architecture in `src/` for new code
- Add tests for new functionality
- Update documentation as needed
- Maintain backward compatibility
- Follow existing code style and conventions

## 📋 Roadmap & ToDo

### Current Issues
- [ ] Fix RGB Histogram node graph always appearing in foreground
- [ ] Fix connection line remaining when deleting connected nodes
- [ ] Improve import feature to work after nodes are added

### Future Enhancements
- [ ] Pipeline processing system (graph-based execution)
- [ ] GUI component refactoring
- [ ] Plugin system for dynamic node loading
- [ ] Type safety with comprehensive type hints
- [ ] Auto-generated API documentation
- [ ] Performance monitoring and optimization
- [ ] Export to production-ready code

## 👥 Authors & Contributors

**Original Author:**  
Fork from Kazuhito Takahashi ([@KzhtTkhs](https://twitter.com/KzhtTkhs))

**Repository Builder :**  
[hackolite](https://github.com/hackolite)

We appreciate all contributions from the community!

## 📄 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

### Important License Notes

- The source code of CV Studio itself is under [Apache-2.0 license](LICENSE)
- Each algorithm/node implementation is subject to its own license
- Please check the LICENSE file in each node directory for specific algorithm licenses
- Third-party dependencies have their own licenses

### Image License

Sample images are sourced from:
- [Free Material Pakutaso](https://www.pakutaso.com/)
- [NHK Creative Library](https://www.nhk.or.jp/archives)

## 🙏 Acknowledgments

- Original [Image-Processing-Node-Editor](https://github.com/Kazuhito00/Image-Processing-Node-Editor) project
- [DearPyGUI](https://github.com/hoffstadt/DearPyGui) for the GUI framework
- [OpenCV](https://opencv.org/) for computer vision functionality
- [ONNX Runtime](https://onnxruntime.ai/) for ML model inference
- [MediaPipe](https://mediapipe.dev/) for ML solutions
- All contributors and users of this project

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/hackolite/CV_Studio/issues)
- **Discussions:** [GitHub Discussions](https://github.com/hackolite/CV_Studio/discussions)
- **Documentation:** See the docs in this repository

---

<div align="center">

**Made with ❤️ for the Computer Vision Community**

⭐ Star this repo if you find it useful!

</div>
