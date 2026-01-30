# Building a Windows Executable (.exe) for CV_Studio

## Overview

This guide explains how to build a standalone Windows executable (.exe) for CV_Studio that includes all nodes, particularly ONNX object detection nodes.

## 🎯 Goal

Create a `.exe` file that:
- ✅ Runs standalone (no Python installation needed)
- ✅ Includes all nodes (Input, Process, DL, Audio, etc.)
- ✅ Contains all ONNX models for object detection
- ✅ Bundles all necessary dependencies
- ✅ Can be easily distributed

## 📋 Prerequisites

### Required Software

1. **Python 3.7 or higher** (tested with Python 3.12)
2. **Git** to clone the repository
3. **Visual C++ Redistributable** (for runtime)

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# Install Python dependencies
pip install -r requirements.txt

# Install PyInstaller (build tool)
pip install pyinstaller
```

## 🚀 Quick Build

### Method 1: Automated Script (RECOMMENDED)

The easiest way is to use the automated build script:

```bash
# Standard build
python build_exe.py

# Build with cleanup
python build_exe.py --clean

# Windowed mode build (no console)
python build_exe.py --windowed

# Build with custom icon
python build_exe.py --icon CV_Studio.ico
```

The script will:
1. ✅ Check dependencies
2. ✅ Clean old builds (if --clean)
3. ✅ Configure the build
4. ✅ Compile the executable
5. ✅ Create documentation

### Method 2: Manual Build with PyInstaller

If you prefer more control:

```bash
# Use the pre-configured spec file
pyinstaller CV_Studio.spec

# Or direct build (without spec)
pyinstaller --name CV_Studio ^
            --add-data "node;node" ^
            --add-data "node_editor;node_editor" ^
            --add-data "src;src" ^
            --hidden-import dearpygui ^
            --hidden-import cv2 ^
            --hidden-import onnxruntime ^
            --collect-all mediapipe ^
            main.py
