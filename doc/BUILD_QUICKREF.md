# CV_Studio Build - Quick Reference

> One-page cheat sheet for building CV_Studio executables

## Quick Commands

```bash
# Standard build (GPU)
python build_unified.py --clean

# CPU-only build
python build_unified.py --clean --cpu

# CI/CD build
python build_unified.py --clean --skip-checks

# GUI-only (no console)
python build_unified.py --clean --windowed

# With custom icon
python build_unified.py --clean --icon myicon.ico
```

## Options

| Option | Description |
|--------|-------------|
| `--clean` | Clean previous build artifacts |
| `--cpu` | CPU-only (no CUDA) |
| `--windowed` | Hide console window |
| `--icon FILE` | Custom icon file |
| `--skip-checks` | Skip dependency checks |

## Output

```
dist/CV_Studio/
├── CV_Studio.exe    # Executable
├── node/            # Nodes + models
├── node_editor/     # Core + settings
└── _internal/       # Dependencies
```

## Common Issues

### "Python 3.7+ required"
```bash
python --version  # Check version
# Upgrade if needed
```

### "Failed to install dependencies"
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### "CUDA not found" at runtime
```bash
# Rebuild for CPU
python build_unified.py --clean --cpu
```

### Missing DLLs (Windows)
Download: https://aka.ms/vs/17/release/vc_redist.x64.exe

## Build Comparison

| Script | Platform | Features |
|--------|----------|----------|
| `build_unified.py` | All | **Recommended** - Clean, modern, full-featured |
| `build.py` | Windows | Legacy - French output |
| `build_exe.py` | All | Legacy - Complex options |
| `build.sh` | Linux | Legacy - Bash script |

## Distribution

1. Build: `python build_unified.py --clean --cpu`
2. Test: `cd dist/CV_Studio && ./CV_Studio.exe`
3. Package: Zip the entire `dist/CV_Studio` folder
4. Share: Users extract and run the executable

## More Info

- **Full Guide**: [BUILD_GUIDE.md](BUILD_GUIDE.md)
- **Issues**: [GitHub Issues](https://github.com/hackolite/CV_Studio/issues)
- **README**: [README.md](../README.md)
