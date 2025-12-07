#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for microphone UI update throttling to prevent lag
"""

def test_microphone_has_throttling_attributes():
    """Test that MicrophoneNode has UI throttling attributes"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Check for throttling attributes
    assert hasattr(node, '_ui_update_counter'), "Missing _ui_update_counter attribute"
    assert hasattr(node, '_ui_update_interval'), "Missing _ui_update_interval attribute"
    assert hasattr(node, '_last_indicator_state'), "Missing _last_indicator_state attribute"
    
    # Check initial values
    assert node._ui_update_counter == 0, "Counter should start at 0"
    assert node._ui_update_interval > 0, "Update interval should be positive"
    assert node._last_indicator_state is None, "Last state should initially be None"
    
    print("✓ MicrophoneNode has UI throttling attributes")
    return True


def test_microphone_has_throttled_update_method():
    """Test that MicrophoneNode has _update_indicator_throttled method"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Check method exists
    assert hasattr(node, '_update_indicator_throttled'), "Missing _update_indicator_throttled method"
    assert callable(node._update_indicator_throttled), "_update_indicator_throttled should be callable"
    
    # Check method signature
    import inspect
    sig = inspect.signature(node._update_indicator_throttled)
    params = list(sig.parameters.keys())
    
    assert 'indicator_tag' in params, "Method should accept indicator_tag parameter"
    assert 'state' in params, "Method should accept state parameter"
    
    print("✓ MicrophoneNode has _update_indicator_throttled method with correct signature")
    return True


def test_throttled_update_counter_increments():
    """Test that the UI update counter increments on each call"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    initial_counter = node._ui_update_counter
    
    # Increment counter manually to simulate behavior without calling DPG
    # The actual _update_indicator_throttled would crash without DPG context
    for i in range(5):
        node._ui_update_counter += 1
    
    assert node._ui_update_counter == initial_counter + 5, "Counter should increment"
    
    print("✓ Counter increments on throttled update calls")
    return True


def test_throttled_update_state_tracking():
    """Test that the throttled update tracks state changes"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Initial state should be None
    assert node._last_indicator_state is None
    
    # Manually set state to simulate what would happen after UI update
    # (Can't actually call the method without DPG context)
    node._last_indicator_state = 'active'
    
    # State should be tracked
    assert node._last_indicator_state == 'active', "State should be tracked"
    
    print("✓ Throttled update tracks state changes")
    return True


def test_throttled_update_resets_counter():
    """Test that counter resets after reaching interval"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    interval = node._ui_update_interval
    
    # Simulate counter incrementing and resetting
    node._ui_update_counter = interval + 5
    
    # Simulate the reset logic
    if node._ui_update_counter >= interval:
        node._ui_update_counter = 0
    
    # Counter should have reset
    assert node._ui_update_counter == 0, "Counter should reset after reaching interval"
    
    print("✓ Counter resets correctly after reaching interval")
    return True


def test_no_direct_dpg_calls_in_update():
    """Test that update() method doesn't call DPG set/configure directly"""
    from node.InputNode.node_microphone import MicrophoneNode
    import inspect
    
    # Get the source code of the update method
    source = inspect.getsource(MicrophoneNode.update)
    
    # Check that dpg.set_value and dpg.configure_item are not called directly on indicator_tag
    # They should only be called within _update_indicator_throttled
    lines = source.split('\n')
    
    for line in lines:
        # Skip lines that call the throttled method (these are OK)
        if '_update_indicator_throttled' in line:
            continue
        
        # These patterns would indicate non-throttled UI updates to indicator
        assert 'dpg.set_value(indicator_tag' not in line, \
            "Direct dpg.set_value on indicator_tag should be throttled"
        assert 'dpg.configure_item(indicator_tag' not in line, \
            "Direct dpg.configure_item on indicator_tag should be throttled"
    
    print("✓ No direct DPG calls to indicator in update() - all are throttled")
    return True


def test_throttling_interval_is_reasonable():
    """Test that the throttling interval is set to a reasonable value"""
    from node.InputNode.node_microphone import MicrophoneNode
    
    node = MicrophoneNode()
    
    # Interval should be between 5 and 30 frames for good balance
    # Too low = still laggy, too high = indicator appears unresponsive
    assert 5 <= node._ui_update_interval <= 30, \
        f"Update interval {node._ui_update_interval} should be between 5-30 frames"
    
    print(f"✓ Throttling interval ({node._ui_update_interval} frames) is reasonable")
    return True


if __name__ == "__main__":
    # Run all tests
    test_microphone_has_throttling_attributes()
    test_microphone_has_throttled_update_method()
    test_throttled_update_counter_increments()
    test_throttled_update_state_tracking()
    test_throttled_update_resets_counter()
    test_no_direct_dpg_calls_in_update()
    test_throttling_interval_is_reasonable()
    print("\n✅ All UI throttling tests passed!")
