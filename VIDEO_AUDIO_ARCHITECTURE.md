# Video/Audio Split Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                          VIDEO NODE                                  │
│                                                                       │
│  User Action: Select Movie File                                      │
│  ↓                                                                    │
│  _callback_file_select()                                             │
│  ↓                                                                    │
│  _preprocess_video()                                                 │
│  ├─ Extract all video frames → _video_frames[node_id]               │
│  ├─ Extract audio → librosa.load()                                   │
│  ├─ Chunk audio (5s chunks, 1s steps) → _audio_chunks[node_id]      │
│  ├─ Pre-compute spectrograms → _spectrogram_chunks[node_id]         │
│  └─ Store metadata → _chunk_metadata[node_id]                       │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    update() Method                             │  │
│  │                                                                 │  │
│  │  1. Read current frame from OpenCV VideoCapture                │  │
│  │     ↓                                                           │  │
│  │     frame = video_capture.read()                               │  │
│  │                                                                 │  │
│  │  2. Get audio chunk for current frame                          │  │
│  │     ↓                                                           │  │
│  │     current_frame_num = self._frame_count[node_id]             │  │
│  │     audio_chunk_data = _get_audio_chunk_for_frame(             │  │
│  │         node_id, current_frame_num                             │  │
│  │     )                                                           │  │
│  │     ↓                                                           │  │
│  │     Returns: {                                                 │  │
│  │         'data': numpy_array,    # Audio samples                │  │
│  │         'sample_rate': 22050    # Sample rate                  │  │
│  │     }                                                           │  │
│  │                                                                 │  │
│  │  3. Update internal spectrogram display (if enabled)           │  │
│  │     ↓                                                           │  │
│  │     if Show Spectrogram checkbox is enabled:                   │  │
│  │         spectrogram_bgr = _get_spectrogram_for_frame()         │  │
│  │         spectrogram_with_cursor = _add_playback_cursor()       │  │
│  │         dpg_set_value(spectrogram_texture)                     │  │
│  │                                                                 │  │
│  │  4. Return outputs                                             │  │
│  │     ↓                                                           │  │
│  │     return {                                                   │  │
│  │         "image": frame,              # → IMAGE Output          │  │
│  │         "json": None,                                          │  │
│  │         "audio": audio_chunk_data    # → AUDIO Output          │  │
│  │     }                                                           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌─────────────────────────┐    ┌─────────────────────────┐         │
│  │   Output01              │    │   Output03              │         │
│  │   TYPE_IMAGE            │    │   TYPE_AUDIO            │         │
│  │   (Video Frames)        │    │   (Audio Chunks)        │         │
│  └──────────┬──────────────┘    └──────────┬──────────────┘         │
└─────────────┼───────────────────────────────┼────────────────────────┘
              │                               │
              │                               │
              ▼                               ▼
┌─────────────────────────┐    ┌─────────────────────────┐
│  Image Processing Node   │    │  Audio Processing Node  │
│  (e.g., Object Detection)│    │  (e.g., Spectrogram)    │
│                          │    │                          │
│  Input: TYPE_IMAGE       │    │  Input: TYPE_AUDIO      │
│  Expects: numpy array    │    │  Expects: dict with     │
│           (H x W x 3)    │    │    - 'data': numpy array│
│                          │    │    - 'sample_rate': int │
└─────────────────────────┘    └─────────────────────────┘
```

## Data Flow Timing

```
Frame Timeline (30 FPS):
├─ Frame 0  (0.00s) ─┬─ IMAGE: frame[0]      ─┬─ AUDIO: chunk[0] (0-5s)
├─ Frame 1  (0.03s) ─┤                        │
├─ ...              ─┤                        │
├─ Frame 29 (0.97s) ─┤                        │
│                                             │
├─ Frame 30 (1.00s) ─┬─ IMAGE: frame[30]     ─┬─ AUDIO: chunk[1] (1-6s)
├─ Frame 31 (1.03s) ─┤                        │
├─ ...              ─┤                        │
├─ Frame 59 (1.97s) ─┤                        │
│                                             │
├─ Frame 60 (2.00s) ─┬─ IMAGE: frame[60]     ─┬─ AUDIO: chunk[2] (2-7s)
└─ ...
```

**Chunk Index Calculation:**
```
chunk_index = int((frame_number / fps) / step_duration)
            = int((frame_number / 30) / 1.0)

Examples:
- Frame 0:  chunk_index = int(0 / 30 / 1) = 0
- Frame 30: chunk_index = int(30 / 30 / 1) = 1
- Frame 60: chunk_index = int(60 / 30 / 1) = 2
```

## Memory Layout

```
Video Node Instance (node_id = "1:Video")
│
├─ _video_frames["1:Video"] = [
│   frame[0],    # numpy array (H x W x 3)
│   frame[1],
│   ...
│   frame[N]
│ ]
│
├─ _audio_chunks["1:Video"] = [
│   chunk[0],    # numpy array (samples,) for 0-5 seconds
│   chunk[1],    # numpy array (samples,) for 1-6 seconds
│   chunk[2],    # numpy array (samples,) for 2-7 seconds
│   ...
│ ]
│
├─ _spectrogram_chunks["1:Video"] = [
│   spec[0],     # numpy array (H x W x 3) BGR colormap
│   spec[1],
│   ...
│ ]
│
└─ _chunk_metadata["1:Video"] = {
    'fps': 30.0,
    'sr': 22050,
    'chunk_duration': 5.0,
    'step_duration': 1.0,
    'num_frames': 1000,
    'num_chunks': 100
  }
```

## Node Connection Example

```
┌──────────────┐
│  Video Node  │
└───┬──────┬───┘
    │      │
    │      └─────────────────┐
    │                        │
    │ IMAGE                  │ AUDIO
    │                        │
    ▼                        ▼
┌──────────────┐      ┌─────────────┐
│   Object     │      │ Spectrogram │
│  Detection   │      │    Node     │
└──────┬───────┘      └──────┬──────┘
       │                     │
       │ IMAGE               │ IMAGE
       │                     │
       ▼                     ▼
┌──────────────┐      ┌─────────────┐
│   Overlay    │      │   Display   │
│    Node      │      │    Node     │
└──────────────┘      └─────────────┘
```
