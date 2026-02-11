# Node Selection Enhancement - Visual Guide

## Summary
This enhancement improves the visual feedback when a node is selected in the CV Studio editor by making the title bar **brighter and more saturated**.

## What Changed

### Before
Selected nodes had **the same color** as unselected nodes - there was no visual distinction making it hard to tell which node was selected.

### After
Selected nodes now have:
- **20% brighter** colors (capped at maximum brightness)
- **15% more saturated** colors (more vibrant, less gray)
- The enhancement preserves the color's hue while making it more prominent

## Color Examples

Here are some example transformations for different node categories:

| Node Category | Original Color | Selected Color | Brightness Increase |
|--------------|----------------|----------------|---------------------|
| Input        | #ffff99 (pastel yellow) | #ffffaf (bright yellow) | 3.3% |
| VisionProcess | #90ee90 (pastel green) | #a7ffa7 (bright green) | 12.0% |
| VisionModel  | #ffdab9 (peach) | #ffffda (bright peach) | 10.6% |
| AudioProcess | #b0e0e6 (powder blue) | #ceffff (bright blue) | 13.7% |
| Trigger      | #dda0dd (plum) | #ffb9ff (bright plum) | 15.4% |
| System       | #c0c0c0 (gray) | #e6e6e6 (bright gray) | 19.8% |

## Technical Details

The enhancement is applied through:
1. **Saturation boost** (1.15x) - Applied first to preserve color relationships
2. **Brightness boost** (1.2x) - Applied second to increase overall luminance
3. All values are clamped to the valid RGB range (0-255)
4. Alpha channel is preserved unchanged

## User Experience Impact

Users will now be able to:
- ✅ Clearly see which node is currently selected
- ✅ Quickly identify the active node when editing parameters
- ✅ Better distinguish between selected and unselected nodes in complex workflows
- ✅ Navigate the node editor more efficiently

## Code Location

The enhancement is implemented in `/node_editor/node_main.py`:
- `_enhance_color_for_selection()` function performs the color transformation
- `node_style()` function applies the enhanced color to `mvNodeCol_TitleBarSelected`
- Constants `_SELECTION_SATURATION_BOOST` and `_SELECTION_BRIGHTNESS_BOOST` control the enhancement intensity
