#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shared utilities for heatmap visualization"""

import cv2


# Colormap names and their corresponding OpenCV constants
HEATMAP_COLORMAPS = {
    "JET": cv2.COLORMAP_JET,
    "HOT": cv2.COLORMAP_HOT,
    "COOL": cv2.COLORMAP_COOL,
    "RAINBOW": cv2.COLORMAP_RAINBOW,
    "VIRIDIS": cv2.COLORMAP_VIRIDIS,
    "TURBO": cv2.COLORMAP_TURBO,
}

# Colormap names for dropdown UI
COLORMAP_NAMES = ["JET", "HOT", "COOL", "RAINBOW", "VIRIDIS", "TURBO"]


def get_colormap(colormap_name):
    """
    Get OpenCV colormap constant from name.
    
    Args:
        colormap_name: Name of the colormap (e.g., "JET", "HOT", etc.)
        
    Returns:
        OpenCV colormap constant, defaults to JET if name not found
    """
    return HEATMAP_COLORMAPS.get(colormap_name, cv2.COLORMAP_JET)


def ensure_odd_blur_size(blur_size):
    """
    Ensure blur size is odd for GaussianBlur.
    
    Args:
        blur_size: Desired blur kernel size
        
    Returns:
        Odd blur size (increments by 1 if even)
    """
    if blur_size % 2 == 0:
        blur_size += 1
    return blur_size
