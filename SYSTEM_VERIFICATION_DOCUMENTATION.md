# System Verification Documentation

## Overview

CV Studio includes an automatic system verification module that checks for required dependencies and programs at startup. This helps identify missing or misconfigured components before they cause runtime errors.

## What is Verified

The system verification checks:

### 1. FFmpeg Installation
- ✅ Detects if FFmpeg is installed and accessible
- ✅ Verifies FFmpeg can be executed
- ✅ Extracts and logs version information
- ⚠️ Warns if FFmpeg is missing (video encoding will not work)

### 2. Python Packages
Checks for essential packages:
- `opencv-contrib-python` (cv2)
- `numpy`
- `dearpygui`
- `ffmpeg-python`
- `soundfile`
- `sounddevice`
- `librosa`

### 3. OpenCV Modules
Verifies OpenCV has required capabilities:
- DNN module (for deep learning models)
- VideoCapture (for camera/video input)
- VideoWriter (for video output)

## Automatic Verification

System verification runs automatically when CV Studio starts:

```python
# In main.py
logger.info("Running system verification...")
verification_passed = run_system_verification()
```

## Verification Results

Results are logged to both console and log file:

```
============================================================
SYSTEM VERIFICATION RESULTS
============================================================
[OK        ] FFmpeg: FFmpeg is installed and working
  Details: ffmpeg version 4.4.2-0ubuntu0.22.04.1
[OK        ] Package: opencv-contrib-python is installed
[OK        ] Package: numpy is installed
[OK        ] Package: dearpygui is installed
[OK        ] Package: ffmpeg-python is installed
[WARNING   ] Package: soundfile not found
  Details: Install with: pip install soundfile
[OK        ] Package: sounddevice is installed
[OK        ] Package: librosa is installed
[OK        ] OpenCV: OpenCV 4.8.0 with required modules
  Details: DNN: True, Video: True, Writer: True
============================================================
Summary - OK: 8, Warnings: 1, Errors: 0, Not Found: 0
============================================================
```

## Verification Status Levels

| Status | Icon | Description | Impact |
|--------|------|-------------|--------|
| OK | ✅ | Component is installed and working | None - all features available |
| WARNING | ⚠️ | Component is missing but not critical | Some features may not work |
| ERROR | ❌ | Critical component has issues | Major features will not work |
| NOT_FOUND | ⚠️ | Component is not installed | Dependent features unavailable |

## Manual Verification

You can run verification manually:

```python
from src.utils.system_verification import run_system_verification

# Run verification and get status
success = run_system_verification()
if not success:
    print("Some critical components are missing!")
```

### Using the Verifier Class

For more control, use the `SystemVerifier` class directly:

```python
from src.utils.system_verification import SystemVerifier

# Create verifier
verifier = SystemVerifier()

# Run all checks
verifier.verify_all()

# Get results
results = verifier.get_results()
for result in results:
    print(f"{result.status.value}: {result.component}")
    print(f"  {result.message}")
    if result.details:
        print(f"  Details: {result.details}")

# Get summary
summary = verifier.get_summary()
print(f"OK: {summary['ok']}, Warnings: {summary['warning']}")
```

## Individual Checks

You can run specific verification checks:

### Check FFmpeg Only

```python
from src.utils.system_verification import SystemVerifier

verifier = SystemVerifier()
result = verifier.verify_ffmpeg()

if result.status == VerificationStatus.OK:
    print("FFmpeg is working!")
else:
    print(f"FFmpeg issue: {result.message}")
```

### Check Python Packages Only

```python
verifier = SystemVerifier()
results = verifier.verify_python_packages()

for result in results:
    if result.status != VerificationStatus.OK:
        print(f"{result.component}: {result.message}")
```

### Check OpenCV Only

```python
verifier = SystemVerifier()
result = verifier.verify_opencv()

print(f"OpenCV: {result.message}")
print(f"Details: {result.details}")
```

## Common Issues and Solutions

### FFmpeg Not Found

**Symptom:**
```
[NOT_FOUND ] FFmpeg: FFmpeg not found in PATH
  Details: Please install FFmpeg: https://ffmpeg.org/download.html
```

