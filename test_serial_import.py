#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Test: Verify Serial Module Import

This script tests that the 'serial' module (from pyserial package) can be imported
successfully, which was the main issue reported in the problem statement.

Usage:
    python test_serial_import.py
"""

import sys


def test_serial_import():
    """Test that serial module can be imported"""
    print("Testing serial module import...")
    print("=" * 60)
    
    try:
        import serial
        print("✅ SUCCESS: 'serial' module imported successfully!")
        print(f"   Module location: {serial.__file__}")
        if hasattr(serial, 'VERSION'):
            print(f"   Version: {serial.VERSION}")
        
        # Test serial.tools.list_ports
        print("\nTesting serial.tools.list_ports...")
        from serial.tools import list_ports
        ports = list(list_ports.comports())
        print(f"✅ SUCCESS: serial.tools.list_ports imported successfully!")
        print(f"   Available serial ports: {len(ports)}")
        
        if ports:
            print("   Detected ports:")
            for port in ports[:5]:  # Show first 5 ports
                print(f"     - {port.device}")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("The serial module is properly configured for the build.")
        return 0
        
    except ImportError as e:
        print(f"❌ FAILED: {e}")
        print("\nThe 'serial' module could not be imported.")
        print("Please install pyserial:")
        print("  pip install pyserial")
        print("\n" + "=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(test_serial_import())
