# Microphone Node - Visual Layout

## Before (Original)
```
┌─────────────────────────────────┐
│      Microphone Node            │
├─────────────────────────────────┤
│ Device: [0: Default Microphone] │
│ Sample Rate: [44100 Hz]         │
│ Chunk (s): [1.0]                │
│ [      Start      ]             │
│                                 │
│ [Audio]  ◄─── Output            │
│ [JSON]   ◄─── Output            │
└─────────────────────────────────┘
```

## After (With Volume Meters)
```
┌─────────────────────────────────┐
│      Microphone Node            │
├─────────────────────────────────┤
│ Device: [0: Default Microphone] │
│ Sample Rate: [44100 Hz]         │
│ Chunk (s): [1.0]                │
│ [      Start      ]             │
│                                 │
│ Volume Levels:                  │
│ RMS:  ███████░░░░░░ RMS: 0.45   │ ◄─── NEW!
│ Peak: ██████████░░░ Peak: 0.78  │ ◄─── NEW!
│                                 │
│ [Audio]  ◄─── Output            │
│ [JSON]   ◄─── Output            │
└─────────────────────────────────┘
```

## Visual States

### State 1: Not Recording (Idle)
```
Volume Levels:
RMS:  ░░░░░░░░░░░░░░ RMS: 0.00
Peak: ░░░░░░░░░░░░░░ Peak: 0.00
```

### State 2: Recording - Low Volume
```
Volume Levels:
RMS:  ██░░░░░░░░░░░░ RMS: 0.15
Peak: ████░░░░░░░░░░ Peak: 0.25
```
⚠️ Volume may be too low - move closer or increase gain

### State 3: Recording - Optimal Volume
```
Volume Levels:
RMS:  ██████░░░░░░░░ RMS: 0.45
Peak: ██████████░░░░ Peak: 0.78
```
✅ Perfect recording levels!

### State 4: Recording - High Volume
```
Volume Levels:
RMS:  ████████████░░ RMS: 0.85
Peak: █████████████░ Peak: 0.95
```
⚠️ Getting close to clipping - reduce gain or move away

### State 5: Recording - Clipping!
```
Volume Levels:
RMS:  █████████████░ RMS: 0.92
Peak: ██████████████ Peak: 1.00
```
🚨 CLIPPING! Reduce microphone gain immediately!

## Color Coding (Future Enhancement)
While the current implementation uses the default DearPyGUI progress bar styling, future versions could add color coding:

```
┌─ Optimal Range ──┐
│ Green:  0.00-0.70 │ Safe range
│ Yellow: 0.70-0.90 │ Getting loud
│ Red:    0.90-1.00 │ Clipping danger!
└──────────────────┘
```

## Real-Time Behavior

The meters update every audio chunk (default 1.0 second):

```
Time 0.0s:  RMS: 0.00  Peak: 0.00  [Not recording]
Time 1.0s:  RMS: 0.42  Peak: 0.65  [Speaking]
Time 2.0s:  RMS: 0.38  Peak: 0.58  [Speaking]
Time 3.0s:  RMS: 0.03  Peak: 0.08  [Silence]
Time 4.0s:  RMS: 0.55  Peak: 0.82  [Louder speech]
Time 5.0s:  RMS: 0.00  Peak: 0.00  [Recording stopped]
```

## Integration with Other Nodes

### Example: Microphone + Spectrogram
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ Microphone  │     │ Spectrogram  │     │ Result Image │
│             │     │              │     │              │
│ RMS:  0.45  │────►│ Method: mel  │────►│   [Visual    │
│ Peak: 0.78  │     │              │     │   output]    │
└─────────────┘     └──────────────┘     └──────────────┘
```

The volume meters help you:
1. Verify microphone is capturing audio
2. Ensure adequate signal level for the spectrogram
3. Avoid clipping that would distort the visualization

## User Workflow

### Quick Check (5 seconds)
1. Add Microphone node
2. Click "Start"
3. Make noise
4. See meters move? ✅ Working!

### Proper Setup (2 minutes)
1. Add Microphone node
2. Configure sample rate and device
3. Click "Start"
4. Speak normally while watching meters
5. Adjust position/gain until:
   - RMS: 0.30-0.60 ✅
   - Peak: < 0.90 ✅
6. Ready to record!

## Technical Details

### Meter Update Rate
- Updates: Once per audio chunk
- Chunk duration: 0.1s to 5.0s (configurable)
- Default: 1.0s (1 Hz update rate)

### Calculation Performance
- RMS calculation: ~0.5ms for 44100 samples
- Peak calculation: ~0.3ms for 44100 samples
- Total overhead: < 1ms (negligible)

### Meter Range
- Minimum: 0.00 (silence)
- Maximum: 1.00 (full scale)
- Resolution: 0.01 (2 decimal places)

## Keyboard Shortcuts
(Standard DearPyGUI node operations)
- Click "Start" button: Toggle recording
- Delete key (node selected): Remove node
- No special shortcuts for meters (read-only display)

## Accessibility
- Numerical overlay: Exact values for precise monitoring
- Visual bar: Quick glance reference
- Both metrics shown: RMS and Peak for complete picture

---

**Note**: This is a visual representation. The actual implementation uses DearPyGUI's native progress bar widgets with the default styling. The bars fill from left to right proportionally to the volume level (0.0 = empty, 1.0 = full).
