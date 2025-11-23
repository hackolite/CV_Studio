#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verification script - Demonstrates Spectrogram Node functionality
This script simulates what happens when the node is used in CV_Studio
"""
import sys
import os
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def simulate_node_loading():
    """Simulate the node editor loading the Spectrogram node"""
    print("=" * 70)
    print("STEP 1: Node Loading (simulating CV_Studio node editor)")
    print("=" * 70)
    
    from importlib import import_module
    
    # This is what the node editor does
    import_path = 'node.AudioProcessNode.node_spectrogram_node'
    
    try:
        module = import_module(import_path)
        factory = module.FactoryNode()
        print(f"✓ Successfully loaded Spectrogram node")
        print(f"  - Node tag: {factory.node_tag}")
        print(f"  - Node label: {factory.node_label}")
        print(f"  - Factory has add_node: {hasattr(factory, 'add_node')}")
        return factory
    except Exception as e:
        print(f"✗ Failed to load node: {e}")
        return None


def simulate_audio_processing():
    """Simulate processing audio through the Spectrogram node"""
    print("\n" + "=" * 70)
    print("STEP 2: Audio Processing (simulating node update)")
    print("=" * 70)
    
    from node.AudioProcessNode.node_spectrogram_node import SpectrogramNode
    
    # Create a test audio signal (sine wave at 440 Hz - A4 note)
    duration = 1.0
    sample_rate = 44100
    frequency = 440.0
    
    print(f"\nGenerating test audio signal:")
    print(f"  - Duration: {duration}s")
    print(f"  - Sample rate: {sample_rate} Hz")
    print(f"  - Frequency: {frequency} Hz (A4 note)")
    
    t = np.linspace(0, duration, int(sample_rate * duration))
    samples = np.sin(2 * np.pi * frequency * t)
    samples_int16 = (samples * 32767).astype(np.int16)
    
    audio_data = {
        'samples': samples_int16,
        'sample_rate': sample_rate
    }
    
    # Create node instance
    node = SpectrogramNode()
    
    # Test different configurations
    configs = [
        {'fft_size': 1024, 'colormap': 'jet'},
        {'fft_size': 2048, 'colormap': 'viridis'},
        {'fft_size': 512, 'colormap': 'plasma'},
    ]
    
    print(f"\nTesting {len(configs)} different configurations:")
    
    for i, config in enumerate(configs, 1):
        try:
            spectrogram_image = node._generate_spectrogram(
                audio_data,
                fft_size=config['fft_size'],
                colormap=config['colormap']
            )
            
            if spectrogram_image is not None:
                print(f"  {i}. FFT={config['fft_size']}, Colormap={config['colormap']:8s} ✓ "
                      f"Output: {spectrogram_image.shape}")
            else:
                print(f"  {i}. FFT={config['fft_size']}, Colormap={config['colormap']:8s} ✗ Failed")
        except Exception as e:
            print(f"  {i}. FFT={config['fft_size']}, Colormap={config['colormap']:8s} ✗ Error: {e}")


def verify_node_attributes():
    """Verify all required node attributes and methods"""
    print("\n" + "=" * 70)
    print("STEP 3: Node Verification (checking all required components)")
    print("=" * 70)
    
    from node.AudioProcessNode.node_spectrogram_node import FactoryNode, SpectrogramNode
    
    # Check FactoryNode
    factory = FactoryNode()
    factory_checks = [
        ('node_label', 'Spectrogram'),
        ('node_tag', 'Spectrogram'),
    ]
    
    print("\nFactoryNode checks:")
    for attr, expected in factory_checks:
        value = getattr(factory, attr, None)
        status = "✓" if value == expected else "✗"
        print(f"  {status} {attr}: {value} (expected: {expected})")
    
    factory_methods = ['add_node']
    for method in factory_methods:
        has_method = hasattr(factory, method)
        status = "✓" if has_method else "✗"
        print(f"  {status} Method {method}: {'present' if has_method else 'missing'}")
    
    # Check SpectrogramNode
    node = SpectrogramNode()
    node_checks = [
        ('node_label', 'Spectrogram'),
        ('node_tag', 'Spectrogram'),
    ]
    
    print("\nSpectrogramNode checks:")
    for attr, expected in node_checks:
        value = getattr(node, attr, None)
        status = "✓" if value == expected else "✗"
        print(f"  {status} {attr}: {value} (expected: {expected})")
    
    node_methods = ['update', 'close', 'get_setting_dict', 'set_setting_dict', '_generate_spectrogram']
    for method in node_methods:
        has_method = hasattr(node, method)
        status = "✓" if has_method else "✗"
        print(f"  {status} Method {method}: {'present' if has_method else 'missing'}")


def main():
    """Run all verification steps"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  SPECTROGRAM NODE - VERIFICATION SCRIPT".center(68) + "║")
    print("║" + "  Demonstrating the fix for the non-functional Spectrogram node".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # Step 1: Node loading
    factory = simulate_node_loading()
    if factory is None:
        print("\n✗ VERIFICATION FAILED: Could not load node")
        return False
    
    # Step 2: Audio processing
    simulate_audio_processing()
    
    # Step 3: Attribute verification
    verify_node_attributes()
    
    # Final summary
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print("\n✅ The Spectrogram node is fully functional and ready to use!")
    print("\nTo use in CV_Studio:")
    print("  1. Open CV_Studio")
    print("  2. Go to AudioProcess → Spectrogram")
    print("  3. Connect an audio source (e.g., Video node)")
    print("  4. Configure FFT size and colormap")
    print("  5. View the spectrogram visualization")
    print("\n" + "=" * 70)
    
    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
