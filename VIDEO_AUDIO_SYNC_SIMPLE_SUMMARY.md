# Video-Audio Synchronization: Simple Visual Summary

## The Complete Process in One Page

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 1: SÉPARER AUDIO ET VIDÉO / STEP 1: SPLIT AUDIO AND VIDEO   │
│                                                                      │
│  Input: video.mp4                                                   │
│  ┌────────────────────────────────────────────────┐                 │
│  │  Video + Audio (combined)                      │                 │
│  └────────────────────────────────────────────────┘                 │
│                        │                                             │
│                        │ ffmpeg extraction                           │
│                        ▼                                             │
│       ┌────────────────┴────────────────┐                           │
│       │                                 │                           │
│       ▼                                 ▼                           │
│  ┌─────────┐                    ┌──────────────┐                   │
│  │ VIDEO   │                    │ AUDIO        │                   │
│  │ Frames  │                    │ 22,050 Hz    │                   │
│  └─────────┘                    └──────────────┘                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 2: DÉCOUPER EN FRAMES / STEP 2: CUT INTO FRAMES             │
│                                                                      │
│  Video stream → Individual frames                                   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐                           │
│  │Frame │  │Frame │  │Frame │  │Frame │  ...                       │
│  │  0   │  │  1   │  │  2   │  │  3   │                            │
│  └──────┘  └──────┘  └──────┘  └──────┘                           │
│      ↑                                                               │
│      └─ frame_count increments (0, 1, 2, 3...)                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 3: SPECTROGRAMME / STEP 3: SPECTROGRAM                       │
│                                                                      │
│  Audio samples → Spectrogram columns                                │
│                                                                      │
│  Audio: [0.1, 0.2, -0.1, 0.3, ...] (22,050 samples/sec)            │
│            │                                                         │
│            │ librosa.feature.melspectrogram()                       │
│            │ hop_length = 512 samples per column                    │
│            ▼                                                         │
│  ┌───────────────────────────────────────────┐                      │
│  │  Spectrogram (128 mels × N columns)      │                      │
│  │                                           │                      │
│  │  High freq: ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓          │                      │
│  │  Mid freq:  ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓          │                      │
│  │  Low freq:  ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓ ▓▓▓          │                      │
│  │             ─────────────────→             │                      │
│  │                 Time                       │                      │
│  └───────────────────────────────────────────┘                      │
│                                                                      │
│  Each column = 512 samples = 0.023 seconds                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 4: FAIRE CORRESPONDRE / STEP 4: MATCH FRAMES                │
│                                                                      │
│  The KEY formula that synchronizes everything:                      │
│                                                                      │
│  Frame Number → Time → Audio Sample → Spectrogram Column            │
│                                                                      │
│  Example at 30 FPS:                                                 │
│                                                                      │
│  Frame 900                                                           │
│      │                                                               │
│      │ ÷ 30 fps                                                     │
│      ▼                                                               │
│  30.0 seconds                                                        │
│      │                                                               │
│      │ × 22,050 sr                                                  │
│      ▼                                                               │
│  661,500 samples                                                     │
│      │                                                               │
│      │ ÷ 512 hop_length                                             │
│      ▼                                                               │
│  Column 1,292                                                        │
│                                                                      │
│  Formula: column = (frame / fps) × sr / hop_length                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 5: FENÊTRE DÉFILANTE / STEP 5: SCROLLING WINDOW             │
│                                                                      │
│  Full spectrogram (too big to display):                             │
│  [████████████████████████████████████████████████] (N columns)     │
│                         ▲                                            │
│                    Current position                                  │
│                                                                      │
│  Extract window (240 columns centered):                             │
│                   [█████████|█████████]                             │
│                             ▲                                        │
│                       Yellow line                                    │
│                                                                      │
│  As video plays:                                                    │
│  t=0s:   [|████]  ──────────────────────────                        │
│  t=10s:  ────[███|███]  ────────────────────                        │
│  t=30s:  ────────────────[███|███]  ────────                        │
│  t=60s:  ──────────────────────────────[███|]                       │
│                                                                      │
│  Window scrolls smoothly with playback!                             │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ÉTAPE 6: JOUER DANS LE NODE / STEP 6: PLAY IN NODE                │
│                                                                      │
│  ┌─────────────────────────────────────────┐                        │
│  │  Video Node                             │                        │
│  ├─────────────────────────────────────────┤                        │
│  │  [Select Movie]                         │                        │
│  ├─────────────────────────────────────────┤                        │
│  │  ┌───────────────────────────────────┐  │                        │
│  │  │                                   │  │                        │
│  │  │   Video Frame (current)           │  │                        │
│  │  │                                   │  │                        │
│  │  └───────────────────────────────────┘  │                        │
│  ├─────────────────────────────────────────┤                        │
│  │  ☑ Show Spectrogram                    │                        │
│  │  ┌───────────────────────────────────┐  │                        │
│  │  │  ▓▓▓▓▓▓|▓▓▓▓▓▓▓                   │  │  ← Scrolling window  │
│  │  │  ▓▓▓▓▓▓|▓▓▓▓▓▓▓                   │  │     with yellow line  │
│  │  │  ▓▓▓▓▓▓|▓▓▓▓▓▓▓                   │  │                        │
│  │  └───────────────────────────────────┘  │                        │
│  ├─────────────────────────────────────────┤                        │
│  │  ☑ Loop                                 │                        │
│  │  [Start]                                │                        │
│  └─────────────────────────────────────────┘                        │
│                                                                      │
│  Both update together every frame → Perfect sync!                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Key Points / Points Clés

