# How to Get the Windows Executable (.exe)

## 🎯 Automatic Method - GitHub Actions (RECOMMENDED)

The Windows executable is now automatically built via GitHub Actions!

### Option 1: Manual Build (Easiest)

1. **Go to the Actions tab** of this GitHub repository
   - URL: https://github.com/hackolite/CV_Studio/actions

2. **Click on "Build Windows Executable"** workflow in the left sidebar

3. **Click "Run workflow"** (button on the right)
   - Select the `main` branch or your preferred branch
   - Click the green "Run workflow" button

4. **Wait for the build to complete** (approximately 10-15 minutes)
   - You'll see a green ✓ checkmark when it's done

5. **Download the executable**
   - Click on the completed workflow
   - Scroll down to the "Artifacts" section
   - Download `CV_Studio-Windows-Executable.zip`
   - Extract the ZIP and run `CV_Studio.exe`

### Option 2: Automatic Build on Release

When you create a new release on GitHub, the executable is automatically built and attached to the release.

1. **Create a new release**:
   - Go to "Releases" → "Create a new release"
   - Create a new tag (e.g., `v1.0.0`)
   - Publish the release

2. **The executable will be automatically built** and added to the release assets

3. **Download from the release page**: `CV_Studio-Windows.zip`

### Option 3: Automatic Build on Tag Push

Every time you push a tag starting with `v` (e.g., `v1.0.0`), an automatic build is triggered:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The executable will be available in the Actions tab as an artifact.

## 🖥️ Manual Method - Local Build on Windows

If you prefer to build the executable yourself on your Windows machine:

### Prerequisites
- Windows 10/11
- Python 3.7+ installed
- Git installed

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# 2. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 3. Build the executable
python build_exe.py --clean

# 4. The executable is in dist/CV_Studio/
cd dist/CV_Studio
CV_Studio.exe
```

## 📦 Executable Contents

Once downloaded and extracted, you'll have:

```
CV_Studio/
├── CV_Studio.exe           # ← Main executable to run
├── README.txt              # Documentation
├── node/                   # All nodes (Input, Process, DL, Audio...)
│   └── DLNode/            
│       └── object_detection/
│           ├── YOLOX/model/*.onnx      # ONNX models
│           ├── YOLO/model/*.onnx
│           └── ...
├── node_editor/           # Node editor
└── _internal/            # Python dependencies
```

## 🚀 Usage

Simply double-click `CV_Studio.exe`!

No Python installation required. Everything is included.

## ❓ Frequently Asked Questions

### How long does the build take?
- About 10-15 minutes on GitHub Actions
- About 5-10 minutes locally depending on your machine

### What is the size of the executable?
- About 800 MB - 1.5 GB (includes all ONNX models and dependencies)

### Can I build for Linux or macOS?
- Yes, modify `.github/workflows/build-exe.yml` to use `ubuntu-latest` or `macos-latest`
- On Linux, the executable will be named `CV_Studio` (without .exe)
- On macOS, it will be a `.app` application

### The executable won't start?
1. Install Visual C++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Run from command line to see errors:
   ```bash
   cd dist\CV_Studio
   CV_Studio.exe --use_debug_print
   ```

## 🔗 Complete Documentation

For more details on building and customization:
- [Complete French guide](BUILD_EXE_GUIDE_FR.md)
- [Complete English guide](BUILD_EXE_GUIDE.md)
- [Quick reference](BUILD_EXE_QUICKREF.md)

## 📞 Support

Questions? Open an issue on GitHub:
https://github.com/hackolite/CV_Studio/issues

---

**Enjoy CV_Studio! 🎨**
