# Menu Item Coloring Implementation

## Overview
This implementation extends the color theming system to menu items in the node editor's menu bar. Now menu items (droplist items) in the CV Studio interface are colored according to their node category, making it easier to visually identify and organize different types of nodes.

## Problem Statement
Previously, only the nodes themselves were colored after creation. The menu items in the menu bar (Input, VisionProcess, VisionModel, etc.) and their individual node items (WebCam, Video, Resize, etc.) displayed with default colors, making it harder to visually distinguish between different node categories when browsing the menu.

## Solution
Created a new `menu_style()` function in `node_editor/node_editor.py` that generates themes for menu items. This theme is applied to all individual node menu items within each category menu, so users can immediately see which category a node belongs to before adding it to the editor.

## Changes Made

### Modified: `node_editor/node_editor.py`

#### 1. New Function: `menu_style()`

Added a new function to create menu item themes:

```python
def menu_style(module_name):
    """Create a theme for menu items based on node category colors
    
    Args:
        module_name: The category name (Input, VisionProcess, VisionModel, etc.)
    
    Returns:
        A DearPyGUI theme for menu items
    """
    tuple_style = STYLE[module_name]["style"][0]
    TEXT_COLOR_BLACK = (0, 0, 0, 255)
    
    with dpg.theme() as menu_theme:
        with dpg.theme_component(dpg.mvMenuItem):
            # Menu item background color
            dpg.add_theme_color(
                dpg.mvThemeCol_Header, tuple_style, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderHovered, tuple_style, category=dpg.mvThemeCat_Core
            )
            dpg.add_theme_color(
                dpg.mvThemeCol_HeaderActive, tuple_style, category=dpg.mvThemeCat_Core
            )
            # Keep text in black for readability
            dpg.add_theme_color(
                dpg.mvThemeCol_Text, TEXT_COLOR_BLACK, category=dpg.mvThemeCat_Core
            )
    return menu_theme
```

#### 2. Theme Application in Menu Creation

Modified the menu creation loop to:
1. Create a menu theme for each category
2. Apply the theme to each menu item within that category

```python
for menu_info in menu_dict.items():
    menu_label = menu_info[0]
    
    # Create menu theme for this category
    category_menu_theme = menu_style(menu_label)
    
    with dpg.menu(label=menu_label):
        # ... load nodes ...
        
        menu_item_tag = "Menu_" + factorynode.node_tag
        dpg.add_menu_item(
            tag=menu_item_tag,
            label=factorynode.node_label,
            callback=self._callback_add_node,
            user_data=factorynode.node_tag,
        )
        
        # Apply the menu theme to this menu item
        dpg.bind_item_theme(menu_item_tag, category_menu_theme)
```

## How It Works

1. **Theme Creation**: When the node editor initializes, for each menu category (Input, VisionProcess, etc.), a menu theme is created using `menu_style()`.

2. **Theme Application**: Each menu item within a category menu gets the theme applied via `dpg.bind_item_theme()`.

3. **Color Source**: Colors come from `node_editor/style.py`:
   - **Input nodes**: Yellow pastel `(255, 255, 153, 255)`
   - **VisionProcess nodes**: Green pastel `(144, 238, 144, 255)`
   - **VisionModel nodes**: Peach puff pastel `(255, 218, 185, 255)`
   - **AudioProcess nodes**: Powder blue pastel `(176, 224, 230, 255)`
   - **AudioModel nodes**: Pink pastel `(255, 192, 203, 255)`
   - **Visual nodes**: Light pink `(255, 182, 193, 255)`
   - **Video nodes**: Very light green pastel `(193, 255, 193, 255)`
   - **System nodes**: Silver gray pastel `(192, 192, 192, 255)`
   - And all other categories with their respective colors

4. **Visual Consistency**: Menu items display with:
   - Background color matching the node category color
   - Black text for optimal readability
   - Consistent hover and active states

## Examples of Colored Menu Items

### Input Menu (Yellow Pastel)
- WebCam
- Video
- RTSP
- YouTubeInput
- VideoSetFramePos

### VisionProcess Menu (Green Pastel)
- Resize
- Crop
- Zoom
- Grayscale
- ApplyColorMap
- Threshold

### VisionModel Menu (Peach Puff Pastel)
- Classification
- ObjectDetection
- PoseEstimation
- SemanticSegmentation
- FaceDetection

### AudioProcess Menu (Powder Blue Pastel)
- Spectrogram

### Visual Menu (Light Pink)
- Heatmap
- ObjChart
- Visual

