# Building CV_Studio.exe for Windows

## Quick Start

To build CV_Studio.exe, simply run:

```batch
build_simple.bat
```

This will:
1. Install/update PyInstaller
2. Clean previous build artifacts
3. Build the executable using the `internal/` directory structure

## Output

The executable will be created at: `dist\CV_Studio\CV_Studio.exe`

You can copy the entire `dist\CV_Studio\` folder to any location and run `CV_Studio.exe` from there.

## Structure

The project is organized as follows:

```
CV_Studio/
├── internal/           # All source code
│   ├── main.py        # Main entry point
│   ├── src/           # Core utilities
│   ├── node/          # Node implementations
│   └── node_editor/   # Node editor UI
├── CV_Studio_new.spec # PyInstaller specification
├── build_simple.bat   # Build script for Windows
└── dist/              # Build output (after running build_simple.bat)
    └── CV_Studio/
        └── CV_Studio.exe
```

## Requirements

- Python 3.7+
- PyInstaller (automatically installed by build_simple.bat)
- All dependencies listed in `requirements.txt`

## Troubleshooting

### Import Errors

If you encounter import errors when running the .exe, make sure:
- The `internal/` directory structure is intact
- All Python files are in the correct subdirectories
- The spec file correctly references the internal path

### Missing Files

If the .exe complains about missing files (like .onnx models or configuration files), ensure that:
- The `CV_Studio_new.spec` file includes all necessary data directories
- The `node_editor/setting/setting.json` file exists

### Build Fails

If PyInstaller build fails:
1. Check Python version (must be 3.7+)
2. Try cleaning build artifacts: `rmdir /s /q build dist`
3. Reinstall PyInstaller: `pip install pyinstaller --upgrade --force-reinstall`
4. Check the build log for specific errors
