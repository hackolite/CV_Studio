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
onnxruntime     1.16.0 or later
dearpygui       2.0.0 or later
mediapipe       0.8.10 or later  ※ Required for MediaPipe nodes
protobuf        3.20.0 or later  ※ Required for MediaPipe nodes
filterpy        1.4.5 or later   ※ Required for MOT (Multi-Object Tracking) nodes
```

## 🚀 Installation

> **📘 Windows Users**: For detailed Windows-specific installation instructions with troubleshooting, see:
> - 🇬🇧 [INSTALLATION_WINDOWS.md](INSTALLATION_WINDOWS.md) (English)
> - 🇫🇷 [INSTALLATION_WINDOWS_FR.md](INSTALLATION_WINDOWS_FR.md) (Français)

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

#### 🎯 Option A: Automatic Build via GitHub Actions (EASIEST - NO LOCAL BUILD NEEDED)

**No Python or build tools installation required!** Simply trigger a build on GitHub:

1. **Go to the [Actions tab](../../actions)** in this repository
2. **Click on "Build Windows Executable"** in the left sidebar
3. **Click "Run workflow"** → Select branch → Click green "Run workflow" button
4. **Wait 10-15 minutes** for the build to complete
5. **Download** the `CV_Studio-Windows-Executable.zip` from the Artifacts section
6. **Extract and run** `CV_Studio.exe` - Done! 🎉

📖 **Detailed instructions:** See [COMMENT_OBTENIR_EXE.md](COMMENT_OBTENIR_EXE.md) (Français) or [HOW_TO_GET_EXE.md](HOW_TO_GET_EXE.md) (English)

#### 🎬 Option B: Automated Build Script (RECOMMENDED FOR LOCAL BUILD)

**The easiest way to build locally!** Just download and run a script that does everything automatically:

**Using Batch Script (Simple - Double-click to run):**
1. Download [`build_windows.bat`](build_windows.bat)
2. Double-click the file
3. Wait 5-15 minutes
4. Find your executable in `dist/CV_Studio/CV_Studio.exe`

**Using PowerShell (Modern):**
```powershell
# Download the script (or clone the repo to get it)
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

The script automatically:
- ✅ Clones the repository (if needed)
- ✅ Installs all Python dependencies
- ✅ Builds the .exe with PyInstaller
- ✅ Shows you where to find the result

📖 **Full guide:** See [BUILD_WINDOWS_SCRIPT.md](BUILD_WINDOWS_SCRIPT.md) for detailed instructions and troubleshooting

#### ⚡ Option C: Unified Build System (NEW - CROSS-PLATFORM)

**The modern, clean way to build CV_Studio!** Works on Windows, Linux, and macOS.

```bash
# Clone repository
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# Install dependencies
pip install -r requirements.txt

# Build executable (GPU support)
python build_unified.py --clean

# Or build for CPU-only (no CUDA required)
python build_unified.py --clean --cpu
```

**Features:**
- ✅ Cross-platform (Windows/Linux/macOS)
- ✅ Clean, colored output
- ✅ CPU/GPU build modes
- ✅ Comprehensive error handling
- ✅ Single command builds
- ✅ CI/CD friendly

**Quick Reference:**
- 📖 [BUILD_QUICKREF.md](BUILD_QUICKREF.md) - One-page cheat sheet
- 📚 [BUILD_GUIDE.md](BUILD_GUIDE.md) - Comprehensive guide

#### 🔧 Option D: Manual Build on Your Windows Machine (Legacy)

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
```

The build process will:
1. ✅ Verify all dependencies are installed
2. ✅ Clean previous build artifacts (if --clean flag used)
3. ✅ Package all Python dependencies
4. ✅ Include all nodes (Input, Process, DL, Audio, etc.)
5. ✅ Bundle all ONNX models for object detection
6. ✅ Create the standalone executable

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

To share your executable:

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

# Combine options
python build_exe.py --clean --windowed --icon your_icon.ico
```

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

#### 3. Zoom and Navigate
Use the **mouse wheel** to zoom in and out of the node editor canvas (range: 10% to 500%). The current zoom level is displayed in the menu bar. Use the **View menu** for precise zoom controls.

<details>
<summary>🔍 Zoom Controls</summary>

- **Mouse Wheel Up/Down**: Zoom in/out by 10% per scroll
- **View → Zoom In**: Zoom in by 10%
- **View → Zoom Out**: Zoom out by 10%
- **View → Reset Zoom**: Return to 100%
- **Zoom Range**: 0.1x (10%) to 5.0x (500%)

For more details, see [Node Editor Zoom Controls](docs/NODE_EDITOR_ZOOM_CONTROLS.md).

</details>

#### 4. Delete a Node
Select the node and press the **Delete** key.

<img src="https://user-images.githubusercontent.com/37477845/172030418-201d7df5-1984-4fa7-8e47-9264c5dcb6cf.gif" loading="lazy" width="60%">

#### 5. Export Your Graph
Save your processing pipeline as a JSON file via the **Export** menu option.

