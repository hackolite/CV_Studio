# PyInstaller Build Fix - Import Error Resolution

## Issue Description

When building CV_Studio with PyInstaller, the built executable failed with:
```
ModuleNotFoundError: No module named 'uuid'
```

This error occurred when running the built application from the `_internal` directory structure created by PyInstaller.

## Root Cause

The issue was **NOT** that the `uuid` module (or other standard library modules) were missing from the build. PyInstaller automatically includes all Python standard library modules.

The real problem was that **sys.path was not properly configured at runtime** to allow Python to find modules in the PyInstaller bundle structure.

## Solution

A PyInstaller runtime hook was created to properly configure `sys.path` when the frozen application starts.

### Files Modified

1. **hook-runtime-cv-studio.py** (NEW)
   - Runtime hook that configures sys.path when the application starts
   - Adds bundle directory and subdirectories to sys.path
   - Only activates when running as a frozen application

2. **CV_Studio.spec**
   - Added runtime hook configuration
   - Added hookspath configuration
   - Removed unnecessary standard library imports

3. **build_exe.py**
   - Updated spec file generation to include runtime hook
   - Removed unnecessary standard library imports from template

## How the Fix Works

### Before Fix
```
User runs CV_Studio.exe
  → PyInstaller bootloader starts
  → Python interpreter starts
  → sys.path does not include bundle subdirectories
  → Import node.basenode fails
  → Import uuid fails (not in sys.path)
  → Application crashes
```

### After Fix
```
User runs CV_Studio.exe
  → PyInstaller bootloader starts
  → Runtime hook executes (hook-runtime-cv-studio.py)
  → sys.path is configured with bundle directory and subdirectories
  → Python interpreter starts
  → Import node.basenode succeeds
  → Import uuid succeeds (standard library is in bundle)
  → Application runs successfully
```

## Technical Details

### The Runtime Hook

The runtime hook (`hook-runtime-cv-studio.py`) does the following:

1. **Detects frozen environment**: Checks if `sys.frozen` is set
2. **Gets bundle directory**: Uses `sys._MEIPASS` to find the bundle location
3. **Adds to sys.path**: Adds bundle directory and subdirectories in correct priority order:
   - Bundle directory (`sys._MEIPASS`)
   - `node/` directory
   - `node_editor/` directory  
   - `src/` directory

### Why This Works

PyInstaller creates this structure:
```
CV_Studio.exe
_internal/
  ├── Python312.dll (Python runtime with stdlib)
  ├── node/ (application code as data)
  ├── node_editor/ (application code as data)
  ├── src/ (application code as data)
  └── ... (other dependencies)
```

Without the runtime hook, Python doesn't know to look in the subdirectories for modules. The hook adds these directories to sys.path so imports work correctly.

## Building with the Fix

### Using build_exe.py (Recommended)
```bash
python build_exe.py --clean
```

### Using PyInstaller directly
```bash
pyinstaller CV_Studio.spec
```

Both methods will use the runtime hook automatically.

## Testing the Fix

After building:

1. Navigate to the build directory:
   ```bash
   cd dist/CV_Studio
   ```

2. Run the executable:
   ```bash
   CV_Studio.exe
   ```

3. The application should start without import errors

## Additional Notes

### What NOT to Do

❌ **Don't add standard library modules to hiddenimports**
- Standard library modules (uuid, json, os, sys, etc.) are automatically included by PyInstaller
- Adding them to hiddenimports is unnecessary and doesn't solve path issues

✅ **Do use runtime hooks for sys.path configuration**
- Runtime hooks execute before the application code
- They're the correct way to configure the runtime environment

### Debugging Import Issues

If you encounter import issues:

1. **Check if it's a standard library module**: If yes, the issue is likely sys.path related, not a missing module
2. **Check if it's a third-party module**: Add it to hiddenimports if PyInstaller can't detect it
3. **Use PyInstaller debug mode**: `pyinstaller --debug=all CV_Studio.spec` to see detailed import information

## References

- [PyInstaller Runtime Hooks Documentation](https://pyinstaller.org/en/stable/hooks.html#understanding-pyinstaller-hooks)
- [PyInstaller sys._MEIPASS](https://pyinstaller.org/en/stable/runtime-information.html)

## Summary

This fix resolves the `ModuleNotFoundError: No module named 'uuid'` issue by properly configuring sys.path at runtime using a PyInstaller runtime hook. The fix is minimal, follows PyInstaller best practices, and ensures all modules can be imported correctly in the frozen application.