**Solution:**

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract to a folder
3. Add the `bin` folder to your PATH

**Verify Installation:**
```bash
ffmpeg -version
```

### Missing Python Packages

**Symptom:**
```
[WARNING   ] Package: soundfile not found
  Details: Install with: pip install soundfile
```

**Solution:**
```bash
# Install single package
pip install soundfile

# Install all requirements
pip install -r requirements.txt
```

### OpenCV Missing Modules

**Symptom:**
```
[WARNING   ] OpenCV: OpenCV 4.8.0 missing some modules
  Details: DNN: False, Video: True, Writer: True
```

**Solution:**
```bash
# Uninstall standard opencv
pip uninstall opencv-python

# Install opencv-contrib-python (includes all modules)
pip install opencv-contrib-python
```

## Extending Verification

### Adding New Checks

You can extend `SystemVerifier` to add custom checks:

```python
from src.utils.system_verification import SystemVerifier, VerificationResult, VerificationStatus

class CustomVerifier(SystemVerifier):
    def verify_custom_tool(self):
        """Verify custom tool is installed"""
        try:
            # Your verification logic here
            result = subprocess.run(['custom-tool', '--version'], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                return VerificationResult(
                    component="CustomTool",
                    status=VerificationStatus.OK,
                    message="Custom tool is installed",
                    details=result.stdout.strip()
                )
        except FileNotFoundError:
            return VerificationResult(
                component="CustomTool",
                status=VerificationStatus.NOT_FOUND,
                message="Custom tool not found",
                details="Install from: https://example.com"
            )
```

## Verification in CI/CD

Use verification in automated testing:

```python
import sys
from src.utils.system_verification import run_system_verification

if __name__ == "__main__":
    # Run verification
    success = run_system_verification()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)
```

```bash
# In CI script
python -c "from src.utils.system_verification import run_system_verification; import sys; sys.exit(0 if run_system_verification() else 1)"
```

## Configuration

### Disabling Verification

To skip verification at startup (not recommended):

```python
# In main.py, comment out or remove:
# verification_passed = run_system_verification()
```

### Custom Verification Requirements

Edit `src/utils/system_verification.py` to modify:

```python
# Required packages
required_packages = [
    ('cv2', 'opencv-contrib-python'),
    ('numpy', 'numpy'),
    # Add your packages here
]
```

## Best Practices

### 1. Always Run at Startup
Keep system verification enabled to catch issues early.

### 2. Review Warnings
Even if verification passes, review warnings:
```python
if not verification_passed:
    logger.warning("System verification detected issues")
```

### 3. Document Dependencies
Update `requirements.txt` when adding new dependencies:
```bash
pip freeze > requirements.txt
```

### 4. Test in Clean Environment
Verify your application works in a fresh environment:
```bash
# Create virtual environment
python -m venv test_env
source test_env/bin/activate

# Install requirements
pip install -r requirements.txt

# Run verification
python -c "from src.utils.system_verification import run_system_verification; run_system_verification()"
```

## Troubleshooting

### Verification Hangs

If verification seems to hang:
- Check if FFmpeg is prompting for input
- Increase timeout in `verify_ffmpeg()`:
  ```python
  result = subprocess.run(['ffmpeg', '-version'], 
                         capture_output=True, text=True, 
                         timeout=10)  # Increase from 5
  ```

### False Positives

If verification incorrectly reports issues:
1. Check import names match package names
2. Verify PATH environment variable
3. Try importing packages manually in Python shell

### Permission Issues

On Linux/macOS, ensure FFmpeg is executable:
```bash
chmod +x $(which ffmpeg)
```

## Summary

System verification:
- ✅ Automatically checks dependencies at startup
- ✅ Detects FFmpeg installation and version
- ✅ Verifies Python packages
- ✅ Validates OpenCV capabilities
- ✅ Provides clear error messages with solutions
- ✅ Logs all results for debugging
- ✅ Returns success/failure status

For more information:
- `src/utils/system_verification.py` - Implementation
- `tests/test_system_verification.py` - Test suite
- `LOGGING_SYSTEM_DOCUMENTATION.md` - Related logging features
