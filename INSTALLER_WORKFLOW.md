# CV Studio - Installer Creation Workflow

## 📊 Visual Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CV Studio Build Process                      │
└─────────────────────────────────────────────────────────────────┘

START
  │
  ├─── Prerequisites Check
  │     ├─ Python 3.8-3.12 ✓
  │     ├─ pip & dependencies ✓
  │     └─ PyInstaller installed ✓
  │
  ├─── Build Executable
  │     │
  │     └─── python build_exe.py --clean
  │           │
  │           ├─ [1/7] Check requirements
  │           ├─ [2/7] Clean build directories
  │           ├─ [3/7] Configure build
  │           ├─ [4/7] Build executable
  │           ├─ [5/7] Create documentation
  │           ├─ [6/7] Create installer (optional)
  │           └─ [7/7] Build summary
  │
  ├─── Output
  │     │
  │     ├─── dist/CV_Studio/
  │     │      ├─ CV_Studio.exe ✓
  │     │      ├─ node/ (all nodes + ONNX models) ✓
  │     │      ├─ node_editor/ ✓
  │     │      ├─ src/ ✓
  │     │      └─ _internal/ (Python runtime) ✓
  │     │
  │     └─── installer_output/ (if --installer used)
  │            └─ CV_Studio_Setup_v1.0.0.exe ✓
  │
  └─── Distribution
        │
        ├─── Option A: ZIP Archive (Portable)
        │     └─ Compress-Archive -Path CV_Studio -DestinationPath CV_Studio.zip
        │
        └─── Option B: Windows Installer (Professional)
              └─ Share CV_Studio_Setup_v1.0.0.exe
```

## 🔄 Build Flow Diagram

```
┌──────────────┐
│   Developer  │
└──────┬───────┘
       │
       │ git clone & setup
       ▼
┌──────────────────────────┐
│  Source Code Repository  │
│  - main.py               │
│  - node/                 │
│  - node_editor/          │
│  - requirements.txt      │
│  - build_exe.py          │
│  - installer.iss         │
└──────┬───────────────────┘
       │
       │ pip install -r requirements.txt
       │ pip install -r requirements-build.txt
       ▼
┌──────────────────────────┐
│   Dependencies Ready     │
│   - Python packages      │
│   - PyInstaller          │
│   - ONNX Runtime GPU     │
└──────┬───────────────────┘
       │
       │ python build_exe.py --clean
       ▼
┌──────────────────────────┐
│  PyInstaller Process     │
│  - Analyze dependencies  │
│  - Collect files         │
│  - Bundle Python runtime │
│  - Package ONNX models   │
│  - Create executable     │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│   dist/CV_Studio/        │
│   Standalone Executable  │
│   (800 MB - 1.5 GB)      │
└──────┬───────────────────┘
       │
       │ Optional: python build_exe.py --installer
       │           or: iscc installer.iss
       ▼
┌──────────────────────────┐
│  Inno Setup Compiler     │
│  - Read installer.iss    │
│  - Package files         │
│  - Create setup wizard   │
│  - Compress installer    │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│ installer_output/        │
│ CV_Studio_Setup.exe      │
│ (Professional Installer) │
└──────┬───────────────────┘
       │
       │ Distribution
       ▼
┌──────────────────────────┐
│   End Users              │
│   - Download installer   │
│   - Run setup wizard     │
│   - Install & launch     │
└──────────────────────────┘
```

## 🎯 Decision Tree: Which Distribution Method?

```
                    Start Distribution
                          │
                          ▼
              ┌───────────────────────┐
              │  Who is your target   │
              │       audience?       │
              └───────────┬───────────┘
                          │
           ┌──────────────┼──────────────┐
           │                             │
           ▼                             ▼
    ┌─────────────┐              ┌─────────────┐
    │  Technical  │              │   General   │
    │    Users    │              │    Users    │
    │  Developers │              │ End Users   │
    └──────┬──────┘              └──────┬──────┘
           │                            │
           ▼                            ▼
    ┌─────────────┐              ┌─────────────┐
    │ ZIP Archive │              │  Installer  │
    │  (Portable) │              │(Professional)│
    └──────┬──────┘              └──────┬──────┘
           │                            │
           │                            │
           ├─ Easy to extract           ├─ Start Menu shortcuts
           ├─ No admin required         ├─ Desktop shortcut
           ├─ Portable (USB)            ├─ Control Panel uninstall
           ├─ No installation           ├─ Prerequisites check
           └─ Manual cleanup            └─ Professional look
