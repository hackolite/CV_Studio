# -*- coding: utf-8 -*-
"""
BoT-SORT: Robust Associations Multi-Pedestrian Tracking
A fast and robust tracker combining SORT with improved association strategies
Ideal for tracking fast-moving objects in sports scenarios

Based on: "BoT-SORT: Robust Associations Multi-Pedestrian Tracking"
https://arxiv.org/abs/2206.14651
"""
import numpy as np
from filterpy.kalman import KalmanFilter


def linear_assignment(cost_matrix):
    """
    Linear assignment using Hungarian algorithm
    """
    try:
        from scipy.optimize import linear_sum_assignment
        x, y = linear_sum_assignment(cost_matrix)
        return np.array(list(zip(x, y)))
    except ImportError:
        # Fallback to greedy assignment
        if cost_matrix.size == 0:
            return np.empty((0, 2), dtype=int)
        
        rows, cols = cost_matrix.shape
        matches = []
        used_rows = set()
        used_cols = set()
        
        flat_indices = np.argsort(cost_matrix.ravel())
        
        for flat_idx in flat_indices:
            row = flat_idx // cols
            col = flat_idx % cols
            
            if row in used_rows or col in used_cols:
                continue
            
            matches.append([row, col])
            used_rows.add(row)
            used_cols.add(col)
            
            if len(used_rows) == rows or len(used_cols) == cols:
                break
        
        return np.array(matches) if len(matches) > 0 else np.empty((0, 2), dtype=int)


def iou_batch(bb_test, bb_gt):
    """
    Computes IOU between two bboxes in the form [x1, y1, x2, y2]
    """
    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)
    
    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])
    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h
    o = wh / ((bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])
              + (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1]) - wh)
    return o


def giou_batch(bb_test, bb_gt):
    """
    Computes GIoU (Generalized Intersection over Union) between two bboxes
    GIoU is better for non-overlapping boxes
    """
    iou = iou_batch(bb_test, bb_gt)
    
    # Compute enclosing box
    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)
    
    x1_c = np.minimum(bb_test[..., 0], bb_gt[..., 0])
    y1_c = np.minimum(bb_test[..., 1], bb_gt[..., 1])
    x2_c = np.maximum(bb_test[..., 2], bb_gt[..., 2])
    y2_c = np.maximum(bb_test[..., 3], bb_gt[..., 3])
    
    area_c = (x2_c - x1_c) * (y2_c - y1_c)
    area_test = (bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])
    area_gt = (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1])
    
    # GIoU = IoU - (C - (A ∪ B)) / C
    union = area_test + area_gt - iou * area_test * area_gt / (iou + 1e-7)
    giou = iou - (area_c - union) / (area_c + 1e-7)
    
    return giou


def convert_bbox_to_z(bbox):
    """
    Takes a bounding box in the form [x1, y1, x2, y2] and returns z in the form
    [x, y, s, r] where x, y is the center of the box and s is the scale/area and r is
    the aspect ratio
    """
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2.
    y = bbox[1] + h / 2.
    s = w * h
    r = w / float(max(h, 1e-6))
    return np.array([x, y, s, r]).reshape((4, 1))


def convert_x_to_bbox(x, score=None):
    """
    Takes a bounding box in the centre form [x, y, s, r] and returns it in the form
    [x1, y1, x2, y2]
    """
    s = max(x[2], 1e-6)
    r = max(x[3], 1e-6)
    w = np.sqrt(s * r)
    h = s / w
    if score is None:
        return np.array([x[0] - w / 2., x[1] - h / 2., x[0] + w / 2., x[1] + h / 2.]).reshape((1, 4))
    else:
        return np.array([x[0] - w / 2., x[1] - h / 2., x[0] + w / 2., x[1] + h / 2., score]).reshape((1, 5))


