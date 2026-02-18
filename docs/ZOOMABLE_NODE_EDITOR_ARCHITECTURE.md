# ZoomableNodeEditor - Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ZoomableNodeEditor                               │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ State Management                                                 │  │
│  │                                                                  │  │
│  │  • zoom: float (0.1 - 5.0)      Range controlled               │  │
│  │  • offset_x: float               Pan in X direction             │  │
│  │  • offset_y: float               Pan in Y direction             │  │
│  │  • dirty: bool                   Redraw needed?                 │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Data Storage                                                     │  │
│  │                                                                  │  │
│  │  nodes = {                                                       │  │
│  │    "node1": {                                                    │  │
│  │      x, y,           ← World coordinates                         │  │
│  │      width, height,  ← Auto-calculated                           │  │
│  │      label,          ← Display text                              │  │
│  │      inputs,         ← Number of input ports                     │  │
│  │      outputs         ← Number of output ports                    │  │
│  │    }                                                             │  │
│  │  }                                                               │  │
│  │                                                                  │  │
│  │  connections = [                                                 │  │
│  │    {                                                             │  │
│  │      from: (node_id, port_idx),                                  │  │
│  │      to: (node_id, port_idx)                                     │  │
│  │    }                                                             │  │
│  │  ]                                                               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Event Handlers (via dpg.handler_registry)                        │  │
│  │                                                                  │  │
│  │  Mouse Wheel ──→ _on_wheel()                                     │  │
│  │                  │                                               │  │
│  │                  ├→ Calculate new zoom                            │  │
│  │                  ├→ Clamp to [0.1, 5.0]                          │  │
│  │                  ├→ Adjust offset to keep cursor fixed           │  │
│  │                  │   offset_x -= mouse_x * zoom_ratio / zoom     │  │
│  │                  └→ Set dirty = True                              │  │
│  │                                                                  │  │
│  │  Middle Mouse ──→ _on_pan()                                      │  │
│  │    + Drag         │                                              │  │
│  │                  ├→ Calculate mouse delta                         │  │
│  │                  ├→ Update offset with zoom compensation         │  │
│  │                  │   offset += delta / zoom                       │  │
│  │                  └→ Set dirty = True                              │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Rendering Pipeline (update() → _redraw())                        │  │
│  │                                                                  │  │
│  │  1. Check dirty flag                                             │  │
│  │     └→ If false and throttled: skip                              │  │
│  │                                                                  │  │
│  │  2. Clear drawlist                                               │  │
│  │                                                                  │  │
│  │  3. Draw connections (behind nodes)                              │  │
│  │     For each connection:                                         │  │
│  │       ├→ Get port positions (world coords)                       │  │
│  │       ├→ Transform to screen coords                              │  │
│  │       └→ Draw Bezier curve                                       │  │
│  │           control_offset = abs(x2-x1) * 0.5                      │  │
│  │                                                                  │  │
│  │  4. Draw nodes                                                   │  │
│  │     For each node:                                               │  │
│  │       ├→ Transform to screen coords:                             │  │
│  │       │   screen_x = (world_x + offset_x) * zoom                 │  │
│  │       │   screen_y = (world_y + offset_y) * zoom                 │  │
│  │       │                                                           │  │
│  │       ├→ Viewport culling check:                                 │  │
│  │       │   if outside viewport: continue                          │  │
│  │       │                                                           │  │
│  │       ├→ Draw node body (rounded rect)                           │  │
│  │       ├→ Draw node header (colored)                              │  │
│  │       ├→ Draw label (centered)                                   │  │
│  │       ├→ Draw input ports (left, green)                          │  │
│  │       └→ Draw output ports (right, red)                          │  │
│  │                                                                  │  │
│  │  5. Reset dirty flag                                             │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Dual Drawlist System                                             │  │
│  │                                                                  │  │
│  │  ┌────────────────────┐  ┌────────────────────┐                  │  │
│  │  │ Grid Drawlist      │  │ Content Drawlist   │                  │  │
│  │  │ (Static)           │  │ (Zoomable)         │                  │  │
│  │  ├────────────────────┤  ├────────────────────┤                  │  │
│  │  │ • 50px grid        │  │ • Nodes            │                  │  │
│  │  │ • Never zooms      │  │ • Connections      │                  │  │
│  │  │ • Gray (50,50,50)  │  │ • Scales with zoom │                  │  │
│  │  │ • Drawn once       │  │ • Redraws on dirty │                  │  │
│  │  └────────────────────┘  └────────────────────┘                  │  │
│  │         ↓                         ↓                               │  │
│  │    Stays fixed              Zooms/pans                            │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ Performance Optimizations                                         │  │
│  │                                                                  │  │
│  │  Dirty Flag:                                                     │  │
│  │    • Set on zoom/pan/add node                                    │  │
│  │    • Skip redraw if not dirty                                    │  │
│  │    • Reset after redraw                                          │  │
│  │                                                                  │  │
│  │  Viewport Culling:                                               │  │
│  │    • Check if node is visible                                    │  │
│  │    • Skip drawing if outside viewport                            │  │
│  │    • Scales to 100+ nodes                                        │  │
│  │                                                                  │  │
│  │  FPS Throttling:                                                 │  │
│  │    • Track last_draw_time                                        │  │
│  │    • Skip if < 1/60 seconds elapsed                              │  │
│  │    • Prevents CPU waste                                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        Coordinate Systems                               │
│                                                                         │
│  World Coordinates               Screen Coordinates                    │
│  (Logical positions)             (Pixel positions)                     │
│                                                                         │
│  node.x, node.y     ────────→   screen_x, screen_y                     │
│                     Transform    = (world + offset) * zoom             │
│                                                                         │
│  Example:                                                               │
│    World: (100, 200)                                                    │
│    Zoom: 2.0                                                            │
│    Offset: (50, 100)                                                    │
│    → Screen: (300, 600)                                                 │
│       Calculation: ((100+50)*2, (200+100)*2)                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        Zoom Formula Breakdown                           │
│                                                                         │
│  Goal: Keep world position under cursor constant during zoom           │
│                                                                         │
│  Before zoom:                                                           │
│    world_pos = (screen_pos - offset * zoom_old) / zoom_old             │
│                                                                         │
│  After zoom (world_pos must stay same):                                │
│    world_pos = (screen_pos - offset * zoom_new) / zoom_new             │
│                                                                         │
│  Solving for offset_new:                                               │
│    offset_new = offset_old + screen_pos * (1/zoom_new - 1/zoom_old)    │
│                                                                         │
│  Simplified implementation:                                             │
│    zoom_ratio = zoom_new / zoom_old - 1                                │
│    offset -= screen_pos * zoom_ratio / zoom_new                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        Node Auto-Sizing                                 │
│                                                                         │
│  Width calculation:                                                     │
│    label_width = len(label) * font_size * 0.6                          │
│    ports_width = max(inputs, outputs) * 30                             │
│    width = max(150, label_width + 40, ports_width)                     │
│                                                                         │
│  Height calculation:                                                    │
│    header_height = 30                                                   │
│    port_count = max(inputs, outputs)                                   │
│    height = header_height + (port_count * 25) + 20                     │
│                                                                         │
│  Example:                                                               │
│    Label: "Data Transform" (14 chars)                                  │
│    Font: 15px                                                           │
│    Inputs: 2, Outputs: 1                                               │
│    → Width: max(150, 14*15*0.6+40, 2*30) = 166px                       │
│    → Height: 30 + (2*25) + 20 = 100px                                  │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        Usage Flow                                       │
│                                                                         │
│  1. Create context                                                      │
│     dpg.create_context()                                                │
│                                                                         │
│  2. Create editor                                                       │
│     editor = ZoomableNodeEditor(tag="demo", width=800, height=600)     │
│                                                                         │
│  3. Create window and add editor                                       │
│     with dpg.window(...):                                               │
│         editor.create(parent)                                           │
│                                                                         │
│  4. Add nodes and connections                                          │
│     editor.add_node("n1", "Input", 100, 100, inputs=0, outputs=2)      │
│     editor.add_connection("n1", 0, "n2", 0)                             │
│                                                                         │
│  5. Setup viewport                                                      │
│     dpg.create_viewport()                                               │
│     dpg.setup_dearpygui()                                               │
│     dpg.show_viewport()                                                 │
│                                                                         │
│  6. Main loop (IMPORTANT!)                                             │
│     while dpg.is_dearpygui_running():                                   │
│         editor.update()  ← Must call this!                              │
│         dpg.render_dearpygui_frame()                                    │
│                                                                         │
│  7. Cleanup                                                             │
│     dpg.destroy_context()                                               │
└─────────────────────────────────────────────────────────────────────────┘
```