```

## 📂 Output Structure

After building, you'll get:

```
dist/CV_Studio/
├── CV_Studio.exe           # Main executable ← RUN THIS
├── README.txt              # Usage documentation
├── node/                   # All nodes
│   ├── DLNode/            # Deep Learning nodes
│   │   └── object_detection/
│   │       ├── YOLOX/model/*.onnx      # YOLOX models
│   │       ├── YOLO/model/*.onnx       # YOLO models
│   │       ├── FreeYOLO/model/*.onnx   # FreeYOLO models
│   │       └── ...
│   ├── InputNode/         # Input nodes
│   ├── ProcessNode/       # Processing nodes
│   ├── AudioProcessNode/  # Audio nodes
│   └── ...
├── node_editor/           # Node editor
│   ├── font/             # Fonts
│   └── setting/          # Configuration files
├── src/                   # Source utilities
└── _internal/            # Python runtime and dependencies
```

## 🎮 Using the Executable

### Simple Launch

```bash
# Double-click the file
CV_Studio.exe

# Or from command line
cd dist\CV_Studio
CV_Studio.exe
```

### Command Line Options

```bash
# With custom configuration file
CV_Studio.exe --setting my_config.json

# Debug mode
CV_Studio.exe --use_debug_print

# Disable async rendering
CV_Studio.exe --unuse_async_draw
```

## 🧪 Testing the Executable

### Basic Verification

1. **Launch the application**
   ```bash
   dist\CV_Studio\CV_Studio.exe
   ```

2. **Test a simple node**
   - Add an "Image" node (Input → Image)
   - Select an image
   - Add a "Result Image" node
   - Connect the two nodes

3. **Test ONNX object detection**
   - Add an "Image" or "WebCam" node
   - Add an "Object Detection" node (VisionModel → Object Detection)
   - Select a model (e.g., YOLOX nano)
   - Add a "Draw Information" node
   - Connect: Input → Object Detection → Draw Information → Result Image

### Verify ONNX Models

The following models should be present and functional:

```
node/DLNode/object_detection/
├── YOLOX/model/
│   ├── yolox_nano.onnx    ✅
│   ├── yolox_tiny.onnx    ✅
│   ├── yolox_s.onnx       ✅
│   └── yolo11_n.onnx      ✅
├── FreeYOLO/model/
│   └── freeyolo.onnx      ✅
└── TennisYOLO/model/
    └── tennis.onnx        ✅
```

## 🎨 Advanced Build Options

### Windowed Mode (no console)

For a pure GUI application without console window:

```bash
python build_exe.py --windowed
```

### Single File (onefile)

To create a single .exe file (slower startup):

```bash
python build_exe.py --onefile
```

**Note**: Onefile mode is slower to start because it must extract all files temporarily.

### Custom Icon

```bash
python build_exe.py --icon my_icon.ico
```

### Debug Build

For debugging:

```bash
python build_exe.py --debug
```

## 📦 Distribution

### Prepare for Distribution

1. **Test the executable** on your machine
2. **Compress the folder**
   ```bash
   # Create a ZIP archive
   cd dist
   tar -a -c -f CV_Studio_v1.0.zip CV_Studio
   ```

3. **Share the archive**
   - Upload to GitHub Releases
   - Share via Google Drive / Dropbox
   - Distribute directly

### What Users Need to Do

1. Download the ZIP archive
2. Extract the `CV_Studio` folder
3. Run `CV_Studio.exe`

**That's it!** No Python installation required.

### Approximate Size

- Standard build: ~800 MB - 1.5 GB
  - Python runtime: ~100 MB
  - OpenCV + dependencies: ~200 MB
  - ONNX Runtime: ~100 MB
  - ONNX models: ~100-500 MB
  - Other dependencies: ~300 MB

## 🔧 Troubleshooting

### Problem: PyInstaller not found

```bash
pip install pyinstaller
```

### Problem: Missing dependencies (ModuleNotFoundError: No module named 'cv2')

If you encounter `ModuleNotFoundError` when running `python build_exe.py`, it means the required Python packages are not installed.

**Solution 1: Let the build script install them automatically (Recommended)**

Run the build script and when prompted, select option 1:

```bash
python build_exe.py --clean

# When asked, choose option 1 to install packages automatically
Choose option (1/2/3) [1]: 1
```

**Solution 2: Install manually first**

```bash
# Install all dependencies before building
pip install -r requirements.txt

# Then run the build script
python build_exe.py --clean
```

**Solution 3: Skip package check (CI/CD environments)**

If packages are already installed but the check fails, use:

```bash
python build_exe.py --clean --skip-package-check
```

**Note**: The build requires all packages from `requirements.txt` including:
- opencv-contrib-python (cv2)
- onnxruntime-gpu
- dearpygui
- numpy
- mediapipe
- And many others...

### Problem: "module not found" error in exe

Add the missing module in `CV_Studio.spec`:

```python
hiddenimports += [
    'missing_module_name',
]
```

Then rebuild:

```bash
pyinstaller CV_Studio.spec
```

### Problem: ONNX models not found

Verify models are included in `datas` in the spec file:

```python
# In CV_Studio.spec
datas.append(('node/DLNode', 'node/DLNode'))
```

### Problem: Exe won't start

1. **Test from command line** to see errors:
   ```bash
   cd dist\CV_Studio
   CV_Studio.exe --use_debug_print
   ```

2. **Install Visual C++ Redistributable**:
   - Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - Install and restart

3. **Check permissions**:
   - Run as administrator
   - Temporarily disable antivirus

### Problem: "Failed to execute script"

Rebuild with debug mode to see details:

```bash
python build_exe.py --debug
```

### Problem: Poor performance

- Use smaller ONNX models (nano, tiny)
- Disable GPU acceleration if no compatible GPU
- Reduce processing resolution

## 🌟 Included Features

### Nodes Included in the Exe

✅ **Input Nodes**
- Image, Video, WebCam, RTSP, Screen Capture
- Int Value, Float Value

✅ **Process Nodes**
- Blur, Brightness, Contrast, Canny
- Crop, Flip, Resize, Threshold, Grayscale
- And more...

✅ **Deep Learning Nodes**
- Object Detection (YOLOX, YOLO, FreeYOLO)
- Face Detection (YuNet, MediaPipe)
- Classification, Pose Estimation
- Semantic Segmentation
- Low-Light Enhancement, Depth Estimation

✅ **Audio Nodes**
- Audio processing and model nodes
- Spectrogram, ESC50 classification

✅ **Other Nodes**
- Tracking (MOT)
- Overlay (Draw, PutText, Image Concat)
- Visual (Result Image, RGB Histogram)
- Action (Video Writer, ON/OFF Switch)

### ONNX Models Included

✅ **Object Detection**
- YOLOX (nano, tiny, small)
- YOLO11 (nano)
- FreeYOLO
- Tennis YOLO
- Lightweight Person Detector

✅ **Face Detection**
- YuNet

✅ **Classification**
- ResNet, MobileNet, EfficientNet

✅ **Others**
- Depth estimation models
- Low-light enhancement models
- Segmentation models

## 📝 Customization

### Modify the Spec File

To customize the build, edit `CV_Studio.spec`:

```python
# Add hidden imports
hiddenimports += [
    'my_module',
]

# Add data files
datas.append(('my_folder', 'my_folder'))

# Exclude unnecessary packages
excludes=[
    'package_to_exclude',
]

# Change exe name
name='MyApplication',

# Hide console
console=False,

# Add icon
icon='my_icon.ico',
```

### Optimize Size

To reduce exe size:

1. **Exclude unused packages** in the spec
2. **Remove unused ONNX models**
3. **Use UPX compression** (already enabled)
4. **Clean test/doc files**

## 🔗 Useful Links

- **PyInstaller Documentation**: https://pyinstaller.org/
- **CV_Studio GitHub**: https://github.com/hackolite/CV_Studio
- **ONNX Runtime**: https://onnxruntime.ai/
- **DearPyGUI**: https://github.com/hoffstadt/DearPyGui

## ✅ Build Checklist

- [ ] Python 3.7+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] PyInstaller installed (`pip install pyinstaller`)
- [ ] Run `python build_exe.py`
- [ ] Test `dist/CV_Studio/CV_Studio.exe`
- [ ] Verify ONNX nodes work
- [ ] Verify all nodes are present
- [ ] Create ZIP archive for distribution
- [ ] Test on a clean machine (without Python)

## 🎓 Usage Examples

### Example 1: Standard Build

```bash
cd CV_Studio
python build_exe.py --clean
```

### Example 2: Build for Distribution

```bash
# Build with custom icon and windowed mode
python build_exe.py --clean --windowed --icon logo.ico

# Test
cd dist\CV_Studio
CV_Studio.exe

# Create archive
cd dist
tar -a -c -f CV_Studio_Release_v1.0.zip CV_Studio
```

### Example 3: Debug Build

```bash
# Build with debug information
python build_exe.py --debug

# Run with debug
dist\CV_Studio\CV_Studio.exe --use_debug_print
```

## 📞 Support

For questions or issues:

1. **Check this guide** first
2. **Consult PyInstaller documentation**
3. **Open an issue** on GitHub: https://github.com/hackolite/CV_Studio/issues
4. **Check existing issues** for similar problems

---

**Happy building! 🚀**
