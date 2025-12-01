# Quick Reference: Building CV_Studio Executable

## 🚀 Quick Start (1-2-3)

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Run the build script
python build_exe.py --clean

# 3. Test your executable
dist\CV_Studio\CV_Studio.exe
```

**Done!** Your standalone .exe is ready in `dist/CV_Studio/`

## 📁 Files You Need to Know

| File | Purpose |
|------|---------|
| `build_exe.py` | **Main build script** - Run this to build the .exe |
| `CV_Studio.spec` | PyInstaller configuration - Includes all nodes and ONNX models |
| `BUILD_EXE_GUIDE.md` | Full documentation (English) |
| `BUILD_EXE_GUIDE_FR.md` | Full documentation (French) |

## 🎯 Common Build Commands

```bash
# Standard build
python build_exe.py

# Clean build (removes old files first)
python build_exe.py --clean

# GUI-only mode (no console window)
python build_exe.py --windowed

# With custom icon
python build_exe.py --icon my_icon.ico

# Debug build
python build_exe.py --debug

# Single file exe (slower, but just one file)
python build_exe.py --onefile
```

## ✅ What's Included

Your .exe will include:

✅ All input nodes (Image, Video, WebCam, RTSP)
✅ All process nodes (Blur, Brightness, Crop, etc.)
✅ All Deep Learning nodes
✅ **All ONNX object detection models** (YOLOX, YOLO, FreeYOLO, etc.)
✅ Face detection models
✅ Audio processing nodes
✅ All configuration files and fonts
✅ Complete Python runtime

## 🧪 Quick Test

After building, test ONNX object detection:

1. Run `dist\CV_Studio\CV_Studio.exe`
2. Add: Input → Image
3. Add: VisionModel → Object Detection
4. Select model: YOLOX nano
5. Add: Overlay → Draw Information
6. Add: Visual → Result Image
7. Connect: Image → Object Detection → Draw Information → Result Image
8. Load an image with objects
9. See detection results! ✅

## 📦 Distribution

To share your .exe:

```bash
# 1. Go to dist directory
cd dist

# 2. Create ZIP
tar -a -c -f CV_Studio.zip CV_Studio

# 3. Share the ZIP file
# Users just extract and run CV_Studio.exe
```

## 🔧 Common Issues & Fixes

| Problem | Solution |
|---------|----------|
| PyInstaller not found | `pip install pyinstaller` |
| Build fails | `python build_exe.py --clean` |
| Exe won't start | Run from cmd to see errors: `CV_Studio.exe --use_debug_print` |
| ONNX models missing | Check that `node/DLNode` folder exists in dist |
| DLL errors | Install VC++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe |

## 📏 Size Expectations

- Complete build: **~1 GB** (includes all models)
- Startup time: **5-10 seconds** (first launch)
- ONNX models: **~200-500 MB**

## 🎨 Customization

Edit `CV_Studio.spec` to:
- Add/remove modules
- Change exe name
- Add custom icon
- Hide console window
- Include/exclude specific files

## 🆘 Getting Help

1. Read `BUILD_EXE_GUIDE.md` for detailed instructions
2. Check PyInstaller docs: https://pyinstaller.org/
3. Open issue: https://github.com/hackolite/CV_Studio/issues

---

**That's it! Building a CV_Studio .exe is that easy.** 🎉
