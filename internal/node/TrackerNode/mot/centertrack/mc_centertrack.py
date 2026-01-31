# -*- coding: utf-8 -*-
"""
Multi-Class CenterTrack Wrapper
Wraps the CenterTrack tracker for use in CV Studio
"""
from node.TrackerNode.mot.centertrack.centertrack_tracker import CentroidTracker


class MultiClassCenterTrack(object):
    def __init__(
        self,
        max_disappeared=30,
        max_distance=50,
    ):
        """
        Initialize Multi-Class CenterTrack tracker
        
        Args:
            max_disappeared: Maximum number of frames to keep alive a track without associated detections
            max_distance: Maximum distance (in pixels) between centroids to consider a match
        """
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        self.tracker = CentroidTracker(
            max_disappeared=max_disappeared,
            max_distance=max_distance,
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
        # Update tracker with detections
        track_ids, track_bboxes, track_scores, track_class_ids = self.tracker.update(
            bboxes, class_ids, scores
        )

        return track_ids, track_bboxes, track_scores, track_class_ids
