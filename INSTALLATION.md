# CV Studio - Clean Installation Guide

This guide provides step-by-step instructions for a clean installation of CV Studio.

## Prerequisites

- **Python 3.7 or later** (Python 3.8+ recommended)
- **pip** (usually comes with Python)
- **Git** (for cloning the repository)

## Quick Installation (Recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

### Step 2: Create a Virtual Environment (Recommended)

Using a virtual environment keeps your CV Studio dependencies isolated from other Python projects.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Run CV Studio

```bash
python main.py
```

## Troubleshooting

### Issue: `dearpygui-nodezoomfork` installation fails

**Solution:** The `dearpygui-nodezoomfork` package has been replaced with the standard `dearpygui` package. Make sure you have the latest version of `requirements.txt` that uses `dearpygui>=2.0.0` instead of `dearpygui-nodezoomfork>=2.1.0`.

If you still see an error, run:
```bash
pip uninstall dearpygui-nodezoomfork
pip install dearpygui>=2.0.0
```

### Issue: Build errors during installation

Some packages may require compilation. Install pre-built binary wheels only:

```bash
pip install --only-binary=:all: -r requirements.txt
```

If this fails for specific packages, you may need to install them individually or use a different version.

### Issue: OpenBLAS or other system dependencies not found

Some packages like `scipy` may require system libraries. 

**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install build-essential libopenblas-dev liblapack-dev
```

**On macOS:**
```bash
brew install openblas lapack
```

**On Windows:**
Use the pre-built wheels which should install without requiring these dependencies.

### Issue: Permission errors

If you see permission errors during installation:

1. **Use a virtual environment** (recommended - see Step 2 above)
2. **Or use user installation**: `pip install --user -r requirements.txt`
3. **Avoid using sudo/administrator** unless absolutely necessary

## Platform-Specific Notes

### Windows

For the best experience on Windows:

1. Install Python from [python.org](https://www.python.org/downloads/) (not from Microsoft Store)
2. During installation, check "Add Python to PATH"
3. Use PowerShell or Command Prompt
4. See [INSTALLATION_WINDOWS.md](INSTALLATION_WINDOWS.md) for detailed Windows instructions

### Linux

Most Linux distributions come with Python pre-installed. You may need to install:
```bash
sudo apt-get install python3 python3-pip python3-venv
```

### macOS

macOS comes with Python, but it's recommended to install Python 3 via [Homebrew](https://brew.sh/):
```bash
brew install python@3.11
```

## Verification

To verify your installation is working correctly:

```bash
# Test imports
python -c "import cv2; import dearpygui.dearpygui; import onnxruntime; print('All core dependencies imported successfully!')"

# Run the application
python main.py
```

## Clean Installation (Starting Fresh)

If you had a previous installation that's not working, here's how to start fresh:

### Step 1: Remove existing installation

```bash
# Deactivate virtual environment if active
deactivate

# Remove virtual environment directory
rm -rf venv  # Linux/macOS
rmdir /s venv  # Windows

# Navigate to the repository
cd CV_Studio

# Pull latest changes
git pull origin main
```

### Step 2: Follow Quick Installation steps

Follow the Quick Installation steps above starting from "Create a Virtual Environment".

## Dependencies Overview

CV Studio requires the following main dependencies:

- **numpy** - Numerical computing
- **opencv-contrib-python** - Computer vision algorithms  
- **onnxruntime** - ONNX model inference
- **dearpygui** - GUI framework with node editor
- **mediapipe** - Machine learning pipelines
- **protobuf** - Data serialization
- **filterpy** - Filtering algorithms for tracking
- **scipy** - Scientific computing
- **matplotlib** - Plotting and visualization
- **librosa** - Audio analysis
- **soundfile** - Audio file I/O
- **sounddevice** - Audio input/output

See [requirements.txt](requirements.txt) for the complete list.

## Alternative Installation Methods

### Method 1: Install from source

```bash
pip install git+https://github.com/hackolite/CV_Studio.git
```

### Method 2: Download executable (Windows only)

For Windows users who don't want to install Python, you can download a pre-built executable. See [HOW_TO_GET_EXE.md](HOW_TO_GET_EXE.md) for instructions.

## Getting Help

If you encounter issues not covered in this guide:

1. Check existing [GitHub Issues](https://github.com/hackolite/CV_Studio/issues)
2. See platform-specific guides:
   - [INSTALLATION_WINDOWS.md](INSTALLATION_WINDOWS.md) - Windows installation
   - [DEARPYGUI_NODEZOOMFORK_INSTALL.md](DEARPYGUI_NODEZOOMFORK_INSTALL.md) - DearPyGui details
3. Open a new issue with:
   - Your operating system and version
   - Python version (`python --version`)
   - Complete error message
   - Steps you've already tried

## Next Steps

After successful installation:

1. Read the [README.md](README.md) for an overview of features
2. Check [QUICKSTART.md](QUICKSTART.md) for a quick tutorial
3. Explore [examples/](examples/) for sample node configurations
4. Visit the [documentation](docs/) for detailed usage instructions

---

**Last Updated:** February 2026  
**Note:** This guide assumes you're using the latest version of CV Studio from the main branch.
