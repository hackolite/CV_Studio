# Video-Audio Synchronization Documentation Index

## 📚 Complete Documentation Suite

This directory contains **6 comprehensive documentation files** (2,058 lines total) explaining how the CV Studio Video Node synchronizes video playback with audio spectrogram visualization.

---

## 🎯 Start Here

### New to the Topic?
**Read:** [VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md) (18KB, ~225 lines)
- One-page visual overview
- All 6 steps with ASCII diagrams
- Bilingual (English/French)
- Perfect for quick understanding

### Need to Navigate?
**Read:** [VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md](VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md) (8.3KB, ~270 lines)
- Navigation guide to all docs
- Recommendations based on your needs
- Learning path for beginners to advanced
- Use cases and quick links

---

## 📖 Documentation Files

### 1. Simple Summary (Start Here!) ⭐
**File:** [VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md)
- **Size:** 18KB (~225 lines)
- **Language:** English + French
- **Best for:** Quick overview, visual learners
- **Contains:** One-page summary with ASCII art for all 6 steps

### 2. Documentation Guide (Navigation)
**File:** [VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md](VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md)
- **Size:** 8.3KB (~270 lines)
- **Language:** English
- **Best for:** Finding the right documentation
- **Contains:** Navigation, use cases, learning paths

### 3. Quick Reference (Formulas & Lookup)
**File:** [VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md)
- **Size:** 5.5KB (~165 lines)
- **Language:** English
- **Best for:** Developers, quick lookup, troubleshooting
- **Contains:** Process overview, key parameters, formulas, examples

### 4. Complete Explanation (English)
**File:** [VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md)
- **Size:** 16KB (~485 lines)
- **Language:** English
- **Best for:** Technical understanding, developers, in-depth study
- **Contains:** Detailed step-by-step with code, formulas, examples, performance details

### 5. Complete Explanation (French)
**File:** [SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md)
- **Size:** 15KB (~460 lines)
- **Language:** Français
- **Best for:** French speakers, technical understanding
- **Contains:** Explication détaillée pas à pas avec code, formules, exemples

### 6. Visual Diagrams (Comprehensive)
**File:** [VISUAL_SYNC_DIAGRAMS.md](VISUAL_SYNC_DIAGRAMS.md)
- **Size:** 31KB (~453 lines)
- **Language:** English
- **Best for:** Visual learners, presentations, detailed flowcharts
- **Contains:** Extensive ASCII diagrams for every step and concept

---

## 🔍 What Each Document Covers

All documents explain these 6 steps:

1. **Split Audio and Video**
   - FFmpeg extraction
   - 22,050 Hz audio sampling
   
2. **Cut Video into Frames**
   - OpenCV frame-by-frame reading
   - Frame counting mechanism

3. **Generate Spectrogram**
   - mel-spectrogram with librosa
   - Parameters: hop_length=512, n_mels=128

4. **Match Frames to Audio**
   - Synchronization formula: `column = (frame/fps) × sr / hop_length`
   - Mathematical precision

5. **Display Scrolling Window**
   - 240-column sliding window
   - Yellow indicator line
   - Smooth scrolling

6. **Play in Node**
   - DearPyGUI display
   - Synchronized updates

---

## 🎓 Recommended Reading Order

### Beginner Path
1. [Simple Summary](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md) - Get the big picture
2. [Quick Reference](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) - Understand key concepts
3. [Visual Diagrams](VISUAL_SYNC_DIAGRAMS.md) - See it visually

### Developer Path
1. [Quick Reference](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) - Key formulas
2. [Complete Explanation](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md) - Deep dive
3. Review code in `node/InputNode/node_video.py`

### Visual Learner Path
1. [Simple Summary](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md) - One-page overview
2. [Visual Diagrams](VISUAL_SYNC_DIAGRAMS.md) - Detailed diagrams
3. [Documentation Guide](VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md) - Fill in gaps

