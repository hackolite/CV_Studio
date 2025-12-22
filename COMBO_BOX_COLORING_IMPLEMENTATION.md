# Combo Box Coloring Implementation

## Overview
This implementation adds color styling to combo boxes (drop-down lists) within nodes, matching their parent node's color scheme.

## Changes Made

### Modified: `node_editor/node_editor.py`

The `node_style()` function now includes theme components for combo boxes:

```python
def node_style(module_name):
    tuple_style = STYLE[module_name]["style"][0]
    # Constant for text color to ensure consistency
    TEXT_COLOR_BLACK = (0, 0, 0, 255)
    
    with dpg.theme() as custom_theme:
        with dpg.theme_component(dpg.mvNode):
            # Node styling (title bar, etc.)
            ...
        
        # Add combo box (drop list) styling with node color
        with dpg.theme_component(dpg.mvCombo):
            # Use the node's color for combo box background
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBg, tuple_style, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgHovered, tuple_style, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_FrameBgActive, tuple_style, category=dpg.mvThemeCat_Core
            )
            # Keep text in black for readability
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, TEXT_COLOR_BLACK, category=dpg.mvThemeCat_Core
            )
    return custom_theme
```

## How It Works

1. **Theme Application**: When a node's theme is bound using `dpg.bind_item_theme(node.tag_node_name, factorynode.style)`, it now applies to both:
   - The node itself (title bar coloring)
   - All combo boxes within that node (background coloring)

2. **Color Source**: The colors are defined in `node_editor/style.py` under the `STYLE` dictionary for each node category:
   - Input nodes: Yellow pastel `(255, 255, 153, 255)`
   - VisionProcess nodes: Green pastel `(144, 238, 144, 255)`
   - VisionModel nodes: Peach puff pastel `(255, 218, 185, 255)`
   - AudioProcess nodes: Powder blue pastel `(176, 224, 230, 255)`
   - And more...

3. **Visual Result**: 
   - Combo boxes now have the same pastel color as their parent node's title bar
   - Text remains black for optimal readability
   - Hover and active states maintain the same color

## Example Nodes with Combo Boxes

The following nodes benefit from this implementation:
- `ApplyColorMap` (ProcessNode) - Green pastel combo box
- `VideoWriter` (VideoNode) - Light green pastel combo box
- `Classification` (DLNode) - Peach puff pastel combo box
- `Spectrogram` (AudioProcessNode) - Powder blue pastel combo box
- `Heatmap` (VisualNode) - Light pink combo box
- And all other nodes with combo boxes

## Testing

All existing tests pass:
- ✅ `test_node_style_lookup.py`
- ✅ `test_node_editor_initialization.py`
- ✅ No security vulnerabilities found (CodeQL)

## Commits

- `4ce6c1b`: Add color styling to combo boxes based on node colors
- `d1af9ce`: Refactor: Extract text color constant for consistency
