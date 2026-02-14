# Fix Summary: JSON Data Transfer Between CoordinateExamples and Map Nodes

## Problem Statement

The user reported an error when connecting CoordinateExamples node to Map node:
```
ap node: Received JSON string (length: 17)
Map node: JSON parse error: Expecting value: line 1 column 1 (char 0)
```

## Root Cause Analysis

The Map node was using `dpg_get_value(tag_node_input01_value_name)` to retrieve JSON input data. However, DearPyGUI node attributes don't automatically transfer data between connected nodes. Instead, the correct pattern (used by other nodes like `node_obj_chart.py`) is to:

1. Parse `connection_list` to find the source node ID
2. Read data directly from `node_result_dict[source_node_id]`

The incorrect approach was causing the Map node to receive invalid/empty data from DearPyGUI widgets, resulting in JSON parse errors.

## Solution Implemented

### Changes to node/VisualNode/node_map.py

**Before:**
```python
# Get input JSON data
input_value = dpg_get_value(tag_node_input01_value_name)
```

**After:**
```python
# Find connected source for JSON data
connection_info_src = ''
for connection_info in connection_list:
    connection_type = connection_info[0].split(':')[2]
    if connection_type == self.TYPE_JSON:
        connection_info_src = connection_info[0]
        connection_info_src = connection_info_src.split(':')[:2]
        connection_info_src = ':'.join(connection_info_src)
        break

# Get input JSON data from node_result_dict (correct approach)
input_value = node_result_dict.get(connection_info_src, None)

# Log received data for debugging
if connection_info_src:
    if input_value is not None:
        print(f"Map node: Received data from {connection_info_src}")
        print(f"Map node: Data type: {type(input_value).__name__}")
        if isinstance(input_value, (list, dict)):
            try:
                import json as json_module
                json_str = json_module.dumps(input_value, indent=2)
                print(f"Map node: JSON data (first 500 chars):\n{json_str[:500]}")
            except Exception as e:
                print(f"Map node: Could not serialize data: {e}")
        elif isinstance(input_value, str):
            print(f"Map node: String data (length {len(input_value)}): {input_value[:100]}")
    else:
        print(f"Map node: No data received from {connection_info_src}")
```

### Changes to node/InputNode/node_coordinate_examples.py

Added logging to show what data is being sent:

```python
# Log generated JSON for debugging
print(f"CoordinateExamples node: Sending {len(json_output) if isinstance(json_output, list) else 0} coordinates")
if json_output and isinstance(json_output, list) and len(json_output) > 0:
    try:
        import json as json_module
        json_str = json_module.dumps(json_output[0], indent=2)
        print(f"CoordinateExamples node: First coordinate:\n{json_str}")
    except Exception as e:
        print(f"CoordinateExamples node: Could not serialize first coordinate: {e}")
```

## Key Benefits of the Fix

1. **Correct Data Flow**: Map node now receives Python list/dict objects directly, not strings
2. **No JSON Parsing Errors**: Since data isn't serialized to strings during transfer, no parsing is needed
3. **Comprehensive Logging**: Both nodes now print detailed information about data being sent/received
4. **Consistent Pattern**: Map node now follows the same pattern as other processing nodes (e.g., node_obj_chart.py)
5. **JSON Compatibility Guaranteed**: Data remains as native Python objects throughout the pipeline

## Data Flow Explanation

```
1. CoordinateExamples.update()
   ↓ Returns {"json": [{"latitude": X, "longitude": Y, ...}]} (Python list)
   
2. main.py update_node_info()
   ↓ node_result_dict["1:CoordinateExamples"] = data["json"] (stores Python object)
   
3. Map.update(connection_list, node_result_dict)
   ↓ Parses connection_list to find source: "1:CoordinateExamples"
   ↓ input_value = node_result_dict.get("1:CoordinateExamples")
   ↓ Receives Python list (no parsing needed)
   ↓ _extract_lat_lon_from_json(input_value)
   ↓ points = [{"lat": X, "lon": Y, "name": Z}]
   
4. Map creates visualization
   ↓ Generates preview image with points plotted
   ↓ Optionally creates interactive HTML map with Folium
```

## Testing

### Created Tests
1. **test_coordinate_map_integration.py**: Integration test verifying data transfer
2. **validate_coordinate_map_fix.py**: Validation script demonstrating the fix

### Test Results
```
Testing Coordinate Examples → Map Node Integration...

✓ Using AISTRACKER with 5 coordinates
✓ Map node extracted 5 points from CoordinateExamples data
✓ All extracted points have valid lat/lon format
✓ Original coordinates are JSON serializable (length: 459)
✓ JSON round-trip successful
✓ Data remains as Python list (not serialized to string)
✓ GPS simulation format is compatible with Map node
✓ Map node extracted 2 GPS simulation points
✓ Map node handles latitude/longitude format
✓ Map node handles lat/lon format
✓ Map node handles nested boats format

All integration tests passed! ✓
```

### Existing Tests
All existing tests continue to pass:
- test_coordinate_examples_node.py ✓
- test_map_node.py ✓

## Expected Logs After Fix

When running with CoordinateExamples → Map connection, you should see:

```
CoordinateExamples node: Sending 5 coordinates
CoordinateExamples node: First coordinate:
{
  "latitude": 49.4431,
  "longitude": 0.1073,
  "name": "Vessel Le Havre",
  "mmsi": "123456789"
}

Map node: Received data from 1:CoordinateExamples
Map node: Data type: list
Map node: JSON data (first 500 chars):
[
  {
    "latitude": 49.4431,
    "longitude": 0.1073,
    ...
  }
]
Map node: Received JSON object (type: list)
Map node: JSON is a list with 5 items
Map node: Extracted 5 points with lat/lon
Map node: ✓ 5 point(s) displayed
```

## Verification

The fix guarantees:
- ✅ JSON data is compatible between nodes (remains as Python objects)
- ✅ Map displays correctly (receives valid list of coordinates)
- ✅ No JSON parse errors (no string serialization during transfer)
- ✅ Comprehensive logging for debugging

## Files Modified

1. `node/VisualNode/node_map.py` - Fixed data retrieval and added logging
2. `node/InputNode/node_coordinate_examples.py` - Added logging
3. `tests/test_coordinate_map_integration.py` - New integration test
4. `tests/validate_coordinate_map_fix.py` - New validation script

## Minimal Changes

The fix is surgical and minimal:
- Only changed how Map node retrieves input data
- Added logging for debugging (non-invasive)
- No changes to data formats or structures
- No changes to other nodes or the core system
- Backward compatible with existing workflows
