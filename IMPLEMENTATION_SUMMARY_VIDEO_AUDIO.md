# Implementation Summary: Video/Audio Split

## Problem Statement (French)
> garde le split de video, image d'un coté et audio de l'autre, mais je veux que les images passent frame par frame au travers des links du node ce qui permet de passer le resultat a un autre node (type=image), et pour la partie audio (chunk des audio), il faut que ça puisse paser par des nodes qui gèrent audio comme le node spectrograme que tu as crée avant de type AUDIO.

**Translation:**
Keep the split of video (image on one side and audio on the other), but I want the images to pass frame by frame through the node links which allows passing the result to another node (type=image), and for the audio part (audio chunks), it should be able to pass through nodes that handle audio like the spectrogram node you created before of type AUDIO.

## Solution Implemented ✅

### What Was Changed

1. **Video Node Output Separation**
   - **Before**: AUDIO output was returning the spectrogram image (BGR array)
   - **After**: AUDIO output returns actual audio chunk data in the correct format

2. **New Method: `_get_audio_chunk_for_frame()`**
   - Retrieves the appropriate audio chunk for the current video frame
   - Returns format: `{'data': numpy_array, 'sample_rate': int}`
   - Synchronized with video playback using frame timing

3. **Modified `update()` Method**
   - Gets current frame number from `_frame_count`
   - Retrieves corresponding audio chunk
   - Returns both:
     - `image`: Video frame (numpy array) → IMAGE output
     - `audio`: Audio chunk dict → AUDIO output

### How It Works

```
Video File Loading:
├─ User selects video file
├─ _preprocess_video() extracts:
│  ├─ All video frames
│  ├─ Audio chunks (5s duration, 1s step)
│  └─ Pre-computed spectrograms
└─ Data stored in memory

Playback Loop:
├─ Read current frame from VideoCapture
├─ Calculate current frame number
├─ Get audio chunk for current frame
├─ Update internal spectrogram display (if enabled)
└─ Return:
   ├─ IMAGE output: frame (numpy array)
   └─ AUDIO output: {'data': chunk, 'sample_rate': sr}
```

### Node Connection Examples

**Image Processing:**
```
Video (IMAGE Output) → Object Detection → Display
```

**Audio Processing:**
```
Video (AUDIO Output) → Spectrogram → Display
```

**Combined Processing:**
```
Video ─┬─ IMAGE → Object Detection → Overlay
       └─ AUDIO → Spectrogram → Display
```

## Implementation Details

### Files Modified
1. `node/InputNode/node_video.py` (+46 lines, -4 lines)
   - Added `_get_audio_chunk_for_frame()` method
   - Modified `update()` to return audio chunks
   - Maintained internal spectrogram visualization

### Files Created
1. `tests/test_video_audio_integration.py` (+134 lines)
   - Tests audio chunk format
   - Tests Spectrogram node compatibility
   - Tests output type separation

2. `VIDEO_AUDIO_SPLIT_IMPLEMENTATION.md` (+166 lines)
   - Complete documentation
   - Usage examples
   - Technical details

3. `VIDEO_AUDIO_ARCHITECTURE.md` (+7.1KB)
   - Visual diagrams
   - Data flow documentation
   - Memory layout

## Test Results ✅

All 5 tests pass:
- ✅ test_video_node_structure
- ✅ test_requirements_updated
- ✅ test_audio_chunk_format
- ✅ test_spectrogram_node_compatibility
- ✅ test_video_node_outputs

## Key Benefits

1. **Proper Data Separation**
   - Video frames flow through IMAGE connections
   - Audio chunks flow through AUDIO connections
   - Each stream can be processed independently

2. **Format Compatibility**
   - Audio chunks match the format expected by audio processing nodes
   - No conversion needed by downstream nodes

3. **Frame-Level Synchronization**
   - Audio chunks are synchronized with video frames
   - Chunk selection based on current frame timing

4. **Backward Compatibility**
   - Internal spectrogram visualization still works
   - Existing video playback unchanged
   - No breaking changes to the node interface

## Verification Steps

1. ✅ Code compiles without errors
2. ✅ All tests pass
3. ✅ Audio chunk format verified
4. ✅ Spectrogram node compatibility confirmed
5. ✅ Documentation created
6. ✅ Architecture diagrams added

## Next Steps for Users

1. Load a video file in the Video node
2. Connect IMAGE output to image processing nodes
3. Connect AUDIO output to Spectrogram node or other audio processing nodes
4. Both streams will flow independently and synchronized

## Technical Notes

- Audio chunks are 5 seconds long with 1-second steps (overlapping)
- Sample rate: 22050 Hz (configurable)
- Chunk selection: `chunk_index = int((frame_number / fps) / step_duration)`
- All data is pre-loaded into memory during video loading

## Code Quality

- ✅ No syntax errors
- ✅ Follows existing code style
- ✅ Comprehensive documentation
- ✅ Integration tests added
- ✅ Minimal changes (surgical edits)
- ✅ No breaking changes
