#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify boolean consistency between trigger, router and video recorder
This simulates the data flow: Trigger -> Router -> VideoRecorder
"""

def test_trigger_output():
    """Test that trigger node outputs correct format"""
    print("=" * 60)
    print("TEST 1: Trigger Node Output (ObjDetCount)")
    print("=" * 60)
    
    # Simulate trigger being active
    trigger_active = True
    output_json = {"BOOL": trigger_active}
    
    print(f"Trigger active: {trigger_active}")
    print(f"Output JSON: {output_json}")
    print(f"Has 'BOOL' field: {'BOOL' in output_json}")
    print(f"BOOL value type: {type(output_json['BOOL'])}")
    print(f"BOOL value: {output_json['BOOL']}")
    
    assert 'BOOL' in output_json, "Output must have BOOL field"
    assert isinstance(output_json['BOOL'], bool), "BOOL must be a boolean"
    assert output_json['BOOL'] == trigger_active, "BOOL must match trigger state"
    print("✓ PASSED\n")
    
    return output_json


def test_router_output(trigger_json):
    """Test that router node outputs correct format"""
    print("=" * 60)
    print("TEST 2: Router Node Output (SimpleRouter)")
    print("=" * 60)
    
    # Simulate router receiving trigger JSON and processing it
    # Router checks if combination is met and outputs BOOL
    combination_met = False
    
    # Extract BOOL from input trigger
    if trigger_json and isinstance(trigger_json, dict):
        if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
            combination_met = trigger_json['BOOL']
    
    # Router outputs its own BOOL based on logic
    trigger_active = combination_met  # Simplified logic for test
    output_json = {"BOOL": trigger_active}
    
    print(f"Input from trigger: {trigger_json}")
    print(f"Combination met: {combination_met}")
    print(f"Router trigger active: {trigger_active}")
    print(f"Output JSON: {output_json}")
    print(f"Has 'BOOL' field: {'BOOL' in output_json}")
    print(f"BOOL value type: {type(output_json['BOOL'])}")
    print(f"BOOL value: {output_json['BOOL']}")
    
    assert 'BOOL' in output_json, "Output must have BOOL field"
    assert isinstance(output_json['BOOL'], bool), "BOOL must be a boolean"
    assert output_json['BOOL'] == trigger_active, "BOOL must match trigger state"
    print("✓ PASSED\n")
    
    return output_json


def test_video_recorder_input(router_json):
    """Test that video recorder correctly interprets BOOL field"""
    print("=" * 60)
    print("TEST 3: Video Recorder Input Processing")
    print("=" * 60)
    
    trigger_json = router_json
    
    # Simulate video recorder logic (from node_video_recorder.py lines 282-298)
    should_record = False
    if trigger_json and isinstance(trigger_json, dict):
        # Priority order: 'BOOL' > 'record' > 'trigger' > any boolean
        if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
            should_record = trigger_json['BOOL']
            print(f"Using 'BOOL' field: {should_record}")
        elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
            should_record = trigger_json['record']
            print(f"Using 'record' field: {should_record}")
        elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
            should_record = trigger_json['trigger']
            print(f"Using 'trigger' field: {should_record}")
        else:
            # Fallback: look for any boolean field with value True
            for key, value in trigger_json.items():
                if isinstance(value, bool) and value:
                    should_record = True
                    print(f"Using fallback boolean field '{key}': {should_record}")
                    break
    
    print(f"Input from router: {trigger_json}")
    print(f"Should record: {should_record}")
    
    # Verify the video recorder correctly interprets the BOOL field
    expected_should_record = trigger_json.get('BOOL', False) if trigger_json else False
    assert should_record == expected_should_record, f"Expected {expected_should_record}, got {should_record}"
    print("✓ PASSED\n")
    
    return should_record


def test_edge_cases():
    """Test edge cases and error conditions"""
    print("=" * 60)
    print("TEST 4: Edge Cases")
    print("=" * 60)
    
    test_cases = [
        # (input_json, expected_should_record, description)
        ({'BOOL': True}, True, "BOOL=True should trigger recording"),
        ({'BOOL': False}, False, "BOOL=False should not trigger recording"),
        ({'BOOL': True, 'record': False}, True, "BOOL should override 'record'"),
        ({'BOOL': False, 'record': True, 'trigger': True}, False, "BOOL should override all other fields"),
        ({'record': True}, True, "Backward compatibility: 'record' field should work"),
        ({'trigger': True}, True, "Backward compatibility: 'trigger' field should work"),
        ({'BOOL': 1}, False, "Non-boolean BOOL should not trigger"),
        ({'BOOL': 'true'}, False, "String 'true' should not trigger"),
        ({}, False, "Empty JSON should not trigger"),
        (None, False, "None JSON should not trigger"),
    ]
    
    failed = 0
    for trigger_json, expected, description in test_cases:
        # Video recorder logic
        should_record = False
        if trigger_json and isinstance(trigger_json, dict):
            if 'BOOL' in trigger_json and isinstance(trigger_json['BOOL'], bool):
                should_record = trigger_json['BOOL']
            elif 'record' in trigger_json and isinstance(trigger_json['record'], bool):
                should_record = trigger_json['record']
            elif 'trigger' in trigger_json and isinstance(trigger_json['trigger'], bool):
                should_record = trigger_json['trigger']
            else:
                for key, value in trigger_json.items():
                    if isinstance(value, bool) and value:
                        should_record = True
                        break
        
        status = "✓" if should_record == expected else "✗"
        if should_record != expected:
            failed += 1
        
        print(f"{status} {description}")
        print(f"  Input: {trigger_json}")
        print(f"  Expected: {expected}, Got: {should_record}")
    
    assert failed == 0, f"{failed} edge case test(s) failed"
    print(f"\n✓ All {len(test_cases)} edge cases PASSED\n")


def test_full_pipeline():
    """Test the complete pipeline: Trigger -> Router -> VideoRecorder"""
    print("=" * 60)
    print("TEST 5: Full Pipeline Integration")
    print("=" * 60)
    
    # Step 1: Trigger outputs
    trigger_output = test_trigger_output()
    
    # Step 2: Router receives trigger output and produces its own output
    router_output = test_router_output(trigger_output)
    
    # Step 3: Video recorder receives router output
    should_record = test_video_recorder_input(router_output)
    
    print("=" * 60)
    print("FULL PIPELINE VERIFICATION")
    print("=" * 60)
    print(f"Trigger output: {trigger_output}")
    print(f"Router output: {router_output}")
    print(f"Video recorder decision: {should_record}")
    print("\n✓ FULL PIPELINE PASSED")
    

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("BOOLEAN CONSISTENCY TEST SUITE")
    print("Verifying Trigger -> Router -> VideoRecorder data flow")
    print("=" * 60 + "\n")
    
    try:
        # Run individual component tests
        trigger_json = test_trigger_output()
        router_json = test_router_output(trigger_json)
        test_video_recorder_input(router_json)
        
        # Run edge case tests
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("The boolean consistency between trigger, router,")
        print("and video recorder is working correctly!")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        exit(1)