---

## 🌐 Language Support

- **English:**
  - VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md (bilingual)
  - VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md
  - VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md
  - VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md
  - VISUAL_SYNC_DIAGRAMS.md

- **Français:**
  - VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md (bilingue)
  - SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md

---

## ⚡ Key Formula

Found in all documents:

```python
# Synchronization formula that makes everything work
spectrogram_column = (video_frame / fps) × sample_rate / hop_length

# Standard values:
fps = 30              # frames per second (video)
sample_rate = 22050   # samples per second (audio)
hop_length = 512      # samples per spectrogram column

# Example:
# Frame 900 → 30s → 661,500 samples → Column 1,292
```

---

## 📂 Implementation

**Primary file:** `node/InputNode/node_video.py`

**Key methods:**
- `_prepare_spectrogram()` (lines 286-402) - Audio extraction and spectrogram generation
- `update()` (lines 408-580) - Frame-by-frame synchronization and display

**Storage:**
- `_spectrogram_array[node_id]` - Full spectrogram (128 × N)
- `_spectrogram_meta[node_id]` - Metadata (sr, hop_length, fps)
- `_frame_count[node_id]` - Current video frame

---

## ✨ Benefits

All documents explain these benefits:

✅ **Perfect synchronization** - Mathematical precision  
✅ **Frame-by-frame accuracy** - Every frame matches exact audio moment  
✅ **Readable display** - 1:1 pixel mapping, no compression  
✅ **Smooth scrolling** - Window slides continuously  
✅ **Efficient** - Heavy computation once at load  
✅ **Loop support** - Proper reset when video loops  

---

## 📊 Statistics

- **Total files:** 6
- **Total lines:** 2,058
- **Total size:** ~94KB
- **Languages:** English + French
- **Diagrams:** 30+ ASCII diagrams
- **Code examples:** 50+ snippets
- **Formulas:** Complete mathematical derivations

---

## 🔗 Quick Links

| Document | Purpose | Size | Lines |
|----------|---------|------|-------|
| [Simple Summary](VIDEO_AUDIO_SYNC_SIMPLE_SUMMARY.md) | Quick overview | 18KB | ~225 |
| [Doc Guide](VIDEO_AUDIO_SYNC_DOCUMENTATION_GUIDE.md) | Navigation | 8.3KB | ~270 |
| [Quick Reference](VIDEO_AUDIO_SYNC_QUICK_REFERENCE.md) | Lookup | 5.5KB | ~165 |
| [Complete (EN)](VIDEO_AUDIO_SYNCHRONIZATION_EXPLAINED.md) | Deep dive | 16KB | ~485 |
| [Complete (FR)](SYNCHRONISATION_VIDEO_AUDIO_EXPLIQUEE.md) | Approfondi | 15KB | ~460 |
| [Visual Diagrams](VISUAL_SYNC_DIAGRAMS.md) | Diagrams | 31KB | ~453 |

---

## 💡 Tips

- Start with the **Simple Summary** for a quick understanding
- Use the **Documentation Guide** to find what you need
- Keep the **Quick Reference** handy for formulas
- Read the **Complete Explanation** for deep understanding
- Study the **Visual Diagrams** to see the flow

---

## 📞 Related Documentation

- [SPECTROGRAM_SCROLLING_FIX.md](SPECTROGRAM_SCROLLING_FIX.md) - Implementation details
- [SPECTROGRAM_VIDEO_LOOP_FIX.md](SPECTROGRAM_VIDEO_LOOP_FIX.md) - Loop fix
- [SPECTROGRAM_SYNC_FEATURE.md](SPECTROGRAM_SYNC_FEATURE.md) - Original feature
- [VISUAL_EXPLANATION.md](VISUAL_EXPLANATION.md) - Before/after comparison

---

**Last Updated:** October 2025  
**Documentation Version:** 1.0  
**Implementation:** CV Studio Video Node
