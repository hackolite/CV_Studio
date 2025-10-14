# Spectrogram Scrolling Fix - Visual Explanation

## The Problem: "Les spectrogrammes ne défilent pas images par images"

### Before the Fix ❌

Imagine a 5-minute video with audio. The spectrogram has **12,919 columns** representing the entire audio.

```
Full Spectrogram (12,919 columns wide):
[████████████████████████████████████████████████████████████████████████████████]
 ^                          ^                          ^                         ^
 0s                         100s                       200s                      300s

Display Window (240 pixels wide):
[████████████████]  <-- Entire spectrogram COMPRESSED 53:1 into this tiny window!

Result:
- Spectrogram is illegible (too compressed)
- Yellow indicator barely moves
- No sense of scrolling
```

The entire spectrogram was squashed to fit in 240 pixels!

### After the Fix ✅

Now we show a **sliding window** that follows playback:

```
Full Spectrogram (12,919 columns):
[████████████████████████████████████████████████████████████████████████████████]
         [█████████|█████████]  <-- Window shows only 240 columns at 1:1 resolution
                   ▲
              Yellow indicator (centered)

As video plays, the window SLIDES along the spectrogram:

t=0s:    [|███████████] Window at start
t=30s:   ───── [███|███████] Window moved right  
t=60s:   ────────── [███|███████] Window keeps moving
t=150s:  ────────────────────────── [███|███████] Centered
```

## How It Works

### Sliding Window Extraction

```python
# 1. Calculate current position in spectrogram
spectrogram_col = 5000  # Example: at middle of video

# 2. Extract 240-column window centered at current position
window_start = 5000 - 120 = 4880
window_end = 5000 + 120 = 5120
window = full_spectrogram[:, 4880:5120]  # Extract just this slice

# 3. Draw indicator at center of window
indicator_position = 120  # Center of 240-pixel window
draw_yellow_line(window, x=120)

# 4. Display the window (no compression needed!)
display(window)  # Already 240 pixels wide
```

### Visual Example at Different Times

```
Time: 0 seconds
├─ Full spectrogram: [|████████████████████████████████████████]
├─ Window shown:     [|███████████]
└─ Indicator:         ▲ (at left edge, start of video)

Time: 30 seconds  
├─ Full spectrogram: [████|████████████████████████████████████]
├─ Window shown:        [███|███████]
└─ Indicator:              ▲ (centered in window)

Time: 150 seconds (middle)
├─ Full spectrogram: [████████████████████|███████████████████]
├─ Window shown:                    [███|███████]
└─ Indicator:                          ▲ (centered in window)

Time: 299 seconds (end)
├─ Full spectrogram: [████████████████████████████████████████|]
├─ Window shown:                                  [███████████|]
└─ Indicator:                                                 ▲
```

## Key Benefits

### 1. Full Resolution Display
- **Before:** 12,919 columns → 240 pixels = 53:1 compression (illegible)
- **After:** 240 columns → 240 pixels = 1:1 (perfect clarity!)

### 2. Visible Scrolling
- **Before:** Yellow line moves imperceptibly 
- **After:** Window scrolls smoothly, frame by frame

### 3. Readable Frequencies
- **Before:** All frequencies mushed together
- **After:** Can see individual frequency components

### 4. Intuitive Behavior
- **Before:** Static, compressed image
- **After:** Dynamic, scrolling visualization like a spectrogram analyzer

## Code Comparison

### Before (Lines 506-542 old)
```python
# Just show the entire spectrogram (compressed)
spectrogram_bgr = self._spectrogram_array[str(node_id)].copy()

# Draw line somewhere (might be off-screen)
if 0 <= spectrogram_col < spectrogram_bgr.shape[1]:
    cv2.line(spectrogram_bgr, (spectrogram_col, 0), ...)

# Compress entire thing to 240x135
texture = self.convert_cv_to_dpg(spectrogram_bgr, 240, 135)
```

### After (Lines 506-577 new)
```python
# Get full spectrogram
full_spectrogram = self._spectrogram_array[str(node_id)]

# Extract sliding window (240 columns centered at current position)
start_col = max(0, spectrogram_col - 120)
end_col = min(full_spectrogram.shape[1], start_col + 240)
window = full_spectrogram[:, start_col:end_col].copy()

# Draw line in window (always visible!)
indicator_col = spectrogram_col - start_col  # Position within window
cv2.line(window, (indicator_col, 0), ...)

# Display window (already 240 pixels, no compression!)
texture = self.convert_cv_to_dpg(window, 240, 135)
```

## The Result

Users now see:
- ✅ **Smooth scrolling** as video plays
- ✅ **Full frequency detail** at 1:1 resolution  
- ✅ **Always-visible indicator** centered in window
- ✅ **Frame-by-frame updates** for real-time tracking
- ✅ **Professional spectrogram analyzer** experience

Just like professional audio software (Audacity, Adobe Audition, etc.)!
