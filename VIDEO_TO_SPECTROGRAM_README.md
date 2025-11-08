# Video to Spectrogram Conversion

This directory contains utilities for converting video chunks (audio from videos) into spectrogram images using the Fourier transformation and logarithmic frequency scaling.

## Overview

The scripts use the same `fourier_transformation` and `make_logscale` functions that are used in the Video Node for real-time spectrogram display, adapted for batch processing of audio/video files.

## Scripts

### 1. `simple_video_to_spectrogram.py`

A straightforward script that follows the exact pattern shown in the problem statement. Perfect for processing datasets like ESC-50.

**Key Functions:**
- `fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning)`: Performs STFT on audio signal
- `make_logscale(spec, sr=44100, factor=20.)`: Applies logarithmic frequency scaling
- `plot_spectrogram(location, plotpath=None, binsize=2**10, colormap="jet")`: Generates and saves spectrogram
- `process_video_chunks_to_spectrograms(csv_path, audio_root, spectrogram_root)`: Batch processes files using CSV metadata

**Usage Example:**
```python
from simple_video_to_spectrogram import process_video_chunks_to_spectrograms

# Process dataset with CSV metadata
process_video_chunks_to_spectrograms(
    csv_path='metadata/dataset.csv',
    audio_root='audio/',
    spectrogram_root='spectrograms/'
)
```

### 2. `video_to_spectrogram.py`

A more feature-rich command-line tool that supports both single file and batch processing modes.

**Features:**
- Single file conversion
- Batch processing from CSV
- Support for both audio (.wav) and video files (.mp4, .avi, etc.)
- Automatic audio extraction from video files using ffmpeg
- Configurable FFT bin size and colormap

**Command-Line Usage:**

Single file mode:
```bash
# Process an audio file
python video_to_spectrogram.py --mode single --input audio.wav --output spectrogram.jpg

# Process a video file (extracts audio automatically)
python video_to_spectrogram.py --mode single --input video.mp4 --output spectrogram.jpg
```

Batch mode:
```bash
# Process multiple files from CSV
python video_to_spectrogram.py --mode batch \
    --csv metadata.csv \
    --audio-dir ./audio \
    --output-dir ./spectrograms
```

With custom parameters:
```bash
python video_to_spectrogram.py --mode batch \
    --csv metadata.csv \
    --audio-dir ./audio \
    --output-dir ./spectrograms \
    --binsize 2048 \
    --colormap viridis
```

## CSV Format

For batch processing, the CSV file should contain at minimum:
- `filename`: Name of the audio/video file
- `category` (optional): Category for organizing output into subdirectories

Example CSV structure (ESC-50 format):
```csv
filename,category
1-100032-A-0.wav,dog
1-100210-A-1.wav,rooster
1-101296-A-2.wav,pig
```

## Technical Details

### Fourier Transformation
- Uses Short-Time Fourier Transform (STFT) with overlapping windows
- Default frame size: 1024 samples (2^10)
- Default overlap: 50%
- Window function: Hanning window

### Logarithmic Frequency Scaling
- Compresses frequency bins using logarithmic scaling
- Provides better resolution for low frequencies
- Factor parameter controls the degree of compression (default: 20.0 for batch, 1.0 for single)

### Spectrogram Generation
- Amplitude converted to decibels (dB)
- Default output size: 15" x 7.5"
- Default colormap: jet (other options: viridis, inferno, plasma, etc.)
- Format: JPEG images

## Dependencies

Required packages (already in requirements.txt):
- numpy
- scipy
- matplotlib
- librosa
- soundfile
- pandas

For video processing:
- ffmpeg (must be installed separately on your system)

## Installing FFmpeg

### Ubuntu/Debian:
```bash
sudo apt-get install ffmpeg
```

### macOS:
```bash
brew install ffmpeg
```

### Windows:
Download from https://ffmpeg.org/download.html and add to PATH

## Examples

### Example 1: ESC-50 Dataset Processing

```python
from simple_video_to_spectrogram import process_video_chunks_to_spectrograms

process_video_chunks_to_spectrograms(
    csv_path='ESC-50-master/meta/esc50.csv',
    audio_root='ESC-50-master/audio',
    spectrogram_root='ESC-50-master/spectrogram'
)
```

This will:
1. Read the CSV metadata
2. Create category subdirectories in the output folder
3. Generate spectrogram for each audio file
4. Save as JPG in the corresponding category folder

### Example 2: Single Video Processing

```python
from simple_video_to_spectrogram import plot_spectrogram

plot_spectrogram(
    location='path/to/audio.wav',
    plotpath='path/to/output/spectrogram.jpg',
    binsize=1024,
    colormap='viridis'
)
```

### Example 3: Custom Dataset with Videos

```bash
python video_to_spectrogram.py --mode batch \
    --csv my_dataset.csv \
    --audio-dir videos/ \
    --output-dir spectrograms/ \
    --binsize 2048
```

## Output Structure

When using batch processing with categories:
```
spectrogram_root/
├── category1/
│   ├── file1.jpg
│   ├── file2.jpg
│   └── ...
├── category2/
│   ├── file3.jpg
│   ├── file4.jpg
│   └── ...
└── ...
```

## Integration with CV Studio

These utilities use the same spectrogram generation functions as the Video Node in CV Studio, ensuring consistency between:
- Real-time spectrogram visualization in the node editor
- Batch processing for datasets
- Pre-generated spectrogram images for classification tasks

The spectrograms generated by these scripts can be used as input to classification nodes in CV Studio for audio event detection and other audio analysis tasks.

## Troubleshooting

**Error: "No module named 'scipy'"**
- Run: `pip install scipy`

**Error: "ffmpeg: command not found"**
- Install ffmpeg on your system (see Installation section)

**Error: "Unable to read file"**
- Ensure audio files are in WAV format or valid video format
- Check file paths are correct
- Verify file permissions

**Warning: "DeprecationWarning: ... get_cmap"**
- This is expected with newer matplotlib versions, the code handles this automatically

## Performance Tips

1. **Binsize**: Larger binsize (e.g., 2048) = better frequency resolution but slower processing
2. **Factor**: For batch processing, use factor=1.0 for balanced frequency representation
3. **Multiprocessing**: For large datasets, consider parallelizing the batch processing

## License

This code is part of CV Studio and follows the same license (Apache 2.0).
