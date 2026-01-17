"""
Bounding box utility functions.

This module provides pure NumPy implementations of bounding box operations,
replacing the cython_bbox dependency to avoid compilation issues.
"""

import numpy as np


def bbox_overlaps(boxes1, boxes2):
    """
    Compute pairwise IoU (Intersection over Union) between two sets of bounding boxes.
    
    This is a pure NumPy replacement for cython_bbox.bbox_overlaps.
    The implementation uses vectorized operations for efficiency.
    
    Args:
        boxes1: numpy array of shape (N, 4) in format [x1, y1, x2, y2]
                where (x1, y1) is the top-left corner and (x2, y2) is the bottom-right corner
        boxes2: numpy array of shape (M, 4) in format [x1, y1, x2, y2]
                where (x1, y1) is the top-left corner and (x2, y2) is the bottom-right corner
        
    Returns:
        ious: numpy array of shape (N, M) containing pairwise IoU values
              Each element ious[i, j] represents the IoU between boxes1[i] and boxes2[j]
    
    Note:
        This function expects boxes to be in contiguous float64 format.
        It handles empty arrays gracefully and returns zeros for non-overlapping boxes.
    """
    # Ensure inputs are numpy arrays with correct dtype and memory layout
    boxes1 = np.ascontiguousarray(boxes1, dtype=np.float64)
    boxes2 = np.ascontiguousarray(boxes2, dtype=np.float64)
    
    # Get number of boxes
    N = boxes1.shape[0]
    M = boxes2.shape[0]
    
    # Handle empty cases
    if N == 0 or M == 0:
        return np.zeros((N, M), dtype=np.float64)
    
    # Compute areas of all boxes
    # boxes format: [x1, y1, x2, y2]
    area1 = (boxes1[:, 2] - boxes1[:, 0]) * (boxes1[:, 3] - boxes1[:, 1])  # Shape: (N,)
    area2 = (boxes2[:, 2] - boxes2[:, 0]) * (boxes2[:, 3] - boxes2[:, 1])  # Shape: (M,)
    
    # Expand dimensions for broadcasting
    # boxes1: (N, 4) -> (N, 1, 4)
    # boxes2: (M, 4) -> (1, M, 4)
    boxes1_exp = boxes1[:, np.newaxis, :]  # Shape: (N, 1, 4)
    boxes2_exp = boxes2[np.newaxis, :, :]  # Shape: (1, M, 4)
    
    # Compute intersection coordinates using broadcasting
    # Result shapes will be (N, M)
    x1_inter = np.maximum(boxes1_exp[:, :, 0], boxes2_exp[:, :, 0])
    y1_inter = np.maximum(boxes1_exp[:, :, 1], boxes2_exp[:, :, 1])
    x2_inter = np.minimum(boxes1_exp[:, :, 2], boxes2_exp[:, :, 2])
    y2_inter = np.minimum(boxes1_exp[:, :, 3], boxes2_exp[:, :, 3])
    
    # Compute intersection area
    inter_width = np.maximum(0.0, x2_inter - x1_inter)
    inter_height = np.maximum(0.0, y2_inter - y1_inter)
    intersection = inter_width * inter_height  # Shape: (N, M)
    
    # Compute union area using broadcasting
    # area1: (N,) -> (N, 1)
    # area2: (M,) -> (1, M)
    # Result: (N, M)
    union = area1[:, np.newaxis] + area2[np.newaxis, :] - intersection
    
    # Compute IoU (handle division by zero)
    ious = np.where(union > 0, intersection / union, 0.0)
    
    return ious
