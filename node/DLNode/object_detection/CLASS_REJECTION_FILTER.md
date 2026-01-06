# Object Detection - Class Rejection Filter

## Overview

The Object Detection node now includes a **Class Rejection Filter** feature that allows you to exclude specific object classes from detection results.

## Usage

### Rejecting Classes

1. In the Object Detection node, locate the **"Reject"** text input field
2. Enter the class IDs you want to reject, separated by commas
3. The specified classes will be filtered out from the detection results

### Examples

**Reject persons (class 0):**
```
0
```

**Reject multiple classes (persons, bicycles, cars):**
```
0, 1, 2
```

**Reject with various spacing formats (all valid):**
```
0,1,2
0, 1, 2
0 , 1 , 2
```

## Class IDs

The class IDs correspond to the classes defined in the COCO dataset or the specific model being used:

**COCO Classes (common):**
- 0: person
- 1: bicycle
- 2: car
- 3: motorcycle
- 5: bus
- 7: truck
- ... (see coco_class_names.py for full list)

## Behavior

- **Empty field:** No classes are rejected (all detections pass through)
- **Invalid IDs:** Non-numeric values are ignored
- **Non-existent classes:** Specifying class IDs that don't appear in detections has no effect
- **Rejected classes:** Are completely removed from:
  - The visual output (bounding boxes and labels)
  - The JSON output (detection data)
  - Downstream nodes (tracking, counting, etc.)

## Use Cases

1. **Privacy**: Reject person detections (class 0) to avoid detecting people in sensitive areas
2. **Focus on specific objects**: Reject irrelevant classes to focus on objects of interest
3. **Performance**: Reduce processing load by filtering out unwanted detections early
4. **Downstream processing**: Simplify data for nodes that only care about specific object types

## Technical Details

- The filter is applied **after** NMS (Non-Maximum Suppression)
- The filter preserves the order of remaining detections
- The filter works with all supported object detection models (YOLOX, YOLO11, FreeYOLO, etc.)
- Settings are saved/restored when loading/saving the node graph

## Example Workflow

```
[Video Input] 
    ↓
[Object Detection] (Reject: 0,1,2)  ← Reject persons, bicycles, cars
    ↓
[Tracking/Counting] ← Only receives detections for other classes
    ↓
[Result Display]
```