<img src="https://user-images.githubusercontent.com/37477845/172030429-9c6c453c-b8b0-4ccf-b36e-eb666c2d919f.gif" loading="lazy" width="60%">

#### 6. Import a Graph
Load a previously saved processing pipeline from a JSON file.

<img src="https://user-images.githubusercontent.com/37477845/172030433-8a07b702-9ba4-43e7-9f2f-f0885f472c44.gif" loading="lazy" width="60%">

### Workflow Examples

Here are some practical examples to help you get started with common computer vision tasks:

#### Standalone Examples

For complete, runnable code examples including DearPyGui usage patterns, see the **[examples/](examples/)** directory:

- **[dearpygui_node_editor_colored_combo_example.py](examples/dearpygui_node_editor_colored_combo_example.py)** - Demonstrates node editor with themed combo boxes, domain-based coloring, and dynamic UI updates

See **[examples/README.md](examples/README.md)** for detailed documentation on each example.

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

- **[src/README.md](src/README.md)** - Technical architecture documentation
- **[Timestamped Queue System](TIMESTAMPED_QUEUE_SYSTEM.md)** - FIFO queue documentation 🆕

## 🧪 Testing

CV Studio includes comprehensive test coverage with 150+ test files and pytest configuration.

### Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suite
python -m pytest tests/test_utils/ -v
python -m pytest tests/test_core/ -v

