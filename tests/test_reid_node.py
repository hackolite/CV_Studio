#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for ReId node functionality
"""
import pytest
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from node.TrackerNode.node_reid import Node as ReIdNode


class TestReIdNode:
    """Test the ReId node implementation"""
    
    def test_node_creation(self):
        """Test that ReId node can be instantiated"""
        node = ReIdNode()
        assert node is not None
        assert node.node_label == 'ReId'
        assert node.node_tag == 'ReId'
    
    def test_feature_extraction(self):
        """Test feature extraction from bbox"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Create a test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Create a test bbox
        bbox = [100, 100, 200, 200]
        
        # Extract features
        feature = node._extract_features(frame, bbox)
        
        # Check feature vector
        assert feature is not None
        assert len(feature) == 48  # 16 bins * 3 channels
        assert np.all(feature >= 0)
        assert np.all(feature <= 1)  # Normalized
    
    def test_invalid_bbox(self):
        """Test feature extraction with invalid bbox"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Create a test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Invalid bbox (x2 < x1)
        bbox = [200, 100, 100, 200]
        
        # Extract features
        feature = node._extract_features(frame, bbox)
        
        # Should return zero feature
        assert feature is not None
        assert len(feature) == 48
        assert np.all(feature == 0)
    
    def test_out_of_bounds_bbox(self):
        """Test feature extraction with out of bounds bbox"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Create a test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Out of bounds bbox
        bbox = [500, 400, 700, 500]  # x2=700 > 640
        
        # Extract features
        feature = node._extract_features(frame, bbox)
        
        # Should handle gracefully and return a valid feature
        assert feature is not None
        assert len(feature) == 48
    
    def test_centroid_init_from_detections(self):
        """Direct centroid initialisation from first N-player frame (replaces KMeans)."""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}

        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 2

        # Two clearly distinct feature vectors
        feat_a = np.zeros(48, dtype=np.float32)
        feat_b = np.ones(48, dtype=np.float32)
        features = [feat_a, feat_b]

        node._init_centroids(tag_node_name, features, n_slots=2)

        assert tag_node_name in node._centroids
        assert node._centroids_initialized[tag_node_name] is True
        centroids = node._centroids[tag_node_name]
        assert centroids.shape == (2, 48)

    def test_centroid_init_more_detections_than_slots(self):
        """When > N detections are present, pick the most spread-out N."""
        node = ReIdNode()
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 2

        # 3 features: two clusters far apart, one in the middle
        f0 = np.zeros(48, dtype=np.float32)
        f1 = np.ones(48, dtype=np.float32)
        f_mid = np.ones(48, dtype=np.float32) * 0.5
        features = [f0, f_mid, f1]

        node._init_centroids(tag_node_name, features, n_slots=2)

        centroids = node._centroids[tag_node_name]
        assert centroids.shape == (2, 48)
        # The chosen pair should be the two most distant (f0 and f1)
        dist = np.linalg.norm(centroids[0] - centroids[1])
        assert dist > np.sqrt(48) * 0.9  # close to max distance

    def test_centroid_init_fewer_detections_than_slots(self):
        """When fewer detections than slots, use what is available."""
        node = ReIdNode()
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 3  # 3 slots

        features = [np.zeros(48, dtype=np.float32)]  # only 1 detection

        node._init_centroids(tag_node_name, features, n_slots=3)
        assert node._centroids[tag_node_name].shape[0] == 1

    def test_centroid_ema_update(self):
        """EMA update moves centroid towards new feature."""
        from node.TrackerNode.node_reid import _CENTROID_EMA_ALPHA
        node = ReIdNode()
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 2

        c0 = np.zeros(48, dtype=np.float32)
        c1 = np.ones(48, dtype=np.float32)
        node._centroids[tag_node_name] = np.array([c0.copy(), c1.copy()])
        node._centroids_initialized[tag_node_name] = True

        new_feat = np.ones(48, dtype=np.float32) * 0.5
        node._update_centroid(tag_node_name, 0, new_feat)

        expected = _CENTROID_EMA_ALPHA * c0 + (1 - _CENTROID_EMA_ALPHA) * new_feat
        np.testing.assert_allclose(node._centroids[tag_node_name][0], expected)

    def test_assign_to_centroid(self):
        """Test assigning a feature to nearest centroid"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}

        tag_node_name = "1:ReId"
        node._centroids[tag_node_name] = np.array([
            np.ones(48) * 0.1,  # Centroid 1
            np.ones(48) * 0.9,  # Centroid 2
        ])

        feature1 = np.ones(48) * 0.15
        result1 = node._assign_to_centroid(feature1, tag_node_name)
        assert result1 == 1

        feature2 = np.ones(48) * 0.85
        result2 = node._assign_to_centroid(feature2, tag_node_name)
        assert result2 == 2

    def test_get_color_for_name(self):
        """Test color generation for names"""
        node = ReIdNode()

        color1a = node._get_color_for_name("player1")
        color1b = node._get_color_for_name("player1")
        assert color1a == color1b

        assert len(color1a) == 3
        assert all(0 <= c <= 255 for c in color1a)

    def test_slot_name_defaults(self):
        """Test default slot naming"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}

        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 1
        node._slot_names[tag_node_name] = {1: "A"}

        node._slot_id[tag_node_name] = 3
        node._slot_names[tag_node_name][2] = "B"
        node._slot_names[tag_node_name][3] = "C"

        assert node._slot_names[tag_node_name][1] == "A"
        assert node._slot_names[tag_node_name][2] == "B"
        assert node._slot_names[tag_node_name][3] == "C"

    def test_object_detection_format_compatibility(self):
        """Output format matches ObjectDetection JSON (bboxes/scores/class_ids/class_names dict)."""
        node = ReIdNode()
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 2
        node._slot_names[tag_node_name] = {1: "A", 2: "B"}

        od_json = {
            'bboxes': [[100, 100, 200, 200], [300, 300, 400, 400]],
            'scores': [0.9, 0.8],
            'class_ids': [0, 0],
            'class_names': {0: 'person'},
        }

        # After initialisation, output must include these keys
        assert 'bboxes' in od_json
        assert 'scores' in od_json
        assert 'class_ids' in od_json
        assert 'class_names' in od_json
        assert 'track_ids' not in od_json

    def test_reset_centroids(self):
        """Reset clears centroids and initialized flag."""
        node = ReIdNode()
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 2
        node._slot_names[tag_node_name] = {1: "A", 2: "B"}

        # Initialise
        features = [np.zeros(48, dtype=np.float32), np.ones(48, dtype=np.float32)]
        node._init_centroids(tag_node_name, features, n_slots=2)
        assert node._centroids_initialized[tag_node_name] is True
        assert tag_node_name in node._centroids

        # Reset
        node._reset_kmeans(None, None, tag_node_name)

        assert node._centroids_initialized.get(tag_node_name, False) is False
        assert tag_node_name not in node._centroids


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