### 🎯 The Magic Formula
```python
# This ONE formula keeps everything synchronized
spectrogram_column = (video_frame / fps) × sample_rate / hop_length

# Valeurs standards / Standard values:
fps = 30              # frames per second
sample_rate = 22050   # audio samples per second
hop_length = 512      # samples per spectrogram column
```

### 🔄 The Synchronization Loop
```
Every frame during playback:
1. Read next video frame (frame_count++)
2. Calculate matching spectrogram column (formula above)
3. Extract 240-column window centered at that column
4. Draw yellow line in center of window
5. Update both displays (video + spectrogram)
→ User sees perfectly synchronized video and audio visualization!
```

### ⚡ Performance
- **Heavy work (ONCE at load):**
  - Extract audio from video
  - Generate full spectrogram
  - Total: ~2-5 seconds
  
- **Light work (EVERY frame):**
  - Calculate column number (math)
  - Extract window (array slice)
  - Draw line (1 line operation)
  - Total: < 5ms per frame

### ✨ Why It Works
1. **Mathematical precision:** Formula guarantees exact matching
2. **Pre-computation:** Spectrogram generated once, reused
3. **Efficient display:** Only show what's needed (240 columns)
4. **Smooth scrolling:** Window slides continuously
5. **Visual feedback:** Yellow line shows exact position

## Example Timeline / Exemple de Chronologie

For a 60-second video at 30 FPS:

```
Time    Frame    Sample      Column   What You See
────    ─────    ──────      ──────   ────────────────────────
0s      0        0           0        Window at start
1s      30       22,050      43       Window moving right
10s     300      220,500     430      Window scrolling
30s     900      661,500     1,292    Window centered
60s     1,800    1,323,000   2,584    Window at end
```

## Files / Fichiers

**Implementation:**
- `node/InputNode/node_video.py` - Main code

**Documentation:**
- `VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md` - Navigation guide
- `VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md` - Quick reference
- `VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md` - Complete guide (English)
- `SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md` - Guide complet (Français)
- `VISUAL_SYNC_DIAGRAMS.md` - Visual diagrams

## Summary / Résumé

**EN:** The system splits video and audio, processes video frame-by-frame, generates an audio spectrogram, matches each video frame to a spectrogram column using precise math, and displays a scrolling window with a yellow indicator showing the current position. Everything stays perfectly synchronized!

**FR:** Le système sépare la vidéo et l'audio, traite la vidéo image par image, génère un spectrogramme audio, fait correspondre chaque image vidéo à une colonne du spectrogramme avec des maths précises, et affiche une fenêtre défilante avec un indicateur jaune montrant la position actuelle. Tout reste parfaitement synchronisé !

---

**🎉 That's it! C'est tout! Simple, non? 🎉**
