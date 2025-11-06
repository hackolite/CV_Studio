#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility functions for spectrogram colormap application.

This module provides utilities for applying colormaps to 2D spectrogram arrays,
converting them to colored RGB images for better visualization and event detection.
"""

import cv2
import numpy as np
import matplotlib.cm as cm


def apply_colormap_cv2(spectrogram_2d, colormap=cv2.COLORMAP_INFERNO):
    """
    Apply colormap to a 2D spectrogram using OpenCV (fast and efficient).
    
    Args:
        spectrogram_2d: np.ndarray with shape (H, W), dtype float or int
                       Represents amplitude/dB values of the spectrogram
        colormap: OpenCV colormap constant (e.g., cv2.COLORMAP_INFERNO, 
                 cv2.COLORMAP_VIRIDIS, cv2.COLORMAP_JET)
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D
    """
    if spectrogram_2d.ndim != 2:
        raise ValueError("spectrogram_2d must be 2D")
    
    # Normalize to 0..255
    norm = cv2.normalize(spectrogram_2d, None, 0, 255, cv2.NORM_MINMAX)
    img_u8 = np.clip(norm, 0, 255).astype(np.uint8)
    
    # Apply colormap (returns BGR)
    colored_bgr = cv2.applyColorMap(img_u8, colormap)
    
    # Convert BGR to RGB
    colored_rgb = cv2.cvtColor(colored_bgr, cv2.COLOR_BGR2RGB)
    
    return colored_rgb


def apply_colormap_mpl(spectrogram_2d, cmap_name='viridis'):
    """
    Apply colormap to a 2D spectrogram using matplotlib (fallback method).
    
    Args:
        spectrogram_2d: np.ndarray with shape (H, W), dtype float or int
                       Represents amplitude/dB values of the spectrogram
        cmap_name: Matplotlib colormap name (e.g., 'viridis', 'inferno', 'jet')
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D
    """
    if spectrogram_2d.ndim != 2:
        raise ValueError("spectrogram_2d must be 2D")
    
    # Get the colormap (use new API if available, fallback to deprecated)
    import matplotlib
    if hasattr(matplotlib, 'colormaps'):
        cmap = matplotlib.colormaps.get_cmap(cmap_name)
    else:
        cmap = cm.get_cmap(cmap_name)
    
    # Normalize to 0..1 range, handling edge cases
    min_val = np.nanmin(spectrogram_2d)
    max_val = np.nanmax(spectrogram_2d)
    denom = max_val - min_val
    
    if denom == 0 or not np.isfinite(denom):
        # All values are the same or invalid
        normed = np.full_like(spectrogram_2d, 0.5, dtype=np.float64)
    else:
        normed = (spectrogram_2d - min_val) / denom
    
    # Replace any non-finite values with 0
    normed = np.nan_to_num(normed, nan=0.0, posinf=1.0, neginf=0.0)
    
    # Apply colormap (returns RGBA with values in 0..1)
    rgba = cmap(normed)
    
    # Convert to RGB (discard alpha) and scale to 0..255
    rgb = (rgba[..., :3] * 255).astype(np.uint8)
    
    return rgb


def apply_colormap_to_spectrogram(arr2d, method='cv2', cmap='INFERNO'):
    """
    Robust wrapper for applying colormaps to spectrograms.
    Detects the method and applies the appropriate colormap function.
    
    Args:
        arr2d: np.ndarray with shape (H, W), dtype float or int
               2D spectrogram array
        method: 'cv2' (default, uses OpenCV) or 'mpl' (uses matplotlib)
        cmap: Colormap name. For 'cv2' method: 'INFERNO', 'VIRIDIS', 'JET', 
              'MAGMA', 'PLASMA', etc. For 'mpl' method: lowercase matplotlib 
              colormap names like 'inferno', 'viridis', 'jet', etc.
    
    Returns:
        np.ndarray: RGB image with shape (H, W, 3) and dtype uint8
    
    Raises:
        ValueError: If input is not 2D or method is not recognized
    """
    if arr2d.ndim != 2:
        raise ValueError("Input array must be 2D")
    
    if method == 'cv2':
        # Map string to OpenCV colormap constant
        cmap_upper = cmap.upper()
        colormap_attr = f"COLORMAP_{cmap_upper}"
        
        if hasattr(cv2, colormap_attr):
            cv_colormap = getattr(cv2, colormap_attr)
        else:
            # Default to INFERNO if colormap not found
            print(f"Warning: Colormap '{cmap}' not found, using INFERNO as fallback")
            cv_colormap = cv2.COLORMAP_INFERNO
        
        return apply_colormap_cv2(arr2d, colormap=cv_colormap)
    
    elif method == 'mpl':
        # Use matplotlib with lowercase colormap name
        cmap_name = cmap.lower()
        return apply_colormap_mpl(arr2d, cmap_name=cmap_name)
    
    else:
        raise ValueError(f"Unknown method '{method}'. Use 'cv2' or 'mpl'.")


# OpenCV colormap constants for reference
AVAILABLE_OPENCV_COLORMAPS = [
    'AUTUMN', 'BONE', 'JET', 'WINTER', 'RAINBOW', 'OCEAN', 'SUMMER',
    'SPRING', 'COOL', 'HSV', 'PINK', 'HOT', 'PARULA', 'MAGMA', 'INFERNO',
    'PLASMA', 'VIRIDIS', 'CIVIDIS', 'TWILIGHT', 'TWILIGHT_SHIFTED', 'TURBO'
]
