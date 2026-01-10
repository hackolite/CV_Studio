# Object Detection - Class Rejection Filter

## Overview

The Object Detection node now includes a **Class Rejection Filter** feature that allows you to exclude specific object classes from detection results.

## Usage

### Rejecting Classes

1. In the Object Detection node, locate the **"Reject"** dropdown field
2. Select the class you want to reject from the dropdown list (e.g., "0: person")
3. The dropdown shows all available classes in the format "ID: name"
4. **The dropdown automatically updates** when you change the model selection to show only the classes available for the selected model
5. The specified classes will be filtered out from the detection results

**Note:** When you switch models (e.g., from YOLOX to YOLOTENNIS), the rejected classes selection is automatically cleared to prevent invalid class IDs. You'll need to reselect any classes you want to reject for the new model.

### Examples

**Reject persons (class 0):**
Select "0: person" from the dropdown, or manually enter:
```
0
```

**Reject multiple classes (persons, bicycles, cars):**
You can manually enter comma-separated values in the dropdown:
```
0, 1, 2
```

Or use the dropdown format:
```
0: person, 1: bicycle, 2: car
```

**Backward compatibility:**
The filter still supports the legacy text format:
```
0,1,2
0, 1, 2
0 , 1 , 2
```

## Class IDs

The class IDs correspond to the classes defined in the COCO dataset or the specific model being used. The dropdown automatically displays the correct classes for the selected model.

**COCO Classes (YOLOX, YOLO11, FreeYOLO):**
- 0: person
- 1: bicycle
- 2: car
- 3: motorcycle
- 5: bus
- 7: truck
- ... (see coco_class_names.py for full list)

**Light-Weight Person Detector:**
- 0: person

**Tennis Model (YOLOTENNIS):**
- 0: player1
- 1: player2
- 2: ball

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
