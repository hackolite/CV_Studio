# DearPyGui NodeZoomFork Installation Guide

CV_Studio now uses `dearpygui-nodezoomfork` instead of the standard `dearpygui` package. This fork adds zoom functionality for node editors.

## Installation

### macOS ARM64 (Apple Silicon)

The package is available on PyPI with pre-built wheels:

```bash
pip install dearpygui-nodezoomfork>=2.1.0
```

### Other Platforms (Linux, Windows, macOS Intel)

The PyPI package currently only provides pre-built wheels for macOS ARM64. For other platforms, you have two options:

#### Option 1: Install from GitHub Source (Requires Build Tools)

Prerequisites:
- CMake (>= 3.15)
- C++ compiler (GCC, Clang, or MSVC)
- Git

```bash
# Install build dependencies
pip install setuptools wheel

# Clone and install from source
git clone https://github.com/Maltergate/DearPyGui.git
cd DearPyGui
git submodule update --init --recursive
pip install .
```

#### Option 2: Use Standard DearPyGui (Fallback)

If you encounter issues with the fork, you can temporarily use the standard DearPyGui package:

```bash
pip install dearpygui>=2.0
```

Note: This will not include the node zoom functionality.

## Platform-Specific Notes

### Linux
Make sure you have the required system libraries:
```bash
# Ubuntu/Debian
sudo apt-get install build-essential cmake libgl1-mesa-dev libglu1-mesa-dev

# Fedora/RHEL
sudo dnf install gcc-c++ cmake mesa-libGL-devel mesa-libGLU-devel
```

### Windows
- Install Visual Studio 2019 or newer with C++ development tools
- Install CMake from https://cmake.org/download/

### macOS Intel
- Install Xcode Command Line Tools: `xcode-select --install`
- Install CMake via Homebrew: `brew install cmake`

## Troubleshooting

If you encounter installation issues:

1. Ensure all build tools are properly installed
2. Try updating pip: `pip install --upgrade pip setuptools wheel`
3. Check the [DearPyGui fork repository](https://github.com/Maltergate/DearPyGui) for latest updates
4. Open an issue in the CV_Studio repository with your platform details and error message

## Why This Fork?

The `dearpygui-nodezoomfork` adds zoom functionality to node editors, which improves usability when working with large node graphs in CV_Studio.

According to the fork's README:
> "This fork offers zoom in nodes until this is implemented in upstream package. Then this package will be deleted."

Once the zoom feature is merged into the main DearPyGui package, we will migrate back to the official package.
