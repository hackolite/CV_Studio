# Documentation Guide: Video-Audio Synchronization

## What You're Looking For

This guide helps you find the right documentation for your needs.

---

## 🚀 Quick Start

**Just want to understand the basics?**  
→ Start here: [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md)

**Need step-by-step technical details?**  
→ Read: [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)

**Préférez-vous le français?**  
→ Lisez: [SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md)

**Like visual diagrams and flowcharts?**  
→ See: [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md)

---

## 📚 Documentation Files

### 1. [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md)
**Best for:** Quick lookup, formulas, troubleshooting  
**Length:** ~5 pages  
**Language:** English  
**Contains:**
- Process overview (5 steps)
- Key parameters table
- Synchronization formula
- Example timeline
- Troubleshooting guide

---

### 2. [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)
**Best for:** Complete understanding, developers, technical readers  
**Length:** ~16 pages  
**Language:** English  
**Contains:**
- Detailed explanation of each step
- Code examples with line numbers
- Mathematical formulas with examples
- Performance optimizations
- Complete data flow diagrams
- Practical examples (30s, 60s videos)
- Benefits and technical details

**Key sections:**
1. Step 1: Splitting Audio and Video
2. Step 2: Video Frame Extraction  
3. Step 3: Audio Spectrogram Generation
4. Step 4: Frame-by-Frame Synchronization
5. Step 5: Scrolling Window Display
6. Step 6: Playing in the Node

---

### 3. [SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md)
**Best for:** French speakers, complete understanding  
**Length:** ~15 pages  
**Language:** Français  
**Contains:**
- Explication détaillée de chaque étape
- Exemples de code avec numéros de ligne
- Formules mathématiques avec exemples
- Optimisations de performance
- Diagrammes de flux de données complets
- Exemples pratiques (vidéos de 30s, 60s)
- Avantages et détails techniques

**Sections principales:**
1. Étape 1 : Séparation Audio et Vidéo
2. Étape 2 : Découpage de la Vidéo en Frames
3. Étape 3 : Génération du Spectrogramme Audio
4. Étape 4 : Correspondance Frame par Frame
5. Étape 5 : Fenêtre de Défilement
6. Étape 6 : Lecture dans le Nœud

---

### 4. [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md)
**Best for:** Visual learners, presentations, quick understanding  
**Length:** ~21 pages  
**Language:** English  
**Contains:**
- ASCII art diagrams
- Process flowcharts
- Step-by-step visual representations
- Timeline alignments
- Window scrolling visualization
- Complete data flow diagrams
- Performance optimization diagrams

**Key diagrams:**
- Process Overview Diagram
- Audio-Video Split
- Video Frame Extraction Loop
- Spectrogram Generation (FFT → Mel → Color)
- Frame-to-Spectrogram Synchronization
- Scrolling Window Display
- Node Interface Layout
- Complete Data Flow Timeline

---

## 🎯 Use Cases

### "I want to understand the basic concept"
→ [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) (Section: Process Overview)

### "I need to know the exact formula"
→ [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) (Section: Synchronization Formula)

### "I want to see how it works step by step"
→ [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md) (All steps)

### "I prefer visual explanations"
→ [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md) (All diagrams)

### "I'm debugging a synchronization issue"
→ [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) (Section: Troubleshooting)

### "I want to modify the code"
→ [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md) (Section: Files Modified + Code examples)

### "Je veux comprendre en français"
→ [SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md) (Toutes les sections)

---

## 🔍 Key Concepts Explained

### What does "split audio and video" mean?
The video file contains two streams (video frames + audio samples). We separate them to process independently. The audio is extracted at 22,050 samples per second.

### What does "cut into frames" mean?
Video is a sequence of still images (frames). At 30 FPS, we read 30 frames per second. Each frame is numbered (0, 1, 2, 3...).

### What is a "spectrogram"?
A visual representation of audio where:
- X-axis = time progression
- Y-axis = frequency (low to high)
- Color = energy/loudness (dark = quiet, bright = loud)

### How do frames match spectrogram columns?
Using this mathematical formula:
```
video_frame → time_in_seconds → audio_sample → spectrogram_column

Example: Frame 900 → 30s → 661,500 samples → Column 1,292
```

### What is the "scrolling window"?
Instead of showing the entire spectrogram (compressed and unreadable), we show only 240 columns at a time, centered at the current position. As the video plays, this window slides along, creating a scrolling effect.

---

## 📊 Quick Facts

| Metric | Value |
|--------|-------|
| Audio sample rate | 22,050 Hz |
| Spectrogram hop length | 512 samples |
| Spectrogram frequency bands | 128 mel-bands |
| Typical video FPS | 30 frames/second |
| Display window width | 240 columns |
| Indicator color | Yellow (BGR: 0, 255, 255) |
| Time per spectrogram column | ~0.023 seconds |
| Time per video frame (30 FPS) | ~0.033 seconds |

---

## 🛠️ Implementation Details

**Primary file:** `node/InputNode/node_video.py`

**Key methods:**
- `_prepare_spectrogram()` - Extracts audio and generates spectrogram
- `update()` - Synchronizes playback frame-by-frame

**Data structures:**
- `_spectrogram_array[node_id]` - Full spectrogram (128 × N columns)
- `_spectrogram_meta[node_id]` - Metadata (sr, hop_length, fps)
- `_frame_count[node_id]` - Current video frame number
- `_video_capture[node_id]` - OpenCV VideoCapture object

---

## 🌟 Benefits

✅ **Perfect sync** - Mathematical precision ensures audio matches video  
✅ **Frame-accurate** - Every video frame has exact audio correspondence  
✅ **Readable** - 1:1 pixel mapping, no compression in display  
✅ **Smooth** - Window scrolls continuously with playback  
✅ **Efficient** - Heavy computation done once at load, playback is fast  
✅ **Loop support** - Properly resets when video loops  

---

## 📖 Related Documentation

For information about specific fixes and features:
- [SPECTROGRAM_SCROLLING_FIX.md](SPECTROGRAM_SCROLLING_FIX.md) - How scrolling was implemented
- [SPECTROGRAM_VIDEO_LOOP_FIX.md](SPECTROGRAM_VIDEO_LOOP_FIX.md) - Loop synchronization fix
- [SPECTROGRAM_SYNC_FEATURE.md](SPECTROGRAM_SYNC_FEATURE.md) - Original sync implementation
- [VISUAL_EXPLANATION.md](VISUAL_EXPLANATION.md) - Visual before/after comparison

---

## 🎓 Learning Path

**Beginner:**
1. Read [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md)
2. Look at diagrams in [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md)

**Intermediate:**
1. Read complete guide: [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)
2. Study the synchronization formula
3. Understand the scrolling window concept

**Advanced:**
1. Read the implementation in `node/InputNode/node_video.py`
2. Modify parameters and observe effects
3. Implement custom variations

---

## 💡 Tips

- The **hop_length=512** parameter is critical - it's used both in generation and playback
- Frame counting starts at 0
- The yellow indicator line is always centered in the window (except at video start/end)
- Window padding (black pixels) appears only at video boundaries
- The spectrogram is generated once and reused throughout playback

---

## Questions?

If something is unclear:
1. Check the [Quick Reference](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) troubleshooting section
2. Read the relevant step in the [Complete Explanation](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)
3. Look at the [Visual Diagrams](VISUAL_SYNC_DIAGRAMS.md) for that concept
4. Review the actual code in `node/InputNode/node_video.py`

---

**Last Updated:** October 2025  
**Version:** 1.0  
**Maintainer:** CV Studio Team
