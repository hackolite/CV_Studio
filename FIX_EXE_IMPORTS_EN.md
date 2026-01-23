# Fix for Import Issues in .exe Executable

## Problem Solved

After building the .exe executable with PyInstaller, the following errors occurred:

1. **pytz** - `ModuleNotFoundError: No module named 'pytz'`
2. **lap** - `ModuleNotFoundError: No module named 'lap'` or runtime errors
3. **PIL.ImageGrab** - Errors when using screen capture functionality

## Root Cause

PyInstaller doesn't automatically detect certain special dependencies:

- **pytz**: Timezone data files are not automatically included
- **lap**: Compiled C extensions (.pyd/.so) are not detected
- **PIL.ImageGrab**: Requires explicit inclusion, especially on Windows

## Implemented Solution

### 1. Custom PyInstaller Hooks

Three hooks were created in the `hooks/` directory:

#### `hooks/hook-pytz.py`
Collects pytz timezone data files and all its submodules.

**Affected Node:** `node.ActionNode.node_mongodb` (uses pytz for UTC timezone handling)

#### `hooks/hook-lap.py`
Collects dynamic libraries (compiled C extensions) and submodules of lap.

**Affected Node:** `node.TrackerNode.mot.bytetrack.tracker.matching` (uses lap for object tracking)

#### `hooks/hook-PIL.py`
Ensures PIL.ImageGrab and all PIL dependencies are properly included.

**Affected Node:** `node.VideoNode.node_screen_capture` (uses PIL.ImageGrab for screen capture)

### 2. CV_Studio.spec Modifications

The following changes were made:

```python
# Add data files for pytz and PIL
datas += collect_data_files('pytz')  # CRITICAL for pytz
datas += collect_data_files('PIL')

# Add compiled binaries for lap
from PyInstaller.utils.hooks import collect_dynamic_libs
binaries = []
binaries += collect_dynamic_libs('lap')  # CRITICAL for lap

# Use hooks directory
a = Analysis(
    ...
    hookspath=['hooks'],  # Use custom hooks
    ...
)
```

### 3. build_exe.py Modifications

The same modifications were applied to the build script to ensure consistency.

## How to Use

### Standard Build
```bash
python build_exe.py --clean
```

### Build with PyInstaller Directly
```bash
pyinstaller CV_Studio.spec
```

### Test Critical Imports
```bash
python test_critical_imports.py
```

## Verification After Build

1. **Build the executable**
   ```bash
   python build_exe.py --clean
   ```

2. **Run the exe**
   ```bash
   cd dist/CV_Studio
   CV_Studio.exe
   ```

3. **Test problematic nodes**
   - MongoDB node (tests pytz)
   - ByteTrack tracker node (tests lap)
   - Screen Capture node (tests PIL.ImageGrab)

## Added File Structure

```
CV_Studio/
├── hooks/
│   ├── README.md           # Hooks documentation
│   ├── hook-pytz.py        # Hook for pytz
│   ├── hook-lap.py         # Hook for lap
│   └── hook-PIL.py         # Hook for PIL/Pillow
├── test_critical_imports.py # Import test script
├── CV_Studio.spec          # Modified
└── build_exe.py            # Modified
```

## Troubleshooting

### If imports still fail after build

1. **Clean and rebuild**
   ```bash
   python build_exe.py --clean
   ```

2. **Check PyInstaller warnings**
   During build, look for warnings about pytz, lap, or PIL

3. **Verify hooks directory exists**
   ```bash
   ls -la hooks/
   ```

4. **Install all dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Common Error Messages and Solutions

#### `ModuleNotFoundError: No module named 'pytz'`
- **Solution**: The pytz hook wasn't used. Verify that `hookspath=['hooks']` is in the spec.

#### `ModuleNotFoundError: No module named 'lap'` or runtime crash
- **Solution**: lap C extensions are not included. Check `collect_dynamic_libs('lap')`.

#### `ImportError: cannot import name 'ImageGrab'`
- **Solution**: PIL.ImageGrab is unavailable or misconfigured. Check the PIL hook.

## Technical References

- **PyInstaller Hooks**: https://pyinstaller.org/en/stable/hooks.html
- **pytz**: https://pypi.org/project/pytz/
- **lap**: https://pypi.org/project/lap/
- **Pillow**: https://pypi.org/project/Pillow/

## Changelog

### Current Version
- ✅ Added PyInstaller hooks for pytz, lap, and PIL
- ✅ Updated CV_Studio.spec with hookspath and data collections
- ✅ Updated build_exe.py for consistency
- ✅ Added test_critical_imports.py test script
- ✅ Complete documentation of fixes

## Support

If you still encounter issues after applying these fixes:

1. Run `python test_critical_imports.py` before building
2. Check PyInstaller warnings during build
3. Open a GitHub issue with complete error logs
