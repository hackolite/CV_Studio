# SimpleRouter Node Implementation

## Overview

The SimpleRouter node is a logical router that allows users to combine multiple boolean trigger inputs with configurable expected states and a time window. It provides visual feedback through blinking when conditions are met.

## Features

### Dynamic Slot Management
- **Add Slot Button**: Dynamically add input slots (up to 10 maximum)
- **Remove Slot Button**: Remove the last slot (minimum 1 slot required)
- Each slot can connect to a trigger node that outputs boolean JSON data

### Expected State Configuration
- Each slot has a checkbox labeled "Slot N expects True"
- When checked: The slot expects the input to be `True`
- When unchecked: The slot expects the input to be `False`
- This allows creating complex logical combinations (AND logic across all slots)

### Time Window
- Configurable sliding window in seconds (default: 5.0 seconds)
- Minimum: 0.1 seconds
- The node tracks when the combination condition is met within the window
- Returns `True` as long as there is at least one activation within the time window

### Visual Feedback
- **Blinking Effect**: When the output is active (True), the node blinks white/original color
- Blinking pattern matches the trigger node system:
  - 1.0 second cycle duration
  - 0.5 seconds white, 0.5 seconds original color
  - Continuous blinking while active

### Output
- Outputs a JSON object with a `BOOL` field
- `{"BOOL": True}` when at least one activation exists in the time window
- `{"BOOL": False}` when no activations in the time window

## Usage Example

### Scenario: Detect when multiple conditions are met
1. Add a SimpleRouter node to your graph
2. Connect multiple trigger nodes (e.g., ObjDetCount nodes) to the input slots
3. Configure each slot's checkbox based on expected state:
   - Slot 1: expects True (checked) - person detected
   - Slot 2: expects False (unchecked) - no car detected
   - Slot 3: expects True (checked) - motion detected
4. Set the time window (e.g., 10 seconds)
5. The router outputs True when all conditions are met simultaneously at least once within the 10-second window

## Technical Details

### Node Structure
- **Node Label**: SimpleRouter
- **Node Tag**: SimpleRouter
- **Category**: Router
- **Style**: Lavender pastel (216, 191, 216, 255)

### Input/Output Types
- **Inputs**: Multiple JSON slots (TYPE_JSON) with boolean data
- **Output**: Single JSON slot with boolean data (TYPE_JSON)

### State Management
- Uses a deque (double-ended queue) to efficiently track activation timestamps
- Implements sliding window algorithm with O(1) amortized time complexity
- Cleans up old timestamps outside the window to prevent memory growth

### Settings Persistence
The node saves and restores:
- Window duration
- Number of slots
- Expected state for each slot (checkbox values)
- Node position

## Implementation Notes

### Based On
The implementation follows patterns from existing trigger nodes, particularly:
- `node/TriggerNode/node_objdetcount.py` for blinking behavior
- `node/basenode.py` for base node structure

### Error Handling
- Gracefully handles GUI item access errors during node deletion or UI updates
- Provides default values when configuration values cannot be retrieved
- Safe exception handling prevents crashes during edge cases

### Performance
- Efficient sliding window implementation
- Minimal memory footprint (only stores timestamps within window)
- No blocking operations in update cycle

## Future Enhancements

Potential improvements for future versions:
- Support for OR logic in addition to AND logic
- Configurable logic operators per slot
- Visual indicators for individual slot states
- Export/import of slot configurations
- Custom labels for slots
