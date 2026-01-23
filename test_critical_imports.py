#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify critical imports work correctly in the built .exe

This script tests the three problematic imports that were failing:
1. pytz - timezone handling
2. lap - linear assignment for tracking
3. PIL.ImageGrab - screen capture

Run this after building the .exe to verify the fixes work.
"""

import sys

def test_pytz():
    """Test pytz import and timezone data access"""
    print("Testing pytz...")
    try:
        import pytz
        # Test that timezone data is accessible
        tz = pytz.timezone('UTC')
        from datetime import datetime
        dt = datetime.now(tz)
        print(f"  ✓ pytz works - current UTC time: {dt}")
        return True
    except Exception as e:
        print(f"  ✗ pytz failed: {e}")
        return False

def test_lap():
    """Test lap import and basic functionality"""
    print("Testing lap...")
    try:
        import lap
        import numpy as np
        # Test basic lap functionality with a small cost matrix
        cost_matrix = np.array([[1.0, 2.0], [3.0, 4.0]])
        cost, x, y = lap.lapjv(cost_matrix, extend_cost=True)
        print(f"  ✓ lap works - linear assignment result: cost={cost}, x={x}, y={y}")
        return True
    except Exception as e:
        print(f"  ✗ lap failed: {e}")
        return False

def test_pil_imagegrab():
    """Test PIL.ImageGrab import"""
    print("Testing PIL.ImageGrab...")
    try:
        from PIL import ImageGrab
        print("  ✓ PIL.ImageGrab imported successfully")
        # Don't actually grab screen in test, just verify import works
        print("  Note: Screen capture not tested, only import verification")
        return True
    except Exception as e:
        print(f"  ✗ PIL.ImageGrab failed: {e}")
        return False

def main():
    """Run all import tests"""
    print("=" * 70)
    print("CV_Studio - Critical Import Test")
    print("=" * 70)
    print()
    
    results = []
    results.append(("pytz", test_pytz()))
    print()
    results.append(("lap", test_lap()))
    print()
    results.append(("PIL.ImageGrab", test_pil_imagegrab()))
    print()
    
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {name}")
    
    all_passed = all(passed for _, passed in results)
    print()
    if all_passed:
        print("✓ All tests passed! The .exe build should work correctly.")
        return 0
    else:
        print("✗ Some tests failed. The .exe may have import issues.")
        print("  Make sure to rebuild with: python build_exe.py --clean")
        return 1

if __name__ == '__main__':
    sys.exit(main())
