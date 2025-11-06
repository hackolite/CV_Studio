# Fix Summary: AttributeError in spectrogram_utils

## Problem
The application was crashing on startup with the following error:
```
AttributeError: module 'node.InputNode.spectrogram_utils' has no attribute 'FactoryNode'
```

## Root Cause
The `node_editor/node_editor.py` module uses `glob` to discover and load all Python files in node directories (e.g., `node/InputNode/*.py`). It assumes every Python file contains a `FactoryNode` class that can be instantiated.

However, `spectrogram_utils.py` is a utility module that provides colormap functions for spectrograms - it doesn't define a `FactoryNode` class because it's not a node itself, just a helper module.

## Solution
Modified `node_editor/node_editor.py` to gracefully handle modules without `FactoryNode`:

```python
try:
    module = import_module(import_path)
    factorynode = module.FactoryNode()
    # ... register the node ...
except AttributeError:
    # Skip files without FactoryNode class (utility modules)
    logger.debug(f"Skipping {import_path}: no FactoryNode attribute")
    continue
```

This is a minimal, surgical fix that:
- Adds only 6 lines of code
- Uses proper exception handling
- Logs skipped modules for debugging
- Preserves all existing functionality

## Files Changed
1. **node_editor/node_editor.py** - Added try-except block around FactoryNode instantiation
2. **tests/test_node_editor_fix.py** - Tests to verify the fix works correctly
3. **tests/test_node_editor_utility_skip.py** - Additional validation tests

## Verification
- ✅ All tests pass
- ✅ Code review completed with no issues
- ✅ Security scan (CodeQL) found no vulnerabilities
- ✅ Verified that `spectrogram_utils.py` is the only top-level utility file in node directories
- ✅ Confirmed all actual node files follow the `node_*.py` naming convention

## Context on Colormap Feature
The problem statement also mentioned adding colors to spectrograms (inspired by the `plot_spectrogram` example with `colormap="jet"`).

**Good news:** The colormap feature is already fully implemented! 

The `spectrogram_utils.py` module was added in PR #62 specifically to provide colormap functionality. It includes:
- `apply_colormap_cv2()` - Fast OpenCV-based colormaps
- `apply_colormap_mpl()` - Matplotlib-based colormaps
- `apply_colormap_to_spectrogram()` - Unified wrapper supporting both methods

The `node_video.py` already uses this to apply colormaps to spectrograms with the default colormap being 'INFERNO'. The system supports all standard colormaps including 'JET', 'VIRIDIS', 'MAGMA', 'PLASMA', etc.

## Impact
This fix allows the application to start successfully and utilize the colormap features that were already implemented. Users can now visualize spectrograms with various colormaps for better audio event detection.
