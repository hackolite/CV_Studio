# CV Studio Installation and Running Guide for Windows

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installing Python](#installing-python)
- [Installing CV Studio](#installing-cv-studio)
- [Running the Application](#running-the-application)
- [Verifying the Installation](#verifying-the-installation)
- [Troubleshooting](#troubleshooting)
- [Alternative: Windows Executable](#alternative-windows-executable)

## Overview

This guide explains how to install and run CV Studio on Windows for development and daily use. If you want to create a standalone executable (.exe), see [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md) or [HOW_TO_GET_EXE.md](HOW_TO_GET_EXE.md) instead.

## Prerequisites

### Minimum System Requirements

- **Operating System**: Windows 10 or later (64-bit recommended)
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk Space**: 5 GB free space
- **Processor**: Modern multi-core processor
- **GPU**: Optional but recommended for Deep Learning nodes (NVIDIA with CUDA support)

### Required Software

1. **Python 3.7 or later** (3.10 or 3.11 recommended)
   - Python 3.7 is supported, but Python 3.8+ is recommended for optimal experience and better compatibility with recent DearPyGUI versions
2. **Git for Windows** (optional but recommended)
3. **Microsoft Visual C++ Redistributable** (usually already installed)

## Installing Python

### Method 1: Install from python.org (RECOMMENDED)

1. **Download Python** from the official website:
   - Go to [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Download the latest Python 3.11 or 3.10 version for Windows (or Python 3.8+ for best experience)

2. **Run the installer**:
   - ⚠️ **IMPORTANT**: Check "Add Python to PATH" at the bottom of the window
   - Click "Install Now"
   - Wait for the installation to complete

3. **Verify the installation**:
   ```cmd
   python --version
   ```
   You should see something like `Python 3.11.x` or `Python 3.10.x`

   If the `python` command doesn't work, try:
   ```cmd
   python3 --version
   ```
   or
   ```cmd
   py --version
   ```

### Method 2: Install via Microsoft Store

1. Open the **Microsoft Store**
2. Search for "Python"
3. Install **Python 3.11** or **Python 3.10**
4. Python will be automatically added to PATH

## Installing CV Studio

### Step 1: Open Command Prompt (PowerShell or CMD)

**Option A - PowerShell (Recommended)**:
- Press `Windows + X`
- Select "Windows PowerShell" or "Terminal"

**Option B - Command Prompt**:
- Press `Windows + R`
- Type `cmd` and press Enter

### Step 2: Clone the Repository

If you have **Git installed**:

```cmd
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio
```

If you **don't have Git**:

1. Go to [https://github.com/hackolite/CV_Studio](https://github.com/hackolite/CV_Studio)
2. Click the green "Code" button → "Download ZIP"
3. Extract the ZIP file to a folder of your choice
4. Open Command Prompt in that folder:
   - In Windows Explorer, hold `Shift` + right-click in the folder
   - Select "Open PowerShell window here" or "Open command window here"

### Step 3: Create a Virtual Environment (Recommended)

A virtual environment isolates CV Studio's dependencies:

```cmd
python -m venv venv
```

If the `python` command doesn't work, try `python3` or `py`:
```cmd
python3 -m venv venv
```
or
```cmd
py -m venv venv
```

### Step 4: Activate the Virtual Environment

**In PowerShell**:
```powershell
.\venv\Scripts\Activate.ps1
```

If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then try activating again.

**In CMD**:
```cmd
venv\Scripts\activate.bat
```

You should see `(venv)` appear at the beginning of your command line.

### Step 5: Update pip

```cmd
python -m pip install --upgrade pip
```

### Step 6: Install Dependencies

```cmd
pip install -r requirements.txt
```

This command will install all necessary libraries:
- OpenCV for image processing
- DearPyGUI for the graphical interface
- ONNX Runtime for Deep Learning models
- MediaPipe for ML models
- And other dependencies

⏱️ **Installation may take 5-10 minutes** depending on your Internet connection.

## Running the Application

Once installation is complete, you can launch CV Studio:

### Standard Method

```cmd
python main.py
```

### With Debug Options

```cmd
# Enable debug messages
python main.py --use_debug_print

# Disable asynchronous drawing (if display issues occur)
python main.py --unuse_async_draw

# Use a custom configuration file
python main.py --setting path\to\config.json

# Combine multiple options
python main.py --use_debug_print --unuse_async_draw
```

### Each Time You Want to Use CV Studio

1. Open Command Prompt in the CV_Studio folder
2. Activate the virtual environment:
   - PowerShell: `.\venv\Scripts\Activate.ps1`
   - CMD: `venv\Scripts\activate.bat`
3. Launch the application: `python main.py`

## Verifying the Installation

### Quick Test

Once the application is running:

1. **The GUI should open** with an empty workspace
2. **Add an Image node**:
   - Click the "Input" menu → "Image"
   - Click on the workspace to place the node
3. **Add a Result Image node**:
   - Click the "Visual" menu → "Result Image"
   - Place it next to the first node
4. **Connect the nodes**:
   - Drag from the Image node's output to the Result Image node's input
5. **Load an image**:
   - Click "Select Image" in the Image node
   - Select an image from your computer
   - The image should display in the Result Image node

✅ If everything works, your installation is successful!

## Troubleshooting

### Problem: "python is not recognized..."

**Solution 1**: Try `python3` or `py` instead of `python`

**Solution 2**: Reinstall Python and check "Add Python to PATH"

**Solution 3**: Manually add Python to PATH:
1. Search for "Environment Variables" in the Start menu
2. Click "Environment Variables"
3. In "System variables", find "Path" and click "Edit"
4. Add the path to Python (e.g., `C:\Users\YourName\AppData\Local\Programs\Python\Python311`)
5. Also add `C:\Users\YourName\AppData\Local\Programs\Python\Python311\Scripts`
6. Restart Command Prompt

### Problem: Error during dependency installation

**Error with opencv-python**:
```cmd
pip install --upgrade pip setuptools wheel
pip install opencv-python
```

**Error with dearpygui**:
- Make sure you're using 64-bit Python
- Try: `pip install dearpygui==1.11.0`

**Error "Microsoft Visual C++ 14.0 is required"**:
1. Download and install [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
2. Restart dependency installation

### Problem: Application crashes on startup

**Solution 1**: Disable asynchronous drawing
```cmd
python main.py --unuse_async_draw
```

**Solution 2**: Check your graphics card drivers
- Update drivers from the manufacturer's website (NVIDIA, AMD, Intel)

**Solution 3**: Try with debug logs
```cmd
python main.py --use_debug_print
```
Error messages will help you identify the problem.

### Problem: Webcam not detected

**Solutions**:
1. Close all applications using the webcam (Zoom, Teams, Skype, etc.)
2. Check camera permissions in Windows:
   - Settings → Privacy → Camera
   - Enable "Allow desktop apps to access your camera"
3. Try different device numbers in the WebCam node (0, 1, 2...)

### Problem: "Cannot connect to GPU" error

If you don't have an NVIDIA GPU or CUDA:
1. This is normal, Deep Learning nodes will use CPU
2. Simply uncheck the "GPU" option in Deep Learning nodes
3. Processing will be slower but functional

If you have an NVIDIA GPU:
1. Install [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads)
2. Install onnxruntime-gpu: `pip install onnxruntime-gpu`
3. Verify that your NVIDIA drivers are up to date

### Problem: PowerShell execution policy error

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: Application is slow

**Solutions**:
1. Add a **Resize** node at the beginning of your pipeline to reduce resolution
2. Disable resource-intensive nodes with an **ON/OFF Switch** node
3. Enable GPU for Deep Learning nodes (if available)
4. Reduce FPS rate in video/webcam nodes

### Problem: "Module not found" after installation

**Solution**:
1. Verify the virtual environment is activated (you should see `(venv)`)
2. Reinstall dependencies:
   ```cmd
   pip install -r requirements.txt --force-reinstall
   ```

## Alternative: Windows Executable

If you don't want to install Python and prefer a standalone executable:

### Option 1: Download a Pre-compiled Executable

See [HOW_TO_GET_EXE.md](HOW_TO_GET_EXE.md) to get an executable via GitHub Actions.

### Option 2: Build Your Own Executable

See [BUILD_EXE_GUIDE.md](BUILD_EXE_GUIDE.md) to create your own .exe file.

**Advantages of the executable**:
- ✅ No need to install Python
- ✅ Portable (can be copied to a USB drive)
- ✅ Simpler for end users

**Advantages of Python installation**:
- ✅ Easier for development
- ✅ Instant code modifications
- ✅ Less disk space used
- ✅ Faster updates

## 💡 Tips for Optimal Use on Windows

### Performance

1. **Close unnecessary applications** to free up RAM
2. **Use an SSD** for better I/O performance
3. **Enable GPU** if you have a CUDA-compatible NVIDIA card
4. **Adjust resolution** of images/videos for faster processing

### Organization

1. **Create a shortcut**:
   - Create a `launchCV_Studio.bat` file with the content:
     ```batch
     @echo off
     REM Navigate to script directory
     cd /d "%~dp0"
     REM Activate virtual environment
     call venv\Scripts\activate.bat
     if %errorlevel% neq 0 (
         echo Error: Unable to activate virtual environment
         echo Make sure the venv folder exists
         pause
         exit /b 1
     )
     REM Start CV Studio
     python main.py
     pause
     ```
   - Double-click this file to launch CV Studio directly

2. **Save your configurations**:
   - Use the Export function to save your pipelines
   - Create a `my_projects` folder for your JSON files

### Security

1. **Antivirus**: If your antivirus blocks the application:
   - Add the CV_Studio folder to exceptions
   - This is a common false positive with Python applications

2. **Firewall**: If you're using RTSP streams or external servers:
   - Allow Python in Windows Firewall

## 📚 Additional Resources

- **Main README**: [README.md](README.md) - Complete project documentation
- **Usage Guide**: See the "Usage" section in [README.md](README.md)
- **Examples**: [examples/](examples/) folder for code examples
- **Available Nodes**: Complete list in [README.md](README.md)
- **Tests**: [tests/](tests/) for unit tests

## 🆘 Support

If you encounter problems not covered by this guide:

1. **Check GitHub Issues**: [https://github.com/hackolite/CV_Studio/issues](https://github.com/hackolite/CV_Studio/issues)
2. **Open a new Issue**: Describe your problem with:
   - Your Windows version
   - Your Python version
   - The complete error message
   - Steps to reproduce the problem
3. **Discussions**: [https://github.com/hackolite/CV_Studio/discussions](https://github.com/hackolite/CV_Studio/discussions)

---

**Happy developing with CV Studio! 🎉**
