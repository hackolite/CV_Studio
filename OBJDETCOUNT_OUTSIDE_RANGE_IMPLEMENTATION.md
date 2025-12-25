# ObjectDetCount Node - Trigger When Outside Range Implementation

## Overview
This implementation updates the ObjectDetCount trigger node to activate when the count is **outside** the threshold range, rather than only during threshold crossings.

## Problem Statement
"ObjectDetCount: Trigger, blink when outside range min max, not in transition"

This means:
- The trigger should be active when the detection count is **outside** the configured threshold range [min, max]
- The node should blink when transitioning to the "outside range" state
- The trigger remains active continuously while outside the range (not just at the moment of transition)

## Previous Behavior
The node would trigger only when **crossing** threshold boundaries:
- Trigger activates when entering the threshold range (outside → inside)
- Trigger activates when leaving the threshold range (inside → outside)
- Trigger is inactive while staying within or outside the range

## New Behavior
The node now triggers when the count is **outside** the threshold range:
- Trigger is active when count < min_threshold
- Trigger is active when count > max_threshold (if max_threshold > 0)
- Trigger is inactive when min_threshold ≤ count ≤ max_threshold
- Blinking occurs for 3 seconds when transitioning from inside to outside range

## Implementation Details

### Trigger Logic Change
**Before:**
```python
# Trigger only on crossing: entering or leaving the threshold range
trigger_active = (within_threshold != self.previous_within_threshold)
```

**After:**
```python
# Trigger is active when count is OUTSIDE the threshold range
trigger_active = not within_threshold
```

### Blinking Behavior
The blinking behavior remains the same:
- Blinks white/original for 3 seconds
- Blinking is triggered when `trigger_active` transitions from False to True
- This means blinking occurs when moving from inside→outside the range
- The node continues to blink for the full 3 seconds even if the state changes

### Examples

#### Example 1: Monitoring Occupancy (Min=5, Max=20)
```
Count: 3  → Trigger: Active (below minimum) → Blinks when first entering this state
Count: 4  → Trigger: Active (below minimum) → No blinking (already outside)
Count: 5  → Trigger: Inactive (within range) → No blinking
Count: 10 → Trigger: Inactive (within range) → No blinking
Count: 21 → Trigger: Active (above maximum) → Blinks when entering this state
Count: 25 → Trigger: Active (above maximum) → No blinking (already outside)
Count: 15 → Trigger: Inactive (back within range) → No blinking
```

#### Example 2: No Upper Limit (Min=10, Max=0)
```
Count: 5  → Trigger: Active (below minimum) → Blinks when first entering this state
Count: 8  → Trigger: Active (below minimum) → No blinking (already outside)
Count: 10 → Trigger: Inactive (at/above minimum) → No blinking
Count: 50 → Trigger: Inactive (no upper limit) → No blinking
```

## Files Modified
1. `node/TriggerNode/node_objdetcount.py` - Updated trigger logic
2. `tests/test_objdetcount_threshold_crossing.py` - Updated tests to match new behavior

## Test Coverage
Updated 7 test cases to verify the new behavior:
1. ✅ `test_trigger_when_outside_threshold_below_min` - Verifies trigger is active below minimum
2. ✅ `test_trigger_when_inside_threshold` - Verifies trigger is inactive within range
3. ✅ `test_trigger_when_exceeding_maximum` - Verifies trigger is active above maximum
4. ✅ `test_trigger_stays_active_while_outside_threshold` - Confirms trigger stays active while outside
5. ✅ `test_multiple_range_transitions` - Tests multiple transitions between states
6. ✅ `test_threshold_with_no_upper_limit` - Tests with max_threshold=0
7. ✅ `test_threshold_with_sliding_window` - Tests with sliding window expiration

All existing tests continue to pass:
- ✅ 8 basic objdetcount tests
- ✅ 6 blinking tests
- ✅ 4 integration tests

## Backward Compatibility
This is a **behavioral change** that will affect existing workflows:
- Node configurations remain the same (no API changes)
- JSON export/import format unchanged
- However, the trigger output will behave differently

**Migration Note**: Users relying on the previous "trigger on crossing" behavior will need to update their workflows. The new behavior is more intuitive for most use cases (e.g., alerting when count is outside acceptable range).

## Use Cases

### Alert When Outside Safe Range
Perfect for monitoring scenarios where you want continuous alerts when values are outside safe limits:
- Security: Alert when people count is too low or too high
- Quality Control: Alert when defect count exceeds threshold
- Traffic: Alert when vehicle count is below or above capacity

### Integration with Other Nodes
The trigger output can be used with:
- Alert nodes: Send notifications while count is outside range
- Recording nodes: Record video only when count is abnormal
- Display nodes: Highlight abnormal conditions
- Logic nodes: Combine with other conditions

## Benefits
1. **More Intuitive**: Trigger active = problem exists (outside range)
2. **Continuous Feedback**: Trigger stays active while the condition persists
3. **Better Alerting**: Natural for "out of range" alerting scenarios
4. **Visual Feedback**: White blinking indicates when transitioning to problem state

## Conclusion
The implementation successfully changes the trigger behavior from "activate on crossing" to "activate when outside range". This provides more intuitive and useful behavior for monitoring and alerting scenarios.
