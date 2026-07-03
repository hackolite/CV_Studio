# DearPyGui Installation Guide

CV_Studio uses the standard `dearpygui` package (version 2.0+) which includes built-in zoom functionality for node editors.

## Installation

The standard DearPyGui package is available on PyPI with pre-built wheels for all major platforms:

```bash
pip install dearpygui>=2.0.0
```

This package is included in the main `requirements.txt` file and will be installed automatically when you run:

```bash
pip install -r requirements.txt
```

## Platform Support

DearPyGui 2.0+ provides pre-built wheels for:
- **Windows** (x64)
- **Linux** (x64)
- **macOS** (Intel and Apple Silicon)

No compilation or build tools are required for installation on these platforms.

## Zoom Functionality

DearPyGui 2.0+ includes built-in zoom functionality for node editors and plots through the following functions:
- `set_axis_zoom_constraints()` - Set zoom constraints for plot axes
- `reset_axis_zoom_constraints()` - Reset zoom constraints to defaults
- Mouse wheel zoom support in node editors

## Troubleshooting

If you encounter installation issues:

1. Update pip: `pip install --upgrade pip setuptools wheel`
2. Check your Python version (Python 3.7+ is required)
3. Try installing DearPyGui separately: `pip install dearpygui>=2.0.0`
4. Check the [official DearPyGui repository](https://github.com/hoffstadt/DearPyGui) for known issues
5. Open an issue in the CV_Studio repository with your platform details and error message

## Previous NodeZoomFork

**Note:** CV_Studio previously used `dearpygui-nodezoomfork`, a fork that added zoom functionality. Since DearPyGui 2.0+ now includes this functionality in the main package, we have migrated back to the official DearPyGui package for better stability and compatibility.
