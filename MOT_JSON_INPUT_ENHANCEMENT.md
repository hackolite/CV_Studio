# MOT JSON Input Enhancement

## Summary

This enhancement adds a dedicated JSON input (Input04) to the MOT (Multiple Object Tracking) node to receive detection data from ReId or ObjectDetection nodes, enabling proper tracking of re-identified objects.

## Problem Statement

Previously, the MOT node could only receive detection data implicitly through the image source node. This made it difficult to:
1. Explicitly connect detection JSON from ReId to MOT
2. Separate boolean control (start/stop) from detection data
3. Visualize the data flow in the node editor UI

## Solution

Added a fourth JSON input (Input04) to the MOT node specifically for detection data, while keeping Input03 for boolean start/stop control.

## Changes Made

### 1. MOT Node Structure (`node/TrackerNode/node_mot.py`)

**New Input:**
- `Input04`: JSON input for detection data (bboxes, scores, class_ids, class_names)

**Existing Inputs:**
- `Input01`: Image (for visualization)
- `Input02`: Text (tracker selection dropdown)
- `Input03`: JSON (boolean for enable/disable tracking)

**Outputs:**
- `Output01`: Image (annotated with tracking)
- `Output02`: TIME_MS (processing time)
- `Output03`: JSON (tracking data with track_ids)

### 2. Connection Logic

The MOT node now:
1. Distinguishes between Input03 (boolean control) and Input04 (detection data) by checking the destination tag
2. Prioritizes Input04 for detection data when connected
3. Falls back to getting data from the image source node (backward compatible)
4. No longer checks source node type (ObjectDetection/ReId/Classification) - works with any source

### 3. Pipeline Flow

```
ObjectDetection Node
  ├─ Output01 (Image) ────────────────┐
  └─ Output03 (JSON: detections) ─┐   │
                                  │   │
                                  ↓   ↓
                            ReId Node
                              ├─ Output01 (Image) ─────────────────┐
                              └─ Output03 (JSON: reid labels) ─┐   │
                                                               │   │
Boolean Control (start/stop) ──────────────────────────┐       │   │
                                                       │       │   │
                                                       ↓       ↓   ↓
                                                     MOT Node
                                                       ├─ Input01 (Image)
                                                       ├─ Input03 (Boolean)
                                                       └─ Input04 (JSON: detections)
                                                         
                                                       ├─ Output01 (Image: tracked)
                                                       └─ Output03 (JSON: track_ids)
```

## Data Format

### ObjectDetection Output
```json
{
  "bboxes": [[x1, y1, x2, y2], ...],
  "scores": [0.95, 0.87, ...],
  "class_ids": [0, 0, ...],
  "class_names": ["person", "person", ...]
}
```

### ReId Output (Modified)
```json
{
  "bboxes": [[x1, y1, x2, y2], ...],
  "scores": [0.95, 0.87, ...],
  "class_ids": [0, 1, ...],              // ReId labels (not class IDs)
  "class_names": ["player1", "player2", ...] // Slot names
}
```

### MOT Output
```json
{
  "bboxes": [[x1, y1, x2, y2], ...],
  "scores": [0.95, 0.87, ...],
  "class_ids": [0, 1, ...],
  "class_names": ["player1", "player2", ...],
  "track_ids": [1, 2, ...],              // Persistent tracking IDs
  "track_id_dict": {1: 0, 2: 1, ...}     // Mapping for visualization
}
```

## Testing

### New Tests
- `tests/test_mot_json_input.py`: Tests MOT Input04 functionality
- `tests/test_complete_pipeline_integration.py`: Tests complete pipeline flow

### Existing Tests (All Pass)
- `tests/test_reid_node.py`: 11 tests for ReId node
- `tests/test_reid_pipeline_integration.py`: Pipeline integration test
- All MOT-related tests remain compatible

## Benefits

1. **Clear UI**: Users can now see explicit JSON connections in the node editor
2. **Flexibility**: Supports both explicit JSON input and legacy implicit mode
3. **ReId Integration**: ReId output can be directly connected to MOT Input04
4. **Separation of Concerns**: Boolean control (Input03) is separate from detection data (Input04)
5. **Backward Compatible**: Existing pipelines continue to work without changes

## Usage Example

### Connect Nodes in UI:
1. Connect `ObjectDetection.Output01` → `ReId.Input01` (Image)
2. Connect `ObjectDetection.Output03` → `ReId.Input02` (JSON detections)
3. Connect `ReId.Output01` → `MOT.Input01` (Image for visualization)
4. Connect `ReId.Output03` → `MOT.Input04` (JSON detection data with ReId labels)
5. Connect `BooleanSource` → `MOT.Input03` (Optional: start/stop control)

### Result:
- MOT tracks objects using ReId labels as distinct identities
- Each "player" is tracked separately with persistent track IDs
- UI shows clear data flow through explicit connections
