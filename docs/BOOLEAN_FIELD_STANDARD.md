# Boolean Field Standard for CV Studio Nodes

## Overview

This document describes the standardized boolean field format used across CV Studio nodes for trigger, routing, and action nodes.

## Standard Format

All trigger and router nodes **MUST** output JSON in the following format:

```json
{
  "BOOL": true
}
```

or

```json
{
  "BOOL": false
}
```

### Key Requirements

1. **Field Name**: The field MUST be named `"BOOL"` (all uppercase)
2. **Value Type**: The value MUST be a boolean (`true` or `false`), not:
   - Integer (0 or 1)
   - String ("true" or "false")
   - None/null
   - Any other type
3. **Presence**: The field MUST be present in the output JSON

## Node Categories

### Trigger Nodes (Producers)

Trigger nodes detect conditions and output boolean signals.

**Standardized Nodes:**
- **ObjDetCount**: Outputs `{"BOOL": trigger_active}` based on object count thresholds
- **Boolean Inverter**: Outputs `{"BOOL": not input_bool}` to invert input
- **Keypoint Deviation**: Adds `output_json['BOOL'] = trigger_state` to its output

**Implementation Example:**
```python
# In trigger node's update() method
trigger_active = self.check_condition()  # Returns True or False
output_json = {"BOOL": trigger_active}
return {"image": None, "json": output_json, "audio": None}
```

### Router Nodes (Processors)

Router nodes receive boolean signals, apply logic, and output boolean signals.

**Standardized Nodes:**
- **SimpleRouter**: Outputs `{"BOOL": trigger_active}` based on combination logic

**Implementation Example:**
```python
# In router node's update() method
# Read input BOOL
input_bool = False
if node_result and isinstance(node_result, dict):
    if 'BOOL' in node_result and isinstance(node_result['BOOL'], bool):
        input_bool = node_result['BOOL']

# Apply router logic
trigger_active = self.apply_logic(input_bool)
output_json = {"BOOL": trigger_active}
return {"image": None, "json": output_json, "audio": None}
```

### Action Nodes (Consumers)

Action nodes receive boolean signals and perform actions when triggered.

**Standardized Nodes:**
- **VideoRecorder**: Checks `BOOL` field to start/stop recording
- **Buzzer**: Checks `BOOL` field to play sound

**Priority Order for VideoRecorder:**
1. `BOOL` field (standard, highest priority)
2. `record` field (legacy support)
3. `trigger` field (legacy support)
4. Any boolean field with value `true` (fallback)

**Implementation Example:**
```python
# In action node's update() method
should_activate = False
if trigger_json and isinstance(trigger_json, dict):
    # Priority: BOOL > legacy fields
    if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
        should_activate = trigger_json['BOOL']
    elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
        # Backward compatibility
        should_activate = trigger_json['record']
    # ... other legacy fields

if should_activate:
    self.perform_action()
```

## Benefits of Standardization

1. **Consistency**: All nodes use the same field name and type
2. **Type Safety**: Boolean validation prevents errors from non-boolean values
3. **Clarity**: Clear semantic meaning (BOOL for boolean trigger state)
4. **Backward Compatibility**: Action nodes still support legacy field names
5. **Easy Integration**: Nodes from different categories work together seamlessly

## Testing

### Unit Tests

Each node type should have tests verifying:
- Output contains `BOOL` field
- `BOOL` value is a boolean type
- `BOOL` value correctly reflects the node's state

### Integration Tests

Pipeline tests should verify:
- Trigger → Router → Action flow works correctly
- `BOOL=true` triggers actions
- `BOOL=false` does not trigger actions
- Type safety (non-boolean values are rejected)

**Example Test:**
```python
def test_trigger_router_recorder_pipeline():
    # Trigger outputs
    trigger_output = {"BOOL": True}
    
    # Router processes and outputs
    router_output = {"BOOL": True}
    
    # Recorder receives and acts
    should_record = False
    if 'BOOL' in router_output and isinstance(router_output['BOOL'], bool):
        should_record = router_output['BOOL']
    
    assert should_record == True
```

## Migration Guide

### For Trigger/Router Node Developers

If your node currently outputs a different format:

**Old Format:**
```python
return {"image": None, "json": {"trigger": True}, "audio": None}
```

**New Format:**
```python
return {"image": None, "json": {"BOOL": True}, "audio": None}
```

### For Action Node Developers

Add `BOOL` field support with highest priority:

```python
should_activate = False
if trigger_json and isinstance(trigger_json, dict):
    # NEW: Check BOOL field first
    if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
        should_activate = trigger_json['BOOL']
    # LEGACY: Keep old field support
    elif 'your_legacy_field' in trigger_json:
        should_activate = trigger_json['your_legacy_field']
```

## Common Pitfalls

### ❌ Incorrect: Using integer instead of boolean
```python
output_json = {"BOOL": 1}  # WRONG!
```

### ✅ Correct: Using boolean
```python
output_json = {"BOOL": True}  # CORRECT!
```

### ❌ Incorrect: Using string
```python
output_json = {"BOOL": "true"}  # WRONG!
```

### ✅ Correct: Using boolean
```python
output_json = {"BOOL": True}  # CORRECT!
```

### ❌ Incorrect: Not checking type
```python
if trigger_json['BOOL']:  # WRONG! Could be non-boolean
    activate()
```

### ✅ Correct: Checking type
```python
if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
    if trigger_json['BOOL']:  # CORRECT! Type-safe
        activate()
```

## Related Tests

- `tests/test_bool_field_standardization.py` - Unit tests for boolean field handling
- `tests/test_trigger_router_recorder_integration.py` - Integration tests for complete pipeline
- `test_bool_consistency.py` - Comprehensive consistency verification

## Questions?

For questions about the boolean field standard, please refer to:
- This documentation
- The test files listed above
- Example implementations in the standardized nodes
