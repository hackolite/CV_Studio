# HLS Video Input Node

## Description

The HLS (HTTP Live Streaming) Input Node allows you to stream video from HLS sources (.m3u8 URLs) directly into CV Studio for processing and analysis.

## Features

- Support for HLS video streams (.m3u8 format)
- Start/Stop button for stream control
- Real-time video frame output
- Compatible with OpenCV's VideoCapture
- Audio and JSON output support (placeholders)
- Configurable multiprocessing support

## Usage

1. **Add the Node**: Select "HLS" from the "Input" menu
2. **Enter URL**: Paste your .m3u8 HLS stream URL in the URL field
3. **Start Stream**: Click the "Start" button to begin streaming
4. **Connect Output**: Connect the image output to other processing nodes
5. **Stop Stream**: Click the "Stop" button to stop the stream

## Supported URL Formats

- Standard HLS streams: `http://example.com/stream.m3u8`
- Secure HLS streams: `https://example.com/stream.m3u8`

## Example URLs

You can test the node with publicly available HLS streams. Search for "public HLS test streams" to find sample .m3u8 URLs.

## Technical Details

### Inputs
- **URL**: Text input for the HLS stream URL (.m3u8)

### Outputs
- **Image**: Video frames from the stream
- **Audio**: Audio data (placeholder for future implementation)
- **JSON**: Metadata (placeholder for future implementation)

### Processing Modes

The node supports two processing modes configured in `setting.json`:

1. **Single-threaded mode** (`use_multiprocessing_hls: false`):
   - Default mode
   - Video capture runs in the main process
   - Lower resource usage
   
2. **Multiprocessing mode** (`use_multiprocessing_hls: true`):
   - Video capture runs in a separate process
   - Better performance for high-resolution streams
   - Requires configuration in settings

## Configuration

To enable multiprocessing mode, add this to your `node_editor/setting/setting.json`:

```json
{
  "use_multiprocessing_hls": true
}
```

## Error Handling

- If the URL is invalid or unreachable, the node will return no frames
- The node will attempt to reconnect if the stream is interrupted
- Check the console for error messages if streaming fails

## Compatibility

- **OpenCV Version**: Requires OpenCV with FFmpeg support
- **Protocols**: Supports HLS (HTTP Live Streaming) protocol
- **Video Codecs**: Depends on OpenCV's FFmpeg build

## Known Limitations

- Audio extraction is not yet implemented (placeholder only)
- Some DRM-protected streams may not work
- Network latency can affect stream quality
- Requires stable internet connection for remote streams

## Node Version

- **Version**: 0.0.1
- **Based on**: RTSP node implementation
- **Node Tag**: HLS
- **Node Label**: HLS

## Dependencies

- OpenCV (`opencv-contrib-python>=4.8.1.78`)
- NumPy
- DearPyGUI

## Notes

- HLS streams may have inherent latency depending on the segment duration
- For local network streams, ensure firewall settings allow the connection
- The node will automatically retry connection if the stream is temporarily unavailable
