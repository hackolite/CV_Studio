# Audio Output Handle Change - Video Node

## Summary

The audio output handle for the video node has been moved from a separate button to the spectrogram texture area. This change makes the UI more intuitive by placing the audio output handle directly on the visual representation of the audio (the spectrogram).

## Before

```
┌─────────────────────────────┐
│      Video Node             │
├─────────────────────────────┤
│ [Select Movie]              │
│ ┌─────────────────────────┐ │ ← Video output handle
│ │    Video Display        │●│   (on video texture)
│ └─────────────────────────┘ │
│ ☐ Show Spectrogram          │
│ ┌─────────────────────────┐ │
│ │  Spectrogram Display    │ │
│ └─────────────────────────┘ │
│ ☑ Loop                      │
│ Skip Rate:    |──●─|        │
│ Target FPS:   |─────────●─| │
│ Speed:        |────●──────| │
│ [Start]                     │
│ Audio (output)              │ ← Audio output as separate button
│ JSON (output)               │
│ Float (output)              │
└─────────────────────────────┘
```

## After

```
┌─────────────────────────────┐
│      Video Node             │
├─────────────────────────────┤
│ [Select Movie]              │
│ ┌─────────────────────────┐ │ ← Video output handle
│ │    Video Display        │●│   (on video texture)
│ └─────────────────────────┘ │
│ ☐ Show Spectrogram          │
│ ┌─────────────────────────┐ │ ← Audio output handle
│ │  Spectrogram Display    │●│   (on spectrogram texture) ⭐ NEW
│ └─────────────────────────┘ │
│ ☑ Loop                      │
│ Skip Rate:    |──●─|        │
│ Target FPS:   |─────────●─| │
│ Speed:        |────●──────| │
│ [Start]                     │
│ JSON (output)               │
│ Float (output)              │
└─────────────────────────────┘
```

## Key Changes

1. **Audio output handle moved**: Now attached to the spectrogram texture area instead of being a separate button
2. **More intuitive UI**: The audio output handle is now on the visual representation of the audio
3. **Cleaner layout**: One less separate output button at the bottom
4. **Logical grouping**: Video output on video texture, Audio output on audio spectrogram texture

## Benefits

### User Experience
- **Intuitive**: Users can connect audio from the visual representation of the audio (spectrogram)
- **Consistent**: Similar to how video output is on the video texture
- **Less clutter**: Fewer buttons at the bottom of the node

### Technical
- **Clean implementation**: Changed attribute type from `mvNode_Attr_Static` to `mvNode_Attr_Output`
- **Minimal changes**: Only 4 lines added, 8 lines removed
- **No breaking changes**: Tag names remain the same, connections will work as before

## Implementation Details

### Code Changes in `node/InputNode/node_video.py`

#### Changed Section (lines 158-168)
```python
# Before:
with dpg.node_attribute(
        tag=node.tag_node_spectrogram_name,
        attribute_type=dpg.mvNode_Attr_Static,
):

# After:
with dpg.node_attribute(
        tag=node.tag_node_output_audio_name,
        attribute_type=dpg.mvNode_Attr_Output,
):
```

#### Removed Section (lines 259-262)
```python
# Removed this separate audio output button:
with dpg.node_attribute(tag=node.tag_node_output_audio_name, attribute_type=dpg.mvNode_Attr_Output):
    btn = add_yellow_disabled_button("Audio", node.tag_node_output_audio_value_name)
```

## Usage

### Connecting Audio Output
1. Enable the spectrogram display by checking "Show Spectrogram"
2. Connect from the output handle (●) on the spectrogram area to another node's audio input
3. The spectrogram will show the synchronized audio visualization

### Node Connections
- **Video texture**: Connect to nodes that need video input
- **Spectrogram texture**: Connect to nodes that need audio input
- **JSON output**: Connect to nodes that need JSON data
- **Float output**: For numerical outputs (currently static)

## Files Modified

- `node/InputNode/node_video.py`: Main implementation (12 lines changed)
  - Changed spectrogram area to use audio output attribute
  - Removed separate audio output button

## Compatibility

- **Backward compatible**: Existing projects will continue to work
- **Connection behavior**: Audio output connections will work exactly as before
- **Tag names**: No changes to tag naming scheme
