# PyInstaller Hooks for CV_Studio

This directory contains custom PyInstaller hooks to fix import issues in the built .exe file.

## Hooks Included

### hook-pytz.py
Fixes runtime import errors with the `pytz` timezone library.

**Problem:** Without this hook, pytz fails to load timezone data at runtime because PyInstaller doesn't automatically include the timezone database files.

**Solution:** Collects all pytz data files (timezone database) and submodules.

**Affected Node:** `node.ActionNode.node_mongodb` (uses pytz for UTC timezone handling)

### hook-lap.py
Fixes import errors with the `lap` (Linear Assignment Problem) package.

**Problem:** The `lap` package contains compiled C extensions (`.pyd` on Windows, `.so` on Linux) that PyInstaller doesn't automatically detect and include.

**Solution:** Collects all dynamic libraries (compiled C extensions) and submodules from lap.

**Affected Node:** `node.TrackerNode.mot.bytetrack.tracker.matching` (uses lap for object tracking)

### hook-PIL.py
Ensures PIL.ImageGrab and all PIL dependencies are properly included.

**Problem:** `PIL.ImageGrab` on Windows requires special handling and may fail if not explicitly included.

**Solution:** Explicitly collects all PIL submodules including ImageGrab and PIL data files.

**Affected Node:** `node.VideoNode.node_screen_capture` (uses PIL.ImageGrab for screen capture)

## Usage

These hooks are automatically used by PyInstaller when building with `CV_Studio.spec`:

```bash
pyinstaller CV_Studio.spec
```

Or when using the build script:

```bash
python build_exe.py
```

The `CV_Studio.spec` file references this hooks directory with: `hookspath=['hooks']`

## Testing

To verify the hooks work correctly after building:

1. Build the executable: `python build_exe.py --clean`
2. Run the built executable: `dist/CV_Studio/CV_Studio.exe`
3. Test nodes that use these imports:
   - MongoDB node (pytz)
   - ByteTrack tracker node (lap)
   - Screen Capture node (PIL.ImageGrab)

## Troubleshooting

If imports still fail after building:

1. Verify the hooks directory exists and is readable
2. Check that `CV_Studio.spec` has `hookspath=['hooks']`
3. Clean build artifacts and rebuild: `python build_exe.py --clean`
4. Check PyInstaller warnings during build for missing dependencies

## References

- PyInstaller Hooks Documentation: https://pyinstaller.org/en/stable/hooks.html
- pytz: https://pypi.org/project/pytz/
- lap: https://pypi.org/project/lap/
- Pillow: https://pypi.org/project/Pillow/
