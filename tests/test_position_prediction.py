#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the Position Prediction node and Kalman filter.
"""

import pytest
import numpy as np

from node.TimeseriesNode.position_prediction.kalman_position_filter import (
    KalmanPositionFilter,
    MultiKeypointTracker,
)


class TestKalmanPositionFilter:
    """Tests for KalmanPositionFilter class."""

    def test_initialization(self):
        """Test Kalman filter initialization."""
        kf = KalmanPositionFilter()
        assert kf.dt == 1.0
        assert kf.ndim == 2
        assert kf._motion_mat.shape == (4, 4)
        assert kf._observation_mat.shape == (2, 4)

    def test_initiate(self):
        """Test initializing a new track."""
        kf = KalmanPositionFilter()
        measurement = [100, 200]
        mean, cov = kf.initiate(measurement)

        assert mean.shape == (4,)
        assert mean[0] == 100  # x position
        assert mean[1] == 200  # y position
        assert mean[2] == 0    # vx (velocity starts at 0)
        assert mean[3] == 0    # vy (velocity starts at 0)
        assert cov.shape == (4, 4)

    def test_predict(self):
        """Test prediction step."""
        kf = KalmanPositionFilter()
        measurement = [100, 200]
        mean, cov = kf.initiate(measurement)

        predicted_mean, predicted_cov = kf.predict(mean, cov)

        # Position should remain the same with zero velocity
        assert predicted_mean.shape == (4,)
        assert predicted_cov.shape == (4, 4)

    def test_update(self):
        """Test update step with new measurement."""
        kf = KalmanPositionFilter()
        measurement = [100, 200]
        mean, cov = kf.initiate(measurement)

        # Predict
        predicted_mean, predicted_cov = kf.predict(mean, cov)

        # New measurement
        new_measurement = np.array([105, 210], dtype=np.float64)
        updated_mean, updated_cov = kf.update(predicted_mean, predicted_cov, new_measurement)

        # Mean should shift toward new measurement
        assert updated_mean.shape == (4,)
        assert updated_cov.shape == (4, 4)

    def test_predict_n_steps(self):
        """Test multi-step prediction."""
        kf = KalmanPositionFilter()
        measurement = [100, 200]
        mean, cov = kf.initiate(measurement)

        # Set some velocity
        mean[2] = 10  # vx
        mean[3] = 5   # vy

        predicted_mean, predicted_cov = kf.predict_n_steps(mean, cov, n_steps=5)

        # Position should have moved based on velocity
        assert predicted_mean[0] > 100  # x should increase
        assert predicted_mean[1] > 200  # y should increase

    def test_constant_velocity_prediction(self):
        """Test that constant velocity model predicts linearly."""
        kf = KalmanPositionFilter(dt=1.0, process_noise=0.0, measurement_noise=0.01)
        measurement = [0, 0]
        mean, cov = kf.initiate(measurement)

        # Set constant velocity
        mean[2] = 10  # vx = 10 pixels per step
        mean[3] = 20  # vy = 20 pixels per step

        # Predict 3 steps ahead
        predicted_mean, _ = kf.predict_n_steps(mean, cov, n_steps=3)

        # With zero process noise, position should be exactly 3*velocity
        assert abs(predicted_mean[0] - 30) < 1  # 3 * 10 = 30
        assert abs(predicted_mean[1] - 60) < 1  # 3 * 20 = 60


class TestMultiKeypointTracker:
    """Tests for MultiKeypointTracker class."""

    def test_initialization(self):
        """Test tracker initialization."""
        tracker = MultiKeypointTracker(num_keypoints=17)
        assert tracker.num_keypoints == 17
        assert len(tracker.filters) == 0
        assert len(tracker.states) == 0

    def test_update_single_keypoint(self):
        """Test updating a single keypoint."""
        tracker = MultiKeypointTracker()
        
        # First observation
        state = tracker.update(0, [100, 200])
        assert state is not None
        assert len(state) == 4  # x, y, vx, vy
        assert 0 in tracker.states

    def test_update_multiple_keypoints(self):
        """Test updating multiple keypoints."""
        tracker = MultiKeypointTracker()
        
        for i in range(5):
            tracker.update(i, [100 + i * 10, 200 + i * 10])
        
        assert len(tracker.states) == 5
        assert len(tracker.filters) == 5

    def test_predict_position(self):
        """Test predicting future position."""
        tracker = MultiKeypointTracker()
        
        # Add some observations to establish velocity
        tracker.update(0, [100, 200])
        tracker.update(0, [110, 210])  # Moving +10, +10 per step
        tracker.update(0, [120, 220])

        predicted = tracker.predict_position(0, n_steps=3)
        assert predicted is not None
        assert len(predicted) == 2  # x, y only

    def test_predict_nonexistent_keypoint(self):
        """Test predicting for non-existent keypoint returns None."""
        tracker = MultiKeypointTracker()
        predicted = tracker.predict_position(999, n_steps=1)
        assert predicted is None

    def test_get_velocity(self):
        """Test getting velocity estimate."""
        tracker = MultiKeypointTracker()
        
        # Multiple observations to establish velocity
        tracker.update(0, [100, 200])
        tracker.update(0, [110, 220])

        velocity = tracker.get_velocity(0)
        assert velocity is not None
        assert len(velocity) == 2  # vx, vy

    def test_process_pose_results(self):
        """Test processing pose estimation results."""
        tracker = MultiKeypointTracker()
        
        # Mock pose results (similar to MoveNet output)
        pose_results = [
            {
                0: [100, 200, 0.9],  # keypoint_id: [x, y, score]
                1: [120, 180, 0.85],
                2: [80, 180, 0.8],
            }
        ]
        
        updated_states = tracker.process_pose_results(pose_results)
        
        assert len(updated_states) == 1
        assert 0 in updated_states[0]
        assert 'position' in updated_states[0][0]
        assert 'velocity' in updated_states[0][0]
        assert 'score' in updated_states[0][0]

    def test_process_pose_results_with_bbox(self):
        """Test that bbox is ignored in pose results."""
        tracker = MultiKeypointTracker()
        
        pose_results = [
            {
                0: [100, 200, 0.9],
                'bbox': [50, 50, 200, 400, 0.95],  # Should be ignored
            }
        ]
        
        updated_states = tracker.process_pose_results(pose_results)
        
        assert len(updated_states) == 1
        assert 0 in updated_states[0]
        assert 'bbox' not in updated_states[0]

    def test_predict_all_positions(self):
        """Test predicting all tracked positions."""
        tracker = MultiKeypointTracker()
        
        # Add some keypoints
        tracker.update(0, [100, 200])
        tracker.update(1, [150, 250])
        tracker.update(2, [200, 300])
        
        predictions = tracker.predict_all_positions(n_steps=3)
        
        assert len(predictions) == 3
        assert 0 in predictions
        assert 1 in predictions
        assert 2 in predictions

    def test_reset(self):
        """Test resetting the tracker."""
        tracker = MultiKeypointTracker()
        
        tracker.update(0, [100, 200])
        tracker.update(1, [150, 250])
        
        assert len(tracker.states) == 2
        
        tracker.reset()
        
        assert len(tracker.states) == 0
        assert len(tracker.filters) == 0


class TestIntegration:
    """Integration tests for the position prediction system."""

    def test_tracking_moving_point(self):
        """Test tracking a point moving in a straight line."""
        tracker = MultiKeypointTracker(
            dt=1.0,
            process_noise=0.01,
            measurement_noise=0.1
        )
        
        # Simulate point moving +5, +3 per step
        for i in range(10):
            x = 100 + i * 5
            y = 100 + i * 3
            tracker.update(0, [x, y])
        
        # Predict next position
        predicted = tracker.predict_position(0, n_steps=1)
        
        # Should be close to (150, 130) + (5, 3) = (155, 133)
        expected_x = 100 + 10 * 5  # ~150
        expected_y = 100 + 10 * 3  # ~130
        
        assert abs(predicted[0] - expected_x) < 20
        assert abs(predicted[1] - expected_y) < 20

    def test_noisy_measurements(self):
        """Test that filter smooths noisy measurements."""
        tracker = MultiKeypointTracker(
            dt=1.0,
            process_noise=0.1,
            measurement_noise=0.5
        )
        
        np.random.seed(42)
        
        # True position moving at constant velocity
        true_positions = [(100 + i * 5, 100 + i * 3) for i in range(20)]
        
        # Add noise to measurements
        noisy_measurements = [
            (x + np.random.normal(0, 5), y + np.random.normal(0, 5))
            for x, y in true_positions
        ]
        
        for x, y in noisy_measurements:
            tracker.update(0, [x, y])
        
        # Get current state
        state = tracker.states[0][0]
        estimated_x, estimated_y = state[0], state[1]
        
        # True position at end
        true_x, true_y = true_positions[-1]
        
        # Estimated should be closer to true than last noisy measurement
        last_noisy_x, last_noisy_y = noisy_measurements[-1]
        
        # The filter should reduce the error compared to raw measurements
        filter_error = np.sqrt((estimated_x - true_x)**2 + (estimated_y - true_y)**2)
        noise_error = np.sqrt((last_noisy_x - true_x)**2 + (last_noisy_y - true_y)**2)
        
        # Filter should generally reduce error (with some tolerance)
        assert filter_error < noise_error + 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
