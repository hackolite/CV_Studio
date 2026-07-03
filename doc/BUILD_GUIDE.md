# CV_Studio Build Guide

> **Unified Build System** - Clean, maintainable, cross-platform build process

## Quick Start

### Standard Build (Recommended)

```bash
# Clone the repository (if not already done)
git clone https://github.com/hackolite/CV_Studio.git
cd CV_Studio

# Build with GPU support (requires CUDA)
python build_unified.py --clean
```

### CPU-Only Build

```bash
# Build without CUDA dependency
python build_unified.py --clean --cpu
```

### CI/CD Build

```bash
# Assumes dependencies are pre-installed
python build_unified.py --clean --skip-checks
```

## Build Options

| Option | Description |
|--------|-------------|
| `--clean` | Clean build directories before building |
| `--cpu` | Use CPU-only dependencies (no CUDA required) |
| `--windowed` | Hide console window (GUI-only mode) |
| `--icon ICON` | Specify custom icon file (.ico) |
| `--skip-checks` | Skip dependency checks (for CI/CD) |
| `--help` | Show help message |

## Build Process Overview

The unified build script (`build_unified.py`) performs the following steps:

1. **Dependency Check** - Verifies Python version and required packages
2. **Cleanup** - Removes previous build artifacts (if `--clean` specified)
3. **Configuration** - Configures PyInstaller spec file with options
4. **Build** - Runs PyInstaller to create the executable
5. **Post-Build** - Applies directory structure fixes

## Output Structure

After a successful build, you'll find:

```
dist/CV_Studio/
├── CV_Studio.exe           # Main executable (Windows)
├── CV_Studio               # Main executable (Linux/macOS)
├── node/                   # Node implementations and ONNX models
├── node_editor/            # Node editor core, fonts, settings
├── src/                    # Source utilities
└── _internal/             # Python runtime and dependencies
```

## Prerequisites

### All Platforms

- **Python 3.7+** - Required for running the build script
- **Git** - For cloning the repository
- **Internet Connection** - For downloading dependencies

### Windows

- **Visual C++ Redistributable** - [Download here](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- **CUDA Toolkit** (optional) - Required only for GPU builds

### Linux

```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip python3-venv build-essential

# Fedora
sudo dnf install python3 python3-pip python3-virtualenv gcc gcc-c++ make
```

### macOS

```bash
# Install Homebrew first: https://brew.sh
brew install python3
```

## Build Modes

### GPU Build (Default)

Includes ONNX Runtime with CUDA support for GPU acceleration.

```bash
python build_unified.py --clean
```

**Requirements:**
- NVIDIA GPU with CUDA support
- CUDA Toolkit installed
- CUDNN installed

### CPU Build

Uses CPU-only ONNX Runtime, suitable for systems without NVIDIA GPUs.

```bash
python build_unified.py --clean --cpu
```

**Advantages:**
- No CUDA dependency
- Broader hardware compatibility
- Smaller executable size

**Trade-offs:**
- Slower inference for ML models
- No GPU acceleration

## Advanced Usage

### Custom Icon

```bash
python build_unified.py --clean --icon my_icon.ico
```

### GUI-Only Mode (No Console)

```bash
python build_unified.py --clean --windowed
```

**Note:** Without the console, you won't see error messages. Use this for production releases only.

### Combining Options

```bash
# CPU build with custom icon and no console
python build_unified.py --clean --cpu --windowed --icon cv_studio.ico
```

## Troubleshooting

### Build Fails: "Python 3.7+ required"

**Solution:** Upgrade your Python installation to 3.7 or higher.

```bash
python --version  # Check current version
# Download latest from: https://www.python.org/downloads/
```

### Build Fails: "Failed to install dependencies"

**Solution 1:** Update pip and retry

```bash
python -m pip install --upgrade pip setuptools wheel
python build_unified.py --clean
```

**Solution 2:** Install dependencies manually

```bash
pip install -r requirements.txt
python build_unified.py --clean --skip-checks
```

### Build Fails: "Spec file not found"

**Solution:** Ensure you're in the CV_Studio directory and `CV_Studio.spec` exists.

```bash
cd CV_Studio
ls CV_Studio.spec  # Should show the file
```

### Executable Doesn't Run: "CUDA not found"

**Solution:** Either install CUDA or rebuild with CPU mode.

```bash
# Option 1: Install CUDA Toolkit
# https://developer.nvidia.com/cuda-downloads

# Option 2: Rebuild for CPU
python build_unified.py --clean --cpu
```

### Executable Size is Large

**Explanation:** The executable includes all dependencies, Python runtime, and ONNX models.

**Tips to reduce size:**
- Use CPU build (smaller than GPU)
- Remove unused nodes before building
- Use UPX compression (already enabled)

### Missing DLLs on Windows

**Solution:** Install Visual C++ Redistributable

```bash
# Download and run:
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

## Development Workflow

### Testing Changes

1. Make your code changes
2. Test in development mode first:
   ```bash
   python main.py
   ```
3. Build and test the executable:
   ```bash
   python build_unified.py --clean
   cd dist/CV_Studio
   ./CV_Studio.exe  # or ./CV_Studio on Linux/macOS
   ```

### Incremental Builds

For faster iteration during development:

```bash
# First build (clean)
python build_unified.py --clean

# Subsequent builds (no clean)
python build_unified.py
```

**Note:** If you modify dependencies or the spec file, use `--clean`.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build CV_Studio

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Build executable
      run: python build_unified.py --clean --skip-checks
    
    - name: Upload artifact
      uses: actions/upload-artifact@v2
      with:
        name: cv-studio-${{ matrix.os }}
        path: dist/CV_Studio/
```

### Docker Build

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY . .

RUN apt-get update && \
    apt-get install -y build-essential && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

RUN python build_unified.py --clean --skip-checks --cpu

CMD ["dist/CV_Studio/CV_Studio"]
```

## Comparison with Legacy Build Scripts

| Feature | `build_unified.py` | `build.py` | `build_exe.py` | `build.sh` |
|---------|-------------------|-----------|---------------|-----------|
| Cross-platform | ✅ | ❌ (Win) | ✅ | ❌ (Linux) |
| CPU/GPU modes | ✅ | ❌ | ❌ | ✅ |
| Command-line args | ✅ | ❌ | ✅ | ✅ |
| Colored output | ✅ | ❌ | ❌ | ✅ |
| Clean output | ✅ | ✅ | ✅ | ✅ |
| CI/CD support | ✅ | ❌ | ✅ | ❌ |
| Single file | ✅ | ✅ | ✅ | ✅ |

## Migration Guide

If you're coming from the old build scripts:

### From `build.py`

```bash
# Old:
python build.py

# New:
python build_unified.py --clean
```

### From `build_exe.py`

```bash
# Old:
python build_exe.py --clean --skip-package-check

# New:
python build_unified.py --clean --skip-checks
```

### From `build.sh`

```bash
# Old:
./build.sh --cpu

# New:
python build_unified.py --clean --cpu
```

## Best Practices

1. **Always use `--clean` for release builds** - Ensures no stale artifacts
2. **Test in development mode first** - Catch errors before building
3. **Use CPU build for distribution** - Broader compatibility
4. **Keep the spec file in version control** - Maintains build reproducibility
5. **Test the built executable** - Don't assume it works without testing

## Support

- **Issues**: [GitHub Issues](https://github.com/hackolite/CV_Studio/issues)
- **Documentation**: [README.md](../README.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

CV_Studio is licensed under Apache License 2.0.
