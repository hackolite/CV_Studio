#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Kalman filter for position prediction based on pose estimation data.

This module provides a Kalman filter implementation specifically designed
for predicting future positions of body keypoints from pose estimation models.
"""

import numpy as np
import scipy.linalg


class KalmanPositionFilter:
    """
    A Kalman filter for predicting keypoint positions.

    The 4-dimensional state space:
        x, y, vx, vy

    contains the keypoint position (x, y) and velocity (vx, vy).
    Object motion follows a constant velocity model.
    """

    def __init__(self, dt=1.0, process_noise=0.1, measurement_noise=0.5):
        """
        Initialize the Kalman filter.

        Parameters
        ----------
        dt : float
            Time step between predictions (default: 1.0)
        process_noise : float
            Process noise coefficient (default: 0.1)
        measurement_noise : float
            Measurement noise coefficient (default: 0.5)
        """
        self.dt = dt
        self.ndim = 2  # x, y position

        # State transition matrix (constant velocity model)
        # [x, y, vx, vy]
        self._motion_mat = np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float64)

        # Observation matrix (we observe x, y)
        self._observation_mat = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float64)

        # Process noise
        self._process_noise = process_noise
        self._Q = np.eye(4) * process_noise

        # Measurement noise
        self._measurement_noise = measurement_noise
        self._R = np.eye(2) * measurement_noise

    def initiate(self, measurement):
        """
        Create a new track from a measurement.

        Parameters
        ----------
        measurement : array_like
            Initial position (x, y).

        Returns
        -------
        tuple
            (mean, covariance) - Initial state and covariance matrix.
        """
        mean_pos = np.array(measurement[:2], dtype=np.float64)
        mean_vel = np.zeros(2, dtype=np.float64)
        mean = np.concatenate([mean_pos, mean_vel])

        # Initial covariance (higher for velocity since we don't know it)
        covariance = np.diag([10.0, 10.0, 100.0, 100.0])
        return mean, covariance

    def predict(self, mean, covariance):
        """
        Run Kalman filter prediction step.

        Parameters
        ----------
        mean : ndarray
            The 4-dimensional mean vector of the state.
        covariance : ndarray
            The 4x4 covariance matrix of the state.

        Returns
        -------
        tuple
            (mean, covariance) - Predicted state and covariance.
        """
        # Predict state
        predicted_mean = np.dot(self._motion_mat, mean)
        
        # Predict covariance
        predicted_covariance = np.dot(
            np.dot(self._motion_mat, covariance),
            self._motion_mat.T
        ) + self._Q

        return predicted_mean, predicted_covariance

    def update(self, mean, covariance, measurement):
        """
        Run Kalman filter correction step.

        Parameters
        ----------
        mean : ndarray
            The predicted state mean vector (4-dimensional).
        covariance : ndarray
            The predicted state covariance matrix (4x4).
        measurement : ndarray
            The 2-dimensional measurement vector (x, y).

        Returns
        -------
        tuple
            (mean, covariance) - Corrected state and covariance.
        """
        # Innovation (measurement residual)
        innovation = measurement - np.dot(self._observation_mat, mean)

        # Innovation covariance
        S = np.dot(
            np.dot(self._observation_mat, covariance),
            self._observation_mat.T
        ) + self._R

        # Kalman gain
        K = np.dot(
            np.dot(covariance, self._observation_mat.T),
            np.linalg.inv(S)
        )

        # Updated state
        updated_mean = mean + np.dot(K, innovation)

        # Updated covariance
        I = np.eye(4)
        updated_covariance = np.dot(I - np.dot(K, self._observation_mat), covariance)

        return updated_mean, updated_covariance

    def predict_n_steps(self, mean, covariance, n_steps):
        """
        Predict state n steps into the future.

        Parameters
        ----------
        mean : ndarray
            Current state mean vector.
        covariance : ndarray
            Current state covariance matrix.
        n_steps : int
            Number of steps to predict ahead.

        Returns
        -------
        tuple
            (predicted_mean, predicted_covariance) - State after n steps.
        """
        current_mean = mean.copy()
        current_cov = covariance.copy()

        for _ in range(n_steps):
            current_mean, current_cov = self.predict(current_mean, current_cov)

        return current_mean, current_cov


class MultiKeypointTracker:
    """
    Tracks multiple keypoints using individual Kalman filters.
    """

    def __init__(self, num_keypoints=17, dt=1.0, process_noise=0.1, measurement_noise=0.5):
        """
        Initialize the multi-keypoint tracker.

        Parameters
        ----------
        num_keypoints : int
            Number of keypoints to track (default: 17 for MoveNet).
        dt : float
            Time step between predictions.
        process_noise : float
            Process noise coefficient.
        measurement_noise : float
            Measurement noise coefficient.
        """
        self.num_keypoints = num_keypoints
        self.filters = {}
        self.states = {}  # {keypoint_id: (mean, covariance)}
        self.dt = dt
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise

    def _get_or_create_filter(self, keypoint_id):
        """Get or create a Kalman filter for a keypoint."""
        if keypoint_id not in self.filters:
            self.filters[keypoint_id] = KalmanPositionFilter(
                dt=self.dt,
                process_noise=self.process_noise,
                measurement_noise=self.measurement_noise
            )
        return self.filters[keypoint_id]

    def update(self, keypoint_id, measurement):
        """
        Update a keypoint's state with a new measurement.

        Parameters
        ----------
        keypoint_id : int
            The ID of the keypoint.
        measurement : array_like
            The (x, y) position measurement.

        Returns
        -------
        ndarray
            The updated state mean [x, y, vx, vy].
        """
        kf = self._get_or_create_filter(keypoint_id)

        if keypoint_id not in self.states:
            # Initialize new track
            mean, cov = kf.initiate(measurement)
        else:
            # Predict then update
            mean, cov = self.states[keypoint_id]
            mean, cov = kf.predict(mean, cov)
            mean, cov = kf.update(mean, cov, np.array(measurement[:2], dtype=np.float64))

        self.states[keypoint_id] = (mean, cov)
        return mean

    def predict_position(self, keypoint_id, n_steps=1):
        """
        Predict the future position of a keypoint.

        Parameters
        ----------
        keypoint_id : int
            The ID of the keypoint.
        n_steps : int
            Number of steps to predict ahead.

        Returns
        -------
        ndarray or None
            Predicted (x, y) position, or None if no track exists.
        """
        if keypoint_id not in self.states:
            return None

        kf = self.filters[keypoint_id]
        mean, cov = self.states[keypoint_id]

        predicted_mean, _ = kf.predict_n_steps(mean, cov, n_steps)
        return predicted_mean[:2]  # Return only x, y

    def get_velocity(self, keypoint_id):
        """
        Get the current velocity estimate for a keypoint.

        Parameters
        ----------
        keypoint_id : int
            The ID of the keypoint.

        Returns
        -------
        ndarray or None
            Velocity (vx, vy), or None if no track exists.
        """
        if keypoint_id not in self.states:
            return None

        mean, _ = self.states[keypoint_id]
        return mean[2:4]  # Return vx, vy

    def process_pose_results(self, pose_results):
        """
        Process pose estimation results and update all keypoint tracks.

        Parameters
        ----------
        pose_results : list
            List of pose results from pose estimation node.
            Each result is a dict with keypoint_id: [x, y, score].

        Returns
        -------
        list
            Updated states for all keypoints.
        """
        updated_states = []

        for pose in pose_results:
            pose_state = {}
            for keypoint_id, keypoint_data in pose.items():
                if keypoint_id == 'bbox':
                    continue
                if isinstance(keypoint_id, int) and len(keypoint_data) >= 2:
                    x, y = keypoint_data[0], keypoint_data[1]
                    score = keypoint_data[2] if len(keypoint_data) > 2 else 1.0

                    # Update tracker
                    state = self.update(keypoint_id, [x, y])

                    pose_state[keypoint_id] = {
                        'position': [state[0], state[1]],
                        'velocity': [state[2], state[3]],
                        'score': score
                    }

            updated_states.append(pose_state)

        return updated_states

    def predict_all_positions(self, n_steps=1):
        """
        Predict future positions for all tracked keypoints.

        Parameters
        ----------
        n_steps : int
            Number of steps to predict ahead.

        Returns
        -------
        dict
            Predicted positions for all keypoints.
        """
        predictions = {}
        for keypoint_id in self.states.keys():
            predicted_pos = self.predict_position(keypoint_id, n_steps)
            if predicted_pos is not None:
                predictions[keypoint_id] = predicted_pos.tolist()
        return predictions

    def reset(self):
        """Reset all tracking state."""
        self.filters.clear()
        self.states.clear()
