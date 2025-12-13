# Audio Sample Rate Consistency Fix

## Problem Statement (Original French)
> "corrige en input, car audio sample tu utilises un nombre de samples par secondes basés sur la frequence d'échantillonnage en hertz, garanti que la taille de la queue audio, et que la frequence de population de la queue audio t video, tout au long du workflow, input/video ---> concat [audio, image] ----> videowriter soit cohérent pour pouvoir donner une video AVI ou mpeg fonctionnelle"

**Translation:** Fix input, because for audio samples you use a number of samples per second based on the sampling frequency in Hz, guarantee that the audio queue size, and that the frequency of populating the audio and video queues, throughout the workflow, input/video → concat [audio, image] → videowriter is coherent to be able to produce a functional AVI or mpeg video.

## Root Cause
The application had an inconsistency in audio sample rates across the pipeline:
- **Video Input Node** (`node_video.py`): Extracted audio at **44100 Hz**
- **Video Writer Node** (`node_video_writer.py`): Defaulted to **22050 Hz**
- **Video Worker** (`video_worker.py`): Defaulted to **22050 Hz**
- **Spectrogram Nodes** (`node_spectrogram.py`): Defaulted to **22050 Hz**

This mismatch caused:
1. Incorrect audio duration calculations when sample rate wasn't properly propagated
2. Potential audio/video desynchronization in output files
3. Queue population frequency inconsistencies
4. Risk of non-functional AVI/MPEG video output

## Solution
Updated all default sample rates to **44100 Hz** throughout the codebase to ensure consistency.

### Why 44100 Hz?
1. **ESC-50 Compatibility**: The ESC-50 dataset (used for audio classification) has a native sample rate of 44100 Hz
2. **Industry Standard**: 44100 Hz is the CD-quality audio standard
3. **Video Input Standard**: The video input node already extracted audio at this rate
4. **Better Quality**: Higher sample rate (44100 Hz vs 22050 Hz) provides better audio quality

## Technical Details

### Audio Chunk Sizing Formula
```python
chunk_samples = int(chunk_duration * sample_rate)
```
Where:
- `chunk_duration` is in seconds (e.g., 2.0)
- `sample_rate` is in Hz (samples per second) (e.g., 44100)
- `chunk_samples` is the number of samples (e.g., 2.0 * 44100 = 88200)

### Queue Size Relationships
```python
# Image queue: holds frames for multiple audio chunks
image_queue_size = num_chunks_to_keep * chunk_duration * target_fps

# Audio queue: holds audio chunks
audio_queue_size = num_chunks_to_keep

# Relationship: image_queue_size / audio_queue_size = frames per audio chunk
```

Example with default values:
- `num_chunks_to_keep = 4`
- `chunk_duration = 2.0` seconds
- `target_fps = 24`
- `image_queue_size = 4 * 2.0 * 24 = 192` frames
- `audio_queue_size = 4` chunks
- Ratio: `192 / 4 = 48` frames per audio chunk (which equals `2.0 * 24`)

## Changes Made

### 1. node_video_writer.py
```python
# Before
_DEFAULT_SAMPLE_RATE = 22050

# After
_DEFAULT_SAMPLE_RATE = 44100  # Default audio sample rate in Hz (matches video input extraction)
```
Updated all references from hardcoded `22050` to use `self._DEFAULT_SAMPLE_RATE`.

### 2. video_worker.py
```python
# Before
def __init__(self, total_frames: Optional[int] = None, sample_rate: int = 22050):

# After
def __init__(self, total_frames: Optional[int] = None, sample_rate: int = 44100):
```

### 3. node_spectrogram.py
Updated all spectrogram generation functions:
```python
# Before
def create_mel_spectrogram(audio_data, sample_rate=22050):
def create_stft_spectrogram(audio_data, sample_rate=22050):
def create_chromagram(audio_data, sample_rate=22050):
def create_mfcc(audio_data, sample_rate=22050):
def create_stft_custom(audio_data, sample_rate=22050, binsize=1024, colormap="jet"):

# After
def create_mel_spectrogram(audio_data, sample_rate=44100):
def create_stft_spectrogram(audio_data, sample_rate=44100):
def create_chromagram(audio_data, sample_rate=44100):
def create_mfcc(audio_data, sample_rate=44100):
def create_stft_custom(audio_data, sample_rate=44100, binsize=1024, colormap="jet"):
```

