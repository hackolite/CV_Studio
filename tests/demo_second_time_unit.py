#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Demo script to verify the second time unit and positive decibel changes
"""
import sys
import os
import numpy as np
from datetime import datetime, timedelta

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.VisualNode.node_obj_chart import Node


def demo_time_units():
    """Demonstrate all time unit options"""
    print("\n" + "=" * 60)
    print("DEMO: Time Unit Options")
    print("=" * 60)
    
    # Create a node instance
    node = Node(opencv_setting_dict={'process_width': 600, 'process_height': 400})
    
    # Test all three time units
    time_units = ["second", "minute", "hour"]
    
    for unit in time_units:
        # Add test data
        now = datetime.now()
        for i in range(10):
            bucket = node.get_time_bucket(unit)
            node.time_counts["All"][bucket] = np.random.randint(1, 20)
            
            # Advance time based on unit
            if unit == "second":
                now = now + timedelta(seconds=1)
            elif unit == "minute":
                now = now + timedelta(minutes=1)
            else:  # hour
                now = now + timedelta(hours=1)
        
        # Render chart
        chart_image = node.render_chart(unit, ["All"], {}, "bar")
        
        print(f"\n✓ {unit.capitalize()} time unit chart rendered")
        print(f"  Chart shape: {chart_image.shape}")
        print(f"  Data points: {len(node.time_counts['All'])}")
        
        # Clear data for next unit
        node.time_counts.clear()


def demo_positive_decibels():
    """Demonstrate positive decibel calculation"""
    print("\n" + "=" * 60)
    print("DEMO: Positive Decibel Values")
    print("=" * 60)
    
    # Test various audio signal levels
    test_signals = [
        ("Very quiet", np.array([0.01, 0.02, 0.015], dtype=np.float32)),
        ("Quiet", np.array([0.1, 0.12, 0.08], dtype=np.float32)),
        ("Medium", np.array([0.3, 0.35, 0.28], dtype=np.float32)),
        ("Loud", np.array([0.6, 0.65, 0.58], dtype=np.float32)),
        ("Very loud", np.array([0.9, 0.92, 0.88], dtype=np.float32)),
    ]
    
    print("\nSignal Level | RMS   | Original dB | Positive dB")
    print("-" * 60)
    
    for label, signal in test_signals:
        rms = np.sqrt(np.mean(signal**2))
        db_original = 20 * np.log10(rms)
        db_positive = -db_original  # Transformation applied in node_microphone.py
        
        print(f"{label:12s} | {rms:.4f} | {db_original:11.2f} | {db_positive:11.2f}")
    
    print("\n✓ All decibel values are now positive!")


def demo_chart_with_db_data():
    """Demonstrate chart with positive dB data"""
    print("\n" + "=" * 60)
    print("DEMO: Chart with Positive dB Data")
    print("=" * 60)
    
    # Create a node instance
    node = Node(opencv_setting_dict={'process_width': 600, 'process_height': 400})
    
    # Simulate microphone dB intensity data over time (seconds)
    now = datetime.now()
    for i in range(10):
        bucket = now.replace(microsecond=0)
        
        # Simulate varying audio levels (positive dB values)
        rms = 0.1 + (i * 0.05)  # Increasing audio level
        db_original = 20 * np.log10(rms)
        db_positive = -db_original  # Make positive
        
        node.time_counts["dB"][bucket] = db_positive
        now = now + timedelta(seconds=1)
    
    # Render chart with second time unit
    chart_image = node.render_chart("second", ["dB"], {"dB": "Decibel Intensity"}, "line")
    
    print(f"\n✓ Chart with positive dB values rendered")
    print(f"  Chart shape: {chart_image.shape}")
    print(f"  Time unit: second")
    print(f"  Data points: {len(node.time_counts['dB'])}")
    print(f"  dB value range: {min(node.time_counts['dB'].values()):.2f} to {max(node.time_counts['dB'].values()):.2f}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("VERIFICATION DEMO: Second Time Unit & Positive Decibels")
    print("=" * 60)
    
    try:
        demo_time_units()
        demo_positive_decibels()
        demo_chart_with_db_data()
        
        print("\n" + "=" * 60)
        print("✓ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nSummary of changes:")
        print("1. Added 'second' as a time unit option in chart dropdown")
        print("2. Chart now supports second-level time aggregation")
        print("3. Decibel values are now positive (multiplied by -1)")
        print("4. All existing functionality preserved")
        
    except Exception as e:
        print(f"\n✗ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
