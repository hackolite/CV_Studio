#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hand Tracker for pose estimation specialized for hands.
Tracks multiple hands across frames and maintains their identities.
"""
import numpy as np
from collections import defaultdict


def euclidean_distance(point1, point2):
    """Calculate Euclidean distance between two points."""
    return np.sqrt(np.sum((np.array(point1) - np.array(point2)) ** 2))


class HandTracker:
    """
    A tracker specialized for hand pose estimation.
    Tracks hands using palm center coordinates and maintains IDs across frames.
    """
    
    def __init__(
        self,
        max_distance=100.0,  # Maximum distance to associate same hand across frames
        max_frames_disappeared=30,  # Maximum frames before removing a hand
    ):
        """
        Initialize the hand tracker.
        
        Args:
            max_distance: Maximum pixel distance to match hands between frames
            max_frames_disappeared: Maximum frames a hand can disappear before being removed
        """
        self.max_distance = max_distance
        self.max_frames_disappeared = max_frames_disappeared
        
        # Dictionary to store tracked hands: {hand_id: hand_data}
        self.tracked_hands = {}
        
        # Counter for generating unique hand IDs
        self.next_hand_id = 0
        
        # Counter for frames each hand has been missing
        self.disappeared = defaultdict(int)
    
    def __call__(self, frame, results_list):
        """
        Track hands in the current frame.
        
        Args:
            frame: Current video frame (not used but kept for interface compatibility)
            results_list: List of hand detection results from MediaPipe Hands
                         Each result contains keypoints and palm_moment
        
        Returns:
            Tuple of (hand_ids, results_list_with_ids)
            - hand_ids: List of unique hand IDs for each detected hand
            - results_list_with_ids: Original results with added 'hand_id' field
        """
        # If no hands detected, mark all tracked hands as disappeared
        if not results_list or len(results_list) == 0:
            return self._handle_no_detections()
        
        # Extract palm centers from current detections
        current_palm_centers = []
        for result in results_list:
            palm_center = result.get('palm_moment', [0, 0])
            current_palm_centers.append(palm_center)
        
        # If no tracked hands yet, initialize with current detections
        if len(self.tracked_hands) == 0:
            return self._initialize_tracks(results_list, current_palm_centers)
        
        # Match current detections with existing tracks
        return self._update_tracks(results_list, current_palm_centers)
    
    def _handle_no_detections(self):
        """Handle the case when no hands are detected."""
        # Mark all tracked hands as disappeared
        hands_to_remove = []
        for hand_id in list(self.tracked_hands.keys()):
            self.disappeared[hand_id] += 1
            
            # Remove hands that have disappeared for too long
            if self.disappeared[hand_id] > self.max_frames_disappeared:
                hands_to_remove.append(hand_id)
        
        for hand_id in hands_to_remove:
            del self.tracked_hands[hand_id]
            del self.disappeared[hand_id]
        
        return [], []
    
    def _initialize_tracks(self, results_list, palm_centers):
        """Initialize tracking with first set of detections."""
        hand_ids = []
        results_with_ids = []
        
        for i, (result, palm_center) in enumerate(zip(results_list, palm_centers)):
            hand_id = self.next_hand_id
            self.next_hand_id += 1
            
            self.tracked_hands[hand_id] = {
                'palm_center': palm_center,
                'result': result,
            }
            self.disappeared[hand_id] = 0
            
            # Add hand_id to the result
            result_with_id = result.copy()
            result_with_id['hand_id'] = hand_id
            
            hand_ids.append(hand_id)
            results_with_ids.append(result_with_id)
        
        return hand_ids, results_with_ids
    
    def _update_tracks(self, results_list, palm_centers):
        """Update existing tracks with new detections."""
        # Get current tracked hand IDs and their palm centers
        tracked_ids = list(self.tracked_hands.keys())
        tracked_centers = [self.tracked_hands[hid]['palm_center'] for hid in tracked_ids]
        
        # Compute distance matrix between tracked and detected hands
        num_tracked = len(tracked_centers)
        num_detected = len(palm_centers)
        
        if num_tracked == 0:
            return self._initialize_tracks(results_list, palm_centers)
        
        # Build distance matrix
        distance_matrix = np.zeros((num_tracked, num_detected))
        for i, tracked_center in enumerate(tracked_centers):
            for j, detected_center in enumerate(palm_centers):
                distance_matrix[i, j] = euclidean_distance(tracked_center, detected_center)
        
        # Match detections to tracks using greedy assignment
        matched_pairs, unmatched_tracked, unmatched_detected = self._match_detections(
            distance_matrix, num_tracked, num_detected
        )
        
        hand_ids = []
        results_with_ids = []
        
        # Update matched tracks
        for tracked_idx, detected_idx in matched_pairs:
            hand_id = tracked_ids[tracked_idx]
            
            # Update tracked hand
            self.tracked_hands[hand_id]['palm_center'] = palm_centers[detected_idx]
            self.tracked_hands[hand_id]['result'] = results_list[detected_idx]
            self.disappeared[hand_id] = 0
            
            # Add hand_id to result
            result_with_id = results_list[detected_idx].copy()
            result_with_id['hand_id'] = hand_id
            
            hand_ids.append(hand_id)
            results_with_ids.append(result_with_id)
        
        # Handle unmatched detections (new hands)
        for detected_idx in unmatched_detected:
            hand_id = self.next_hand_id
            self.next_hand_id += 1
            
            self.tracked_hands[hand_id] = {
                'palm_center': palm_centers[detected_idx],
                'result': results_list[detected_idx],
            }
            self.disappeared[hand_id] = 0
            
            result_with_id = results_list[detected_idx].copy()
            result_with_id['hand_id'] = hand_id
            
            hand_ids.append(hand_id)
            results_with_ids.append(result_with_id)
        
        # Handle unmatched tracks (disappeared hands)
        hands_to_remove = []
        for tracked_idx in unmatched_tracked:
            hand_id = tracked_ids[tracked_idx]
            self.disappeared[hand_id] += 1
            
            if self.disappeared[hand_id] > self.max_frames_disappeared:
                hands_to_remove.append(hand_id)
        
        for hand_id in hands_to_remove:
            del self.tracked_hands[hand_id]
            del self.disappeared[hand_id]
        
        return hand_ids, results_with_ids
    
    def _match_detections(self, distance_matrix, num_tracked, num_detected):
        """
        Match detections to tracked hands using greedy assignment.
        
        Returns:
            Tuple of (matched_pairs, unmatched_tracked, unmatched_detected)
        """
        matched_pairs = []
        unmatched_tracked = list(range(num_tracked))
        unmatched_detected = list(range(num_detected))
        
        # Greedy matching: repeatedly match closest pairs
        while len(unmatched_tracked) > 0 and len(unmatched_detected) > 0:
            # Find minimum distance in remaining matches
            min_distance = float('inf')
            min_tracked_idx = -1
            min_detected_idx = -1
            
            for tracked_idx in unmatched_tracked:
                for detected_idx in unmatched_detected:
                    if distance_matrix[tracked_idx, detected_idx] < min_distance:
                        min_distance = distance_matrix[tracked_idx, detected_idx]
                        min_tracked_idx = tracked_idx
                        min_detected_idx = detected_idx
            
            # If minimum distance is too large, stop matching
            if min_distance > self.max_distance:
                break
            
            # Add match
            matched_pairs.append((min_tracked_idx, min_detected_idx))
            unmatched_tracked.remove(min_tracked_idx)
            unmatched_detected.remove(min_detected_idx)
        
        return matched_pairs, unmatched_tracked, unmatched_detected
