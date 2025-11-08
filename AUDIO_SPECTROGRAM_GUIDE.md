# Audio Spectrogram Processing Guide

## Overview

CV_Studio now includes comprehensive audio spectrogram processing utilities for audio classification workflows. These tools enable you to:

- **Chunk audio files** into overlapping segments for temporal analysis
- **Generate spectrograms** from audio chunks for visual representation
- **Create videos** from spectrogram sequences for visualization
- **Annotate spectrograms** with classification results from YOLO models

This workflow is particularly useful for audio event detection, sound classification, and acoustic scene classification tasks using the ESC-50 dataset or custom audio datasets.

## Installation

The audio processing utilities require the following dependencies (already in `requirements.txt`):

```bash
pip install librosa matplotlib soundfile opencv-contrib-python pillow
```

For video creation with audio synchronization, you also need `ffmpeg`:

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Quick Start

### Basic Workflow

```python
from node.InputNode.audio_processing import (
    chunk_audio_wav_or_mp3,
    process_chunks_to_spectrograms,
    create_video_from_spectrograms
)

# Step 1: Chunk audio (5-second chunks, 0.25-second step)
chunk_audio_wav_or_mp3(
    input_audio="audio.wav",
    output_folder="chunks/",
    chunk_duration=5.0,
    step_duration=0.25
)

# Step 2: Generate spectrograms
process_chunks_to_spectrograms(
    chunks_folder="chunks/",
    spectro_output_folder="spectrograms/"
)

# Step 3: Create video
create_video_from_spectrograms(
    input_folder="spectrograms/",
    output_video_path="output.mp4",
    fps=4
)
```

## Module Reference

### `audio_processing.py`

#### Functions

##### `chunk_audio_wav_or_mp3(input_audio, output_folder, chunk_duration=5.0, step_duration=0.25)`

Chunk audio file into overlapping segments using a sliding window.

**Parameters:**
- `input_audio` (str): Path to input audio file (.wav or .mp3)
- `output_folder` (str): Directory to save audio chunks
- `chunk_duration` (float): Duration of each chunk in seconds (default: 5.0)
- `step_duration` (float): Step duration between chunks in seconds (default: 0.25)

**Returns:**
- `int`: Number of chunks created

**Example:**
```python
num_chunks = chunk_audio_wav_or_mp3(
    input_audio="audio.mp3",
    output_folder="chunks/",
    chunk_duration=5.0,
    step_duration=0.25
)
# Creates: chunks/chunk_1.wav, chunks/chunk_2.wav, ...
```

**Use Cases:**
- Temporal audio analysis with sliding windows
- Training data preparation for audio classification
- Audio event detection with overlapping segments

---

##### `fourier_transformation(sig, frameSize, overlapFac=0.5, window=np.hanning)`

Perform Short-Time Fourier Transform (STFT) with windowing and overlap.

**Parameters:**
- `sig` (ndarray): Input audio signal
- `frameSize` (int): Size of each frame/window
- `overlapFac` (float): Overlap factor (0.5 = 50% overlap)
- `window` (callable): Window function (default: np.hanning)

**Returns:**
- `ndarray`: STFT matrix (complex values)

**Example:**
```python
signal = librosa.load("audio.wav", sr=22050)[0]
stft = fourier_transformation(signal, frameSize=1024)
```

---

##### `make_logscale(spec, sr=44100, factor=20.0)`

Apply logarithmic scaling to frequency bins for better low-frequency resolution.

**Parameters:**
- `spec` (ndarray): Spectrogram array (time x frequency)
- `sr` (int): Sample rate in Hz (default: 44100)
- `factor` (float): Scaling factor (higher = more emphasis on low frequencies)

**Returns:**
- `tuple`: (newspec, freqs) - Rescaled spectrogram and corresponding frequencies

**Example:**
```python
stft = fourier_transformation(signal, 1024)
log_spec, freqs = make_logscale(stft, sr=22050, factor=20.0)
```

---

##### `plot_spectrogram(location, plotpath=None, binsize=2**10, colormap="jet")`

Generate and save a spectrogram image from an audio file.

