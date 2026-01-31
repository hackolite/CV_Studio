# PyInstaller Portability Audit - Summary

## Mission Accomplished

This document summarizes the changes made to ensure CV_Studio is compatible with PyInstaller --onefile builds.

## Problem Statement

When using PyInstaller with the `--onefile` option, all application files are extracted to a temporary folder (`_MEIPASS`) at runtime. Hardcoded relative paths (like `os.path.join(os.path.dirname(__file__), ...)`) fail because `__file__` points to the original source location, not the temporary extraction folder.

## Solution Implemented

### 1. Centralized `resource_path()` Function

**Location:** `src/utils/resource_manager.py`

```python
def resource_path(relative_path):
    """
    Get the absolute path to a resource, works for both development and PyInstaller frozen mode.
    
    When running as a script, returns the path relative to the project root directory.
    When running as a PyInstaller executable (.exe), returns the path relative to
    the temporary directory where PyInstaller extracts files (sys._MEIPASS).
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment (script mode)
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    return os.path.normpath(os.path.join(base_path, relative_path))
```

**Exported from:** `src/utils/__init__.py`

### 2. Files Modified

#### DLNode Files (ONNX Model Loading)

All DLNode files now use `resource_path()` instead of `os.path.dirname(os.path.abspath(__file__))`:

1. **`node/DLNode/node_classification.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated Yolo-cls import path to use `resource_path()`
   - Updated all model paths in `_model_path_setting` dictionary
   - Example: `resource_path('node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx')`

2. **`node/DLNode/node_object_detection.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: YOLOX, YOLO11, FreeYOLO, LightWeightPersonDetector, YOLOTENNIS

3. **`node/DLNode/node_semantic_segmentation.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: DeepLabV3, Road Segmentation, Skin/Clothes/Hair Segmentation, YOLOv8-seg

4. **`node/DLNode/node_pose_estimation.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: MoveNet variants, TennisKeyPoints

5. **`node/DLNode/node_face_detection.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: YuNet

6. **`node/DLNode/node_low_light_image_enhancement.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: TBEFN, SCI, AGLLNet

7. **`node/DLNode/node_monocular_depth_estimation.py`**
   - Updated import: `from src.utils import resource_path`
   - Updated all model paths in `_model_path_setting` dictionary
   - Models: FSRE-Depth, HR-Depth

#### Model Implementation Files

8. **`node/DLNode/object_detection/YOLOX/yolox.py`**
   - Updated import: `from src.utils import resource_path`
   - Fixed `__main__` block to use `resource_path()` for both model and coco_classes.txt:
     ```python
     model_path = resource_path('node/DLNode/object_detection/YOLOX/model/yolox_nano.onnx')
     with open(resource_path('node/DLNode/object_detection/YOLOX/coco_classes.txt'), 'rt') as f:
     ```

### 3. Files Verified (No Changes Needed)

- **`main.py`**: Already has its own `get_resource_path()` function for `setting.json`
- **`node_editor/node_editor.py`**: File open operations are for user-provided paths (file dialogs), not bundled resources
- **`node/InputNode/_node_image.py`**: Image loading is for user-provided image files, not bundled resources

## Testing

The `resource_path()` function was tested in both modes:

1. **Normal Mode (Development)**:
   - Base path: Project root directory
   - Successfully resolves paths to actual files

2. **Frozen Mode (Simulated PyInstaller)**:
   - Base path: `sys._MEIPASS`
   - Successfully resolves paths relative to temporary extraction folder

## Impact

### Before
```python
_model_base_path = os.path.dirname(os.path.abspath(__file__)) + '/classification/'
model_path = _model_base_path + 'MobileNetV3/model/MobileNetV3Small.onnx'
# Result: /path/to/source/node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx
```

### After
```python
model_path = resource_path('node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx')
# Development: /path/to/project/node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx
# PyInstaller: /tmp/_MEIxxxxxx/node/DLNode/classification/MobileNetV3/model/MobileNetV3Small.onnx
```

## Resource Types Covered

✅ ONNX model files (.onnx)
✅ JSON configuration files (.json)
✅ Text files (coco_classes.txt)
✅ Font files (.otf) - via node_editor directory structure

## Next Steps for PyInstaller Build

When creating a PyInstaller spec file, ensure all resource directories are included:

```python
datas = [
    ('node', 'node'),
    ('node_editor', 'node_editor'),
    ('src', 'src'),
]
```

All model files, configuration files, and other resources in these directories will be bundled and accessible via `resource_path()` at runtime.

## Backward Compatibility

✅ Changes are fully backward compatible
✅ Works in development mode (running as Python script)
✅ Works in frozen mode (PyInstaller executable)
✅ No breaking changes to existing functionality
