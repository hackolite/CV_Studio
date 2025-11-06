# Audio Diagnostic Agent

This directory contains the audio diagnostic agent for detecting audio classification issues in videos.

## Files

- `audio_diagnostic_agent.py` - Main CLI tool for audio diagnostics
- `utils_audio.py` - Utility functions for audio processing
- `config_example.yaml` - Example configuration file

## Installation

Install the required dependencies:

```bash
pip install -r requirements-dev.txt
```

Make sure you have ffmpeg installed on your system:

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Usage

### Basic Usage

Process a single video file:

```bash
cd scripts
python audio_diagnostic_agent.py --input /path/to/video.mp4
```

Process all videos in a directory:

```bash
python audio_diagnostic_agent.py --input /path/to/videos/
```

### Advanced Usage

Specify output directory and top-k predictions:

```bash
python audio_diagnostic_agent.py --input video.mp4 --outdir results --topk 10
```

Use a custom configuration file:

```bash
python audio_diagnostic_agent.py --input video.mp4 --config config_example.yaml
```

Override spectrogram parameters:

```bash
python audio_diagnostic_agent.py --input video.mp4 --n-fft 4096 --hop-length 1024 --n-mels 256
```

Set custom energy threshold:

```bash
python audio_diagnostic_agent.py --input video.mp4 --threshold 15.0
```

## Command-Line Options

- `--input` - Path to video file or directory (required)
- `--outdir` - Output directory for reports (default: reports)
- `--model` - Path to model file (optional)
- `--topk` - Number of top predictions (default: 5)
- `--config` - Path to YAML configuration file (optional)
- `--n-fft` - FFT window size (default: 2048)
- `--hop-length` - Hop length for spectrogram (default: 512)
- `--n-mels` - Number of Mel bands (default: 128)
- `--threshold` - Energy difference threshold in dB (default: 10.0)

## Output

The agent generates:

1. **Spectrogram Images** - PNG files showing the Mel spectrogram for each video
2. **JSON Reports** - Detailed reports containing:
   - Original and used sample rates
   - Spectrogram parameters
   - Frequency band energy measurements
   - Top-k predictions
   - Suspicion flags and reasons

### Report Structure

```json
{
  "timestamp": "2025-11-06T12:00:00",
  "total_files": 1,
  "suspicious_files": 1,
  "configuration": { ... },
  "results": [
    {
      "video_path": "video.mp4",
      "original_sample_rate": 44100,
      "used_sample_rate": 44100,
      "spectrogram_path": "reports/video_spectrogram.png",
      "top_predictions": [
        {"label": "Dog", "confidence": 0.85},
        ...
      ],
      "frequency_band_energies": {
        "bark": -45.2,
        "snore": -65.1,
        ...
      },
      "suspicion": true,
      "suspicion_reasons": [
        "Large energy variation across bands: 28.9 dB"
      ]
    }
  ]
}
```

## Suspicion Detection

The agent flags files as suspicious based on:

1. **Sample Rate Mismatch** - Original and processed sample rates differ
2. **Energy Variation** - Large energy differences across frequency bands
3. **Extraction Failures** - Unable to extract audio or compute spectrogram

## Configuration

Create a YAML configuration file to customize:

- Spectrogram parameters (n_fft, hop_length, n_mels, fmin, fmax)
- Frequency band definitions
- Suspicion thresholds

See `config_example.yaml` for a complete example.

## Testing

Run the unit tests:

```bash
cd tests
python -m pytest test_audio_agent.py -v
```

## Examples

### Example 1: Detect dog barks vs snoring

```bash
python audio_diagnostic_agent.py --input dog_videos/ --outdir bark_analysis
```

The report will show energy levels in the "bark" (150-2000 Hz) vs "snore" (50-300 Hz) bands.

### Example 2: Compare with custom frequency bands

Create a custom config file:

```yaml
frequency_bands:
  custom_low: [0, 1000]
  custom_mid: [1000, 4000]
  custom_high: [4000, 10000]
```

Then run:

```bash
python audio_diagnostic_agent.py --input video.mp4 --config custom_config.yaml
```

### Example 3: Batch processing

```bash
python audio_diagnostic_agent.py --input /data/videos/ --outdir batch_results --topk 10
```

This will process all videos in `/data/videos/` and save results to `batch_results/`.

## Troubleshooting

### ffmpeg not found

Make sure ffmpeg is installed and in your PATH:

```bash
ffmpeg -version
ffprobe -version
```

### No audio stream

If the video has no audio track, the agent will flag it as suspicious with the reason "Could not determine original sample rate".

### Import errors

Make sure all dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

## License

Same as CV_Studio project license.