**Parameters:**
- `location` (str): Path to audio file (.wav)
- `plotpath` (str, optional): Path to save spectrogram image (if None, display only)
- `binsize` (int): FFT bin size (default: 1024)
- `colormap` (str): Matplotlib colormap name (default: "jet")

**Returns:**
- `ndarray`: Spectrogram intensity matrix in decibels

**Example:**
```python
plot_spectrogram(
    location="audio.wav",
    plotpath="spectrogram.png",
    binsize=1024,
    colormap="inferno"
)
```

**Available Colormaps:**
- `"jet"` - Classic rainbow colormap
- `"inferno"` - Perceptually uniform (recommended)
- `"viridis"` - Perceptually uniform blue-yellow
- `"magma"` - Perceptually uniform purple-yellow
- `"plasma"` - Perceptually uniform purple-orange

---

##### `process_chunks_to_spectrograms(chunks_folder, spectro_output_folder, category="default")`

Convert all audio chunks in a folder to spectrogram images.

**Parameters:**
- `chunks_folder` (str): Folder containing audio chunk files (.wav)
- `spectro_output_folder` (str): Output folder for spectrogram images
- `category` (str): Category name for organization (optional)

**Returns:**
- `int`: Number of spectrograms created

**Example:**
```python
num_spectros = process_chunks_to_spectrograms(
    chunks_folder="chunks/",
    spectro_output_folder="spectrograms/"
)
# Creates: spectrograms/chunk_1.png, spectrograms/chunk_2.png, ...
```

---

##### `annotate_image_with_classification(input_image_path, output_image_path, predictions)`

Annotate an image with classification predictions.

**Parameters:**
- `input_image_path` (str): Path to input image
- `output_image_path` (str): Path to save annotated image
- `predictions` (list): List of (label, score) tuples for top predictions

**Example:**
```python
predictions = [
    ("Dog", 0.95),
    ("Cat", 0.03),
    ("Bird", 0.01)
]

annotate_image_with_classification(
    input_image_path="spectrogram.png",
    output_image_path="annotated.png",
    predictions=predictions
)
```

**Features:**
- Multi-tier text rendering with decreasing font sizes
- Outline text for better visibility
- Color-coded by confidence (green → yellow → orange)

---

##### `create_video_from_spectrograms(input_folder, output_video_path, fps=4)`

Create a video from a sequence of spectrogram images.

**Parameters:**
- `input_folder` (str): Folder containing chunk_XXX.png images
- `output_video_path` (str): Path for output video file
- `fps` (int): Frames per second for the video (default: 4)

**Returns:**
- `str`: Path to created video

**Example:**
```python
video_path = create_video_from_spectrograms(
    input_folder="spectrograms/",
    output_video_path="output.mp4",
    fps=4
)
```

**Timing:**
- Each chunk is displayed for 0.25 seconds (matching the audio step duration)
- At 4 fps, each chunk = 1 frame
- At 1 fps, each chunk = 4 frames (slower playback)

---

##### `create_video_with_audio_sync(input_folder, output_video_path, audio_file=None, fps=4)`

Create video from spectrograms with optional audio synchronization.

**Parameters:**
- `input_folder` (str): Folder containing spectrogram images
- `output_video_path` (str): Path for output video file
- `audio_file` (str, optional): Path to audio file to sync with video
- `fps` (int): Frames per second (default: 4)

**Returns:**
- `str`: Path to created video (with or without audio)

**Example:**
```python
video_path = create_video_with_audio_sync(
    input_folder="spectrograms/",
    output_video_path="output.mp4",
    audio_file="original_audio.wav",
    fps=4
)
# Creates: output_with_audio.mp4
```

---

## Complete Workflow Examples

### Example 1: Audio Event Detection

```python
from node.InputNode.audio_processing import *

# 1. Chunk audio into 5-second segments with 0.25s overlap
chunk_audio_wav_or_mp3(
    input_audio="street_sounds.wav",
    output_folder="chunks/",
    chunk_duration=5.0,
    step_duration=0.25
)

# 2. Generate spectrograms
process_chunks_to_spectrograms(
    chunks_folder="chunks/",
    spectro_output_folder="spectrograms/"
)

# 3. [Run YOLO classification on spectrograms - see YOLO example below]

# 4. Create annotated video
# (after getting predictions from YOLO)
```