Added backward compatibility function:
```python
def create_spectrogram_custom(audio_data, sample_rate=44100, binsize=1024, colormap="jet", n_fft=1024):
    """Backward compatibility alias with n_fft parameter support"""
    effective_binsize = n_fft if n_fft != binsize else binsize
    return create_stft_custom(audio_data, sample_rate, effective_binsize, colormap)
```

### 4. node_video.py
Added comprehensive documentation:
```python
# Audio is resampled to 44100 Hz for consistency across the pipeline
# This ensures sample rate (samples per second in Hz) is uniform for:
# - Audio chunk sizing: chunk_samples = chunk_duration * sample_rate
# - Queue population frequency throughout workflow (input → concat → videowriter)
subprocess.run([
    "ffmpeg",
    "-i", movie_path,
    "-vn",  # No video
    "-acodec", "pcm_s16le",  # WAV codec
    "-ar", "44100",  # Sample rate: 44100 Hz
    "-ac", "1",  # Mono
    "-y", tmp_audio_path,
])
```

## Testing

### Tests Passed
✅ **test_esc50_sample_rate_fix.py** - All 6 tests passed
- Video node extracts audio at 44100 Hz
- Spectrogram node uses 44100 Hz default
- spectrogram_utils uses 44100 Hz default
- Parameters match training code (n_fft=1024, factor=1.0)
- Audio dictionary defaults to 44100 Hz

✅ **test_video_audio_duration_sync.py** - All tests passed
- Frame count tracking
- Video/audio duration calculations
- Required frames calculation for sync
- Frame duplication logic

✅ **test_audio_chunk_sync.py** - All 4 tests passed
- Timestamp preservation
- Multi-slot audio synchronization
- Backward compatibility with no timestamps
- Mixed audio format handling

✅ **CodeQL Security Scan** - No issues found

## Benefits

1. **Consistency**: All components now use the same sample rate (44100 Hz)
2. **Better Audio Quality**: Higher sample rate provides better audio fidelity
3. **ESC-50 Compatibility**: Matches the native sample rate of the ESC-50 audio classification dataset
4. **Proper Synchronization**: Audio and video streams maintain proper timing throughout the pipeline
5. **Functional Output**: AVI and MPEG videos now have properly synchronized audio
6. **Documentation**: Added extensive comments explaining the rationale and calculations

## Verification Steps

To verify the fix is working correctly:

1. **Load a video file** in the Video input node
2. **Check logs** for: `[Video] Audio extracted: SR=44100Hz, Duration=X.XXs`
3. **Connect to VideoWriter** and record a video
4. **Check the output** AVI/MPEG file has synchronized audio
5. **Verify audio duration** matches video duration

## Files Modified

- `node/InputNode/node_video.py` - Audio preprocessing and queue sizing
- `node/VideoNode/node_video_writer.py` - Video writer audio handling
- `node/VideoNode/video_worker.py` - Background worker defaults
- `node/AudioProcessNode/node_spectrogram.py` - Spectrogram generation

## Migration Notes

### For Users
No changes required - the fix is backward compatible.

### For Developers
If you have custom nodes that process audio:
1. Update default sample_rate parameters from 22050 to 44100
2. Ensure your audio processing respects the `sample_rate` from incoming audio data
3. Document the expected sample rate in your function signatures

## References

- ESC-50 Dataset: https://github.com/karolpiczak/ESC-50 (44100 Hz native)
- CD Audio Standard: 44100 Hz, 16-bit
- Sample Rate (Hz): Samples per second
- Audio Quality: Higher sample rate = better quality (up to Nyquist limit)
