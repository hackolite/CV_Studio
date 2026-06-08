# ReId Node - Player Re-Identification

## Overview

The ReId (Re-Identification) node assigns consistent identities to detected objects
(players, people, etc.) across video frames. It uses direct centroid initialisation
from the first frame that contains the expected number of players, and then tracks
each identity with EMA-updated centroids. Feature extraction is pluggable: color
histogram (fallback) or deep OSNet ONNX descriptors.

## Location
- **Domain**: Tracking
- **File**: `node/TrackerNode/node_reid.py`
- **Style**: Blue pastel (Tracking domain color)

## Features

### 1. Slot Management
- **Default Slots**: Initialises with 2 slots (A / B)
- **Add / Remove Slot**: Create or remove identity slots; names are editable
- **Maximum Slots**: Up to 20 identities

### 2. Feature Extraction Methods

| Combo label | Description | Vector dim |
|---|---|---|
| Color Histogram | 16-bin BGR histograms (fallback, no model needed) | 48 |
| OSNet_x0_25 | Lightweight OSNet (fastest) | 512 |
| OSNet_x0_5 | Medium OSNet | 512 |
| OSNet_x1_0 | Full OSNet (highest accuracy) | 512 |

OSNet models (`.onnx`) must be placed in `node/TrackerNode/reid_models/`.
If a model file is missing, the node falls back to Color Histogram automatically.
See `node/TrackerNode/reid_models/README.md` for export instructions.

### 3. Direct Centroid Initialisation
- **Trigger**: The first frame where `len(detections) >= n_slots`
- **Algorithm**: Greedy furthest-point sampling — picks the pair (or N-tuple) of
  feature vectors that maximises pairwise distances, ensuring diverse initial centres.
- **No warmup phase** needed — identities are assigned from the very first eligible frame.
- **Reset button**: Clears centroids so re-initialisation happens on the next eligible frame.

### 4. EMA Centroid Updates
After each assignment the matched centroid is updated:
```
centroid = α × centroid + (1-α) × new_feature    (α = 0.92)
```
This lets centres adapt slowly to gradual appearance changes (lighting, jersey wetness)
while keeping labels stable.

### 5. Re-Identification
- Assigns each detection to its nearest centroid (Euclidean distance in feature space)
- When more detections arrive than slots, the node keeps only the N closest to the
  current centroids (one per slot)
- **JSON output** matches ObjectDetection node format exactly

### 6. Visualization
- Bounding boxes with per-identity color coding
- Custom slot names + score overlaid on boxes

## Inputs

### Input 1: IMAGE
- BGR color frame (NumPy array)

### Input 2: JSON (Object Detection Data)
- `bboxes`: `[[x1,y1,x2,y2], …]`
- `scores`: detection confidences
- `class_ids`: original class ids (overwritten by ReId)
- `class_names`: original class names (overwritten by slot names)

## Outputs

### Output 1: IMAGE
Annotated frame with ReId labels.

### Output 2: TIME_MS (optional)
Processing time (only if `use_pref_counter` is enabled).

### Output 3: JSON
```json
{
  "bboxes":      [[x1,y1,x2,y2], ...],
  "scores":      [0.95, 0.88],
  "class_ids":   [0, 1],
  "class_names": {"0": "A", "1": "B"},
  "timestamp":   1234567890.123
}
```
`class_ids` and `class_names` are the ReId slot assignments, compatible with
Homography and MOT node inputs.

## Usage

```
Video / Camera → Object Detection → ReId → Homography → Display / Record
```

1. Drag the ReId node from the **Tracking** category
2. Connect video frame to **IMAGE** input
3. Connect ObjectDetection JSON output to **JSON** input
4. (Optional) Rename slots (default: A / B)
5. (Optional) Select feature method in the **Method** combo box
6. Hit play — centroids initialise on the first frame with ≥ N players
7. **Reset** button forces re-initialisation if labels drift

## Algorithm Details

### Initialisation (first eligible frame)
1. Extract feature vectors for all `n` detections (`n ≥ n_slots`)
2. Greedy furthest-point sampling:
   - Pick a random starting feature as centroid 0
   - Iteratively add the feature that is furthest from the already-chosen set
3. Store the `n_slots` selected vectors as initial centroids

### Per-frame assignment
1. Extract feature vector for each detected crop
2. For each centroid, compute Euclidean distance to all features
3. Use Hungarian-style greedy matching (closest unmatched detection per centroid)
4. Update matched centroid with EMA

## Limitations

1. **Identity swap on re-occlusion**: centroids can drift if players are occluded for many frames
2. **Lighting changes**: sudden changes may cause temporary mis-assignment until EMA adapts
3. **Similar appearance**: color histograms struggle with same-jersey teams — use OSNet in that case
4. **Slot count fixed after init**: changing slot count triggers a reset

## Testing

```bash
python -m pytest tests/test_reid_node.py tests/test_reid_pipeline_integration.py -v
```

Tests cover: centroid init (exact N / more than N / fewer than N), EMA update,
centroid assignment, feature extraction, output format compatibility, and reset.

## Dependencies

- `numpy`: required
- `opencv-python`: required
- `onnxruntime`: optional (OSNet methods); falls back to Color Histogram if absent

## Version History

- **v0.0.4** (2026-06): Replace KMeans with direct centroid init + EMA updates;
  add OSNet ONNX methods; output dict `class_names`; slot defaults A/B
- **v0.0.2** (2026-01): 2 default slots, K-means cluster count = slot count
- **v0.0.1** (2026-01): Initial K-means implementation
