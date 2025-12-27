# -*- coding: utf-8 -*-
"""
Simple IOU (Intersection over Union) Tracker
A lightweight multi-object tracker based on bounding box overlap
"""
import numpy as np


def compute_iou(bbox1, bbox2):
    """
    Compute IOU between two bounding boxes
    Args:
        bbox1: [x1, y1, x2, y2]
        bbox2: [x1, y1, x2, y2]
    Returns:
        IOU value between 0 and 1
    """
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    if x2 < x1 or y2 < y1:
        return 0.0
    
    intersection = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection
    
    if union == 0:
        return 0.0
    
    return intersection / union


class Track:
    """
    Track object for IOU tracker
    """
    _next_id = 0
    
    def __init__(self, bbox, score, class_id):
        self.id = Track._next_id
        Track._next_id += 1
        self.bbox = bbox
        self.score = score
        self.class_id = class_id
        self.age = 0
        self.hits = 1
        self.time_since_update = 0
    
    def update(self, bbox, score):
        """Update track with new detection"""
        self.bbox = bbox
        self.score = score
        self.hits += 1
        self.time_since_update = 0
        self.age += 1
    
    def predict(self):
        """Predict next position (for IOU tracker, we just keep the same position)"""
        self.age += 1
        self.time_since_update += 1


class IOUTracker:
    """
    Simple IOU-based multi-class tracker
    """
    def __init__(
        self,
        iou_threshold=0.3,
        max_age=5,
        min_hits=3,
    ):
        """
        Args:
            iou_threshold: Minimum IOU for match
            max_age: Maximum frames to keep track without update
            min_hits: Minimum hits before track is confirmed
        """
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.min_hits = min_hits
        self.tracks = {}  # Dictionary to store tracks per class
    
    def update(self, bboxes, scores, class_ids):
        """
        Update tracker with new detections
        Args:
            bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            scores: List of confidence scores
            class_ids: List of class IDs
        Returns:
            track_ids, track_bboxes, track_scores, track_class_ids
        """
        # Group detections by class
        class_detections = {}
        for bbox, score, class_id in zip(bboxes, scores, class_ids):
            if class_id not in class_detections:
                class_detections[class_id] = []
            class_detections[class_id].append((bbox, score))
        
        # Process each class separately
        for class_id in list(self.tracks.keys()):
            if class_id not in class_detections:
                # No detections for this class, just predict
                for track in self.tracks[class_id]:
                    track.predict()
            else:
                # Match detections to tracks
                detections = class_detections[class_id]
                matched, unmatched_dets, unmatched_trks = self._match(
                    self.tracks[class_id], detections
                )
                
                # Update matched tracks
                for track_idx, det_idx in matched:
                    self.tracks[class_id][track_idx].update(
                        detections[det_idx][0], detections[det_idx][1]
                    )
                
                # Create new tracks for unmatched detections
                for det_idx in unmatched_dets:
                    new_track = Track(
                        detections[det_idx][0],
                        detections[det_idx][1],
                        class_id
                    )
                    self.tracks[class_id].append(new_track)
                
                # Mark unmatched tracks as lost
                for track_idx in unmatched_trks:
                    self.tracks[class_id][track_idx].predict()
        
        # Create new tracks for new classes
        for class_id, detections in class_detections.items():
            if class_id not in self.tracks:
                self.tracks[class_id] = []
                for bbox, score in detections:
                    new_track = Track(bbox, score, class_id)
                    self.tracks[class_id].append(new_track)
        
        # Remove old tracks
        for class_id in list(self.tracks.keys()):
            self.tracks[class_id] = [
                track for track in self.tracks[class_id]
                if track.time_since_update < self.max_age
            ]
            if len(self.tracks[class_id]) == 0:
                del self.tracks[class_id]
        
        # Return results
        track_ids = []
        track_bboxes = []
        track_scores = []
        track_class_ids = []
        
        for class_id, tracks in self.tracks.items():
            for track in tracks:
                if track.hits >= self.min_hits or track.age < 1:
                    track_ids.append(str(class_id) + '_' + str(track.id))
                    track_bboxes.append(track.bbox)
                    track_scores.append(track.score)
                    track_class_ids.append(class_id)
        
        return track_ids, track_bboxes, track_scores, track_class_ids
    
    def _match(self, tracks, detections):
        """
        Match detections to tracks using IOU
        Args:
            tracks: List of Track objects
            detections: List of (bbox, score) tuples
        Returns:
            matched, unmatched_detections, unmatched_tracks
        """
        if len(tracks) == 0:
            return [], list(range(len(detections))), []
        
        if len(detections) == 0:
            return [], [], list(range(len(tracks)))
        
        # Compute IOU matrix
        iou_matrix = np.zeros((len(tracks), len(detections)))
        for t, track in enumerate(tracks):
            for d, (det_bbox, _) in enumerate(detections):
                iou_matrix[t, d] = compute_iou(track.bbox, det_bbox)
        
        # Greedy matching
        matched = []
        unmatched_dets = list(range(len(detections)))
        unmatched_trks = list(range(len(tracks)))
        
        while iou_matrix.size > 0:
            # Find maximum IOU
            max_iou_idx = np.unravel_index(
                np.argmax(iou_matrix), iou_matrix.shape
            )
            max_iou = iou_matrix[max_iou_idx]
            
            if max_iou < self.iou_threshold:
                break
            
            # Add to matched
            matched.append((max_iou_idx[0], max_iou_idx[1]))
            
            # Remove matched from unmatched lists
            if max_iou_idx[1] in unmatched_dets:
                unmatched_dets.remove(max_iou_idx[1])
            if max_iou_idx[0] in unmatched_trks:
                unmatched_trks.remove(max_iou_idx[0])
            
            # Remove matched row and column from IOU matrix
            iou_matrix[max_iou_idx[0], :] = -1
            iou_matrix[:, max_iou_idx[1]] = -1
        
        return matched, unmatched_dets, unmatched_trks


class MultiClassIOUTracker(object):
    """
    Multi-class IOU tracker wrapper compatible with MOT interface
    """
    def __init__(
        self,
        iou_threshold=0.3,
        max_age=5,
        min_hits=3,
    ):
        """
        Args:
            iou_threshold: Minimum IOU for match (default: 0.3)
            max_age: Maximum frames to keep track without update (default: 5)
            min_hits: Minimum hits before track is confirmed (default: 3)
        """
        self.tracker = IOUTracker(
            iou_threshold=iou_threshold,
            max_age=max_age,
            min_hits=min_hits,
        )
    
    def __call__(self, _, bboxes, scores, class_ids):
        """
        Track objects in frame
        Args:
            _: Unused frame parameter (for interface compatibility)
            bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            scores: List of confidence scores
            class_ids: List of class IDs
        Returns:
            track_ids, track_bboxes, track_scores, track_class_ids
        """
        if len(bboxes) == 0:
            return [], [], [], []
        
        return self.tracker.update(bboxes, scores, class_ids)
