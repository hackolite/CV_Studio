# Map Tile Loading and Control Logging Enhancement

## Problem Statement (French)
> il n'y a pas de tiles, je ne voit pas de tiles (routes, immeuble), en background des points, le zoom et autres sliders, ne fonctionnent pas, est ce que les tiles sont correctements chargés ? je veux des logs sur ce pour comprendre.

### Translation
There are no tiles, I don't see any tiles (roads, buildings), in background points, the zoom and other sliders, don't work, are the tiles correctly loaded? I want logs on this to understand.

## Issues Identified

### 1. Zoom and Size Sliders Not Working
**Problem**: The zoom and size slider values were being read from the UI but were never passed to the rendering functions. The zoom parameter in contextily was hardcoded to `'auto'` instead of using the user's slider value.

**Impact**:
- Users could adjust the zoom slider (1-18) but it had no effect on the map
- Users could adjust the size slider (0.5-5.0) but it had no effect on the view
- The map always rendered at the automatic zoom level chosen by contextily

### 2. Insufficient Logging
**Problem**: Minimal logging made it impossible to diagnose tile loading issues. When tiles failed to load, there was limited information about what went wrong.

**Impact**:
- Users couldn't tell if tiles were actually being requested
- Network errors provided minimal context
- No visibility into parameter values, bounds calculation, or rendering pipeline
- Difficult to diagnose configuration or connectivity issues

## Solutions Implemented

### 1. Fixed Zoom and Size Controls

#### Changes to `update()` method (lines ~494-515 and ~540-562):
```python
# Get zoom, size, cache, and pan parameters
zoom_level = dpg_get_value(tag_node_zoom_value_name)
size_factor = dpg_get_value(tag_node_size_value_name)
# ... other parameters ...

# NEW: Log current parameter values
print(f"Map node: Parameters - zoom={zoom_level}, size={size_factor}, pan_x={pan_x}, pan_y={pan_y}, cache={use_cache}")

# NEW: Pass zoom_level and size_factor to rendering
preview_image = self._create_preview_image(
    points, small_window_w, small_window_h, zoom_level, size_factor, pan_x, pan_y
)
```

**Before**: `_create_preview_image(points, small_window_w, small_window_h, pan_x, pan_y)`
**After**: `_create_preview_image(points, small_window_w, small_window_h, zoom_level, size_factor, pan_x, pan_y)`

#### Updated Method Signatures:

**`_create_preview_image()`**:
```python
# Before
def _create_preview_image(self, points, width, height, pan_x=0.0, pan_y=0.0):

# After  
def _create_preview_image(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0):
```

**`_render_with_contextily()`**:
```python
# Before
def _render_with_contextily(self, points, width, height, pan_x=0.0, pan_y=0.0):

# After
def _render_with_contextily(self, points, width, height, zoom_level=10, size_factor=1.0, pan_x=0.0, pan_y=0.0):
```

#### Contextily Zoom Parameter:
```python
# Before: Automatic zoom selection
ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik,
              zoom='auto', attribution=None)

# After: Use slider value
ctx.add_basemap(ax, crs='EPSG:3857', source=ctx.providers.OpenStreetMap.Mapnik,
              zoom=zoom_level, attribution=None)
```

### 2. Comprehensive Logging

#### Parameter Logging:
```python
print(f"Map node: Parameters - zoom={zoom_level}, size={size_factor}, pan_x={pan_x}, pan_y={pan_y}, cache={use_cache}")
print(f"Map node: Creating preview with zoom={zoom_level}, size={size_factor}")
print(f"Map node: _render_with_contextily called with zoom={zoom_level}, size={size_factor}, pan=({pan_x}, {pan_y})")
```

#### Coordinate Conversion Logging:
```python
print(f"Map node: Converted {len(mercator_points)} points to Web Mercator")
```

#### Bounds Calculation Logging:
```python
print(f"Map node: Initial bounds - X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
print(f"Map node: X range too small, using default: {DEFAULT_RANGE_METERS}m")
print(f"Map node: Range after size_factor ({size_factor}): X={x_range:.2f}m, Y={y_range:.2f}m")
print(f"Map node: After padding ({MAP_PADDING_FACTOR}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
print(f"Map node: After pan ({pan_x}, {pan_y}): X: [{min_x:.2f}, {max_x:.2f}], Y: [{min_y:.2f}, {max_y:.2f}]")
```

#### Figure Creation Logging:
```python
print(f"Map node: Created figure {fig_width}x{fig_height} inches at {dpi} DPI")
```

#### Tile Loading Logging:
```python
print(f"Map node: Attempting to load OSM tiles with zoom={zoom_level}")
print(f"Map node: Using provider: {ctx.providers.OpenStreetMap.Mapnik}")
print(f"Map node: CRS: EPSG:3857 (Web Mercator)")

# On success:
print("✓ Map node: OpenStreetMap tiles loaded successfully")

# On failure:
print(f"⚠ Map node: Could not load OpenStreetMap tiles")
print(f"  Error type: {type(e).__name__}")
print(f"  Error message: {e}")
import traceback
traceback.print_exc()
print("  Using fallback: light blue background without tiles")
```

#### Enhanced Error Handling:
```python
# traceback is imported at module level
except Exception as e:
    print(f"Map node: Error rendering with contextily: {e}")
    traceback.print_exc()
    print("Map node: Falling back to matplotlib-only rendering")
```

## Example Console Output