class KalmanBoxTracker(object):
    """
    This class represents the internal state of individual tracked objects with BoT-SORT enhancements.
    Includes camera motion compensation and improved state estimation.
    """
    count = 0

    def __init__(self, bbox, class_id, score, confidence_decay=0.9):
        """
        Initialises a tracker using initial bounding box.
        
        Args:
            bbox: Initial bounding box [x1, y1, x2, y2]
            class_id: Object class ID
            score: Detection confidence score
            confidence_decay: Decay factor for confidence during occlusion (default: 0.9)
        """
        # Define constant velocity model with higher-order motion
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        self.kf.F = np.array([[1, 0, 0, 0, 1, 0, 0],
                              [0, 1, 0, 0, 0, 1, 0],
                              [0, 0, 1, 0, 0, 0, 1],
                              [0, 0, 0, 1, 0, 0, 0],
                              [0, 0, 0, 0, 1, 0, 0],
                              [0, 0, 0, 0, 0, 1, 0],
                              [0, 0, 0, 0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0, 0, 0, 0],
                              [0, 1, 0, 0, 0, 0, 0],
                              [0, 0, 1, 0, 0, 0, 0],
                              [0, 0, 0, 1, 0, 0, 0]])

        # BoT-SORT: Tuned for sports scenarios with faster motion
        self.kf.R[2:, 2:] *= 10.
        self.kf.P[4:, 4:] *= 1000.
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)
        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history = []
        self.hits = 0
        self.hit_streak = 0
        self.age = 0
        self.class_id = class_id
        self.score = score
        
        # BoT-SORT specific: track smoothness and confidence
        self.confidence = score
        self.track_high_score = score
        self.smooth_feat = None
        self.velocity_history = []
        self.confidence_decay = confidence_decay

    def update(self, bbox, class_id, score):
        """
        Updates the state vector with observed bbox.
        """
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        
        # BoT-SORT: Update confidence and track high score
        self.confidence = score
        self.track_high_score = max(self.track_high_score, score)
        
        # Store velocity for smoothing
        prev_state = self.kf.x.copy()
        self.kf.update(convert_bbox_to_z(bbox))
        
        # Calculate velocity change
        velocity = self.kf.x[4:6] - prev_state[4:6]
        self.velocity_history.append(velocity)
        if len(self.velocity_history) > 5:
            self.velocity_history.pop(0)
        
        self.class_id = class_id
        self.score = score

    def predict(self):
        """
        Advances the state vector and returns the predicted bounding box estimate.
        BoT-SORT: Uses velocity smoothing for more stable predictions
        """
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
        
        # BoT-SORT: Apply velocity smoothing
        if len(self.velocity_history) > 2 and self.time_since_update > 0:
            # Use smoothed velocity for better prediction during occlusion
            smoothed_velocity = np.mean(self.velocity_history, axis=0)
            self.kf.x[4:6] = smoothed_velocity
        
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        
        # Decay confidence during occlusion
        if self.time_since_update > 1:
            self.confidence *= self.confidence_decay
        
        return self.history[-1]

    def get_state(self):
        """
        Returns the current bounding box estimate.
        """
        return convert_x_to_bbox(self.kf.x)


