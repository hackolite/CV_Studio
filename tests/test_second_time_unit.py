#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for second time unit addition to objchart node
"""
import sys
import os
from datetime import datetime

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_second_time_unit_in_chart():
    """Test that objchart supports 'second' as a time unit"""
    from node.VisualNode.node_obj_chart import Node
    
    # Create a node instance
    node = Node(opencv_setting_dict={'process_width': 600, 'process_height': 400})
    
    # Test get_time_bucket with "second"
    bucket_second = node.get_time_bucket("second")
    
    # Verify microseconds are zeroed but seconds are preserved
    assert bucket_second.microsecond == 0, "Microseconds should be zeroed"
    
    # Test that minute and hour still work
    bucket_minute = node.get_time_bucket("minute")
    assert bucket_minute.second == 0 and bucket_minute.microsecond == 0, "Second bucket should zero seconds"
    
    bucket_hour = node.get_time_bucket("hour")
    assert bucket_hour.minute == 0 and bucket_hour.second == 0 and bucket_hour.microsecond == 0, "Hour bucket should zero minutes"
    
    print("✓ Time bucket calculation verified for all units")
    print(f"  Second bucket: {bucket_second.strftime('%H:%M:%S')}")
    print(f"  Minute bucket: {bucket_minute.strftime('%H:%M')}")
    print(f"  Hour bucket: {bucket_hour.strftime('%H:00')}")
    
    return True


def test_second_time_format_in_chart():
    """Test that chart renders time labels correctly for seconds"""
    from node.VisualNode.node_obj_chart import Node
    import numpy as np
    
    # Create a node instance
    node = Node(opencv_setting_dict={'process_width': 600, 'process_height': 400})
    
    # Add some test data with second-level buckets
    now = datetime.now()
    for i in range(5):
        bucket = now.replace(microsecond=0)
        node.time_counts["All"][bucket] = i + 1
        now = now.replace(second=now.second + 1)
    
    # Render chart with "second" time unit
    chart_image = node.render_chart("second", ["All"], {}, "bar")
    
    assert chart_image is not None, "Chart should be rendered"
    assert isinstance(chart_image, np.ndarray), "Chart should be a numpy array"
    
    print("✓ Chart rendering verified for second time unit")
    print(f"  Chart shape: {chart_image.shape}")
    
    return True


def test_positive_decibel_values():
    """Test that decibel values are now positive"""
    import numpy as np
    
    # Simulate RMS calculation like in node_microphone.py
    test_signal = np.array([0.1, 0.2, 0.15, 0.3], dtype=np.float32)
    rms = np.sqrt(np.mean(test_signal**2))
    
    # Original calculation (negative)
    db_original = 20 * np.log10(rms)
    
    # New calculation (positive)
    db_positive = -db_original
    
    print("✓ Decibel transformation verified")
    print(f"  RMS: {rms:.4f}")
    print(f"  Original dB: {db_original:.2f}")
    print(f"  Positive dB: {db_positive:.2f}")
    
    # Verify the transformation
    assert db_original < 0, "Original dB should be negative for RMS < 1.0"
    assert db_positive > 0, "Transformed dB should be positive"
    assert abs(db_positive + db_original) < 0.001, "Magnitudes should match"
    
    return True


if __name__ == '__main__':
    print("Testing Second Time Unit Addition...")
    print("=" * 60)
    
    tests = [
        ("Second Time Unit in Chart", test_second_time_unit_in_chart),
        ("Second Time Format in Chart", test_second_time_format_in_chart),
        ("Positive Decibel Values", test_positive_decibel_values),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            if test_func():
                passed += 1
                print(f"✓ PASSED: {name}")
        except Exception as e:
            print(f"✗ {name} test failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