```

## 🛠️ Command Reference

```bash
# ═══════════════════════════════════════════════════════════════
#                    BASIC COMMANDS
# ═══════════════════════════════════════════════════════════════

# 1. Setup environment (one time)
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt requirements-build.txt

# 2. Build executable (standard)
python build_exe.py --clean

# 3. Build with installer
python build_exe.py --clean --installer

# 4. Test executable
cd dist\CV_Studio
CV_Studio.exe --use_debug_print

# ═══════════════════════════════════════════════════════════════
#                   ADVANCED OPTIONS
# ═══════════════════════════════════════════════════════════════

# GUI mode (no console window)
python build_exe.py --clean --windowed

# With custom icon
python build_exe.py --clean --icon my_icon.ico

# Debug build
python build_exe.py --clean --debug

# All options combined
python build_exe.py --clean --windowed --icon icon.ico --installer

# ═══════════════════════════════════════════════════════════════
#                  INSTALLER ONLY
# ═══════════════════════════════════════════════════════════════

# Compile installer manually (requires Inno Setup)
iscc installer.iss

# Or with full path
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# ═══════════════════════════════════════════════════════════════
#                   DISTRIBUTION
# ═══════════════════════════════════════════════════════════════

# Create ZIP archive
cd dist
Compress-Archive -Path CV_Studio -DestinationPath CV_Studio_v1.0.0.zip

# With 7-Zip
7z a CV_Studio_v1.0.0.zip CV_Studio

# Upload to GitHub Releases
# (manual through GitHub web interface)
```

## 📁 File Structure

```
CV_Studio/
│
├── 📄 Source Files
│   ├── main.py                          # Application entry point
│   ├── requirements.txt                 # Python dependencies
│   ├── requirements-build.txt           # Build dependencies
│   ├── build_exe.py                     # Build script ⭐ NEW
│   ├── CV_Studio.spec                   # PyInstaller config
│   └── installer.iss                    # Inno Setup script ⭐ NEW
│
├── 📚 Documentation ⭐ NEW
│   ├── BUILD_EXE_GUIDE.md              # Complete guide (English)
│   ├── BUILD_EXE_GUIDE_FR.md           # Guide complet (Français)
│   ├── BUILD_EXE_QUICKREF.md           # Quick reference
│   ├── INSTALLER_SETUP_SUMMARY.md      # Overview summary
│   └── INSTALLER_WORKFLOW.md           # This file
│
├── 🏗️ Build Output (generated)
│   ├── build/                           # Temporary build files
│   ├── dist/
│   │   └── CV_Studio/                  # 📦 Executable package
│   │       ├── CV_Studio.exe           # Main executable
│   │       ├── README.txt              # User documentation
│   │       ├── node/                   # All nodes + ONNX models
│   │       ├── node_editor/            # Editor core
│   │       ├── src/                    # Source utilities
│   │       └── _internal/              # Python runtime & DLLs
│   │
│   └── installer_output/               # 📀 Installer package ⭐ NEW
│       └── CV_Studio_Setup_v1.0.0.exe # Windows installer
│
└── 📦 Source Directories
    ├── node/                            # Node implementations
    ├── node_editor/                     # Editor framework
    └── src/                             # Core utilities
```

## 🔑 Key Decision Points

### When to use `--installer` flag?

```
Use --installer when:
├─ You want professional installation
├─ Targeting non-technical users
├─ Need Start Menu integration
├─ Want easy uninstallation
└─ Have Inno Setup installed

