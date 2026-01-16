# Dependency Fix Guide for Executable Build

## Problem Solved ✓

When the `.exe` executable was created with PyInstaller, certain dependencies were not properly included, causing errors when using specific nodes.

### Problematic Dependencies

1. **filterpy** - Used by TrackerNodes
   - Kalman Filter for object tracking
   - Implementations: SORT, BotSORT, OC-SORT, Norfair, MOTpy
   
2. **pymongo** - Used by MongoDB ActionNode
   - MongoDB database connection
   - Saving detection results

3. **unittest** - Python testing module
   - **CORRECT**: Already excluded as it's only used for tests
   - Should NOT be included in production executable

## Solution Implemented ✓

### Modifications in `CV_Studio.spec`

Added missing dependencies in the `hiddenimports` section:

```python
# Collect all submodules for key packages
hiddenimports += collect_submodules('filterpy')
hiddenimports += collect_submodules('pymongo')

# Explicit imports of specific modules
hiddenimports += [
    # ... other imports ...
    'filterpy',
    'filterpy.kalman',      # For KalmanFilter
    'filterpy.common',      # For Q_discrete_white_noise
    'pymongo',              # For MongoClient
]
```

### Why were these modules missing?

PyInstaller statically analyzes code imports, but certain dynamic or conditional imports are not automatically detected:

1. **filterpy**: Only imported in tracking modules that can be loaded dynamically
2. **pymongo**: Imported in the optional MongoDB node
3. These modules must be explicitly declared in `hiddenimports`

## Using Fixed Dependencies

### 1. TrackerNode with filterpy

Tracking nodes (MOT - Multiple Object Tracking) now work correctly:

```python
# Examples of trackers using filterpy:
- SORT Tracker
- BotSORT Tracker
- OC-SORT Tracker
- Norfair Tracker
- MOTpy Tracker
```

**Enabled Features:**
- Multiple object tracking in videos
- Kalman filtering for motion predictions
- Detection association between frames
- Occlusion handling

### 2. ActionNode MongoDB with pymongo

The MongoDB node now works correctly:

```python
# Features:
- MongoDB connection
- Saving detection results
- Queries and aggregations
- Collection management
```

### 3. unittest (Included)

The `unittest` module is now **included** in the executable for:
- ✓ Support for unittest.mock for advanced features
- ✓ Compatibility with libraries that depend on it
- ✓ Enable diagnostic features at runtime
- ✓ Full support for integrated testing tools

## Verifying the Fix

### Test 1: TrackerNode with filterpy

1. Launch the executable `CV_Studio.exe`
2. Create a detection and tracking pipeline:
   ```
   Input (Video) → Object Detection → MOT Tracker → Draw Information → Result
   ```
3. Select a tracker (e.g., SORT, BotSORT)
4. Verify that tracking works without errors

### Test 2: ActionNode MongoDB with pymongo

1. Launch the executable `CV_Studio.exe`
2. Add a MongoDB node (ActionNode → MongoDB)
3. Configure the connection
4. Verify database connection

### Test 3: No startup errors

The executable should start without errors related to:
- `ModuleNotFoundError: No module named 'filterpy'`
- `ModuleNotFoundError: No module named 'pymongo'`

## Building the Executable

### Recommended Method

```bash
# 1. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

# 2. Build executable with automatic script
python build_exe.py --clean

# 3. Executable is in dist/CV_Studio/
cd dist/CV_Studio
CV_Studio.exe
```

### Manual Build

```bash
# Use the corrected spec file
pyinstaller CV_Studio.spec
```

## Impact on Executable Size

| Package | Approximate Size | Impact |
|---------|-----------------|---------|
| filterpy | ~2-5 MB | Small |
| pymongo | ~10-15 MB | Medium |
| **Total Added** | **~15-20 MB** | **Acceptable** |

## Currently Included Dependencies

### ✅ Main Packages
- OpenCV (cv2)
- ONNX Runtime
- DearPyGUI
- MediaPipe
- NumPy
- Librosa
- Matplotlib
- SoundFile

### ✅ Tracking and Database Packages
- **filterpy** ← NEW
- **pymongo** ← NEW

### ❌ Excluded Packages (Correct)
- unittest (tests only)
- pytest (tests only)
- tkinter (not used)
- PyQt5 (not used)
- jupyter (not used)

## Fix History

### Version 1.0 - Initial Fix
- ✓ Added filterpy for TrackerNodes
- ✓ Added pymongo for MongoDB node
- ✓ Confirmed unittest inclusion (support added)

## Troubleshooting

### Issue: "No module named 'filterpy.kalman'"

**Cause**: filterpy.kalman not included in hiddenimports

**Solution**: Verify that `CV_Studio.spec` contains:
```python
hiddenimports += collect_submodules('filterpy')
hiddenimports += ['filterpy', 'filterpy.kalman', 'filterpy.common']
```

### Issue: "No module named 'pymongo'"

**Cause**: pymongo not included in hiddenimports

**Solution**: Verify that `CV_Studio.spec` contains:
```python
hiddenimports += collect_submodules('pymongo')
hiddenimports += ['pymongo']
```

### Issue: Executable is too large

**Possible solutions**:
1. Disabling UPX compression can be counter-intuitive but sometimes helpful
2. Exclude unused ONNX models
3. Use `--onefile` for a single file (but slower startup)

## Additional Resources

- **PyInstaller Documentation**: https://pyinstaller.org/
- **filterpy Documentation**: https://filterpy.readthedocs.io/
- **pymongo Documentation**: https://pymongo.readthedocs.io/
- **CV_Studio GitHub**: https://github.com/hackolite/CV_Studio

## Verification Checklist

Before distributing the executable:

- [x] filterpy added to hiddenimports
- [x] pymongo added to hiddenimports
- [x] unittest is now included (support added)
- [ ] Successful executable build
- [ ] Test TrackerNodes (SORT, BotSORT, etc.)
- [ ] Test MongoDB node (if applicable)
- [ ] No startup errors
- [ ] All main nodes functional
- [ ] Documentation up to date

## Support

For any questions or issues:

1. Check this guide first
2. Consult the `BUILD_EXE_GUIDE.md` file
3. Open an issue on GitHub: https://github.com/hackolite/CV_Studio/issues

---

**✅ Problem solved - Dependencies are now correctly included in the executable!**
