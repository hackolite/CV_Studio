# JSON Message Format Standardization

## Overview

This document describes the standardized JSON message format used for communication between Trigger, Router, and Action nodes in CV_Studio.

## Standard Format

All Trigger and Router nodes output JSON in the following standardized format:

```json
{"BOOL": true}
```

or

```json
{"BOOL": false}
```

The `BOOL` field is a boolean value that indicates the trigger/router state:
- `true`: The trigger condition is met / router passes the signal
- `false`: The trigger condition is not met / router blocks the signal

## Node Types

### Trigger Nodes

Trigger nodes monitor conditions and output a boolean state:

- **ObjDetCount**: Outputs `{"BOOL": true}` when object count is outside threshold range
- Other trigger nodes should follow the same pattern

### Router Nodes

Router nodes combine multiple trigger inputs and apply logic:

- **SimpleRouter**: Outputs `{"BOOL": true}` when the configured slot combination is met

### Action Nodes

Action nodes consume trigger/router outputs and perform actions:

- **VideoRecorder**: Records video when `{"BOOL": true}` is received
- **Buzzer**: Plays sound when `{"BOOL": true}` is received

## Priority Order

Action nodes check for trigger fields in the following priority order:

### VideoRecorder Priority
1. `BOOL` (standard format) - **HIGHEST PRIORITY**
2. `record` (legacy format)
3. `trigger` (legacy format)
4. Any boolean field with value `true` (fallback)

### Buzzer Priority
1. `BOOL` (standard format) - **HIGHEST PRIORITY**
2. Any boolean field with value `true` (fallback)

## Backward Compatibility

All action nodes maintain backward compatibility with legacy formats:

- VideoRecorder still accepts `{"record": true}` or `{"trigger": true}`
- Buzzer still accepts any JSON with a boolean field set to `true`
- The standard `BOOL` field takes precedence when present

## Examples

### Standard Usage (Recommended)

```
[ObjDetCount] --{"BOOL": true}--> [VideoRecorder] --> Records video
[SimpleRouter] --{"BOOL": false}--> [Buzzer] --> Does not buzz
```

### Chained Usage

```
[ObjDetCount] --{"BOOL": true}--> [SimpleRouter] --{"BOOL": true}--> [VideoRecorder]
                                         |
                                         v
                                    [Buzzer]
```

### Legacy Format (Still Supported)

```
[Custom Node] --{"record": true}--> [VideoRecorder] --> Records video
[Custom Node] --{"detected": true}--> [Buzzer] --> Buzzes
```

But if `BOOL` field is present, it takes priority:

```
[Custom Node] --{"BOOL": false, "record": true}--> [VideoRecorder] --> Does NOT record
```

## Implementation Details

### Trigger/Router Output

```python
# In update() method
trigger_active = # ... compute trigger condition
output_json = {"BOOL": trigger_active}
return {"image": None, "json": output_json, "audio": None}
```

### Action Input (VideoRecorder)

```python
# Check with priority order
should_record = False
if trigger_json and isinstance(trigger_json, dict):
    if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
        should_record = trigger_json['BOOL']  # Standard format - HIGHEST PRIORITY
    elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
        should_record = trigger_json['record']  # Legacy format
    elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
        should_record = trigger_json['trigger']  # Legacy format
    else:
        # Fallback for maximum compatibility
        for key, value in trigger_json.items():
            if isinstance(value, bool) and value:
                should_record = True
                break
```

### Action Input (Buzzer)

```python
# Check with priority order
should_buzz = False
if node_result and isinstance(node_result, dict):
    if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
        should_buzz = node_result['BOOL']  # Standard format - HIGHEST PRIORITY
    else:
        # Fallback for maximum compatibility
        for key, value in node_result.items():
            if isinstance(value, bool) and value:
                should_buzz = True
                break
```

## Migration Guide

If you have custom nodes that produce boolean outputs:

### Before (Legacy)
```python
output_json = {"detected": True, "count": 5}
# or
output_json = {"record": True}
```

### After (Standard)
```python
output_json = {"BOOL": True}
# You can still include additional data:
output_json = {"BOOL": True, "count": 5, "details": "..."}
```

The standard `BOOL` field will be used for triggering, while additional fields can provide metadata.

## Benefits

1. **Consistency**: All trigger/router/action nodes use the same field name
2. **Clarity**: The `BOOL` field name clearly indicates its purpose
3. **Backward Compatibility**: Existing workflows continue to work
4. **Forward Compatibility**: New nodes can rely on the standard format
5. **Easy Debugging**: Standardized format makes it easier to trace signal flow

## Testing

Tests have been added to verify the standardized format:

- `tests/test_bool_field_standardization.py`: Integration tests
- `tests/test_buzzer_bool_field.py`: Buzzer-specific tests
- `tests/test_video_recorder_functional.py`: VideoRecorder-specific tests

Run tests with:
```bash
python -m unittest tests.test_bool_field_standardization -v
```
