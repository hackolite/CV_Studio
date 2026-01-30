# Build Scripts Comparison

This document clarifies the different build scripts available in CV_Studio and which one to use.

## Available Build Scripts

### ✅ Recommended: `build_exe.py`

**Full-featured build script with command-line options**

```bash
python build_exe.py --clean
```

**Features:**
- ✅ Command-line arguments (`--clean`, `--windowed`, `--onefile`, etc.)
- ✅ Package verification and dependency checking
- ✅ Comprehensive error handling and user feedback
- ✅ Uses `CV_Studio.spec` for complete configuration
- ✅ Includes all hidden imports (cv2, onnxruntime, mediapipe, etc.)
- ✅ Includes all ONNX models and data files
- ✅ Runtime hooks for proper path management
- ✅ Creates README documentation for end users

**Usage:**
```bash
python build_exe.py                  # Standard build
python build_exe.py --clean          # Clean build
python build_exe.py --windowed       # No console window
python build_exe.py --debug          # Debug mode
```

**Output:** `dist/CV_Studio/CV_Studio.exe`

---

### ✅ Alternative: `build.py`

**Simplified build script with French output**

```bash
python build.py
```

**Features:**
- ✅ Simple, straightforward script
- ✅ French language console output
- ✅ Uses `CV_Studio.spec` for complete configuration
- ✅ Includes all hidden imports (cv2, onnxruntime, mediapipe, etc.)
- ✅ Automatic cleanup of build artifacts
- ✅ Clear step-by-step progress display

**Usage:**
```bash
python build.py
```

**Output:** `dist/CV_Studio/CV_Studio.exe`

---

## Key Difference

**Both scripts now use the same `CV_Studio.spec` configuration file**, which ensures:
- All Python modules are included (cv2, numpy, onnxruntime, etc.)
- All hidden imports are properly configured
- All data files (ONNX models, fonts, settings) are bundled
- Runtime hooks are properly applied

The main differences are:
- **build_exe.py**: More command-line options, English output, creates user documentation
- **build.py**: Simpler interface, French output, focused on core build process

## Common Issue Fixed

### Problem: `ModuleNotFoundError: No module named 'cv2'`

**Cause:** This error occurred when cv2 (OpenCV) and other dependencies were not included as hidden imports in the PyInstaller build.

**Solution:** Both `build.py` and `build_exe.py` now use `CV_Studio.spec`, which includes comprehensive hidden imports:

```python
hiddenimports += collect_submodules('cv2')
hiddenimports += collect_submodules('onnxruntime')
hiddenimports += collect_submodules('mediapipe')
hiddenimports += collect_submodules('numpy')
# ... and many more
```

## Which Script Should I Use?

| Scenario | Recommended Script |
|----------|-------------------|
| **First time building** | `build_exe.py --clean` |
| **Need command-line options** | `build_exe.py` |
| **Prefer French output** | `build.py` |
| **CI/CD automation** | `build_exe.py --skip-package-check` |
| **Quick rebuild** | Either script works |
| **Need debug build** | `build_exe.py --debug` |
| **Single file exe** | `build_exe.py --onefile` |

## Direct PyInstaller Usage

You can also build directly with PyInstaller:

```bash
pyinstaller CV_Studio.spec
```

This gives you the most control but requires manual cleanup of build artifacts.

## Troubleshooting

### If you get `ModuleNotFoundError` in the built exe:

1. Verify that `CV_Studio.spec` exists in your project directory
2. Check that `CV_Studio.spec` includes the missing module in `hiddenimports`
3. Rebuild using either `build.py` or `build_exe.py --clean`
4. If the issue persists, add the module manually to `CV_Studio.spec`:
   ```python
   hiddenimports += collect_submodules('your_missing_module')
   ```

### If the build fails:

1. Ensure PyInstaller is installed: `pip install pyinstaller`
2. Install all dependencies: `pip install -r requirements.txt`
3. Clean build artifacts: `build_exe.py --clean` or delete `build/` and `dist/` manually
4. Check Python version: Python 3.7+ is required

## More Information

- **Full build guide**: See `BUILD_EXE_GUIDE.md` or `BUILD_EXE_GUIDE_FR.md`
- **Quick reference**: See `BUILD_EXE_QUICKREF.md`
- **PyInstaller spec**: See `CV_Studio.spec` for the complete configuration
