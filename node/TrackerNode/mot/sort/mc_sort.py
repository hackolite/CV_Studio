# -*- coding: utf-8 -*-
"""
Multi-Class SORT Tracker Wrapper
Wraps the SORT tracker to handle multi-class object tracking
"""
import numpy as np
from node.TrackerNode.mot.sort.sort_tracker import Sort


class MultiClassSORT(object):
    def __init__(
        self,
        max_age=1,
        min_hits=3,
        iou_threshold=0.3,
    ):
        """
        Initialize Multi-Class SORT tracker
        
        Args:
            max_age: Maximum number of frames to keep alive a track without associated detections
            min_hits: Minimum number of associated detections before track is confirmed
            iou_threshold: Minimum IOU for match
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.tracker = Sort(
            max_age=max_age,
            min_hits=min_hits,
            iou_threshold=iou_threshold,
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
            results = self.tracker.update(
                np.empty((0, 4)),
                [],
                []
            )
        else:
            # Convert to numpy arrays
            dets = np.array(bboxes)
            class_ids_array = np.array(class_ids)
            scores_array = np.array(scores)
            
            # Update tracker
            results = self.tracker.update(dets, class_ids_array, scores_array)

        # Parse results
        track_ids = []
        track_bboxes = []
        track_scores = []
        track_class_ids = []
        
        if len(results) > 0:
            for result in results:
                x1, y1, x2, y2, track_id, class_id, score = result
                track_ids.append(int(track_id))
                track_bboxes.append([int(x1), int(y1), int(x2), int(y2)])
                track_class_ids.append(int(class_id))
                track_scores.append(float(score))

        return track_ids, track_bboxes, track_scores, track_class_ids