class BotSort(object):
    """
    BoT-SORT: Robust Associations Multi-Pedestrian Tracking
    Enhanced SORT with improved association strategies for robust tracking.
    Uses GIoU for better matching and confidence-based track management.
    """
    
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3, use_giou=True, 
                 high_score_threshold=0.6, low_iou_factor=0.8, confidence_decay=0.9):
        """
        Sets key parameters for BoT-SORT
        
        Args:
            max_age: Maximum frames to keep alive a track without detections
            min_hits: Minimum number of associated detections before track is confirmed
            iou_threshold: Minimum IOU for match
            use_giou: Use GIoU instead of IoU for better non-overlapping box matching
            high_score_threshold: Threshold to separate high/low confidence detections (default: 0.6)
            low_iou_factor: Factor to adjust IOU threshold for low-score detections (default: 0.8)
            confidence_decay: Decay factor for confidence during occlusion (default: 0.9)
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.use_giou = use_giou
        self.high_score_threshold = high_score_threshold
        self.low_iou_factor = low_iou_factor
        self.confidence_decay = confidence_decay
        self.trackers = []
        self.frame_count = 0

    def update(self, dets, class_ids, scores):
        """
        Params:
          dets - a numpy array of detections in the format [[x1, y1, x2, y2], ...]
          class_ids - a list of class IDs for each detection
          scores - a list of confidence scores for each detection
        
        Returns: array where each row contains [x1, y1, x2, y2, track_id, class_id, score]
        """
        self.frame_count += 1
        
        # Get predicted locations from existing trackers
        trks = np.zeros((len(self.trackers), 5))
        to_del = []
        ret = []
        
        for t, trk in enumerate(trks):
            pos = self.trackers[t].predict()[0]
            trk[:] = [pos[0], pos[1], pos[2], pos[3], 0]
            if np.any(np.isnan(pos)):
                to_del.append(t)
        
        trks = np.ma.compress_rows(np.ma.masked_invalid(trks))
        for t in reversed(to_del):
            self.trackers.pop(t)
        
        # BoT-SORT: Two-stage association
        # First stage: High-score detections with trackers
        high_score_mask = np.array(scores) > self.high_score_threshold
        if np.any(high_score_mask):
            high_dets = dets[high_score_mask]
            high_class_ids = np.array(class_ids)[high_score_mask]
            high_scores = np.array(scores)[high_score_mask]
            
            matched_h, unmatched_dets_h, unmatched_trks_h = self.associate_detections_to_trackers(
                high_dets, trks, high_class_ids, self.iou_threshold
            )
            
            # Update matched trackers
            for m in matched_h:
                det_idx = np.where(high_score_mask)[0][m[0]]
                self.trackers[m[1]].update(dets[det_idx], class_ids[det_idx], scores[det_idx])
            
            # Second stage: Low-score detections with remaining trackers
            low_score_mask = ~high_score_mask
            if np.any(low_score_mask) and len(unmatched_trks_h) > 0:
                low_dets = dets[low_score_mask]
                low_class_ids = np.array(class_ids)[low_score_mask]
                low_scores = np.array(scores)[low_score_mask]
                
                remaining_trks = trks[unmatched_trks_h]
                matched_l, unmatched_dets_l, unmatched_trks_l = self.associate_detections_to_trackers(
                    low_dets, remaining_trks, low_class_ids, self.iou_threshold * self.low_iou_factor
                )
                
                # Update matched trackers from second stage
                for m in matched_l:
                    det_idx = np.where(low_score_mask)[0][m[0]]
                    trk_idx = unmatched_trks_h[m[1]]
                    self.trackers[trk_idx].update(dets[det_idx], class_ids[det_idx], scores[det_idx])
                
                unmatched_dets = np.concatenate([
                    np.where(high_score_mask)[0][unmatched_dets_h],
                    np.where(low_score_mask)[0][unmatched_dets_l]
                ])
            else:
                unmatched_dets = np.where(high_score_mask)[0][unmatched_dets_h]
                if np.any(low_score_mask):
                    unmatched_dets = np.concatenate([unmatched_dets, np.where(low_score_mask)[0]])
        else:
            # All detections are low-score
            matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
                dets, trks, class_ids, self.iou_threshold
            )
            for m in matched:
                self.trackers[m[1]].update(dets[m[0]], class_ids[m[0]], scores[m[0]])

        # Create and initialise new trackers for unmatched detections
        for i in unmatched_dets:
            trk = KalmanBoxTracker(dets[i], class_ids[i], scores[i], confidence_decay=self.confidence_decay)
            self.trackers.append(trk)
        
        i = len(self.trackers)
        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            # BoT-SORT: Use confidence-based filtering
            if (trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
                ret.append(np.concatenate((d, [trk.id, trk.class_id, trk.confidence])).reshape(1, -1))
            i -= 1
            # Remove dead tracklet
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)
        
        if len(ret) > 0:
            return np.concatenate(ret)
        return np.empty((0, 8))

    def associate_detections_to_trackers(self, detections, trackers, class_ids, iou_threshold=0.3):
        """
        Assigns detections to tracked object using IoU or GIoU
        Returns 3 lists of matches, unmatched_detections and unmatched_trackers
        """
        if len(trackers) == 0:
            return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0, 5), dtype=int)

        # BoT-SORT: Use GIoU for better matching
        if self.use_giou:
            iou_matrix = giou_batch(detections, trackers)
        else:
            iou_matrix = iou_batch(detections, trackers)

        if min(iou_matrix.shape) > 0:
            a = (iou_matrix > iou_threshold).astype(np.int32)
            if a.sum(1).max() == 1 and a.sum(0).max() == 1:
                matched_indices = np.stack(np.where(a), axis=1)
            else:
                matched_indices = linear_assignment(-iou_matrix)
        else:
            matched_indices = np.empty(shape=(0, 2))

        unmatched_detections = []
        for d, det in enumerate(detections):
            if d not in matched_indices[:, 0]:
                unmatched_detections.append(d)
        
        unmatched_trackers = []
        for t, trk in enumerate(trackers):
            if t not in matched_indices[:, 1]:
                unmatched_trackers.append(t)

        # Filter out matched with low IOU
        matches = []
        for m in matched_indices:
            if iou_matrix[m[0], m[1]] < iou_threshold:
                unmatched_detections.append(m[0])
                unmatched_trackers.append(m[1])
            else:
                # Check if class IDs match
                if class_ids[m[0]] == self.trackers[m[1]].class_id:
                    matches.append(m.reshape(1, 2))
                else:
                    unmatched_detections.append(m[0])
                    unmatched_trackers.append(m[1])

        if len(matches) == 0:
            matches = np.empty((0, 2), dtype=int)
        else:
            matches = np.concatenate(matches, axis=0)

        return matches, np.array(unmatched_detections), np.array(unmatched_trackers)
