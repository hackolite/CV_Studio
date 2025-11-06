# Spectrogram Zero Division Fix

## Issue
The spectrogram generation in `node_video.py` was producing warnings and potentially invisible spectrograms due to division by zero and invalid value operations when processing audio with very low amplitudes or silence.

### Error Messages
```
/media/lamaaz/DL/CV_Studio/node/InputNode/node_video.py:497: RuntimeWarning: divide by zero encountered in log10
  ims = 20. * np.log10(np.abs(sshow) / 10e-6)
/media/lamaaz/DL/CV_Studio/node/InputNode/node_video.py:500: RuntimeWarning: invalid value encountered in subtract
  ims_normalized = (ims - ims.min()) / (ims.max() - ims.min() + 1e-6)
/media/lamaaz/DL/CV_Studio/node/InputNode/node_video.py:500: RuntimeWarning: invalid value encountered in divide
  ims_normalized = (ims - ims.min()) / (ims.max() - ims.min() + 1e-6)
```

## Root Causes

### 1. Division by Zero in Logarithmic Conversion
**Location:** `node/InputNode/node_video.py` - line 497

When the spectrogram array `sshow` contained zeros or very small values:
```python
# BEFORE (problematic)
ims = 20. * np.log10(np.abs(sshow) / 10e-6)
```

This caused:
- `log10(0)` returns `-inf` (negative infinity)
- Spectrograms with silent sections or very quiet audio would have `-inf` values
- These `-inf` values would propagate through normalization

### 2. Invalid Value Operations in Normalization
**Location:** `node/InputNode/node_video.py` - line 500

When normalizing values that contained `-inf`:
```python
# BEFORE (problematic)
ims_normalized = (ims - ims.min()) / (ims.max() - ims.min() + 1e-6)
```

This caused:
- When all values were `-inf`, `ims.min()` and `ims.max()` are both `-inf`
- Subtracting `-inf` from `-inf` produces `nan` (not a number)
- Division operations on `nan` values produce more `nan` values
- Final spectrogram would be invisible (all pixels set to 0 or invalid)

## Changes Made

### 1. Added Epsilon to Prevent Log of Zero
**File:** `node/InputNode/node_video.py` (lines 496-499)

Added a small epsilon value before taking the logarithm:
```python
# AFTER (fixed)
epsilon = 1e-10
sshow_safe = np.maximum(np.abs(sshow), epsilon)
ims = 20. * np.log10(sshow_safe / 1e-6)
```

This ensures:
- No zero values enter the logarithm function
- Minimum value is `log10(1e-10 / 1e-6) = log10(1e-4) = -80 dB`
- All values are finite (no `-inf`)

### 2. Safe Normalization with Finite Value Handling
**File:** `node/InputNode/node_video.py` (lines 501-518)

Implemented robust normalization that handles edge cases:
```python
# AFTER (fixed)
if np.isfinite(ims).any():
    valid_mask = np.isfinite(ims)
    valid_min = ims[valid_mask].min() if valid_mask.any() else 0.0
    valid_max = ims[valid_mask].max() if valid_mask.any() else 1.0
    value_range = valid_max - valid_min
    
    if value_range > 1e-6:
        ims_normalized = np.clip((ims - valid_min) / value_range, 0.0, 1.0)
    else:
        # All valid values are the same, use middle gray
        ims_normalized = np.full_like(ims, 0.5, dtype=np.float64)
    
    # Replace any non-finite values with 0
    ims_normalized[~np.isfinite(ims_normalized)] = 0.0
else:
    # All values are non-finite, use zeros
    ims_normalized = np.zeros_like(ims, dtype=np.float64)
```

This handles multiple edge cases:
- **All same values**: Uses middle gray (0.5) instead of dividing by zero
- **Non-finite values**: Replaces any remaining `nan` or `inf` with 0
- **All non-finite**: Falls back to black spectrogram
- **Normal case**: Normalizes to [0.0, 1.0] range with clipping