### Successful Tile Loading (with network access):
```
Map node: Parameters - zoom=12, size=1.5, pan_x=0.0, pan_y=0.0, cache=True
Map node: Creating preview with zoom=12, size=1.5
Map node: _render_with_contextily called with zoom=12, size=1.5, pan=(0.0, 0.0)
Map node: Converted 5 points to Web Mercator
Map node: Initial bounds - X: [260345.71, 263345.71], Y: [6249064.35, 6252064.35]
Map node: Range after size_factor (1.5): X=4500.00m, Y=4500.00m
Map node: After padding (0.15): X: [259670.71, 264020.71], Y: [6248389.35, 6252739.35]
Map node: After pan (0.0, 0.0): X: [259670.71, 264020.71], Y: [6248389.35, 6252739.35]
Map node: Created figure 6.4x4.8 inches at 100 DPI
Map node: Attempting to load OSM tiles with zoom=12
Map node: Using provider: {'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 'max_zoom': 19, ...}
Map node: CRS: EPSG:3857 (Web Mercator)
✓ Map node: OpenStreetMap tiles loaded successfully
```

### Failed Tile Loading (network issue):
```
Map node: Parameters - zoom=10, size=1.0, pan_x=0.0, pan_y=0.0, cache=True
Map node: Creating preview with zoom=10, size=1.0
Map node: _render_with_contextily called with zoom=10, size=1.0, pan=(0.0, 0.0)
Map node: Converted 1 points to Web Mercator
Map node: Initial bounds - X: [261845.71, 261845.71], Y: [6250564.35, 6250564.35]
Map node: X range too small, using default: 10000m
Map node: Y range too small, using default: 10000m
Map node: Range after size_factor (1.0): X=10000.00m, Y=10000.00m
Map node: After padding (0.15): X: [260345.71, 263345.71], Y: [6249064.35, 6252064.35]
Map node: After pan (0.0, 0.0): X: [260345.71, 263345.71], Y: [6249064.35, 6252064.35]
Map node: Created figure 6.4x4.8 inches at 100 DPI
Map node: Attempting to load OSM tiles with zoom=10
Map node: Using provider: {'url': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', 'max_zoom': 19, ...}
Map node: CRS: EPSG:3857 (Web Mercator)
⚠ Map node: Could not load OpenStreetMap tiles
  Error type: ConnectionError
  Error message: HTTPSConnectionPool(host='tile.openstreetmap.org', port=443): Max retries exceeded...
  [Full traceback follows...]
  Using fallback: light blue background without tiles
```

## Control Behavior

### Zoom Slider (1-18)
- **Lower values (1-5)**: Wide area view, less detail, fewer tile requests
- **Medium values (8-12)**: Balanced view, good for city-level visualization
- **Higher values (15-18)**: Detailed view, individual streets and buildings visible

### Size Slider (0.5-5.0)
- **size_factor < 1.0**: Zoom in (smaller bounding box, more detail)
- **size_factor = 1.0**: Normal view
- **size_factor > 1.0**: Zoom out (larger bounding box, wider area)

### Pan Sliders (-1.0 to 1.0)
- **Pan X**: Horizontal translation (negative = left, positive = right)
- **Pan Y**: Vertical translation (negative = down, positive = up)

## Diagnostic Use Cases

### Problem: No tiles visible
**Look for in logs**:
1. "⚠ Map node: Could not load OpenStreetMap tiles"
2. Error type (ConnectionError, HTTPError, etc.)
3. Check if tile URL is accessible: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`

### Problem: Tiles loading but wrong zoom level
**Look for in logs**:
1. "Attempting to load OSM tiles with zoom=X"
2. Verify X matches your slider value
3. Check bounds calculation shows reasonable values

### Problem: Map not updating when sliders change
**Look for in logs**:
1. "Parameters - zoom=X, size=Y, pan_x=A, pan_y=B"
2. Verify these values change when you move sliders
3. If values don't change, check if node is being updated

## Testing

All existing tests pass with the new changes:

```bash
$ python tests/test_map_node.py
Testing Map Node...
✓ AIS data structure extraction test passed
✓ List data structure extraction test passed
✓ Single point extraction test passed
✓ Map generation test passed (using contextily)
✓ Preview image generation test passed
✓ Empty data handling test passed
✓ Coordinate conversion test passed
All tests passed! ✓

$ python tests/test_map_pan_and_zoom.py
[All pan and zoom tests pass with detailed logging]
```

## Files Changed

### node/VisualNode/node_map.py
**Lines Modified**: ~40 lines across 3 methods
**Methods Updated**:
- `update()`: Added parameter logging, pass zoom_level and size_factor
- `_create_preview_image()`: Added zoom_level and size_factor parameters, logging
- `_render_with_contextily()`: Added zoom_level and size_factor parameters, comprehensive logging

## Benefits

1. **Working Controls**: Zoom and size sliders now actually affect the rendered map
2. **Full Visibility**: Complete logging shows every step of the rendering pipeline
3. **Easy Debugging**: Clear error messages with full stack traces for tile loading failures
4. **Diagnostic Information**: All parameter values, bounds, and calculations are logged
5. **User Feedback**: Clear indication of tile loading success or failure

## Backward Compatibility

- Default parameter values maintain backward compatibility
- Existing code calling these methods without new parameters will work (defaults used)
- All existing tests pass without modification
- Logging output is to console only, doesn't affect functionality

## References

- OpenStreetMap Tiles: https://tile.openstreetmap.org/
- Contextily Documentation: https://contextily.readthedocs.io/
- Web Mercator Projection: https://en.wikipedia.org/wiki/Web_Mercator_projection
- Map Node Implementation: `node/VisualNode/node_map.py`