### Video Menu (Very Light Green Pastel)
- ImageConcat
- VideoWriter
- ScreenCapture
- DynamicPlay

### System Menu (Silver Gray Pastel)
- SyncQueue

## Visual Impact

### Before
- Menu bar menus: Default colors
- Menu items: Default gray/white ✗
- Nodes after creation: Colored title bars ✓

### After
- Menu bar menus: Default colors (unchanged)
- Menu items: Colored by category ✓
- Nodes after creation: Colored title bars ✓

Users can now see at a glance which category each menu item belongs to, making it easier to:
- Find nodes by visual association
- Understand node organization
- Learn the node categorization system

## Testing

### Created: `tests/test_menu_styling.py`

A comprehensive test suite to verify:
- All node categories can create menu themes without errors
- Menu themes are created successfully for all standard categories
- The `menu_style()` function returns valid theme objects

Test results:
```
tests/test_menu_styling.py::TestMenuStyling::test_all_standard_categories PASSED
tests/test_menu_styling.py::TestMenuStyling::test_menu_style_for_audioprocess_category PASSED
tests/test_menu_styling.py::TestMenuStyling::test_menu_style_for_input_category PASSED
tests/test_menu_styling.py::TestMenuStyling::test_menu_style_for_visionmodel_category PASSED
tests/test_menu_styling.py::TestMenuStyling::test_menu_style_for_visionprocess_category PASSED
tests/test_menu_styling.py::TestMenuStyling::test_menu_style_returns_theme PASSED
```

### Existing Tests
All existing tests continue to pass:
- ✅ `test_node_style_lookup.py` - Node style lookups work correctly
- ✅ `test_ui_element_styling.py` - UI element styling unchanged
- ✅ `test_node_editor_initialization.py` - Node editor initializes correctly

## Benefits

1. **Improved Discoverability**: Users can quickly identify node types by color when browsing menus
2. **Visual Consistency**: Menu items now match the color scheme of the nodes they create
3. **Better Organization**: Color-coding helps reinforce the mental model of node categories
4. **Professional Appearance**: Cohesive color scheme throughout the interface
5. **Backward Compatible**: No changes to existing functionality or node behavior
6. **Maintainable**: Single source of truth for colors in `style.py`

## Technical Details

### Styling Properties Applied

**Menu Items**:
- `mvThemeCol_Header`: Background color (normal state)
- `mvThemeCol_HeaderHovered`: Background color (hover state)  
- `mvThemeCol_HeaderActive`: Background color (clicked state)
- `mvThemeCol_Text`: Text color (black for readability)

### Performance
- **Minimal overhead**: Theme objects are created once during initialization
- **Memory efficient**: One theme object per category (15 categories total)
- **Render efficient**: Standard DearPyGUI theming mechanism

## Implementation Notes

1. **Text Color**: All menu items maintain black text (`TEXT_COLOR_BLACK = (0, 0, 0, 255)`) for optimal readability against pastel backgrounds.

2. **State Consistency**: All states (normal, hover, active) use the same category color to maintain visual consistency.

3. **Theme Reuse**: Each category creates one theme that is reused for all menu items in that category.

4. **Complementary to Node Styling**: This implementation works alongside the existing `node_style()` function which colors the nodes after creation.

## User Experience

When users open CV Studio and click on a menu in the menu bar:
1. They see a dropdown list of available nodes
2. Each menu item is colored according to its category
3. Hovering over a menu item keeps the same color (better visual feedback)
4. After clicking and adding a node, the node itself also displays the same color

This creates a consistent visual language throughout the interface.

## Future Enhancements

Potential improvements:
1. **Menu Headers**: Color the menu headers themselves (Input, VisionProcess, etc.)
2. **Tooltips**: Add color-coded tooltips showing category information
3. **Custom Colors**: Allow users to customize category colors via settings
4. **Gradient Effects**: Add subtle gradients for visual depth
5. **Icons**: Add category-specific icons alongside colored backgrounds

## Commits

- `befc3bc`: Add menu item coloring based on node categories

## Related Documentation

- `UI_ELEMENT_COLORING_IMPLEMENTATION.md`: Node UI element coloring (inputs, sliders, buttons)
- `COMBO_BOX_COLORING_IMPLEMENTATION.md`: Combo box coloring within nodes
- `node_editor/style.py`: Color definitions for all node categories
- `tests/test_menu_styling.py`: Test suite for menu item styling

## License

This implementation is part of CV Studio and is licensed under the Apache License 2.0.
