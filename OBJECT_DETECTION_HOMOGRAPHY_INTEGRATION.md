# Object Detection to Homography Integration

## Issue Résolu / Issue Resolved

**Problème (Français):** 
"Je ne vois pas les joueurs, le point qui represente le joueurs quand je fais object detection domaine visionModel/objectdetection option tennis, c'est le point dans la bounding box, au milieu de la ligne botom de la bounding box. c'est ça qui doit etre envoyé ç l'homographie. je veux aussi que tu affiche les anciennes et nouvelles coordinates. vérifie que les template de minicourt dans visual et dans l'homographie sont les même"

**Translation:**
"I don't see the players, the point that represents the player when I do object detection domain visionModel/objectdetection option tennis, it's the point in the bounding box, in the middle of the bottom line of the bounding box. That's what should be sent to homography. I also want you to display the old and new coordinates. Check that the minicourt templates in visual and in homography are the same"

## Solution Implemented

### 1. Bottom-Center Point Extraction from Bounding Boxes

The Homography node now automatically detects when it receives bounding box data from ObjectDetection and extracts the **bottom-center point** of each bounding box:

```python
# For a bounding box [x1, y1, x2, y2]:
center_x = (x1 + x2) / 2.0  # Horizontal center
bottom_y = y2                # Bottom edge (ground contact point)
player_position = [center_x, bottom_y]
```

**Why bottom-center?**
- Represents where the player's feet touch the ground
- Most accurate representation of player position on the court
- Standard approach in sports tracking systems

### 2. Coordinate Display

Both **original (image)** and **transformed (court)** coordinates are now displayed:

#### Console Output
When the Homography node processes data, it prints:
```
======================================================================
[Homography] Coordinate Transformation:
======================================================================
  Player 1:
    Image coordinates (pixels): (250.0, 380.0)
    Court coordinates (meters): (3.29, 16.04)
  Player 2:
    Image coordinates (pixels): (550.0, 280.0)
    Court coordinates (meters): (8.63, 10.24)
======================================================================
```

#### Visual Display
On the TennisCourt visualization, each player marker shows:
```
Img:(250,380) Court:(3.29,16.04)m
```

### 3. Template Verification

**Verified:** Both Homography and TennisCourt nodes use the **same template**:
- Court width: **10.97 meters** (doubles court)
- Court length: **23.77 meters**
- Origin: Bottom-left corner of doubles court
- 14 keypoints matching the TennisKeyPoints model

## Usage

### Pipeline Setup

1. **PoseEstimation Node** (TennisKeyPoints model)
   - Detects court line keypoints
   - Output: JSON with detected keypoints

2. **ObjectDetection Node** (Tennis/YOLO model)
   - Detects players with bounding boxes
   - Output: JSON with `bboxes`, `scores`, `class_ids`

3. **Homography Node**
   - Input 1: Court keypoints from PoseEstimation
   - Input 2: Bounding boxes from ObjectDetection
   - Automatically extracts bottom-center points
   - Transforms to court coordinates
   - Output: JSON with both image and court coordinates

4. **TennisCourt Node** (Visual)
   - Input: JSON from Homography
   - Displays mini-court with player positions
   - Shows both coordinate systems on visualization

### Example Connection Flow

```
[Video Source] 
    ↓
[PoseEstimation: TennisKeyPoints]
    ↓ JSON (court keypoints)
    ↓
[Homography] ← JSON (player bboxes) ← [ObjectDetection: Tennis/Person]
    ↓ JSON (transformed coordinates)
    ↓
[TennisCourt Visual]
    ↓ Image (mini-court with players)
```

## Technical Details

### Bounding Box Format
ObjectDetection outputs bounding boxes as:
```json
{
  "bboxes": [[x1, y1, x2, y2], ...],
  "scores": [0.95, ...],
  "class_ids": [0, ...]
}
```

Where:
- `x1, y1`: Top-left corner
- `x2, y2`: Bottom-right corner

### Bottom-Center Extraction
The Homography node's `_extract_bottom_center_from_bboxes()` method:
- Detects 'bboxes' field in input JSON
- Calculates `(x1+x2)/2, y2` for each bbox
- Returns numpy array of points for transformation

### Coordinate Transformation
Using OpenCV's homography transformation:
1. Calculate homography matrix from court keypoints
2. Transform bottom-center points to court coordinates
3. Store both original and transformed coordinates in output

## Files Modified

1. **node/StatsNode/node_homography.py**
   - Added `_extract_bottom_center_from_bboxes()` method
   - Modified `update()` to handle bbox input
   - Added console logging for coordinate display

2. **node/VisualNode/node_tennis_court.py**
   - Modified `_draw_transformed_points()` to accept input_points
   - Added coordinate labels on visualization
   - Displays both image and court coordinates

3. **tests/test_object_detection_homography_integration.py** (new)
   - Comprehensive integration tests
   - Tests bbox conversion, transformation, and display

4. **examples/demo_object_detection_homography.py** (new)
   - Demonstration script showing the complete pipeline
   - Example output with coordinate transformation

## Testing

Run the integration tests:
```bash
python tests/test_object_detection_homography_integration.py
```

Run the demonstration:
```bash
python examples/demo_object_detection_homography.py
```

## Benefits

✓ **Accurate Player Positioning**: Bottom-center of bbox represents ground contact point  
✓ **Full Transparency**: Both image and court coordinates are displayed  
✓ **Automatic Conversion**: No manual configuration needed  
✓ **Template Consistency**: Verified matching templates between nodes  
✓ **Console Logging**: Real-time coordinate transformation feedback  
✓ **Visual Feedback**: Coordinates displayed directly on the mini-court  

## Minimal Changes

This implementation follows the principle of minimal changes:
- Added 1 new method to Homography node
- Modified 2 existing methods (1 per node)
- No breaking changes to existing functionality
- Backward compatible with existing pipelines
- All existing tests still pass

## Security

✅ No security vulnerabilities introduced  
✅ Input validation for bbox data  
✅ Bounds checking for transformed coordinates  
✅ Safe numpy array operations  

## References

- Tennis court dimensions: ITF (International Tennis Federation) standard
- Homography transformation: OpenCV `cv2.findHomography()`
- Sports tracking: Standard bottom-center approach for player positioning