# Run queue system tests
python -m pytest tests/test_timestamped_queue.py tests/test_queue_adapter.py tests/test_queue_integration.py -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov=node --cov-report=html
```

### Test Coverage

**Core Architecture Tests:**
- ✅ Base node class (14 tests) 🆕
- ✅ Enhanced node class (22 tests) 🆕
- ✅ DPG node ABC (16 tests) 🆕
- ✅ Node factory (7 tests)
- ✅ Settings management (10 tests)

**Utilities Tests:**
- ✅ Exception hierarchy (7 tests)
- ✅ Logging utilities (6 tests)
- ✅ Resource management (8 tests)
- ✅ GPU utilities (7 tests)

**Queue System Tests:**
- ✅ **Timestamped queue system (35 tests)**
  - Core queue functionality (17 tests)
  - Backward compatibility adapter (12 tests)
  - Integration with node system (6 tests)

**Node Integration Tests:**
- ✅ 150+ integration tests for various node implementations
- ✅ Video processing nodes
- ✅ Audio processing nodes
- ✅ Object detection and tracking nodes
- ✅ And many more...

## 📚 Available Nodes

CV Studio ships with **100+ nodes** across 17 categories. Use the table below for a quick overview, then expand each section for details.

### 🗺️ Node Categories Overview

| Category | Emoji | Nodes | Description |
|----------|-------|-------|-------------|
| [Input](#-input-nodes) | 📥 | Image, Video, Webcam, RTSP, HLS, WebRTC, Microphone, API, MQTT, Websocket, Weather, YouTube… | All video/image/data sources |
| [Process](#-process-nodes) | ⚙️ | Blur, Canny, Resize, Crop, CLAHE, Morphology, Color Space… | Classic image processing filters |
| [Deep Learning](#-deep-learning-nodes) | 🤖 | Object Detection, Pose Estimation, Segmentation, Online Training… | ONNX/MediaPipe AI inference |
| [Audio Model](#-audio-model-node) | 🎵 | AudioClassification | Audio classification with YAMNet or custom ONNX |
| [Audio Process](#-audio-process-nodes) | 🔊 | Spectrogram, Equalizer, BandPass, Compressor, Decibel… | Real-time audio signal processing |
| [NLP Model](#-nlp-model-node) | 💬 | TinyBert Vigilance | NLP-based vigilance scoring from text |
| [Map](#-map-node) | 🛰️ | CopernicusMap | Live Sentinel-2 satellite imagery (NDVI, true color…) |
| [Tracker](#-tracker-nodes) | 🎯 | MOT, ReId | Multi-object tracking and re-identification |
| [Stats](#-stats-nodes) | 📊 | IoU, Homography, DistanceTracker, Histogram, BAR, Operator… | Metrics and statistical analysis |
| [Visual](#-visual-nodes) | 🖼️ | HeatMap, Chart, Map, TennisCourt, VigilanceGauge, WordCloud… | Rich data visualisations |
| [Overlay](#-overlay-nodes) | ✏️ | DrawInformation, Overlay, OverlayImage, PutText | Drawing and blending overlays |
| [Video](#-video-nodes) | 🎬 | VideoConcat, VideoWriter, DynamicPlay, ScreenCapture | Video composition and recording |
| [Trigger](#-trigger-nodes) | ⚡ | Count, ObjDetCount, DbDetCount, OnOffSwitch, BooleanInverter… | Event detection and routing logic |
| [Action](#-action-nodes) | 🔔 | Buzzer, VideoRecorder, CamControl (PTZ), Mongodb, VLM | Outputs and external integrations |
| [System](#-system-nodes) | 🔧 | Settings, Deploy, Scan, SyncQueue, SystemResource, Sizing | Pipeline configuration and monitoring |
| [Router](#-router-node) | 🔀 | SimpleRouter | Conditional image routing |
| [Timeseries](#-timeseries-node) | 📈 | PositionPrediction | Kalman-filter trajectory prediction |

---

## 📥 Input Nodes

<details>
<summary>🖼️ Image &amp; Video sources</summary>

<table>
    <tr>
        <td width="200"><strong>Image</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031017-fd0107a5-2a33-4e47-a18b-ea53213f65e1.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Reads still images (bmp, jpg, png, gif) and outputs them as image frames.<br>
            Open the file dialog with the <em>Select Image</em> button.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Video</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031118-9382a9f6-d45c-4d39-ae82-59575a109664.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Reads a video file (mp4, avi) and outputs one image per frame.<br>
            Check <em>Loop</em> to repeat the video. <em>Skip rate</em> controls frame decimation.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Webcam</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031202-2ec0e976-12c7-41a9-94e4-ef162302f0b1.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Reads a webcam and outputs an image for each frame.<br>
            Specify the camera with the <em>Device No</em> drop-down.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>RTSP</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/178135453-293836c2-e38d-476f-9b64-ea654470ba2e.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Reads an RTSP stream from a network/IP camera and outputs frames.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>HLS</strong></td>
        <td width="320">🎞️ HLS Stream</td>
        <td width="760">
            Reads an HLS (HTTP Live Streaming) URL and outputs video frames in real time.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>WebRTC</strong></td>
        <td width="320">📡 WebRTC</td>
        <td width="760">
            Receives a live WebRTC video stream and outputs frames for downstream processing.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Screen Capture</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/216200610-5a5714c0-99ac-4ec9-a56e-90ae99088815.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Captures the desktop full-screen and outputs it as a continuous image stream.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>YouTube</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/179450682-f7cc8237-e9d8-4c0f-b5d8-d2caac453f04.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Reads a YouTube video URL and outputs frames.<br>
            Enter the URL and press <em>Start</em>. Configure loading interval with <em>Interval(ms)</em>.
        </td>
    </tr>
</table>
</details>

<details>
<summary>🔌 Data &amp; IoT sources</summary>

<table>
    <tr>
        <td width="200"><strong>Microphone</strong></td>
        <td width="320">🎤 Audio Input</td>
        <td width="760">
            Captures real-time audio from a microphone and outputs audio data chunks.<br>
            Select device from dropdown; configure sample rate (8–48 kHz) and chunk duration (0.1–5 s).<br>
            Outputs audio compatible with Spectrogram and all AudioProcess nodes.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>API</strong></td>
        <td width="320">🌐 REST API</td>
        <td width="760">
            Polls a REST API endpoint and outputs the response as JSON data.<br>
            Configure URL, method, headers, and polling interval.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>MQTT</strong></td>
        <td width="320">📨 MQTT</td>
        <td width="760">
            Subscribes to an MQTT broker topic and outputs incoming messages as JSON.<br>
            Configure broker host, port, topic, and credentials.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Websocket</strong></td>
        <td width="320">🔗 WebSocket</td>
        <td width="760">
            Connects to a WebSocket server and outputs received messages as JSON data in real time.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Weather</strong></td>
        <td width="320">🌡️ Weather / Temperature</td>
        <td width="760">
            Fetches live weather/temperature data from an external API and outputs it as JSON.<br>
            Useful for environment-aware pipelines (e.g. combine with trigger logic).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>JsonBoolean</strong></td>
        <td width="320">✅ JSON Boolean</td>
        <td width="760">
            Outputs a configurable boolean value as a JSON signal.<br>
            Toggle on/off in the node UI to gate downstream trigger nodes.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>CoordinateExamples</strong></td>
        <td width="320">📍 Coordinate Examples</td>
        <td width="760">
            Outputs example GPS/coordinate data as JSON for testing map and spatial nodes.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Int Value</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031284-95255053-6eaf-4298-a392-062129e698f6.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Outputs a user-defined integer value (slider or input field).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Float Value</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031323-98ae0273-7083-48d0-9ef2-f02af7fde482.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Outputs a user-defined float value.
        </td>
    </tr>
</table>
</details>

---

## ⚙️ Process Nodes

<details>
<summary>Classic image processing filters (25 nodes)</summary>

<table>
    <tr>
        <td width="200"><strong>ApplyColorMap</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031657-81e70c61-05a3-4bff-9423-67ac9e486f5c.png" loading="lazy" width="300px">
        </td>
        <td width="760">Applies a pseudo-color map to a grayscale or depth image.</td>
    </tr>
    <tr>
        <td width="200"><strong>Blur</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031667-399472c9-7731-4cc2-8258-6879a1836b66.png" loading="lazy" width="300px">
        </td>
        <td width="760">Smoothing filter (average, Gaussian, median). Kernel size is adjustable.</td>
    </tr>
    <tr>
        <td width="200"><strong>Bilateral Filter</strong></td>
        <td width="320">🔲 Edge-preserving blur</td>
        <td width="760">
            Applies a bilateral filter that smooths textures while preserving sharp edges.<br>
            Configure diameter, sigmaColor, and sigmaSpace.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Brightness</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172031761-9ab8d83d-9bac-4854-9a6d-44c34692a002.png" loading="lazy" width="300px">
        </td>
        <td width="760">Adjusts image brightness with the <em>alpha</em> slider.</td>
    </tr>
    <tr>
        <td width="200"><strong>Canny</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172032723-df30d0bb-ed24-4909-afee-c3a78f66dad9.png" loading="lazy" width="300px">
        </td>
        <td width="760">Canny edge detection. Set min/max thresholds with sliders.</td>
    </tr>
    <tr>
        <td width="200"><strong>CLAHE</strong></td>
        <td width="320">📊 Adaptive histogram equalization</td>
        <td width="760">
            Contrast Limited Adaptive Histogram Equalization — enhances local contrast.<br>
            Adjust clip limit and tile grid size.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Color Space</strong></td>
        <td width="320">🎨 Color Space conversion</td>
        <td width="760">
            Converts the input image between color spaces (BGR↔HSV, BGR↔LAB, BGR↔YCrCb, etc.).<br>
            Select the target color space from the dropdown.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Contrast</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042432-dab55644-f95f-4854-bcc4-45bb54d9c5bd.png" loading="lazy" width="300px">
        </td>
        <td width="760">Adjusts image contrast with the <em>beta</em> slider.</td>
    </tr>
    <tr>
        <td width="200"><strong>Crop</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042627-1c90f1ca-2d57-45b4-8dbe-ce0e4917d08e.png" loading="lazy" width="300px">
        </td>
        <td width="760">Crops a region from the image using (x1,y1)–(x2,y2) sliders.</td>
    </tr>
    <tr>
        <td width="200"><strong>EqualizeHist</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042718-4f14021f-c29e-4886-b44f-46af644a74fe.png" loading="lazy" width="300px">
        </td>
        <td width="760">Global histogram equalization on the brightness channel.</td>
    </tr>
    <tr>
        <td width="200"><strong>Flip</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042828-62d5ba24-69f9-4d6b-b3f9-322f43af0284.png" loading="lazy" width="300px">
        </td>
        <td width="760">Horizontal / vertical / both flip of the input image.</td>
    </tr>
    <tr>
        <td width="200"><strong>Gamma Correction</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042880-7804d210-72f7-4977-ac11-41f9e7883a65.png" loading="lazy" width="300px">
        </td>
        <td width="760">Applies gamma correction. Gamma value is adjustable with a slider.</td>
    </tr>
    <tr>
        <td width="200"><strong>Grayscale</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042929-1501d980-b00b-42f7-bbb3-a078d95be5ff.png" loading="lazy" width="300px">
        </td>
        <td width="760">Converts the input image to grayscale.</td>
    </tr>
    <tr>
        <td width="200"><strong>Illumination Correct</strong></td>
        <td width="320">💡 Illumination correction</td>
        <td width="760">
            Corrects uneven illumination using background subtraction or homomorphic filtering.<br>
            Useful for normalizing lighting across frames.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Image Alpha Blend</strong></td>
        <td width="320">🔀 Alpha blend</td>
        <td width="760">
            Blends two input images together with a configurable alpha weight (0–1).<br>
            Connects two image inputs; outputs <code>α·A + (1−α)·B</code>.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Kernel Sharpen</strong></td>
        <td width="320">🔪 Sharpening</td>
        <td width="760">
            Applies a configurable sharpening convolution kernel to the input image.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Morphology</strong></td>
        <td width="320">🔲 Morphological ops</td>
        <td width="760">
            Applies morphological operations (erode, dilate, open, close, gradient, top-hat, black-hat).<br>
            Configure operation type, kernel shape, and kernel size.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>NLM Denoise</strong></td>
        <td width="320">🌀 Non-local means</td>
        <td width="760">
            Non-Local Means denoising for high-quality noise removal.<br>
            Adjust <em>h</em> (filter strength) and template/search window sizes.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Omnidirectional Viewer</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/182130848-fff3d053-6c21-4a03-9e96-371111112226.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Transforms a 360° equirectangular image using roll/pitch/yaw sliders.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Resize</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/210739536-5f70e55a-3433-4325-81e2-79619943bd9f.png" loading="lazy" width="300px">
        </td>
        <td width="760">Resizes the image to the specified width, height and interpolation method.</td>
    </tr>
    <tr>
        <td width="200"><strong>Simple Filter</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/178098739-ee15159c-d66f-4b5d-822d-dbaf686448d6.png" loading="lazy" width="300px">
        </td>
        <td width="760">Applies a 3×3 2D convolution filter (preset kernels: identity, edge, emboss…).</td>
    </tr>
    <tr>
        <td width="200"><strong>Adaptive Threshold</strong></td>
        <td width="320">🌓 Adaptive binarization</td>
        <td width="760">
            Binarizes the image using a locally-adaptive threshold (mean or Gaussian neighbourhood).<br>
            Configure block size and constant C.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Threshold</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172042985-3e7908cc-f485-4684-884c-8cfe3d020004.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Binarizes with a global threshold. Supports THRESH_BINARY, THRESH_OTSU (auto), THRESH_TRIANGLE…
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Unsharp Mask</strong></td>
        <td width="320">🔭 Unsharp mask</td>
        <td width="760">
            Sharpens the image using the unsharp masking technique.<br>
            Adjust blur radius and amount slider.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Zoom</strong></td>
        <td width="320">🔍 Digital zoom</td>
        <td width="760">
            Digitally zooms into the centre of the image by a configurable factor and crops to original size.
        </td>
    </tr>
</table>
</details>

---

## 🤖 Deep Learning Nodes

<details>
<summary>AI/ML inference nodes (ONNX, MediaPipe)</summary>

You can select the model from the drop-down list and toggle CPU / GPU inference.<br>
See each node's directory under <code>node/DLNode/</code> for model licences.

<table>
    <tr>
        <td width="200"><strong>Classification</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172043243-2c037f0b-e1ba-4e3b-96a8-b0e3358f6616.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Image classification via ONNX model. When an Object Detection node is connected upstream,
            classifies each detected bounding box individually.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Face Detection</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045704-23c00432-90b1-4a53-b621-6413ba8f18dd.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Detects faces in the input image. Outputs raw image + detection JSON.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Low-Light Image Enhancement</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045825-8ad902e0-d11d-44b7-8390-bb3e7ab12622.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Enhances dark / low-light images using a deep learning model. Output is the enhanced image.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Monocular Depth Estimation</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045864-8e249b46-d5bf-4d48-b540-2e5102afbe21.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Estimates depth from a single RGB image. Output is a grayscale depth map.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Object Detection</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172044154-1ef0a081-0e1e-4e3f-8d0d-599b73ee895d.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Real-time object detection (YOLOX, YOLO, NanoDet, FreeYOLO, custom ONNX…).<br>
            ONNX upload with automatic class-name picker (COCO vs generic).<br>
            Collapsible settings panel (provider, score threshold, draw bbox, line thickness).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Online Training</strong></td>
        <td width="320">🧠 Distillation / fine-tuning</td>
        <td width="760">
            Continuously fine-tunes a student ONNX model in real time using teacher detections as supervision.<br>
            Supports backprop via <em>onnx2torch</em> (head or full backbone) with distillation losses
            (Hungarian matching, IoU+CE/KL, cardinality, FP/FN).<br>
            Falls back to a lightweight affine-head correction when PyTorch is unavailable.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Pose Estimation</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045920-cf18889d-d2f8-43ba-b3a5-773fd8df7eec.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Human pose estimation (skeleton keypoints) on the input image. Outputs raw image + JSON.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Semantic Segmentation</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172045965-6d77f4ef-d208-40c9-a335-25a9d1d07acc.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Per-pixel semantic segmentation on the input image. Output is a coloured segmentation mask.
        </td>
    </tr>
</table>
</details>

---

## 🎵 Audio Model Node

<details>
<summary>Audio classification with deep learning</summary>

<table>
    <tr>
        <td width="200"><strong>AudioClassification</strong></td>
        <td width="320">🔊 Audio classifier</td>
        <td width="760">
            Classifies audio chunks using a deep learning model (built-in YAMNet at 16 kHz, or custom ONNX).<br>
            Accepts audio from a Microphone or other audio source node.<br>
            Produces a spectrogram image output and a classification JSON alongside an audio passthrough,
            enabling the chain: <code>VideoNode → AudioClassification → ImageConcat</code> for frame-aligned sync.<br>
            Automatic resampling to model target sample rate via librosa.
        </td>
    </tr>
</table>
</details>

---

## 🔊 Audio Process Nodes

<details>
<summary>Real-time audio signal processing (8 nodes)</summary>

<table>
    <tr>
        <td width="200"><strong>Spectrogram</strong></td>
        <td width="320">📊 Mel spectrogram</td>
        <td width="760">
            Converts an audio chunk to a mel spectrogram image.<br>
            Configure n_mels, hop length, FFT size, and color map.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>BandPass Filter</strong></td>
        <td width="320">🎚️ Band-pass</td>
        <td width="760">
            Applies a band-pass filter to the audio stream. Set low-cut and high-cut frequencies.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Compressor</strong></td>
        <td width="320">📉 Dynamic compressor</td>
        <td width="760">
            Dynamic range compressor. Configure threshold (dB), ratio, attack, and release.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Decibel</strong></td>
        <td width="320">🔢 dB meter</td>
        <td width="760">
            Computes the RMS level in dB of the incoming audio chunk and outputs it as a numeric value.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Equalizer</strong></td>
        <td width="320">🎛️ Parametric EQ</td>
        <td width="760">
            Multi-band parametric equalizer. Adjust gain per frequency band to shape the audio spectrum.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Noise Gate</strong></td>
        <td width="320">🚪 Noise gate</td>
        <td width="760">
            Silences the signal when its level falls below a configurable threshold (gate open/close).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Normalize</strong></td>
        <td width="320">📐 Normalizer</td>
        <td width="760">
            Normalizes the amplitude of an audio chunk to a target peak level.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Resample</strong></td>
        <td width="320">🔄 Resampler</td>
        <td width="760">
            Resamples the audio stream from its source sample rate to a target sample rate using librosa.
        </td>
    </tr>
</table>
</details>

---

## 💬 NLP Model Node

<details>
<summary>Natural language processing</summary>

<table>
    <tr>
        <td width="200"><strong>TinyBert Vigilance</strong></td>
        <td width="320">🧠 NLP vigilance scorer</td>
        <td width="760">
            Encodes an input text sentence with TinyBERT and compares it against a pre-built CSV vigilance database
            using nearest-neighbour search.<br>
            Outputs a vigilance score (0–1) as JSON, consumed by the <em>Vigilance Gauge</em> visual node.<br>
            Both the model and the vector database are cached in memory after the first load.
        </td>
    </tr>
</table>
</details>

---

## 🛰️ Map Node

<details>
<summary>Satellite imagery via Copernicus</summary>

<table>
    <tr>
        <td width="200"><strong>CopernicusMap</strong></td>
        <td width="320">🗺️ Sentinel-2 / S1 map</td>
        <td width="760">
            Fetches live Sentinel-2 (or Sentinel-1) satellite imagery from the Copernicus Data Space Ecosystem.<br>
            <strong>Features:</strong>
            <ul>
                <li>Dynamic band slots (add / remove) — same UI pattern as VideoConcat</li>
                <li>Band-formula field: e.g. <code>(B08 - B04) / (B08 + B04)</code> for NDVI</li>
                <li>Smart 1 km×1 km tile cache in <code>~/.cv_studio/copernicus_tiles/</code></li>
                <li>Background 3×3 neighbourhood pre-fetch on first GPS fix</li>
                <li>Colormap rendering with per-formula defaults (NDVI → RdYlGn, etc.)</li>
                <li><strong>Visible spectrum only</strong> checkbox: restricts bands to B02/B03/B04</li>
                <li><strong>True color (naked eye)</strong> checkbox: renders natural-color RGB (2.5×B04/B03/B02)</li>
                <li>Continuous GPS overlay with position marker and trace</li>
            </ul>
            Credentials are stored by the <em>Settings</em> system node.
        </td>
    </tr>
</table>
</details>

---

## 🎯 Tracker Nodes

<details>
<summary>Multi-object tracking and re-identification</summary>

<table>
    <tr>
        <td width="200"><strong>MOT</strong> (Multi-Object Tracking)</td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172049681-67df2cc3-3db3-4766-a96e-f7c557e4a5b9.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Takes Object Detection output and assigns persistent track IDs across frames.<br>
            Supports 6 algorithms: <strong>motpy</strong>, <strong>ByteTrack</strong>, <strong>Norfair</strong>,
            <strong>IOU Tracker</strong>, <strong>SORT</strong>, and <strong>CenterTrack</strong>.<br>
            See <a href="node/TrackerNode/mot/README.md">TrackerNode/mot/README.md</a> for details.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>ReId</strong> (Re-Identification)</td>
        <td width="320">🪪 Person Re-ID</td>
        <td width="760">
            Person / object re-identification using appearance embeddings.<br>
            Associates detections across disjoint camera views or time gaps using feature similarity.
        </td>
    </tr>
</table>
</details>

---

## 📊 Stats Nodes

<details>
<summary>Metrics, analytics, and data processing (7 nodes)</summary>

<table>
    <tr>
        <td width="200"><strong>IoU</strong></td>
        <td width="320">📐 Intersection over Union</td>
        <td width="760">
            Computes IoU between bounding boxes from two Object Detection inputs.<br>
            Uses Hungarian matching (DETR cost = 1−IoU + class cost) for set-based distillation loss output
            (box L1+IoU, class CE/KL, cardinality, FP/FN, class-mismatch + detection_score).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Homography</strong></td>
        <td width="320">📌 Court homography</td>
        <td width="760">
            Computes a homography transform mapping detected keypoints to a reference court/field template
            (sport templates selectable from dropdown).<br>
            Tracks player kinematics over a 60-frame sliding window.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>DistanceTracker</strong></td>
        <td width="320">📏 Distance tracker</td>
        <td width="760">
            Tracks the cumulative distance travelled by detected objects over time.<br>
            Outputs per-track distance metrics as JSON.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Histogram</strong></td>
        <td width="320">📊 Data histogram</td>
        <td width="760">
            Computes and plots a histogram of numeric values received over a sliding window.<br>
            Configurable number of bins and display range.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>BAR</strong></td>
        <td width="320">📊 Bar chart node</td>
        <td width="760">
            Renders a live bar chart from numeric or classification data, updating every frame.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>CourtKeypointData</strong></td>
        <td width="320">🏟️ Court keypoint data</td>
        <td width="760">
            Processes and formats keypoint JSON from Pose Estimation for court-specific analytics
            (downstream of Homography).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Operator</strong></td>
        <td width="320">➕ Math operator</td>
        <td width="760">
            Applies a binary arithmetic operation (+, −, ×, ÷, min, max, abs diff) to two numeric inputs.
        </td>
    </tr>
</table>
</details>

---

## 🖼️ Visual Nodes

<details>
<summary>Rich data visualisations (7 nodes)</summary>

<table>
    <tr>
        <td width="200"><strong>Chart</strong></td>
        <td width="320">📈 Detection chart</td>
        <td width="760">
            Plots detection scores over time as a live line chart.<br>
            Accepts Object Detection / OnlineTraining distillation_losses as input.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>HeatMap</strong></td>
        <td width="320">🌡️ Pixel heatmap</td>
        <td width="760">
            Accumulates pixel-level activity (motion, detections) into a heatmap overlay rendered on the source image.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>ObjHeatMap</strong></td>
        <td width="320">🟥 Object heatmap</td>
        <td width="760">
            Projects bounding-box centroids onto a persistent heatmap to show where objects appear most frequently.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Map</strong></td>
        <td width="320">🗺️ GPS map</td>
        <td width="760">
            Displays a GPS track on a map background. Renders position marker, heading, and historical trace.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>TennisCourt</strong></td>
        <td width="320">🎾 Tennis court view</td>
        <td width="760">
            Renders player positions on a top-down tennis court diagram using homography-projected coordinates.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Vigilance Gauge</strong></td>
        <td width="320">🔔 Gauge display</td>
        <td width="760">
            Displays the vigilance score from the <em>TinyBert Vigilance</em> node as an animated gauge widget.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Word Cloud</strong></td>
        <td width="320">☁️ Word cloud</td>
        <td width="760">
            Renders a word cloud image from text output produced by the <em>VLM</em> action node or any JSON text field.
        </td>
    </tr>
</table>
</details>

---

## ✏️ Overlay Nodes

<details>
<summary>Drawing and blending overlays</summary>

<table>
    <tr>
        <td width="200"><strong>Draw Information</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046789-0d43ca22-b202-404a-ba01-dd80a01d01e5.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Draws detection results (bounding boxes, labels, keypoints, masks) from upstream DL nodes onto the image.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Overlay</strong></td>
        <td width="320">🔀 Image overlay</td>
        <td width="760">
            Blends a secondary image (or shape mask) over the primary input image at a configurable opacity and position.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>OverlayImage</strong></td>
        <td width="320">🖼️ Static overlay</td>
        <td width="760">
            Composites a static image asset (PNG with alpha) onto the input frame at a specified position and scale.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>PutText</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046942-7d004807-348d-4576-bac5-f4da27f0e5ed.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Draws custom text on the image. Supports color selection and optional processing-time display.
        </td>
    </tr>
</table>
</details>

---

## 🎬 Video Nodes

<details>
<summary>Video composition and recording</summary>

<table>
    <tr>
        <td width="200"><strong>VideoConcat</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172046873-1bb27261-160a-452e-b454-05d249ec1aca.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Concatenates multiple image/video streams side by side.<br>
            Add image or audio slots dynamically with <em>Add Slot</em>.<br>
            Forwards audio from explicit AUDIO slots or falls back to IMAGE source audio automatically.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>VideoWriter</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047578-7ee450ff-0816-4006-814f-55f854ca921a.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Writes the input video stream to a file (mp4/avi).<br>
            Uses a SyncVideoWriter for frame-ordered recording with audio support (A/V sync via PyAV encoder).
        </td>
    </tr>
    <tr>
        <td width="200"><strong>DynamicPlay</strong></td>
        <td width="320">▶️ Dynamic player</td>
        <td width="760">
            Plays back a video file at a controllable speed, with seek and frame-step controls available at runtime.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Screen Capture</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/216200610-5a5714c0-99ac-4ec9-a56e-90ae99088815.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Captures and outputs the desktop full screen as a live image stream.
        </td>
    </tr>
</table>
</details>

---

## ⚡ Trigger Nodes

<details>
<summary>Event detection and conditional routing</summary>

<table>
    <tr>
        <td width="200"><strong>Count</strong></td>
        <td width="320">🔢 Frame counter</td>
        <td width="760">
            Counts incoming frames and fires a trigger event every N frames.<br>
            Configurable count threshold and reset behaviour.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>ObjDetCount</strong></td>
        <td width="320">👁️ Detection counter</td>
        <td width="760">
            Fires a trigger when the number of detections from an Object Detection node crosses a threshold.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>DbDetCount</strong></td>
        <td width="320">🗄️ DB detection counter</td>
        <td width="760">
            Same as ObjDetCount but counts detections retrieved from a database record.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>ON/OFF Switch</strong></td>
        <td width="320">
            <img src="https://user-images.githubusercontent.com/37477845/172047545-e0887c75-16d0-450e-8cc2-50f4065173e0.png" loading="lazy" width="300px">
        </td>
        <td width="760">
            Passes or blocks the input image stream. Toggle with the UI button or a JSON boolean input.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>BooleanInverter</strong></td>
        <td width="320">🔄 NOT gate</td>
        <td width="760">
            Inverts a boolean JSON value (<code>true → false</code> and vice versa). Used to negate trigger conditions.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>CourtKeypointDeviation</strong></td>
        <td width="320">📐 Keypoint deviation trigger</td>
        <td width="760">
            Fires a trigger when a player's court keypoint position deviates beyond a configurable threshold.
        </td>
    </tr>
</table>
</details>

---

## 🔔 Action Nodes

<details>
<summary>Outputs and external integrations</summary>

<table>
    <tr>
        <td width="200"><strong>Buzzer</strong></td>
        <td width="320">🔔 Audio alarm</td>
        <td width="760">
            Plays a configurable beep / alarm sound via <em>sounddevice</em> when triggered by a JSON boolean input.<br>
            Thread-safe playback lock prevents simultaneous calls from multiple instances.<br>
            Crash-dump logging to <code>node/ActionNode/logs/</code>.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>VideoRecorder</strong></td>
        <td width="320">🎥 Triggered recorder</td>
        <td width="760">
            Records video to disk only while a JSON trigger is active (e.g. from ObjDetCount).<br>
            Configurable output path, codec, and FPS.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>CamControl</strong> (PTZ)</td>
        <td width="320">📷 PTZ camera control</td>
        <td width="760">
            Controls a PTZ (Pan-Tilt-Zoom) camera via the ONVIF protocol.<br>
            Accepts a JSON input with <code>url_ptz</code>, username, and password.<br>
            Provides directional and zoom buttons (up/down/left/right/zoom-in/zoom-out/home/stop).<br>
            Commands are sent in a background thread to keep the GUI responsive.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Mongodb</strong></td>
        <td width="320">🗄️ MongoDB writer</td>
        <td width="760">
            Inserts detection or analytics results as JSON documents into a MongoDB collection.<br>
            Configure connection URI, database, and collection name in the node UI.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>VLM</strong> (Vision Language Model)</td>
        <td width="320">🤖 VLM captioner</td>
        <td width="760">
            Sends the current image frame to an external VLM HTTP server (Ollama-compatible) and outputs the
            generated text caption as JSON.<br>
            Runs in a subprocess to avoid blocking the GUI. Configurable server URL, model, and caption prompt.
        </td>
    </tr>
</table>
</details>

---

## 🔧 System Nodes

<details>
<summary>Pipeline configuration and monitoring</summary>

<table>
    <tr>
        <td width="200"><strong>Settings</strong></td>
        <td width="320">⚙️ Global settings</td>
        <td width="760">
            Central configuration node: sets resolution, GPU flag, API credentials (Copernicus, etc.),
            and writes them to <code>~/.cv_studio/</code> config files for other nodes to read.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Deploy</strong></td>
        <td width="320">🚀 Pipeline deploy</td>
        <td width="760">
            Exports the current node graph to a deployable configuration and optionally starts it
            as a background service.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Scan</strong></td>
        <td width="320">🔍 Network / device scan</td>
        <td width="760">
            Scans the local network or system for available devices (cameras, ONVIF PTZ cameras, etc.)
            and outputs the discovered list as JSON.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>SyncQueue</strong></td>
        <td width="320">⏱️ Sync queue</td>
        <td width="760">
            Inserts a timestamped FIFO buffer between nodes to synchronise data streams with different
            processing speeds or latencies.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>SystemResource</strong></td>
        <td width="320">📈 Resource monitor</td>
        <td width="760">
            Displays real-time CPU, RAM, and GPU utilisation. Outputs metrics as JSON for downstream monitoring.
        </td>
    </tr>
    <tr>
        <td width="200"><strong>Sizing</strong></td>
        <td width="320">📐 Sizing helper</td>
        <td width="760">
            Reports the resolution (width × height) of the connected image stream as a JSON value,
            useful for dynamic resize or crop configuration.
        </td>
    </tr>
</table>
</details>

---

## 🔀 Router Node

<details>
<summary>Conditional image routing</summary>

<table>
    <tr>
        <td width="200"><strong>SimpleRouter</strong></td>
        <td width="320">🔀 Simple router</td>
        <td width="760">
            Routes the input image to one of two output paths based on a JSON boolean condition.<br>
            Enables branching pipelines — e.g. send detections down one path and clean frames down another.
        </td>
    </tr>
</table>
</details>

---

## 📈 Timeseries Node

<details>
<summary>Temporal analytics and prediction</summary>

<table>
    <tr>
        <td width="200"><strong>PositionPrediction</strong></td>
        <td width="320">🎯 Kalman predictor</td>
        <td width="760">
            Predicts the future position of a tracked object using a Kalman filter.<br>
            Accepts bounding-box or keypoint JSON from detection / tracking nodes and outputs
            a predicted position N frames ahead.
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
