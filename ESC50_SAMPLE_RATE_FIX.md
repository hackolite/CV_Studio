# ESC-50 Sample Rate Fix - Documentation

## Problem Statement

The ESC-50 audio classification was not working efficiently with the spectrogram node and YOLO-cls classification. The user reported that despite previous changes, the code in the repository was still not detecting sounds well.

## Root Cause

After analyzing the user's working training code (provided in the problem statement), the issue was identified:

### Sample Rate Mismatch

1. **ESC-50 Dataset**: Uses **44100 Hz** sample rate natively
2. **User's Training Code**: Preserved the native 44100 Hz sample rate
   ```python
   samplerate, samples = wav.read(location)  # Reads at native 44100 Hz
   s = fourier_transformation(samples, binsize)
   sshow, freq = make_logscale(s, factor=1.0, sr=samplerate)  # Uses 44100 Hz
   ```

3. **Previous Repository Code**: Resampled audio to **22050 Hz**
   - In `node_video.py`: `"-ar", "22050"` for ffmpeg
   - In `node_spectrogram.py`: `sample_rate=22050` as default
   - In `spectrogram_utils.py`: `sample_rate=22050` as default

### Impact of Resampling

When audio is resampled from 44100 Hz to 22050 Hz:
- **Nyquist frequency drops** from 22050 Hz to 11025 Hz
- **High-frequency content is lost** (frequencies above 11025 Hz)
- **Spectrogram appearance changes significantly** due to different frequency resolution
- **Model sees different patterns** than what it was trained on

This is critical because:
- The YOLO-cls model was trained on spectrograms generated from 44100 Hz audio
- The model learned to recognize audio patterns based on the full frequency range
- Feeding it spectrograms from 22050 Hz audio corrupts these learned patterns
- Result: Poor classification accuracy

## Solution

Changed the audio sample rate from 22050 Hz to 44100 Hz throughout the pipeline to match the ESC-50 dataset and the model's training data.

### Changes Made

#### 1. Video Node (`node/InputNode/node_video.py`)

**ffmpeg audio extraction:**
```python
# Before
"-ar", "22050",  # Sample rate

# After
"-ar", "44100",  # Sample rate (ESC-50 native sample rate)
```

**librosa fallback:**
```python
# Before
y, sr = librosa.load(movie_path, sr=22050)

# After
y, sr = librosa.load(movie_path, sr=44100)
```

#### 2. Spectrogram Node (`node/AudioProcessNode/node_spectrogram.py`)

**Function signature:**
```python
# Before
def create_spectrogram_custom(audio_data, sample_rate=22050, n_fft=1024, hop_length=512):

# After
def create_spectrogram_custom(audio_data, sample_rate=44100, n_fft=1024, hop_length=512):
```

**Default value:**
```python
# Before
audio_data, sample_rate = None, 22050

# After
audio_data, sample_rate = None, 44100
```

#### 3. Spectrogram Utils (`node/InputNode/spectrogram_utils.py`)

**Function signature:**
```python
# Before
def create_spectrogram_from_audio(audio_data, sample_rate=22050, binsize=2**10, colormap="jet"):

# After
def create_spectrogram_from_audio(audio_data, sample_rate=44100, binsize=2**10, colormap="jet"):
```

### Parameters Preserved

The following parameters match the user's training code and remain unchanged:
- **binsize**: `2**10` (1024) - FFT window size
- **factor**: `1.0` - Log scale factor for frequency binning
- **colormap**: `"jet"` - Colormap for visualization
- **BGR format**: Maintained for OpenCV/YOLO-cls compatibility

## Verification

### Test Coverage

Created comprehensive test `tests/test_esc50_sample_rate_fix.py` that verifies:
1. ✅ Video node extracts audio at 44100 Hz
2. ✅ Spectrogram node uses 44100 Hz default
3. ✅ Spectrogram utils uses 44100 Hz default
4. ✅ FFT parameters match training code (n_fft=1024, factor=1.0)
5. ✅ JET colormap is used by default
6. ✅ Audio dictionary defaults are consistent

### Functional Testing

Verified that:
- ✅ STFT works correctly at 44100 Hz
- ✅ Log-scale transformation produces correct output
- ✅ Spectrogram generation produces valid BGR images
- ✅ Image format is compatible with YOLO-cls (uint8, 3 channels)

### Security

- ✅ CodeQL scan: 0 vulnerabilities
- ✅ Code review: No issues found

## Expected Improvement

### Before Fix
- Sample rate: 22050 Hz (resampled, information loss)
- Frequency range: 0-11025 Hz (limited)
- Classification: Poor accuracy ❌
- Reason: Model trained on 44100 Hz spectrograms, but receiving 22050 Hz spectrograms

### After Fix
- Sample rate: 44100 Hz (native ESC-50 rate)
- Frequency range: 0-22050 Hz (full range)
- Classification: Expected to work well ✓
- Reason: Model receives spectrograms matching its training data

## Technical Details

### Spectrogram Generation Pipeline

```
Audio File (44100 Hz)
    ↓
FFmpeg extraction (preserves 44100 Hz)
    ↓
5-second chunks (44100 Hz)
    ↓
STFT (n_fft=1024)
    ↓
Log-scale transformation (factor=1.0)
    ↓
dB conversion (20*log10(magnitude))
    ↓
Normalization (0-255)
    ↓
JET colormap (BGR format)
    ↓
Spectrogram image → YOLO-cls → Classification
```

### Comparison with User's Training Code

| Parameter | User's Training Code | Previous Repo | Current Fix |
|-----------|---------------------|---------------|-------------|
| Sample Rate | 44100 Hz | 22050 Hz ❌ | 44100 Hz ✓ |
| FFT Window | 2**10 (1024) | 1024 ✓ | 1024 ✓ |
| Log Factor | 1.0 | 1.0 ✓ | 1.0 ✓ |
| Colormap | jet | jet ✓ | jet ✓ |
| Format | BGR (via OpenCV) | BGR ✓ | BGR ✓ |

## Backward Compatibility

This change is **backward compatible** for:
- Video files at various sample rates (ffmpeg handles resampling)
- Different audio sources (webcam, RTSP, etc.)
- Other classification models (they handle the spectrogram as a regular image)

However, if you have **previously trained models** on 22050 Hz spectrograms, you may need to:
1. Retrain them on 44100 Hz spectrograms, OR
2. Temporarily revert the sample rate for those specific models

For ESC-50 classification, this fix is essential and should be kept.

## References

- ESC-50 Dataset: https://github.com/karoldvl/ESC-50
- Sample Rate: 44100 Hz (standard CD quality)
- User's Training Code: Based on https://mpolinowski.github.io/docs/IoT-and-Machine-Learning/ML/2023-09-23--yolo8-listen/2023-09-23/

## Authors

- Issue identified and fix implemented by GitHub Copilot Agent
- Training code reference provided by user (hackolite)

## Related Files

- `node/InputNode/node_video.py` - Audio extraction
- `node/AudioProcessNode/node_spectrogram.py` - Spectrogram generation
- `node/InputNode/spectrogram_utils.py` - Spectrogram utilities
- `tests/test_esc50_sample_rate_fix.py` - Test coverage
