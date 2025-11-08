# Quick Start Guide: Video to Spectrogram Conversion

This guide will help you quickly get started with converting audio/video files to spectrograms.

## Installation

1. **Install Python Dependencies**
```bash
cd CV_Studio
pip install -r requirements.txt
```

2. **Install FFmpeg** (required for video processing)

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

## Quick Examples

### Example 1: Convert a Single WAV File

```python
from simple_video_to_spectrogram import plot_spectrogram

plot_spectrogram(
    location='my_audio.wav',
    plotpath='my_spectrogram.jpg'
)
```

### Example 2: Convert a Video File (Command-Line)

```bash
python video_to_spectrogram.py \
    --mode single \
    --input my_video.mp4 \
    --output my_spectrogram.jpg
```

### Example 3: Batch Process from CSV

**Create a CSV file (dataset.csv):**
```csv
filename,category
dog_bark.wav,dog
cat_meow.wav,cat
rooster.wav,bird
```

**Run the batch processor:**
```bash
python video_to_spectrogram.py \
    --mode batch \
    --csv dataset.csv \
    --audio-dir ./audio \
    --output-dir ./spectrograms
```

**Output structure:**
```
spectrograms/
├── dog/
│   └── dog_bark.jpg
├── cat/
│   └── cat_meow.jpg
└── bird/
    └── rooster.jpg
```

### Example 4: ESC-50 Dataset

If you have the ESC-50 dataset:

```python
from simple_video_to_spectrogram import process_video_chunks_to_spectrograms

process_video_chunks_to_spectrograms(
    csv_path='ESC-50-master/meta/esc50.csv',
    audio_root='ESC-50-master/audio',
    spectrogram_root='ESC-50-master/spectrogram'
)
```

## Advanced Usage

### Custom FFT Bin Size

Larger bin size = better frequency resolution, slower processing:

```bash
python video_to_spectrogram.py \
    --mode single \
    --input audio.wav \
    --output spec.jpg \
    --binsize 2048
```

### Custom Colormap

Try different colormaps for better visualization:

```bash
python video_to_spectrogram.py \
    --mode single \
    --input audio.wav \
    --output spec.jpg \
    --colormap viridis
```

Available colormaps: `jet`, `viridis`, `inferno`, `plasma`, `magma`, `cividis`, etc.

## Python API

### Import and Use

```python
from simple_video_to_spectrogram import (
    fourier_transformation,
    make_logscale,
    plot_spectrogram,
    process_video_chunks_to_spectrograms
)

# Generate spectrogram from audio
plot_spectrogram(
    location='audio.wav',
    plotpath='spectrogram.jpg',
    binsize=1024,
    colormap='jet'
)

# Batch process
process_video_chunks_to_spectrograms(
    csv_path='metadata.csv',
    audio_root='audio/',
    spectrogram_root='spectrograms/'
)
```

### Process Audio Data Directly

```python
import numpy as np
from simple_video_to_spectrogram import fourier_transformation, make_logscale

# Your audio signal
sample_rate = 22050
audio_signal = np.random.randn(sample_rate * 5)  # 5 seconds of audio

# Generate spectrogram
stft = fourier_transformation(audio_signal, frameSize=1024)
scaled_spec, frequencies = make_logscale(stft, sr=sample_rate, factor=1.0)

# Convert to decibels
spectrogram_db = 20.0 * np.log10(np.abs(scaled_spec) / 10e-6)
```

## Troubleshooting

### Error: "No module named 'scipy'"
```bash
pip install scipy
```

### Error: "ffmpeg: command not found"
Install ffmpeg on your system (see Installation section above)

### Error: "Unable to read file"
- Ensure file is in WAV format (for audio) or MP4/AVI (for video)
- Check file path is correct
- Verify file permissions

### Warning: DeprecationWarning about get_cmap
This is expected with newer matplotlib versions. The code handles this automatically.

## Parameters Reference

### plot_spectrogram()

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| location | str | required | Path to audio file (.wav) |
| plotpath | str | None | Output path for spectrogram image |
| binsize | int | 1024 | FFT bin size (power of 2) |
| colormap | str | "jet" | Matplotlib colormap name |

### fourier_transformation()

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| sig | array | required | Input audio signal |
| frameSize | int | required | Size of each FFT frame |
| overlapFac | float | 0.5 | Overlap factor (0.0-1.0) |
| window | function | np.hanning | Window function |

### make_logscale()

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| spec | array | required | Spectrogram array (time x freq) |
| sr | int | 44100 | Sample rate in Hz |
| factor | float | 20.0 | Scaling factor (higher = more low-freq emphasis) |

## Performance Tips

1. **Binsize**: Use 1024 for fast processing, 2048 for better quality
2. **Batch Processing**: Process large datasets overnight
3. **Colormap**: `jet` is fastest, `viridis` is perceptually better
4. **Factor**: Use 1.0 for balanced frequency representation

## Next Steps

- Read the full documentation: [VIDEO_TO_SPECTROGRAM_README.md](VIDEO_TO_SPECTROGRAM_README.md)
- Check examples: [examples/video_to_spectrogram_example.py](examples/video_to_spectrogram_example.py)
- Run tests: `python -m pytest tests/test_video_to_spectrogram.py -v`
- Use spectrograms with CV Studio classification nodes

## Getting Help

- GitHub Issues: https://github.com/hackolite/CV_Studio/issues
- Documentation: See README.md and VIDEO_TO_SPECTROGRAM_README.md
- Examples: See examples/video_to_spectrogram_example.py

---

**Happy Spectrogram Generation! 🎵📊**
