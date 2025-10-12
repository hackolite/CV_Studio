# Logging and GPU Support Improvements

## Overview

This document summarizes the improvements made to CV_Studio's logging system and GPU support detection.

## Changes Made

### 1. GPU Detection Utility (`src/utils/gpu_utils.py`)

Created a new utility module to detect and manage GPU support through ONNX Runtime:

**Key Functions:**
- `check_gpu_availability()`: Detects if CUDA GPU support is available
- `get_execution_providers(use_gpu)`: Returns appropriate execution providers based on GPU availability
- `log_gpu_info()`: Logs detailed GPU support information for diagnostics

**Features:**
- Automatically detects ONNX Runtime installation
- Checks for CUDA GPU provider availability
- Provides informative messages when GPU is not available
- Gracefully handles missing ONNX Runtime installation
- Suggests installation steps when GPU support is missing

### 2. Logging Improvements

Replaced all "wild" print statements with proper structured logging:

**Modified Files:**
- `main.py`: Main application startup and lifecycle logging
- `node_editor/node_editor.py`: Node editor operations and callbacks
- `node/DLNode/node_object_detection.py`: Object detection node operations
- `node/DLNode/node_pose_estimation.py`: Pose estimation node operations
- `node/DLNode/node_face_detection.py`: Face detection node operations
- `node/TrackerNode/node_mot.py`: Multi-object tracking operations

**Debug Prints Commented Out:**
- `node/DLNode/classification/EfficientNetB0/efficientnet.py`
- `node/DLNode/classification/MobileNetV3/mobilenet_v3.py`
- `node/DLNode/object_detection/YOLO/yolo.py`
- `node/DLNode/object_detection/TennisYOLO/yolotennis.py`
- `node/DLNode/object_detection/YOLOX/yolox.py`

### 3. Enhanced Logging Features

**Log Levels:**
- DEBUG: Detailed diagnostic information (connection details, node processing)
- INFO: General informational messages (startup, configuration, GPU detection)
- WARNING: Warning messages (unknown connection types, GPU unavailable)
- ERROR: Error messages with full stack traces

**GPU Integration:**
- Automatic GPU detection on startup when `use_gpu` is enabled in settings
- Detailed GPU information logged at application start
- Clear messages when GPU is requested but not available
- Fallback to CPU execution when GPU is unavailable

### 4. Testing

Created comprehensive tests for GPU detection:
- `tests/test_utils/test_gpu_utils.py`: 7 test cases covering all scenarios
  - GPU available (CUDA)
  - GPU not available (CPU only)
  - ONNX Runtime not installed
  - Provider selection with GPU enabled/disabled
  - Provider fallback when GPU requested but unavailable

All tests pass successfully.

## Usage

### Command Line

The application now respects the `--use_debug_print` flag for detailed logging:

```bash
# Normal logging (INFO level)
python main.py

# Debug logging (DEBUG level)
python main.py --use_debug_print
```

### GPU Detection

GPU support is automatically detected when the application starts if `use_gpu` is enabled in the settings:

```json
{
  "use_gpu": true
}
```

The application will:
1. Check if ONNX Runtime is installed
2. Check if CUDA GPU provider is available
3. Log detailed GPU information
4. Fall back to CPU if GPU is not available
5. Provide installation instructions if needed

### Log Output Examples

**GPU Available:**
```
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - ==================================================
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - GPU Support Information
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - ==================================================
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - Status: GPU support is available (CUDA)
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - Available providers: CUDAExecutionProvider, CPUExecutionProvider
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - ONNX Runtime version: 1.12.0
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - ==================================================
```

**GPU Not Available:**
```
2025-10-12 10:00:00,000 - src.utils.gpu_utils - WARNING - GPU support is not available. Only CPU execution will be used.
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - Available providers: CPUExecutionProvider
2025-10-12 10:00:00,000 - src.utils.gpu_utils - INFO - To enable GPU support, install onnxruntime-gpu and ensure CUDA is properly configured.
```

## Benefits

1. **Better Diagnostics**: Structured logging makes it easier to debug issues
2. **GPU Transparency**: Clear information about GPU availability and usage
3. **Production Ready**: Professional logging suitable for production deployments
4. **Maintainability**: Easier to track application behavior and troubleshoot
5. **User Friendly**: Clear messages guide users to resolve GPU configuration issues

## Migration Notes

- Third-party library code (motpy, norfair trackers) was left unchanged to avoid maintenance issues
- Existing logging infrastructure in `src/utils/logging.py` was utilized
- All changes are backward compatible
- No breaking changes to existing functionality

## Future Enhancements

Potential improvements for future consideration:
- Add logging to file by default with rotation
- Add performance metrics logging
- Add GPU memory usage monitoring
- Add support for other GPU providers (ROCm, DirectML, etc.)
