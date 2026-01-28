# MOT Tracker Enable/Disable Button Feature

## Overview
This feature adds a direct "Enable Tracking" checkbox to the MOT (Multi-Object Tracking) node, allowing users to enable or disable tracking without requiring an external JSON Boolean node connection.

## Problem Statement
Previously, the MOT tracker was always enabled by default and could only be controlled via:
- JSON input connection (Input03) from external nodes like JsonBoolean
- This required users to add additional nodes just to control tracking on/off

## Solution
Added a checkbox directly on the MOT node labeled "Enable Tracking" that:
- Defaults to checked (enabled) for backward compatibility
- Allows direct control without additional nodes
- Maintains backward compatibility with existing JSON input mechanism

## User Interface
The checkbox appears in the MOT node's static attributes section, below the confidence threshold slider:

```
┌─────────────────────────────┐
│   MOT Node                  │
├─────────────────────────────┤
│ Image Input                 │
│ JSON Start/Stop (boolean)   │
│ JSON Detections             │
│ Model Selector Dropdown     │
│ Confidence Slider           │
│ ☑ Enable Tracking          │  ← NEW CHECKBOX
│ Image Output                │
│ JSON Output                 │
└─────────────────────────────┘
```

## Behavior

### Default State
- Checkbox is checked (enabled) by default
- Tracking operates normally when enabled
- This matches previous behavior where tracking was always on

### When Unchecked (Disabled)
- Tracking is disabled
- MOT outputs empty results (no tracking data)
- Downstream nodes (like Homography, Tennis Court) receive no data
- Frame passes through unchanged

### JSON Input Override
- If a JSON input is connected to Input03, it takes priority
- This ensures backward compatibility with existing pipelines
- Order of precedence:
  1. JSON input (if connected) - highest priority
  2. Checkbox value - default control

## Technical Implementation

### Code Changes
1. **UI Addition** (`node_mot.py` lines 71-72, 173-183):
   - Added checkbox tag definition
   - Added checkbox UI element in node attribute

2. **Update Logic** (`node_mot.py` lines 289, 342-357):
   - Read checkbox value as primary control
   - Allow JSON input to override if connected
   - Maintain backward compatibility

3. **Settings Persistence** (`node_mot.py` lines 538, 546-549, 566, 576-578):
   - Save checkbox state in `get_setting_dict()`
   - Restore checkbox state in `set_setting_dict()`
   - Default to True for backward compatibility

### Backward Compatibility
✅ Existing pipelines with JSON input connections continue to work
✅ Saved settings without checkbox value default to enabled (True)
✅ No breaking changes to node interface or behavior

## Usage Examples

### Example 1: Simple Enable/Disable
```
1. Add MOT node to your pipeline
2. Toggle "Enable Tracking" checkbox to control tracking
3. No additional nodes needed
```

### Example 2: Dynamic Control (JSON Override)
```
1. Add MOT node
2. Add JsonBoolean node
3. Connect JsonBoolean output to MOT Input03
4. JsonBoolean value overrides checkbox
5. Useful for programmatic control or complex logic
```

## Testing
Created comprehensive test suite in `tests/test_mot_enable_checkbox.py`:
- Tests checkbox defaults to enabled
- Tests checkbox controls tracking enable/disable
- Tests JSON input can override checkbox value

## Migration Guide
No migration needed! Existing pipelines work without changes:
- Nodes without saved checkbox state default to enabled (True)
- JSON input connections continue to work as before
- The checkbox provides a convenient alternative for simple use cases

## Benefits
✅ Simpler user experience - no extra nodes needed for basic on/off control
✅ Cleaner pipeline graphs - fewer nodes for simple cases
✅ Backward compatible - existing pipelines work unchanged
✅ Flexible - both checkbox and JSON control available
✅ Intuitive - checkbox label clearly indicates function