## Testing

### New Tests Added
Created `tests/test_spectrogram_zero_division_fix.py` with comprehensive test coverage:

1. **test_spectrogram_no_warnings_normal_audio**: Verifies no warnings with normal audio
2. **test_spectrogram_no_warnings_silent_audio**: Verifies no warnings with silent audio (all zeros)
3. **test_spectrogram_no_warnings_very_quiet_audio**: Verifies no warnings with very quiet audio (amplitude 1e-8)
4. **test_spectrogram_valid_output_range**: Verifies output is in valid [0, 255] range

All tests verify:
- No division by zero warnings
- No invalid value warnings
- No `nan` values in output
- No `inf` values in output
- Output is in valid range [0, 255]

### Test Results
All tests pass successfully:
```
tests/test_spectrogram_zero_division_fix.py::test_spectrogram_no_warnings_normal_audio PASSED
tests/test_spectrogram_zero_division_fix.py::test_spectrogram_no_warnings_silent_audio PASSED
tests/test_spectrogram_zero_division_fix.py::test_spectrogram_no_warnings_very_quiet_audio PASSED
tests/test_spectrogram_zero_division_fix.py::test_spectrogram_valid_output_range PASSED
```

### Edge Cases Verified
Manual verification confirms proper handling of:
- **All zeros**: Produces middle gray (127/255)
- **Very small values**: Produces middle gray (127/255)
- **Mixed zeros and small values**: Produces proper gradient from 0 to 255
- **Normal audio**: Produces proper gradient from 0 to 255
- **All same values**: Produces middle gray (127/255)

### Regression Testing
All existing spectrogram tests pass without issues:
```
tests/test_spectrogram.py::test_prepare_spectrogram_defaults PASSED
tests/test_spectrogram.py::test_prepare_spectrogram_with_fmin_fmax PASSED
tests/test_spectrogram.py::test_prepare_spectrogram_only_fmin PASSED
tests/test_spectrogram.py::test_prepare_spectrogram_only_fmax PASSED
tests/test_spectrogram_display_fix.py::test_texture_dimensions_consistency PASSED
tests/test_spectrogram_display_fix.py::test_immediate_texture_update PASSED
tests/test_spectrogram_display_fix.py::test_dpg_imports PASSED
tests/test_spectrogram_display_fix.py::test_syntax_valid PASSED
tests/test_node_video_spectrogram.py::test_video_node_structure PASSED
tests/test_node_video_spectrogram.py::test_requirements_updated PASSED
```

## Impact

### Before the Fix
- Warning messages cluttered the console
- Spectrograms could be completely invisible for:
  - Silent videos
  - Videos with very quiet audio
  - Videos with audio that starts silent
- User experience was degraded

### After the Fix
- No warning messages
- Spectrograms are always visible
- Silent/quiet sections display as middle gray (neutral)
- Gradual transitions from quiet to loud audio display properly
- More robust and predictable behavior

## Technical Details

### Epsilon Choice
- Chose `epsilon = 1e-10` as a safe minimum value
- This is well below typical audio noise floor
- Prevents both division by zero and numerical instability
- Results in minimum dB value of -80 dB (well below audible range)

### Normalization Strategy
- Always produces output in [0.0, 1.0] range
- Clips values to prevent out-of-range results
- Handles degenerate cases (all same value) gracefully
- Replaces non-finite values instead of propagating them

### Performance Impact
- Minimal: Only adds one `np.maximum()` call and conditional logic
- Normalization is more complex but only runs once per video load
- Overall performance impact is negligible compared to FFT computation

## Related Issues
This fix addresses the spectrogram visibility issue reported in the problem statement, which showed:
- RuntimeWarning for divide by zero in log10
- RuntimeWarning for invalid value in subtract
- RuntimeWarning for invalid value in divide
- Spectrogram not visible on screen
