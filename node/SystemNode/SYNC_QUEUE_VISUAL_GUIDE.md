# SyncQueue Node - Visual Guide

## Node Appearance

### Initial State (0 slots)
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│  [Add Slot]  Slots: 0   │
└─────────────────────────┘
```

### After Adding 1 Slot
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│ ○ In1: Image      ○     │  ← IMAGE Input/Output
│ ○ In1: JSON       ○     │  ← JSON Input/Output
│ ○ In1: Audio      ○     │  ← AUDIO Input/Output
├─────────────────────────┤
│  [Add Slot]  Slots: 1   │
└─────────────────────────┘
```

### After Adding 2 Slots
```
┌─────────────────────────┐
│      SyncQueue          │
├─────────────────────────┤
│ ○ In1: Image      ○     │  ← Slot 1: IMAGE
│ ○ In1: JSON       ○     │  ← Slot 1: JSON
│ ○ In1: Audio      ○     │  ← Slot 1: AUDIO
│ ○ In2: Image      ○     │  ← Slot 2: IMAGE
│ ○ In2: JSON       ○     │  ← Slot 2: JSON
│ ○ In2: Audio      ○     │  ← Slot 2: AUDIO
├─────────────────────────┤
│  [Add Slot]  Slots: 2   │
└─────────────────────────┘
```

## Connection Example

### Multi-Camera Synchronization
```
┌──────────┐           ┌─────────────────┐         ┌──────────┐
│ Camera 1 │──IMAGE──→ │ ○ In1: Image  ○ │──IMAGE→ │  Display │
└──────────┘           │ ○ In1: JSON   ○ │         └──────────┘
                       │ ○ In1: Audio  ○ │
┌──────────┐           │                 │         ┌──────────┐
│ Camera 2 │──IMAGE──→ │ ○ In2: Image  ○ │──IMAGE→ │  Save    │
└──────────┘           │ ○ In2: JSON   ○ │         └──────────┘
                       │ ○ In2: Audio  ○ │
┌──────────┐           │   SyncQueue     │
│ Camera 3 │──IMAGE──→ │ ○ In3: Image  ○ │──IMAGE→ ...
└──────────┘           │ ○ In3: JSON   ○ │
                       │ ○ In3: Audio  ○ │
                       │                 │
                       │  [Add Slot]     │
                       └─────────────────┘
```

## Menu Location

The SyncQueue node can be found in the main menu:

```
CV_STUDIO Menu Bar
├── File
│   ├── Export
│   └── Import
├── Input
├── VisionProcess
├── VisionModel
├── AudioProcess
├── AudioModel
├── DataProcess
├── DataModel
├── Trigger
├── Router
├── Action
├── Overlay
├── Tracking
├── Visual
├── Video
└── System              ← NEW CATEGORY
    └── SyncQueue       ← NEW NODE
```

## Slot Creation Flow

1. **Initial Node**
   - Node created with "Add Slot" button
   - No input/output slots initially
   - Status shows "Slots: 0"

2. **Click "Add Slot"**
   - Creates 3 input attributes (IMAGE, JSON, AUDIO)
   - Creates 3 output attributes (IMAGE, JSON, AUDIO)
   - Status updates to "Slots: 1"

3. **Repeat Up To 10 Times**
   - Each click adds another complete slot
   - Maximum of 10 slots per node
   - Each slot is numbered sequentially (01, 02, 03, etc.)

## Data Flow Diagram

```
External Source
      ↓
   [Queue] ← Timestamped Queue System
      ↓
Input Attribute (○)
      ↓
SyncQueue Node Processing
  - Retrieve from queue
  - Synchronize timestamp
  - Pass through data
      ↓
Output Attribute (○)
      ↓
Next Node
```

## Connection Types

### IMAGE Connections
- Input: Accepts image data from camera, processor, or model nodes
- Output: Provides synchronized image data with texture display
- Display: Shows thumbnail preview in node

### JSON Connections
- Input: Accepts JSON metadata from any source
- Output: Provides synchronized JSON data
- Display: Shows truncated text preview

### AUDIO Connections
- Input: Accepts audio stream data
- Output: Provides synchronized audio data
- Display: Text label only (no audio preview)

## Color Coding (Based on Style Module)

The node will be colored according to the "System" category style defined in the style module. Since this is a new category, it will use the default node style.

## Interactive Elements

1. **Add Slot Button**
   - Label: "Add Slot"
   - Action: Creates new input/output slot pair
   - Active: When slots < 10
   - Inactive: When slots = 10 (max reached)

2. **Status Text**
   - Format: "Slots: N"
   - Updates: After each slot addition
   - Range: 0-10

3. **Input Connectors (○)**
   - Left side of node
   - Connection point for incoming data
   - Three per slot (IMAGE, JSON, AUDIO)

4. **Output Connectors (○)**
   - Right side of node
   - Connection point for outgoing data
   - Three per slot (IMAGE, JSON, AUDIO)