Skip --installer when:
├─ Creating quick test build
├─ Don't have Inno Setup
├─ Prefer portable version
└─ Targeting technical users
```

### Which guide to read?

```
Quick Start (< 5 min)
└─ BUILD_EXE_QUICKREF.md

First Time Building (30 min)
└─ BUILD_EXE_GUIDE.md (English)
   or BUILD_EXE_GUIDE_FR.md (Français)

Overview Only
└─ INSTALLER_SETUP_SUMMARY.md

Build Process Understanding
└─ INSTALLER_WORKFLOW.md (this file)
```

## 📊 Timeline Estimates

```
Task                              Time        Notes
─────────────────────────────────────────────────────────────────
Initial setup (dependencies)      10-20 min   One-time only
First complete build              10-20 min   Includes PyInstaller
Subsequent builds (--clean)        5-10 min   With --clean flag
Incremental builds                 2-5 min    Without --clean
Installer compilation              1-3 min    Requires Inno Setup
Testing executable                 5-10 min   Verify all features
Creating ZIP for distribution      1-2 min    Compression
Total (first time)                30-60 min   Complete process
Total (subsequent)                10-20 min   Already setup
```

## 🎓 Learning Path

```
Level 1: First Time Builder
├─ 1. Read BUILD_EXE_QUICKREF.md
├─ 2. Install prerequisites
├─ 3. Run: python build_exe.py --clean
└─ 4. Test the executable

Level 2: Regular Builder
├─ 1. Understand build options
├─ 2. Create both ZIP and Installer
├─ 3. Test on different machines
└─ 4. Read full guide for optimization

Level 3: Advanced User
├─ 1. Customize installer.iss
├─ 2. Optimize build size
├─ 3. Add custom icons
└─ 4. Automate distribution

Level 4: Contributor
├─ 1. Understand CV_Studio.spec
├─ 2. Modify build_exe.py
├─ 3. Add new features
└─ 4. Update documentation
```

## 🔍 Dependency Clarification

```
┌─────────────────────────────────────────────────────────────┐
│                  Dependency Landscape                        │
└─────────────────────────────────────────────────────────────┘

Required (Included in Executable)
├─ Python Runtime ........................... ✅ Auto-included
├─ OpenCV (opencv-contrib-python) .......... ✅ Required
├─ DearPyGUI ............................... ✅ Required
├─ ONNX Runtime GPU ........................ ✅ Required
├─ MediaPipe ............................... ✅ Required
├─ NumPy ................................... ✅ Required
└─ Other libs (librosa, matplotlib, etc.) .. ✅ Required

Optional (For Development Only)
├─ PyTorch ................................. ❌ NOT included
│   └─ Use when:
│       ├─ Training new models
│       ├─ Converting models to ONNX
│       └─ Developing PyTorch-based nodes
│
└─ CUDA Toolkit ............................ ⭐ Optional
    └─ Use when:
        ├─ Have NVIDIA GPU
        ├─ Want GPU acceleration
        └─ Processing large videos
```

## ✅ Quality Checklist

```
Before Distribution:
├─ ☑ Executable builds successfully
├─ ☑ All nodes load correctly
├─ ☑ ONNX models are included
├─ ☑ GPU detection works (if applicable)
├─ ☑ No console errors
├─ ☑ Tested on clean Windows machine
├─ ☑ Installer creates shortcuts
├─ ☑ Uninstaller works properly
├─ ☑ Documentation is included
└─ ☑ Version numbers are correct
```

## 🎯 Summary

This workflow provides:
- ✅ Clear visual representation of the build process
- ✅ Decision trees for choosing distribution methods
- ✅ Command reference for all scenarios
- ✅ Timeline estimates for planning
- ✅ Learning path for different skill levels
- ✅ Dependency clarification
- ✅ Quality checklist

**Ready to build?** Start with `BUILD_EXE_QUICKREF.md` for quick start!
