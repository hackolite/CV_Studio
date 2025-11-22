# IntValue and FloatValue Nodes Usage Guide

## Overview

The IntValue and FloatValue nodes are input nodes that provide adjustable numeric values through sliders. These values can be connected to other nodes that accept integer or float inputs.

## IntValue Node

### Purpose
Outputs an integer value that can be connected to INT-type inputs of other nodes.

### Features
- **Range**: -100 to 100
- **Type**: Integer (INT)
- **UI**: Slider control for easy adjustment
- **Save/Load**: Value is preserved when saving/loading the graph

### Example Usage
1. Add an IntValue node from the Input menu
2. Add a Brightness node from the VisionProcess menu
3. Connect the IntValue output to the Brightness beta input
4. Adjust the IntValue slider to dynamically change the brightness

## FloatValue Node

### Purpose
Outputs a float value that can be connected to FLOAT-type inputs of other nodes.

### Features
- **Range**: -10.0 to 10.0
- **Type**: Float (FLOAT)
- **UI**: Slider control for precise decimal adjustment
- **Save/Load**: Value is preserved when saving/loading the graph

### Example Usage
1. Add a FloatValue node from the Input menu
2. Add a Gamma Correction node from the VisionProcess menu
3. Connect the FloatValue output to the Gamma Correction gamma input
4. Adjust the FloatValue slider to dynamically change the gamma value

## Common Use Cases

### Dynamic Parameter Tuning
- Use IntValue/FloatValue to create interactive parameter controls
- Experiment with different values in real-time without editing code

### Saved Configurations
- Create different graph configurations with preset values
- Share graphs with specific parameter settings

### Debugging
- Quickly test edge cases by adjusting values through sliders
- Compare results with different parameter values side-by-side

## Technical Details

### Output Types
- IntValue: Outputs TYPE_INT ("INT")
- FloatValue: Outputs TYPE_FLOAT ("FLOAT")

### Connection Compatibility
These nodes can connect to any node input that accepts:
- TYPE_INT (for IntValue)
- TYPE_FLOAT (for FloatValue)

### Implementation
Both nodes inherit from BaseNode and follow the standard node pattern:
- Implement `update()`, `close()`, `get_setting_dict()`, and `set_setting_dict()`
- Use DearPyGUI sliders for value input
- Store values in node attributes for persistence
