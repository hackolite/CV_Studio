# -*- coding: utf-8 -*-
"""
CenterTrack: Centroid-based Object Tracker
A simple and efficient tracker based on centroid matching and distance metrics
"""
import numpy as np
from collections import OrderedDict


def compute_centroid(bbox):
    """
    Compute the centroid of a bounding box
    Args:
        bbox: [x1, y1, x2, y2]
    Returns:
        (cx, cy): centroid coordinates
    """
    cx = (bbox[0] + bbox[2]) / 2.0
    cy = (bbox[1] + bbox[3]) / 2.0
    return (cx, cy)


def compute_euclidean_distance(centroid1, centroid2):
    """
    Compute Euclidean distance between two centroids
    """
    return np.sqrt((centroid1[0] - centroid2[0]) ** 2 + (centroid1[1] - centroid2[1]) ** 2)


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


class CentroidTracker:
    """
    Centroid-based object tracker
    Tracks objects by matching centroids between frames
    """
    
    def __init__(self, max_disappeared=30, max_distance=50):
        """
        Initialize the centroid tracker
        
        Args:
            max_disappeared: Maximum number of frames an object can disappear before being deregistered
            max_distance: Maximum distance (in pixels) between centroids to consider a match
        """
        self.next_object_id = 0
        self.objects = OrderedDict()  # {id: (centroid, bbox, class_id, score)}
        self.disappeared = OrderedDict()  # {id: num_frames_disappeared}
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance
        
    def register(self, centroid, bbox, class_id, score):
        """
        Register a new object with the next available object ID
        """
        self.objects[self.next_object_id] = (centroid, bbox, class_id, score)
        self.disappeared[self.next_object_id] = 0
        self.next_object_id += 1
        
    def deregister(self, object_id):
        """
        Deregister an object ID by deleting it from both dictionaries
        """
        del self.objects[object_id]
        del self.disappeared[object_id]
        
    def update(self, bboxes, class_ids, scores):
        """
        Update the tracker with new detections
        
        Args:
            bboxes: List of bounding boxes [[x1, y1, x2, y2], ...]
            class_ids: List of class IDs
            scores: List of confidence scores
            
        Returns:
            track_ids: List of track IDs
            track_bboxes: List of tracked bounding boxes
            track_scores: List of tracked scores
            track_class_ids: List of tracked class IDs
        """
        # If no detections, mark all existing objects as disappeared
        if len(bboxes) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                
                # Deregister if disappeared too long
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            return self._get_results()
        
        # Compute centroids for new detections
        input_centroids = []
        for bbox in bboxes:
            input_centroids.append(compute_centroid(bbox))
        
        # If no existing tracked objects, register all detections
        if len(self.objects) == 0:
            for i, centroid in enumerate(input_centroids):
                self.register(centroid, bboxes[i], class_ids[i], scores[i])
        else:
            # Match existing objects to new detections
            object_ids = list(self.objects.keys())
            object_data = list(self.objects.values())
            object_centroids = [data[0] for data in object_data]
            object_classes = [data[2] for data in object_data]
            
            # Compute distance matrix between existing and new centroids
            D = np.zeros((len(object_centroids), len(input_centroids)))
            for i, obj_centroid in enumerate(object_centroids):
                for j, input_centroid in enumerate(input_centroids):
                    # Only consider matching if same class
                    if object_classes[i] == class_ids[j]:
                        D[i, j] = compute_euclidean_distance(obj_centroid, input_centroid)
                    else:
                        D[i, j] = np.inf  # Infinite distance for different classes
            
            # Find the minimum distance for each row (object) and sort by distance
            rows = D.min(axis=1).argsort()
            
            # Find the minimum distance for each column (detection) and sort by distance
            cols = D.argmin(axis=1)[rows]
            
            # Keep track of which rows and columns we have already examined
            used_rows = set()
            used_cols = set()
            
            # Loop over the combination of (row, column) index tuples
            for (row, col) in zip(rows, cols):
                # Ignore if already examined
                if row in used_rows or col in used_cols:
                    continue
                
                # Check if distance is within threshold
                if D[row, col] > self.max_distance:
                    continue
                
                # Update the object
                object_id = object_ids[row]
                self.objects[object_id] = (
                    input_centroids[col],
                    bboxes[col],
                    class_ids[col],
                    scores[col]
                )
                self.disappeared[object_id] = 0
                
                # Mark as used
                used_rows.add(row)
                used_cols.add(col)
            
            # Compute unused rows and columns
            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)
            
            # Handle disappeared objects
            for row in unused_rows:
                object_id = object_ids[row]
                self.disappeared[object_id] += 1
                
                if self.disappeared[object_id] > self.max_disappeared:
                    self.deregister(object_id)
            
            # Register new objects
            for col in unused_cols:
                self.register(
                    input_centroids[col],
                    bboxes[col],
                    class_ids[col],
                    scores[col]
                )
        
        return self._get_results()
    
    def _get_results(self):
        """
        Get current tracking results
        """
        track_ids = []
        track_bboxes = []
        track_scores = []
        track_class_ids = []
        
        for object_id, (centroid, bbox, class_id, score) in self.objects.items():
            track_ids.append(object_id)
            track_bboxes.append(bbox)
            track_class_ids.append(class_id)
            track_scores.append(score)
        
        return track_ids, track_bboxes, track_scores, track_class_ids
