# SyncQueue Node Documentation

## Overview

The SyncQueue node is a system node that synchronizes data from multiple queues. It provides dynamic input/output slots that can be added at runtime.

## Features

- **Dynamic Slots**: Add input/output pairs using the "Add Slot" button
- **Multi-Type Support**: Each slot supports IMAGE, JSON, and AUDIO data types
- **Queue Synchronization**: Retrieves and synchronizes elements from connected queues
- **Pass-Through**: Each input has corresponding outputs for data routing

## Usage

### Adding Slots

1. Click the "Add Slot" button to create a new input/output slot pair
2. Each slot creates:
   - 3 inputs (IMAGE, JSON, AUDIO)
   - 3 outputs (IMAGE, JSON, AUDIO)
3. Up to 10 slots can be added per node instance

### Connecting Data

1. Connect source nodes to the input slots
2. Data flows through and appears on the corresponding output slots
3. Multiple nodes can connect to the same sync queue for synchronization

### Data Flow

```
[Source Node 1] ---> [Input 1: IMAGE] ---> [Output 1: IMAGE] ---> [Destination]
                     [Input 1: JSON]  ---> [Output 1: JSON]
                     [Input 1: AUDIO] ---> [Output 1: AUDIO]

[Source Node 2] ---> [Input 2: IMAGE] ---> [Output 2: IMAGE] ---> [Destination]
                     [Input 2: JSON]  ---> [Output 2: JSON]
                     [Input 2: AUDIO] ---> [Output 2: AUDIO]
```

## Technical Details

### Node Properties

- **Node Label**: SyncQueue
- **Node Tag**: SyncQueue
- **Max Slots**: 10
- **Supported Types**: IMAGE, JSON, AUDIO

### Methods

- `update()`: Processes connections and synchronizes data
- `close()`: Cleanup when node is removed
- `_add_slot()`: Adds a new input/output slot pair
- `get_setting_dict()`: Saves node configuration
- `set_setting_dict()`: Restores node configuration

## Menu Location

The SyncQueue node is available in the **System** menu category.

## Example Use Cases

1. **Multi-Camera Synchronization**: Synchronize frames from multiple camera inputs
2. **Data Aggregation**: Collect JSON data from multiple sources
3. **Audio Mixing**: Route multiple audio streams through a central point
4. **Workflow Management**: Coordinate data flow between different processing pipelines

## Limitations

- Maximum 10 slots per node instance
- Data is passed through without modification
- Synchronization is based on the timestamped queue system
