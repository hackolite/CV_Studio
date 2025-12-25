# SimpleRouter Node - Architecture Diagram

## Node Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SimpleRouter Node                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Configuration Section                           │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  Window (seconds): [5.0]                                    │   │
│  │  [Add Slot]  [Remove Slot]                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Input Slots (Dynamic)                           │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ ● Input Slot 1    [✓] Slot 1 expects True                  │   │
│  │                                                              │   │
│  │ ● Input Slot 2    [ ] Slot 2 expects True (expects False)  │   │
│  │                                                              │   │
│  │ ● Input Slot 3    [✓] Slot 3 expects True                  │   │
│  │                                                              │   │
│  │ ...                                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Output                                          │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ ● Activations: 3 (Status: Active)                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Logic Flow

```
Input Processing
─────────────────
For each update cycle:
  
  1. Read all connected input slots
     ┌──────────────┐
     │ Slot 1: True │  ✓ Expected: True  → Match!
     └──────────────┘
     ┌──────────────┐
     │ Slot 2: False│  ✓ Expected: False → Match!
     └──────────────┘
     ┌──────────────┐
     │ Slot 3: True │  ✓ Expected: True  → Match!
     └──────────────┘
  
  2. Check if ALL slots match expected states
     All Match? → Combination Met!
     
  3. Add timestamp to activation history
     [t-4.5s, t-2.1s, t-0.3s, NOW]
     
  4. Clean old timestamps (outside window)
     Window: 5.0 seconds
     Keep: [t-2.1s, t-0.3s, NOW]
     
  5. Output: True (activations in window)
     
  6. Trigger blinking effect
```

## Sliding Window Mechanism

```
Time Window: 5 seconds
Current Time: 10.0s

Activation History (timestamps):
┌──────────────────────────────────────────────────────────────┐
│  3.5s   4.2s   6.8s   7.3s   9.1s   9.8s                    │
│   ❌     ❌     ✓      ✓      ✓      ✓                      │
│  (old)  (old) (kept) (kept) (kept) (kept)                   │
└──────────────────────────────────────────────────────────────┘
         ↑
    Cutoff: 5.0s ago = 10.0s - 5.0s = 5.0s
    
    Remove: 3.5s, 4.2s (< 5.0s)
    Keep: 6.8s, 7.3s, 9.1s, 9.8s (>= 5.0s)
    
    Result: 4 activations in window → Output: True
```

## Blinking State Machine

```
State Transitions:
┌─────────────┐
│   Inactive  │  (Output: False)
│  No Blink   │
└──────┬──────┘
       │ Combination Met
       │ (Output becomes True)
       ↓
┌─────────────┐
│   Active    │  (Output: True)
│  Blinking   │
│             │
│ ┌─────────┐ │
│ │ White   │ │ ← 0.0s - 0.5s
│ └─────────┘ │
│ ┌─────────┐ │
│ │Original │ │ ← 0.5s - 1.0s
│ └─────────┘ │
│  (repeat)   │
└──────┬──────┘
       │ Window expires
       │ (Output becomes False)
       ↓
┌─────────────┐
│   Inactive  │
│  Restored   │
└─────────────┘
```

## Data Structure

```python
class Node:
    # Activation tracking
    activation_timestamps: deque([timestamp1, timestamp2, ...])
    
    # Blinking state
    blink_start_time: float | None
    blink_active: bool
    previous_trigger_state: bool
    
    # Slot management
    num_slots: int (default: 2, max: 10)
    
    # Themes
    original_theme: theme_id | None
    white_theme: theme_id
```

## Example Use Cases

### 1. Security Alert System
```
Slot 1: Person detected = True
Slot 2: After hours = True  
Slot 3: Door open = True
→ Trigger alarm if all conditions met within 10s window
```

### 2. Quality Control
```
Slot 1: Defect detected = True
Slot 2: Temperature OK = True (checkbox unchecked for False)
Slot 3: Speed normal = True (checkbox unchecked for False)
→ Flag item if defect found when conditions are otherwise normal
```

### 3. Event Correlation
```
Slot 1: Motion detected = True
Slot 2: Sound detected = True
Slot 3: Light off = True (checkbox unchecked for False)
→ Detect specific scenarios with multiple conditions
```

## Performance Characteristics

- **Time Complexity**: O(1) amortized for update (deque operations)
- **Space Complexity**: O(n) where n = activations within window
- **Update Rate**: Matches CV_Studio frame rate (~30-60 FPS)
- **Memory**: Bounded by window duration and activation frequency

## Integration with CV_Studio

```
Node Categories:
├── Input (WebCam, Video, etc.)
├── VisionProcess (Resize, Crop, etc.)
├── VisionModel (ObjectDetection, etc.)
├── Trigger (ObjDetCount, OnOffSwitch, etc.)
│   └── Outputs: {"BOOL": true/false}
├── Router ← SimpleRouter fits here
│   └── SimpleRouter
│       ├── Inputs: Multiple JSON slots with BOOL
│       └── Output: JSON with BOOL
└── Action (VideoWriter, etc.)
    └── Can be triggered by SimpleRouter output
```
