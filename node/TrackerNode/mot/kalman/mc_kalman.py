# -*- coding: utf-8 -*-
"""
Multi-Class Kalman Filter Tracker Wrapper
Wraps the Kalman filter tracker to handle multi-class object tracking
"""
import numpy as np
from node.TrackerNode.mot.kalman.kalman_tracker import KalmanFilterTracker


class MultiClassKalmanFilter(object):
    def __init__(
        self,
        iou_threshold=0.3,
        max_age=5,
        min_hits=3,
    ):
        """
        Initialize Multi-Class Kalman Filter tracker
        
        Args:
            iou_threshold: Minimum IOU for match (default: 0.3)
            max_age: Maximum number of frames to keep alive a track without associated detections (default: 5)
            min_hits: Minimum number of associated detections before track is confirmed (default: 3)
        """
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracker = KalmanFilterTracker(
            iou_threshold=iou_threshold,
            max_age=max_age,
            min_hits=min_hits,
        )

    def __call__(self, frame, bboxes, scores, class_ids):
        """
        Update tracker with new detections
        
        Args:
            frame: Current frame (not used but kept for interface consistency)
            bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            scores: List of confidence scores
            class_ids: List of class IDs
            
        Returns:
            track_ids: List of track IDs
            track_bboxes: List of tracked bounding boxes
            track_scores: List of tracked scores
            track_class_ids: List of tracked class IDs
        """
        if len(bboxes) == 0:
            # Update with empty detections to handle lost tracks
            return self.tracker.update([], [], [])
        
        # Update tracker
        track_ids, track_bboxes, track_scores, track_class_ids = self.tracker.update(
            bboxes, scores, class_ids
        )
        
        return track_ids, track_bboxes, track_scores, track_class_ids