### Example 2: ESC-50 Dataset Preparation

```python
import os
import pandas as pd

# Load ESC-50 metadata
esc50_df = pd.read_csv('ESC-50-master/meta/esc50.csv')

# Create spectrogram folders
spectrogram_root = 'ESC-50-master/spectrogram'
os.makedirs(spectrogram_root, exist_ok=True)

for cat in esc50_df['category'].unique():
    os.makedirs(os.path.join(spectrogram_root, cat), exist_ok=True)

# Generate spectrograms for all files
for i, row in esc50_df.iterrows():
    filename = row['filename']
    category = row['category']
    audio_path = os.path.join('ESC-50-master/audio', filename)
    save_path = os.path.join(spectrogram_root, category, 
                             filename.replace('.wav', '.jpg'))
    
    try:
        plot_spectrogram(audio_path, plotpath=save_path)
    except Exception as e:
        print(f"Error with {filename}: {e}")
```

### Example 3: YOLO Classification on Spectrograms

```python
# After generating spectrograms, use YOLO for classification
from ultralytics import YOLO

# Train YOLO classifier on spectrograms
model = YOLO('yolov8n-cls.pt')
results = model.train(
    data='ESC-50-master/spectrogram',
    epochs=200,
    imgsz=640
)

# Classify new audio
# 1. Chunk audio
chunk_audio_wav_or_mp3("new_audio.wav", "chunks/", 5.0, 0.25)

# 2. Generate spectrograms
process_chunks_to_spectrograms("chunks/", "spectrograms/")

# 3. Run inference
predictions = []
for spec_file in sorted(os.listdir("spectrograms/")):
    pred = model(os.path.join("spectrograms/", spec_file))
    # Extract top prediction
    top3 = get_top3_predictions(pred)  # Custom function
    predictions.append((spec_file, top3))

# 4. Annotate spectrograms
for spec_file, top3 in predictions:
    annotate_image_with_classification(
        input_image_path=os.path.join("spectrograms/", spec_file),
        output_image_path=os.path.join("annotated/", spec_file),
        predictions=top3
    )

# 5. Create video
create_video_with_audio_sync(
    input_folder="annotated/",
    output_video_path="classified_output.mp4",
    audio_file="new_audio.wav",
    fps=4
)
```

## Performance Tips

### Memory Optimization

- Use smaller `binsize` (e.g., 512) for lower resolution spectrograms
- Process spectrograms in batches for large datasets
- Clean up intermediate files after processing

### Speed Optimization

- Use `librosa.load(..., sr=22050)` for faster loading (downsample if needed)
- Generate spectrograms in parallel using multiprocessing
- Use OpenCV colormaps instead of matplotlib for faster rendering

### Quality Optimization

- Use `binsize=2048` or `binsize=4096` for higher frequency resolution
- Use `colormap="inferno"` or `"viridis"` for perceptually uniform colors
- Increase `factor` in `make_logscale()` for better low-frequency detail

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'librosa'`
- **Solution:** `pip install librosa soundfile`

**Issue:** Spectrograms are all black/white
- **Solution:** Check audio file format, ensure it's not empty or corrupted

**Issue:** Video creation fails
- **Solution:** Install ffmpeg: `sudo apt-get install ffmpeg` (Ubuntu)

**Issue:** Font rendering fails on Linux
- **Solution:** Install DejaVu fonts: `sudo apt-get install fonts-dejavu`

**Issue:** Out of memory when processing large files
- **Solution:** Use smaller chunks or process in batches

## Related Documentation

- [Video Node Documentation](../VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)
- [YOLO Classification Node](../node/DLNode/README.md)
- [ESC-50 Dataset](https://github.com/karolpiczak/ESC-50)

## Contributing

To add new features or improve audio processing:

1. Add functions to `node/InputNode/audio_processing.py`
2. Add tests to `tests/test_audio_processing.py`
3. Update this documentation
4. Submit a pull request

## License

This module is part of CV_Studio and is licensed under Apache 2.0.
Audio processing algorithms are based on standard DSP techniques.
