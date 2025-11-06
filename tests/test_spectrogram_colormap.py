#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for spectrogram colormap utility functions.

This test module validates the colormap application functions for spectrograms,
ensuring they produce correctly formatted RGB output images.
"""

import pytest
import sys
import os
import numpy as np
import cv2
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.InputNode.spectrogram_utils import (
    apply_colormap_cv2,
    apply_colormap_mpl,
    apply_colormap_to_spectrogram,
)


def generate_test_spectrogram(height=256, width=512, seed=42):
    """
    Generate a synthetic 2D spectrogram for testing.
    Creates a gradient pattern with some frequency bands.
    
    Args:
        height: Height of the spectrogram (frequency bins)
        width: Width of the spectrogram (time frames)
        seed: Random seed for reproducibility
    
    Returns:
        np.ndarray: 2D array representing a spectrogram
    """
    # Set random seed for reproducibility
    np.random.seed(seed)
    
    # Create a gradient pattern
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    
    # Combine patterns to create interesting spectrogram-like data
    spectrogram = np.sin(2 * np.pi * X * 5) * np.exp(-Y * 2) + 0.3 * np.random.randn(height, width)
    
    # Normalize to positive values (like dB scale)
    spectrogram = np.abs(spectrogram) * 100
    
    return spectrogram


def test_apply_colormap_cv2_basic():
    """Test basic colormap application using OpenCV."""
    spectrogram = generate_test_spectrogram(128, 256)
    
    # Apply colormap
    result = apply_colormap_cv2(spectrogram, colormap=cv2.COLORMAP_INFERNO)
    
    # Verify output properties
    assert result.shape == (128, 256, 3), "Output shape should be (H, W, 3)"
    assert result.dtype == np.uint8, "Output dtype should be uint8"
    assert np.all(result >= 0) and np.all(result <= 255), "Values should be in 0-255 range"
    
    # Verify that channels are not identical (should be colored, not grayscale)
    assert not np.all(result[..., 0] == result[..., 1]), "Red and Green channels should differ"
    assert not np.all(result[..., 1] == result[..., 2]), "Green and Blue channels should differ"
    


def test_apply_colormap_cv2_different_colormaps():
    """Test different OpenCV colormaps."""
    spectrogram = generate_test_spectrogram(64, 128)
    
    colormaps = [
        cv2.COLORMAP_INFERNO,
        cv2.COLORMAP_VIRIDIS,
        cv2.COLORMAP_JET,
        cv2.COLORMAP_MAGMA,
    ]
    
    for cmap in colormaps:
        result = apply_colormap_cv2(spectrogram, colormap=cmap)
        assert result.shape == (64, 128, 3), f"Output shape should be (64, 128, 3) for colormap {cmap}"
        assert result.dtype == np.uint8, f"Output dtype should be uint8 for colormap {cmap}"
    


def test_apply_colormap_mpl_basic():
    """Test basic colormap application using matplotlib."""
    spectrogram = generate_test_spectrogram(128, 256)
    
    # Apply colormap
    result = apply_colormap_mpl(spectrogram, cmap_name='inferno')
    
    # Verify output properties
    assert result.shape == (128, 256, 3), "Output shape should be (H, W, 3)"
    assert result.dtype == np.uint8, "Output dtype should be uint8"
    assert np.all(result >= 0) and np.all(result <= 255), "Values should be in 0-255 range"
    
    # Verify that channels are not identical (should be colored, not grayscale)
    assert not np.all(result[..., 0] == result[..., 1]), "Red and Green channels should differ"
    


def test_apply_colormap_mpl_different_colormaps():
    """Test different matplotlib colormaps."""
    spectrogram = generate_test_spectrogram(64, 128)
    
    colormaps = ['inferno', 'viridis', 'jet', 'magma', 'plasma']
    
    for cmap in colormaps:
        result = apply_colormap_mpl(spectrogram, cmap_name=cmap)
        assert result.shape == (64, 128, 3), f"Output shape should be (64, 128, 3) for colormap {cmap}"
        assert result.dtype == np.uint8, f"Output dtype should be uint8 for colormap {cmap}"
    


def test_apply_colormap_wrapper_cv2():
    """Test the wrapper function with OpenCV method."""
    spectrogram = generate_test_spectrogram(100, 200)
    
    # Test with different colormaps
    for cmap_name in ['INFERNO', 'VIRIDIS', 'JET']:
        result = apply_colormap_to_spectrogram(spectrogram, method='cv2', cmap=cmap_name)
        assert result.shape == (100, 200, 3), f"Output shape should be (100, 200, 3) for {cmap_name}"
        assert result.dtype == np.uint8, f"Output dtype should be uint8 for {cmap_name}"
    


def test_apply_colormap_wrapper_mpl():
    """Test the wrapper function with matplotlib method."""
    spectrogram = generate_test_spectrogram(100, 200)
    
    # Test with different colormaps
    for cmap_name in ['inferno', 'viridis', 'jet']:
        result = apply_colormap_to_spectrogram(spectrogram, method='mpl', cmap=cmap_name)
        assert result.shape == (100, 200, 3), f"Output shape should be (100, 200, 3) for {cmap_name}"
        assert result.dtype == np.uint8, f"Output dtype should be uint8 for {cmap_name}"
    


def test_edge_case_uniform_values():
    """Test with uniform spectrogram values (edge case)."""
    # Create spectrogram with all same values
    spectrogram = np.full((50, 100), 42.0)
    
    result_cv2 = apply_colormap_cv2(spectrogram, colormap=cv2.COLORMAP_INFERNO)
    result_mpl = apply_colormap_mpl(spectrogram, cmap_name='inferno')
    
    assert result_cv2.shape == (50, 100, 3), "CV2 result should have correct shape"
    assert result_mpl.shape == (50, 100, 3), "MPL result should have correct shape"
    assert result_cv2.dtype == np.uint8, "CV2 result should be uint8"
    assert result_mpl.dtype == np.uint8, "MPL result should be uint8"
    


def test_edge_case_nan_values():
    """Test handling of NaN values in spectrogram."""
    spectrogram = generate_test_spectrogram(50, 100)
    # Add some NaN values
    spectrogram[10:20, 30:40] = np.nan
    
    # Should handle NaN gracefully
    result_mpl = apply_colormap_mpl(spectrogram, cmap_name='inferno')
    
    assert result_mpl.shape == (50, 100, 3), "Result should have correct shape"
    assert result_mpl.dtype == np.uint8, "Result should be uint8"
    assert np.all(np.isfinite(result_mpl)), "Result should not contain NaN or Inf"
    


def test_invalid_input_dimensions():
    """Test that invalid input dimensions raise appropriate errors."""
    # 1D array
    arr_1d = np.random.rand(100)
    with pytest.raises(ValueError):
        apply_colormap_cv2(arr_1d)
    
    # 3D array
    arr_3d = np.random.rand(10, 20, 3)
    with pytest.raises(ValueError):
        apply_colormap_cv2(arr_3d)
    


def test_save_colormap_example():
    """
    Generate and save example colored spectrograms for visual verification.
    This creates test output files that can be manually inspected.
    """
    # Create output directory
    output_dir = tempfile.gettempdir()
    
    # Generate test spectrogram with clear frequency bands
    height, width = 256, 512
    spectrogram = generate_test_spectrogram(height, width)
    
    # Test multiple colormaps
    colormaps = ['INFERNO', 'VIRIDIS', 'JET', 'MAGMA']
    
    for cmap_name in colormaps:
        # Apply colormap
        colored = apply_colormap_to_spectrogram(spectrogram, method='cv2', cmap=cmap_name)
        
        # Convert RGB to BGR for saving with OpenCV
        colored_bgr = cv2.cvtColor(colored, cv2.COLOR_RGB2BGR)
        
        # Save to file
        output_path = os.path.join(output_dir, f'spectro_color_{cmap_name.lower()}.png')
        cv2.imwrite(output_path, colored_bgr)
        
        # Verify file was created
        assert os.path.exists(output_path), f"Output file should be created: {output_path}"
        
        # Verify it can be read back
        loaded = cv2.imread(output_path)
        assert loaded is not None, f"Output file should be readable: {output_path}"
        assert loaded.shape == (height, width, 3), "Loaded image should have correct shape"
        
        print(f"  Saved example: {output_path}")
    


def test_channels_not_identical():
    """
    Verify that colored spectrograms have non-identical RGB channels.
    This ensures the output is truly colored and not grayscale.
    """
    spectrogram = generate_test_spectrogram(128, 256)
    
    # Apply colormap
    result = apply_colormap_to_spectrogram(spectrogram, method='cv2', cmap='INFERNO')
    
    # Extract channels
    r_channel = result[..., 0]
    g_channel = result[..., 1]
    b_channel = result[..., 2]
    
    # Check that at least some pixels differ between channels
    r_g_diff = np.sum(r_channel != g_channel)
    g_b_diff = np.sum(g_channel != b_channel)
    r_b_diff = np.sum(r_channel != b_channel)
    
    assert r_g_diff > 0, "Red and Green channels should have differences"
    assert g_b_diff > 0, "Green and Blue channels should have differences"
    assert r_b_diff > 0, "Red and Blue channels should have differences"
    
    # For colored images, most pixels should have different channel values
    total_pixels = r_channel.size
    assert r_g_diff > total_pixels * 0.5, "More than 50% of pixels should differ in R-G channels"
