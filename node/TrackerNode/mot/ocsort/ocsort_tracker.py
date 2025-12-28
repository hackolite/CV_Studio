# -*- coding: utf-8 -*-
"""
OC-SORT: Observation-Centric SORT
An improved SORT tracker with observation-centric momentum for better handling of occlusions
Ideal for fast-moving objects like tennis balls and players

Based on: "Observation-Centric SORT: Rethinking SORT for Robust Multi-Object Tracking"
https://arxiv.org/abs/2203.14360
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
    This class represents the internal state of individual tracked objects with OC-SORT enhancements.
    Includes observation-centric momentum for better occlusion handling.
    """
    count = 0

    def __init__(self, bbox, class_id, score, delta_t=3):
        """
        Initialises a tracker using initial bounding box.
        
        Args:
            bbox: Initial bounding box [x1, y1, x2, y2]
            class_id: Object class ID
            score: Detection confidence score
            delta_t: Time steps for observation-centric momentum
        """
        # Define constant velocity model
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
        
        # OC-SORT specific: observation history for momentum
        self.last_observation = np.array([-1, -1, -1, -1, -1])
        self.observations = dict()
        self.history_observations = []
        self.velocity = None
        self.delta_t = delta_t

    def update(self, bbox, class_id, score):
        """
        Updates the state vector with observed bbox using observation-centric approach.
        """
        self.time_since_update = 0
        self.history = []
        self.hits += 1
        self.hit_streak += 1
        
        # OC-SORT: Store observation for momentum calculation
        if self.last_observation.sum() >= 0:
            previous_box = self.last_observation
            self.observations[self.age] = previous_box
        self.last_observation = bbox
        
        self.kf.update(convert_bbox_to_z(bbox))
        self.class_id = class_id
        self.score = score
        
        # OC-SORT: Calculate observation-centric velocity
        if len(self.observations) > 0:
            k = np.array(list(self.observations.keys()))
            k = k[k != self.age]
            # Get recent observations within delta_t
            recent_observations = k[k > self.age - self.delta_t]
            
            if len(recent_observations) > 0:
                # Calculate velocity from recent observations
                boxes = np.array([self.observations[i] for i in recent_observations])
                # Simple velocity: difference between current and mean of recent
                mean_box = np.mean(boxes, axis=0)
                self.velocity = bbox - mean_box[:4]

    def predict(self):
        """
        Advances the state vector and returns the predicted bounding box estimate.
        Uses observation-centric momentum when available.
        """
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0
        
        # OC-SORT: Apply observation-centric momentum during occlusion
        if self.time_since_update > 0 and self.velocity is not None:
            # Adjust prediction with observation momentum
            predicted_box = convert_x_to_bbox(self.kf.x)[0]
            # Apply velocity with damping factor
            damping = 0.8 ** self.time_since_update
            predicted_box = predicted_box + self.velocity * damping
            # Update Kalman state with momentum-adjusted prediction
            self.kf.x[:4] = convert_bbox_to_z(predicted_box)
        
        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1
        self.history.append(convert_x_to_bbox(self.kf.x))
        return self.history[-1]

    def get_state(self):
        """
        Returns the current bounding box estimate.
        """
        return convert_x_to_bbox(self.kf.x)


class OCSort(object):
    """
    OC-SORT: Observation-Centric SORT
    Enhanced SORT with observation-centric momentum for better occlusion handling.
    Ideal for tracking fast-moving objects like tennis balls and players.
    """
    
    def __init__(self, max_age=30, min_hits=3, iou_threshold=0.3, delta_t=3):
        """
        Sets key parameters for OC-SORT
        
        Args:
            max_age: Maximum frames to keep alive a track without detections (higher for tennis)
            min_hits: Minimum number of associated detections before track is confirmed
            iou_threshold: Minimum IOU for match
            delta_t: Time steps for observation-centric momentum calculation
        """
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.delta_t = delta_t
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
        
        matched, unmatched_dets, unmatched_trks = self.associate_detections_to_trackers(
            dets, trks, class_ids, self.iou_threshold
        )

        # Update matched trackers with assigned detections
        for m in matched:
            self.trackers[m[1]].update(dets[m[0]], class_ids[m[0]], scores[m[0]])

        # Create and initialise new trackers for unmatched detections
        for i in unmatched_dets:
            trk = KalmanBoxTracker(dets[i], class_ids[i], scores[i], delta_t=self.delta_t)
            self.trackers.append(trk)
        
        i = len(self.trackers)
        for trk in reversed(self.trackers):
            d = trk.get_state()[0]
            if (trk.time_since_update < 1) and (trk.hit_streak >= self.min_hits or self.frame_count <= self.min_hits):
                ret.append(np.concatenate((d, [trk.id, trk.class_id, trk.score])).reshape(1, -1))
            i -= 1
            # Remove dead tracklet
            if trk.time_since_update > self.max_age:
                self.trackers.pop(i)
        
        if len(ret) > 0:
            return np.concatenate(ret)
        return np.empty((0, 8))

    def associate_detections_to_trackers(self, detections, trackers, class_ids, iou_threshold=0.3):
        """
        Assigns detections to tracked object (both represented as bounding boxes)
        Returns 3 lists of matches, unmatched_detections and unmatched_trackers
        """
        if len(trackers) == 0:
            return np.empty((0, 2), dtype=int), np.arange(len(detections)), np.empty((0, 5), dtype=int)

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
