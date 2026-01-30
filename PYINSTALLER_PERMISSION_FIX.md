# PyInstaller PermissionError Fix

## Problem

When building CV_Studio with PyInstaller on Windows, you may encounter a `PermissionError` like this:

```
PermissionError: [WinError 5] Accès refusé: 'C:\Users\...\CV_Studio\dist\CV_Studio\_internal\cv2\cv2.pyd'
```

This occurs when PyInstaller tries to clean the `dist` directory before building, but files are locked by:
- A running instance of CV_Studio.exe
- Windows Explorer browsing the dist folder
- Antivirus software scanning the files
- Previous build processes that didn't terminate properly

## Solution

This fix implements several mechanisms to handle file locking issues:

### 1. Process Detection (Proactive)
Before starting the build, the script checks if CV_Studio.exe is running:
- Automatically detects running processes on Windows
- Warns the user to close the application
- Prevents build issues before they occur

### 2. Retry Mechanism (Reactive)
When cleaning directories fails due to locked files:
- Retries up to 5 times with exponential backoff (0.5s, 1s, 2s, 4s, 8s)
- Waits for files to be released by the operating system
- Handles temporary locks automatically

### 3. Windows Read-Only Handler
Removes read-only attributes that can cause permission errors:
- Detects read-only files
- Changes file permissions to allow deletion
- Retries the operation after permission change

### 4. User Guidance
Provides clear instructions when issues occur:
- Explains what went wrong
- Lists steps to resolve the issue
- Offers option to continue or cancel

## Usage

### Automated Build Scripts

The fix is automatically applied when using the provided build scripts:

**Windows Batch Script:**
```batch
build_windows.bat
```

**Windows PowerShell Script:**
```powershell
powershell -ExecutionPolicy Bypass -File build_windows.ps1
```

**Python Build Script:**
```bash
python build_exe.py --clean
```

### Manual PyInstaller Build

If building manually with PyInstaller, ensure:
1. Close all CV_Studio.exe instances
2. Close Windows Explorer windows browsing the dist folder
3. Run the build command:
   ```bash
   pyinstaller CV_Studio.spec
   ```

## Troubleshooting

### Issue: Still getting PermissionError

**Solution:**
1. Open Task Manager (Ctrl+Shift+Esc)
2. Look for any CV_Studio.exe processes
3. End all CV_Studio.exe tasks
4. Navigate to the repository folder
5. Manually delete the `dist` and `build` folders
6. Retry the build

### Issue: Antivirus blocking file deletion

**Solution:**
1. Temporarily disable your antivirus real-time protection
2. Run the build script
3. Re-enable antivirus after build completes
4. Add the dist folder to antivirus exclusions for future builds

### Issue: Files still locked after closing CV_Studio.exe

**Solution:**
1. Wait 10-30 seconds for Windows to release file handles
2. If still locked, restart Windows Explorer:
   - Open Task Manager
   - Find "Windows Explorer"
   - Right-click → Restart
3. Retry the build

### Issue: Build fails in CI/CD environment

**Solution:**
The build script automatically detects non-interactive environments and attempts to continue. Ensure your CI/CD pipeline:
1. Doesn't have previous builds running
2. Cleans up properly between runs
3. Uses the `--skip-package-check` flag if packages are pre-installed

## Technical Details

### Code Changes

**File: `build_exe.py`**

1. **`check_running_processes()`**: Detects running CV_Studio.exe before build
2. **`remove_readonly()`**: Handles read-only file attributes
3. **`remove_directory_with_retry()`**: Implements retry logic with exponential backoff
4. **`clean_build_directories()`**: Enhanced with robust error handling

**File: `build_windows.bat`**

- Added CV_Studio.exe process check before build
- Enhanced error messages with troubleshooting steps

**File: `build_windows.ps1`**

- Added CV_Studio.exe process check before build
- Enhanced error messages with troubleshooting steps

### Why This Happens

Windows file locking is more aggressive than Unix-like systems:
1. **Executable Locking**: Running .exe files cannot be deleted
2. **DLL/PYD Locking**: Loaded libraries remain locked in memory
3. **Explorer Integration**: Windows Explorer can lock files for preview/thumbnail generation
4. **Antivirus Scanning**: Security software may hold files during scanning

### Best Practices

To avoid this issue in the future:
1. Always close CV_Studio.exe before rebuilding
2. Use the provided build scripts (they include these checks)
3. Close Windows Explorer windows in the dist folder
4. Allow a few seconds between closing the app and rebuilding
5. In CI/CD, ensure proper cleanup between runs

## Testing

The fix has been tested with:
- ✅ Running CV_Studio.exe instance (warns and aborts)
- ✅ Locked files with retry mechanism
- ✅ Read-only files
- ✅ Clean build (no previous dist folder)
- ✅ Interactive and non-interactive modes
- ✅ Windows 10/11

## References

- PyInstaller Issue: https://github.com/pyinstaller/pyinstaller/issues
- Windows File Locking: https://docs.microsoft.com/en-us/windows/win32/fileio/locking-and-unlocking-byte-ranges-in-files
- shutil.rmtree on Windows: https://docs.python.org/3/library/shutil.html#rmtree-example

## Related Issues

- Original error: `PermissionError: [WinError 5] Accès refusé`
- Affects: PyInstaller builds on Windows
- Fixed in: This PR
- Alternative: Use Linux/WSL for building (not affected by Windows file locking)
