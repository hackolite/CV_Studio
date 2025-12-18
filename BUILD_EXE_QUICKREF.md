# Quick Reference: Building CV Studio Executable

**Quick start guide for creating Windows executable and installer**

---

## ⚡ Quick Commands

```bash
# 1. Setup (one time)
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt requirements-build.txt

# 2. Build executable
python build_exe.py --clean

# 3. Create installer (requires Inno Setup)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

# 4. Test
dist\CV_Studio\CV_Studio.exe
```

---

## 📋 Prerequisites

| Item | Link |
|------|------|
| Python 3.8-3.12 | https://www.python.org/downloads/ |
| Git (optional) | https://git-scm.com/download/win |
| Visual C++ Redist | https://aka.ms/vs/17/release/vc_redist.x64.exe |
| Inno Setup 6.2+ | https://jrsoftware.org/isdl.php |
| CUDA 11.8 (GPU) | https://developer.nvidia.com/cuda-downloads |

---

## 🏗️ Build Options

```bash
# Standard build
python build_exe.py --clean

# GUI only (no console)
python build_exe.py --clean --windowed

# With custom icon
python build_exe.py --clean --icon your_icon.ico

# Debug mode
python build_exe.py --clean --debug

# Combined
python build_exe.py --clean --windowed --icon icon.ico
```

---

## 📁 Output Locations

```
dist/CV_Studio/CV_Studio.exe        ← Executable
installer_output/CV_Studio_Setup_v1.0.0.exe  ← Installer
```

---

## ✅ Quick Checklist

### Before Building
- [ ] Python 3.8-3.12 installed
- [ ] Dependencies installed (`pip install -r requirements.txt requirements-build.txt`)
- [ ] Application tested (`python main.py` works)

### Building
- [ ] Run `python build_exe.py --clean`
- [ ] Wait 5-15 minutes for build
- [ ] Test executable: `dist\CV_Studio\CV_Studio.exe`

### Creating Installer
- [ ] Inno Setup installed
- [ ] Build successful (dist/CV_Studio exists)
- [ ] Run: `iscc installer.iss`
- [ ] Test installer: `installer_output\CV_Studio_Setup_v1.0.0.exe`

### Distribution
- [ ] Test on clean machine
- [ ] Include README.txt
- [ ] Include LICENSE
- [ ] Upload to GitHub Releases

---

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| PyInstaller not found | `pip install pyinstaller` |
| Missing dependencies | `pip install -r requirements.txt requirements-build.txt` |
| Exe doesn't start | Install VC++ Redist, check antivirus |
| Models not found | Verify dist/CV_Studio/node/DLNode structure |
| GPU not detected | Check CUDA installation, nvidia-smi |
| Installer won't compile | Verify dist/CV_Studio exists, check paths in installer.iss |

---

## 📦 What's Included

- ✅ Complete Python runtime
- ✅ OpenCV, DearPyGUI, ONNX Runtime
- ✅ All nodes (100+)
- ✅ All ONNX models (YOLOX, YOLO, etc.)
- ✅ GPU support (CUDA)
- ✅ ~800 MB - 1.5 GB total

---

## 🚀 Distribution Methods

### Method 1: ZIP File (Portable)
```bash
cd dist
Compress-Archive -Path CV_Studio -DestinationPath CV_Studio_v1.0.0.zip
```
Users extract and run `CV_Studio.exe`

### Method 2: Installer (Professional)
```bash
iscc installer.iss
```
Users run `CV_Studio_Setup_v1.0.0.exe` installer

---

## 🌐 Languages

- **Full Guide (English):** [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md)
- **Guide Complet (Français):** [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md)

---

## 📚 Documentation

- Main README: [README.md](README.md)
- PyInstaller Script: [build_exe.py](build_exe.py)
- Inno Setup Script: [installer.iss](installer.iss)
- PyInstaller Spec: [CV_Studio.spec](CV_Studio.spec)

---

## 💡 Tips

### Speed up builds
- Close other applications
- Use SSD storage
- Add antivirus exception for build folder
- Don't use --debug for final build

### Reduce size
- Remove unused ONNX models
- Use onnxruntime instead of onnxruntime-gpu (if no GPU needed)
- Edit CV_Studio.spec to exclude files

### Test thoroughly
```bash
# Test with debug output
CV_Studio.exe --use_debug_print

# Test all features:
# - Add nodes
# - Load images/videos
# - Object detection with ONNX
# - Save/load graphs
```

---

## ❓ PyTorch vs ONNX

**CV Studio uses ONNX Runtime (not PyTorch)**

| | ONNX Runtime | PyTorch |
|---|---|---|
| Used for | Inference (running models) | Training + Inference |
| Size | ~200 MB | ~1-2 GB |
| Speed | Faster inference | Slower inference |
| GPU Support | Yes (CUDA) | Yes (CUDA) |
| **Required?** | ✅ Yes | ❌ No (optional) |

**When you need PyTorch:**
- Training new models
- Converting PyTorch models to ONNX
- Developing custom PyTorch-based nodes

**To add PyTorch (optional):**
```bash
# CPU version
pip install torch torchvision

# GPU version (CUDA 11.8)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

Note: Adds ~1-2 GB to executable size

---

## 🆘 Support

- **Issues:** https://github.com/hackolite/CV_Studio/issues
- **Discussions:** https://github.com/hackolite/CV_Studio/discussions
- **Full Guides:** See BUILD_EXE_GUIDE.md or BUILD_EXE_GUIDE_FR.md

---

## 📊 Build Time Estimates

| Task | Time |
|------|------|
| First complete build | 10-20 min |
| Rebuild (--clean) | 5-10 min |
| Incremental build | 2-5 min |
| Installer compilation | 1-3 min |

*Faster with SSD, slower with antivirus scanning*

---

## 🎯 Version Management

Change version in two places:

**1. installer.iss:**
```pascal
#define MyAppVersion "1.0.0"
```

**2. Your code (optional):**
```python
# main.py or config
VERSION = "1.0.0"
```

Then rebuild:
```bash
python build_exe.py --clean
iscc installer.iss
```

---

**Need more details? See the complete guides:**
- [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md) - English
- [BUILD_EXE_GUIDE_FR.md](BUILD_EXE_GUIDE_FR.md) - Français
