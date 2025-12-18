# Complete Guide to Building CV Studio Executable

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installing Dependencies](#installing-dependencies)
4. [Building the Executable](#building-the-executable)
5. [Creating Windows Installer](#creating-windows-installer)
6. [Distribution](#distribution)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## 🎯 Overview

This guide explains how to create a standalone Windows executable (.exe) and installer for CV Studio. The executable includes:

- ✅ **Complete Python runtime** - No Python installation required
- ✅ **All dependencies** - OpenCV, DearPyGUI, ONNX Runtime, etc.
- ✅ **ONNX models** - All object detection models (YOLOX, YOLO, etc.)
- ✅ **All nodes** - Input, Process, DL, Audio, etc.
- ✅ **GPU acceleration** - ONNX Runtime GPU support (CUDA)

**Final size:** Approximately 800 MB - 1.5 GB

---

## 🔧 Prerequisites

### Operating System

- **Windows 10/11** (64-bit) - Required for building Windows executable
- **Windows 7 SP1** or higher - Minimum version to run the application

### Required Software

#### 1. Python

**Recommended version:** Python 3.8 to 3.12

**Installation:**

```bash
# Download from python.org
https://www.python.org/downloads/

# During installation:
# ☑ Check "Add Python to PATH"
# ☑ Check "Install pip"
```

**Verification:**

```bash
python --version
# Should display: Python 3.x.x

pip --version
# Should display: pip x.x.x
```

#### 2. Git (optional but recommended)

```bash
# Download from:
https://git-scm.com/download/win

# Or use GitHub Desktop:
https://desktop.github.com/
```

#### 3. Visual C++ Redistributable

**Important:** Required for running the compiled application.

```bash
# Download and install:
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

#### 4. Inno Setup (for creating installer)

**Recommended version:** Inno Setup 6.2 or higher

```bash
# Download from:
https://jrsoftware.org/isdl.php

# Download "innosetup-6.2.x.exe"
# Install with default options
```

### GPU Setup (optional)

To enable GPU acceleration with ONNX Runtime:

**GPU Requirements:**
- NVIDIA CUDA-compatible GPU
- CUDA Toolkit 11.x
- cuDNN 8.x

**Installing CUDA:**

```bash
# 1. Download CUDA Toolkit
https://developer.nvidia.com/cuda-downloads

# 2. Install CUDA Toolkit 11.8 (recommended)
# Follow installation wizard

# 3. Verify installation
nvcc --version
```

**Note:** If you don't have an NVIDIA GPU, the application will work in CPU-only mode.

---

## 📦 Installing Dependencies

### Step 1: Clone the repository

```bash
# With Git
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# Or download ZIP from GitHub
# Then extract and open terminal in the folder
```

### Step 2: Create virtual environment (recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# You should see (venv) in your terminal
```

### Step 3: Install main dependencies

```bash
# Update pip
python -m pip install --upgrade pip

# Install main dependencies
pip install -r requirements.txt
```

**Main dependencies:**
- `opencv-contrib-python` - Image processing
- `onnxruntime-gpu` - ONNX model inference with GPU
- `dearpygui` - GUI framework
- `mediapipe` - ML solutions
- `librosa` - Audio processing
- `matplotlib` - Visualization
- And more...

### Step 4: Install build dependencies

```bash
pip install -r requirements-build.txt
```

**Build dependencies:**
- `pyinstaller>=5.0.0` - Executable creation

### Step 5: Verify installation

```bash
# Test the application
python main.py

# Application should launch
# If it works, dependencies are correctly installed
```

---

## 🏗️ Building the Executable

### Method 1: Standard Build (Recommended)

```bash
# Build with clean
python build_exe.py --clean

# Duration: 5-15 minutes depending on your system
```

**What this command does:**
1. ✅ Checks that all dependencies are installed
2. ✅ Cleans old build artifacts
3. ✅ Packages all Python dependencies
4. ✅ Includes all nodes and ONNX models
5. ✅ Creates executable in `dist/CV_Studio/`

### Method 2: Build without Console (GUI Mode)

```bash
# Build in windowed mode (no console)
python build_exe.py --clean --windowed
```

**Use this option when:**
- You want a clean interface without console window
- For final distribution to users
- **Note:** Harder to see errors in windowed mode

### Method 3: Build with Custom Icon

```bash
# With custom icon
python build_exe.py --clean --icon your_icon.ico

# Icon must be a .ico file
# Recommended size: 256x256 pixels
```

### Method 4: Debug Build

```bash
# Build with debug information
python build_exe.py --clean --debug

# Useful for diagnosing problems
```

### Advanced Build Options

```bash
# Combining options
python build_exe.py --clean --windowed --icon my_icon.ico

# Available options:
# --clean          : Cleans build folders before
# --windowed       : Hides console window
# --debug          : Build with debug information
# --icon FILE      : Uses custom icon
# --help           : Shows help
```

### Build Output

After a successful build, you'll find:

```
CV_Studio/
├── dist/
│   └── CV_Studio/                    ← Distribution folder
│       ├── CV_Studio.exe            ← Main executable
│       ├── README.txt               ← Documentation
│       ├── node/                    ← All nodes
│       │   ├── DLNode/             ← Deep Learning nodes
│       │   │   └── object_detection/
│       │   │       └── */model/*.onnx  ← ONNX models
│       │   ├── InputNode/
│       │   ├── ProcessNode/
│       │   └── ...
│       ├── node_editor/             ← Node editor
│       ├── src/                     ← Source utilities
│       └── _internal/               ← Python runtime and DLLs
│
├── build/                           ← Temporary files (can be deleted)
└── CV_Studio.spec                   ← PyInstaller config file
```

### Build Verification

```bash
# Navigate to distribution folder
cd dist\CV_Studio

# Test executable
CV_Studio.exe

# Or with debug output
CV_Studio.exe --use_debug_print
```

**Checkpoints:**
- ✅ Application launches without errors
- ✅ Nodes are visible in menu
- ✅ You can add and connect nodes
- ✅ Object detection nodes can load ONNX models
- ✅ Image processing nodes work correctly

---

## 📀 Creating Windows Installer

### Why create an installer?

An installer provides:
- ✅ Professional installation in Program Files
- ✅ Shortcuts in Start Menu and Desktop
- ✅ Clean uninstallation via Control Panel
- ✅ System prerequisites checks
- ✅ Enhanced user experience

### Prerequisites

1. **Successful build** - `dist/CV_Studio/` must exist
2. **Inno Setup installed** - See Prerequisites section above

### Step 1: Verify installation script

The `installer.iss` file is already provided. It configures:
- Application name and version
- Files to include
- Icons and shortcuts
- Prerequisites checks
- Messages in French and English

### Step 2: Compile the installer

**Method A: Via Inno Setup GUI**

1. Open **Inno Setup Compiler**
2. File → Open → Select `installer.iss`
3. Build → Compile (or F9)
4. Installer will be created in `installer_output/`

**Method B: Via command line**

```bash
# Compile with ISCC (Inno Setup Command Line Compiler)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# Or if Inno Setup is in PATH
iscc installer.iss
```

### Step 3: Locate the installer

```bash
installer_output/
└── CV_Studio_Setup_v1.0.0.exe     ← Windows installer
```

**Size:** Approximately 800 MB - 1.5 GB (compressed)

### Step 4: Test the installer

```bash
# Run installer
installer_output\CV_Studio_Setup_v1.0.0.exe

# Installation wizard will guide the user:
# 1. Welcome
# 2. License
# 3. Installation folder selection
# 4. Component selection
# 5. Shortcuts creation
# 6. Installation
# 7. Finished
```

### Customizing the installer

Edit `installer.iss` to customize:

```pascal
; Basic information
#define MyAppName "CV Studio"
#define MyAppVersion "1.0.0"        ; ← Change version
#define MyAppPublisher "hackolite"  ; ← Your name/organization

; Installer icon
SetupIconFile=node_editor\setting\icon.ico  ; ← Your .ico icon

; Output folder
OutputDir=installer_output
OutputBaseFilename=CV_Studio_Setup_v{#MyAppVersion}  ; ← File name
```

---

## 📤 Distribution

### Format 1: ZIP Folder

**Advantages:**
- Simple to create
- No installation required
- Portable

**Creation:**

```bash
# Navigate to dist
cd dist

# Create ZIP archive
# With PowerShell:
Compress-Archive -Path CV_Studio -DestinationPath CV_Studio_v1.0.0.zip

# With 7-Zip (if installed):
7z a CV_Studio_v1.0.0.zip CV_Studio
```

**Instructions for users:**
1. Download ZIP file
2. Extract to a folder
3. Run `CV_Studio.exe`

### Format 2: Windows Installer

**Advantages:**
- Professional installation
- System integration (Start Menu, shortcuts)
- Clean uninstallation
- Prerequisites checking

**Distribution:**
- Share `CV_Studio_Setup_v1.0.0.exe`
- Users double-click and follow wizard

### Distribution on GitHub

```bash
# 1. Create new release on GitHub
https://github.com/your-name/CV_Studio/releases/new

# 2. Release information:
Tag version: v1.0.0
Release title: CV Studio v1.0.0
Description:
  - Main features
  - Bug fixes
  - Release notes

# 3. Upload files:
- CV_Studio_Setup_v1.0.0.exe    (Installer)
- CV_Studio_v1.0.0.zip           (Portable version)
- README.txt                     (Instructions)
- CHANGELOG.md                   (Change history)

# 4. Publish release
```

### Information to provide to users

**README.txt for distribution:**

```markdown
# CV Studio v1.0.0

## System Requirements

- Windows 10/11 (64-bit) recommended
- Windows 7 SP1 minimum
- 4 GB RAM minimum (8 GB recommended)
- 2 GB disk space
- NVIDIA GPU (optional, for acceleration)

## Installation

### Method 1: Installer (Recommended)
1. Run CV_Studio_Setup_v1.0.0.exe
2. Follow installation wizard
3. Launch from Start Menu

### Method 2: Portable Version
1. Extract CV_Studio_v1.0.0.zip
2. Open CV_Studio folder
3. Double-click CV_Studio.exe

## Prerequisites

If application doesn't start:
1. Install Visual C++ Redistributable:
   https://aka.ms/vs/17/release/vc_redist.x64.exe

2. For GPU acceleration:
   - NVIDIA GPU required
   - Updated NVIDIA drivers

## Support

- Documentation: https://github.com/hackolite/CV_Studio
- Issues: https://github.com/hackolite/CV_Studio/issues
```

---

## 🔧 Troubleshooting

### Problem: PyInstaller not found

```bash
# Solution:
pip install pyinstaller

# Or:
pip install -r requirements-build.txt
```

### Problem: Missing dependencies

```bash
# Error during build mentioning missing packages

# Solution:
pip install -r requirements.txt
pip install -r requirements-build.txt

# Verify:
python build_exe.py
# Follow displayed suggestions
```

### Problem: Build fails with memory error

```bash
# If you get "MemoryError" or build stops

# Solution:
# 1. Close other applications
# 2. Disable UPX (compression)

# Edit CV_Studio.spec:
exe = EXE(
    ...
    upx=False,  # ← Change True to False
    ...
)

coll = COLLECT(
    ...
    upx=False,  # ← Change True to False
    ...
)

# Then rebuild:
python build_exe.py --clean
```

### Problem: Exe doesn't start

**Symptom:** Double-clicking exe does nothing

**Solutions:**

1. **Run from command line to see errors:**

```bash
cd dist\CV_Studio
CV_Studio.exe --use_debug_print
```

2. **Install Visual C++ Redistributable:**

```bash
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

3. **Check antivirus:**
- Some antivirus block PyInstaller executables
- Add exception for CV_Studio.exe

4. **Check permissions:**
- Right-click CV_Studio.exe
- Properties → Unblock (if present)

### Problem: ONNX models not found

```bash
# Error: "Model file not found"

# Solution:
# Verify node/DLNode folder is intact

# Expected structure:
dist/CV_Studio/node/DLNode/
├── object_detection/
│   ├── yolox/
│   │   └── model/
│   │       └── *.onnx
│   ├── yolo11/
│   │   └── model/
│   │       └── *.onnx
│   └── ...

# If missing, rebuild:
python build_exe.py --clean
```

### Problem: GPU not detected

**Symptom:** Application uses CPU even with NVIDIA GPU

**Solutions:**

1. **Check CUDA:**

```bash
nvcc --version
nvidia-smi
```

2. **Check onnxruntime-gpu:**

```bash
# In build environment:
pip list | grep onnx

# Should display:
# onnxruntime-gpu    x.x.x
```

3. **Test GPU in application:**
- Add Object Detection node
- Check "GPU" checkbox
- If error, GPU is not available

### Problem: Inno Setup doesn't compile

**Error:** "File not found" in Inno Setup

**Solutions:**

1. **Verify build exists:**

```bash
# dist/CV_Studio folder must exist
dir dist\CV_Studio\CV_Studio.exe
```

2. **Check paths in installer.iss:**

```pascal
; Check these lines:
Source: "dist\CV_Studio\*"; ...        ; ← Correct path?
SetupIconFile=node_editor\setting\icon.ico  ; ← File exists?
LicenseFile=LICENSE                    ; ← File exists?
```

3. **Create missing folders:**

```bash
mkdir installer_output
```

### Problem: Installer too large

**Symptom:** Installer is more than 2 GB

**Solutions:**

1. **Increase compression in installer.iss:**

```pascal
Compression=lzma2/ultra64     ; ← Maximum compression
SolidCompression=yes
```

2. **Remove unused models:**
- Edit `CV_Studio.spec`
- Exclude some heavy ONNX models

### Problem: Application slow to start

**Symptom:** Exe takes 30+ seconds to start

**Solutions:**

1. **Disable real-time antivirus scan** for the folder
2. **Use folder mode** (not --onefile) - already default
3. **Add exception in Windows Defender:**
   - Settings → Virus & threat protection
   - Manage settings
   - Add exclusion → Folder
   - Select CV_Studio folder

---

## ❓ FAQ

### Q1: Is PyTorch necessary?

**A:** No, CV Studio uses **ONNX Runtime** for model inference. PyTorch is not required unless:
- You want to train new models
- You want to convert PyTorch models to ONNX
- You're developing new Deep Learning nodes using PyTorch

**To add PyTorch (optional):**

```bash
# For CPU only:
pip install torch torchvision

# For GPU (CUDA 11.8):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

**Note:** Adding PyTorch will increase executable size by approximately 1-2 GB.

### Q2: What's the difference between ONNX Runtime and PyTorch?

**A:**
- **ONNX Runtime**: Lightweight and fast inference engine (CV Studio uses this)
- **PyTorch**: Complete deep learning framework for training and inference

For distribution, ONNX Runtime is preferable because:
- Lighter (fewer dependencies)
- Faster for inference
- Compatible with many frameworks

### Q3: Can I create a smaller executable?

**A:** Yes, several options:

1. **Remove unused ONNX models** (saves 200-500 MB)
2. **Use onnxruntime instead of onnxruntime-gpu** (saves 100-200 MB)
3. **Remove unused nodes**
4. **Increase UPX compression**

**Warning:** Smaller exe = fewer features

### Q4: Does the application work without GPU?

**A:** Yes! The application works in CPU mode by default. GPU is optional for:
- Accelerating ONNX model inference
- Faster video processing
- Real-time object detection

### Q5: Can I distribute the application commercially?

**A:** CV Studio is under **Apache 2.0** license, so you can:
- ✅ Use commercially
- ✅ Modify code
- ✅ Distribute
- ✅ Patent

**But you must:**
- Include Apache 2.0 license
- State changes made
- Check licenses of individual ONNX models

### Q6: How do I update the version?

**A:**

1. **Change version in code**

```python
# In main.py or a config file
VERSION = "1.0.1"
```

2. **Change in installer.iss**

```pascal
#define MyAppVersion "1.0.1"
```

3. **Rebuild**

```bash
python build_exe.py --clean
iscc installer.iss
```

### Q7: Can I create installer for Linux/Mac?

**A:** This guide is specific to Windows. For Linux/Mac:

**Linux:**
- Use PyInstaller (similar)
- Create .deb package (Debian/Ubuntu)
- Create .rpm package (RedHat/Fedora)
- Use AppImage for portability

**Mac:**
- Use PyInstaller
- Create .app application
- Create .dmg for distribution
- Sign application (required for macOS)

### Q8: How do I debug the compiled application?

**A:**

1. **Build in debug mode:**

```bash
python build_exe.py --clean --debug
```

2. **Run with debug output:**

```bash
CV_Studio.exe --use_debug_print
```

3. **Check logs:**
- Logs are displayed in console
- Use --console=True in spec file

4. **Use monitoring tool:**
- Process Explorer
- Process Monitor
- DebugView

### Q9: Can I include my own ONNX models?

**A:** Yes!

1. **Add model to appropriate folder:**

```
node/DLNode/object_detection/my_model/model/my_model.onnx
```

2. **Create corresponding node** (see development documentation)

3. **Rebuild:**

```bash
python build_exe.py --clean
```

Model will be automatically included in exe.

### Q10: How long does building take?

**A:** Approximate times:

- **First complete build:** 10-20 minutes
- **Rebuild (with --clean):** 5-10 minutes
- **Incremental build:** 2-5 minutes
- **Installer compilation:** 1-3 minutes

**Factors affecting duration:**
- CPU speed
- Disk speed (SSD vs HDD)
- Antivirus (can slow significantly)
- Size of ONNX models

---

## 📝 Command Summary

```bash
# 1. Initial installation
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-build.txt

# 2. Test application
python main.py

# 3. Build executable
python build_exe.py --clean

# 4. Create installer
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 5. Test
dist\CV_Studio\CV_Studio.exe
installer_output\CV_Studio_Setup_v1.0.0.exe

# 6. Distribute
# - Share installer_output\CV_Studio_Setup_v1.0.0.exe
# - Or create ZIP of dist\CV_Studio
```

---

## 🎓 Additional Resources

### Documentation

- [README.md](README.md) - Main documentation
- [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md) - French guide
- [BUILD_EXE_QUICKREF.md](BUILD_EXE_QUICKREF.md) - Quick reference

### Useful Links

- [PyInstaller Documentation](https://pyinstaller.org/)
- [Inno Setup Documentation](https://jrsoftware.org/ishelp/)
- [ONNX Runtime](https://onnxruntime.ai/)
- [Python Packaging Guide](https://packaging.python.org/)

### Support

- **GitHub Issues:** [https://github.com/hackolite/CV_Studio/issues](https://github.com/hackolite/CV_Studio/issues)
- **Discussions:** [https://github.com/hackolite/CV_Studio/discussions](https://github.com/hackolite/CV_Studio/discussions)

---

## ✅ Distribution Checklist

Before distributing your application:

### Tests

- [ ] Exe launches without errors
- [ ] All nodes are accessible
- [ ] Image processing nodes work
- [ ] ONNX models load correctly
- [ ] Object detection works
- [ ] GPU acceleration works (if applicable)
- [ ] Webcam can be opened
- [ ] Videos can be played
- [ ] Export/Import graphs works

### Documentation

- [ ] README.txt included
- [ ] LICENSE included
- [ ] Clear installation instructions
- [ ] System requirements documented
- [ ] Support links provided

### Distribution

- [ ] Files signed (optional but recommended)
- [ ] Version tested on clean machine
- [ ] Acceptable file size (< 2 GB)
- [ ] Uninstallation instructions
- [ ] Release notes (CHANGELOG)

---

**🎉 Congratulations! You now have a professional Windows executable of CV Studio!**

For any questions or problems, feel free to open an issue on GitHub.
