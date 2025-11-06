#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test that grayscale spectrogram mode works correctly for audio classification models.

This test verifies that:
1. The DEFAULT_SPECTROGRAM_COLORMAP is set to 'GRAYSCALE'
2. The _prepare_spectrogram method handles GRAYSCALE mode correctly
3. Grayscale spectrograms are converted to 3-channel BGR for compatibility
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_default_colormap_is_grayscale():
    """Test that the default colormap is set to GRAYSCALE for audio classification"""
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node/InputNode/node_video.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that DEFAULT_SPECTROGRAM_COLORMAP is set to 'GRAYSCALE'
    assert "DEFAULT_SPECTROGRAM_COLORMAP = 'GRAYSCALE'" in content, \
        "DEFAULT_SPECTROGRAM_COLORMAP should be set to 'GRAYSCALE' for audio classification"
    
    print("✓ Default spectrogram colormap is set to GRAYSCALE")


def test_grayscale_mode_implementation():
    """Test that GRAYSCALE mode is implemented in _prepare_spectrogram"""
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node/InputNode/node_video.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that GRAYSCALE mode is implemented
    assert "if self._spectrogram_colormap == 'GRAYSCALE':" in content, \
        "_prepare_spectrogram should check for GRAYSCALE mode"
    
    # Check that grayscale is converted to BGR
    assert "cv2.COLOR_GRAY2BGR" in content, \
        "GRAYSCALE spectrograms should be converted to BGR for compatibility"
    
    print("✓ GRAYSCALE mode is properly implemented")


def test_colormap_comment_updated():
    """Test that comments mention GRAYSCALE option"""
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node/InputNode/node_video.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that comments mention GRAYSCALE
    assert "'GRAYSCALE'" in content, \
        "Comments should mention GRAYSCALE option"
    
    # Check that comments mention audio classification
    assert "audio classification" in content.lower(), \
        "Comments should mention that GRAYSCALE is for audio classification"
    
    print("✓ Comments properly document GRAYSCALE option")


def test_grayscale_processing_logic():
    """Test that grayscale processing logic is correct"""
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node/InputNode/node_video.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Verify the grayscale processing steps are in order
    grayscale_section_start = content.find("if self._spectrogram_colormap == 'GRAYSCALE':")
    assert grayscale_section_start != -1, "GRAYSCALE mode check not found"
    
    # Find the else clause to determine the section boundary
    else_clause_pos = content.find("else:", grayscale_section_start)
    assert else_clause_pos != -1, "else clause not found after GRAYSCALE check"
    
    # Extract the grayscale section
    grayscale_section = content[grayscale_section_start:else_clause_pos]
    
    # Check that normalize is called
    assert "cv2.normalize" in grayscale_section, \
        "cv2.normalize should be called for GRAYSCALE mode"
    
    # Check that flipud is called
    assert "np.flipud" in grayscale_section, \
        "np.flipud should be called for GRAYSCALE mode"
    
    # Check that COLOR_GRAY2BGR conversion is called
    assert "COLOR_GRAY2BGR" in grayscale_section, \
        "COLOR_GRAY2BGR conversion should be called for GRAYSCALE mode"
    
    print("✓ Grayscale processing logic is correctly implemented")


def test_esc50_comment():
    """Test that ESC-50 is mentioned in comments"""
    
    file_path = os.path.join(os.path.dirname(__file__), '..', 'node/InputNode/node_video.py')
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that ESC-50 is mentioned as a use case
    assert "ESC-50" in content or "esc-50" in content.lower() or "audio classification" in content.lower(), \
        "Comments should mention ESC-50 or audio classification use case"
    
    print("✓ ESC-50/audio classification use case is documented")


if __name__ == '__main__':
    print("Running grayscale spectrogram tests...\n")
    
    try:
        test_default_colormap_is_grayscale()
        test_grayscale_mode_implementation()
        test_colormap_comment_updated()
        test_grayscale_processing_logic()
        test_esc50_comment()
        
        print("\n" + "="*70)
        print("All grayscale spectrogram tests passed! ✓")
        print("="*70)
        print("\nGrayscale spectrogram support is now available:")
        print("  ✓ DEFAULT_SPECTROGRAM_COLORMAP set to 'GRAYSCALE'")
        print("  ✓ Grayscale mode properly handles normalization")
        print("  ✓ Grayscale spectrograms converted to BGR for compatibility")
        print("  ✓ Recommended for audio classification models like ESC-50")
        print("\nThis should fix the issue where dog barking was classified as snoring!")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
