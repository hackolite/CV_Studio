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
    
    def test_kmeans_training(self):
        """Test K-means training with sufficient samples"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Setup node structures
        node_id = 1
        tag_node_name = f"{node_id}:ReId"
        node._slot_id[tag_node_name] = 2  # 2 slots
        
        # Create fake features (20 samples)
        node._feature_buffer[tag_node_name] = []
        for _ in range(20):
            node._feature_buffer[tag_node_name].append(np.random.rand(48))
        
        # Train K-means
        result = node._train_kmeans(node_id)
        
        # Check training succeeded
        assert result is True
        assert tag_node_name in node._centroids
        assert tag_node_name in node._kmeans_trained
        assert node._kmeans_trained[tag_node_name] is True
        
        # Check centroids
        centroids = node._centroids[tag_node_name]
        assert centroids.shape[0] == 2  # 2 clusters
        assert centroids.shape[1] == 48  # 48 features
    
    def test_kmeans_insufficient_samples(self):
        """Test K-means training with insufficient samples"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Setup node structures
        node_id = 1
        tag_node_name = f"{node_id}:ReId"
        node._slot_id[tag_node_name] = 2
        
        # Create fake features (only 5 samples - not enough)
        node._feature_buffer[tag_node_name] = []
        for _ in range(5):
            node._feature_buffer[tag_node_name].append(np.random.rand(48))
        
        # Try to train K-means
        result = node._train_kmeans(node_id)
        
        # Should fail due to insufficient samples
        assert result is False
    
    def test_assign_to_centroid(self):
        """Test assigning a feature to nearest centroid"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        # Setup centroids
        tag_node_name = "1:ReId"
        node._centroids[tag_node_name] = np.array([
            np.ones(48) * 0.1,  # Centroid 1
            np.ones(48) * 0.9,  # Centroid 2
        ])
        
        # Test feature close to centroid 1
        feature1 = np.ones(48) * 0.15
        result1 = node._assign_to_centroid(feature1, tag_node_name)
        assert result1 == 1
        
        # Test feature close to centroid 2
        feature2 = np.ones(48) * 0.85
        result2 = node._assign_to_centroid(feature2, tag_node_name)
        assert result2 == 2
    
    def test_get_color_for_name(self):
        """Test color generation for names"""
        node = ReIdNode()
        
        # Same name should produce same color
        color1a = node._get_color_for_name("player1")
        color1b = node._get_color_for_name("player1")
        assert color1a == color1b
        
        # Different names should (usually) produce different colors
        color2 = node._get_color_for_name("player2")
        # Note: hash collisions are possible but unlikely for these simple names
        
        # Colors should be valid BGR tuples
        assert len(color1a) == 3
        assert all(0 <= c <= 255 for c in color1a)
    
    def test_slot_name_defaults(self):
        """Test default slot naming"""
        node = ReIdNode()
        node._opencv_setting_dict = {'process_width': 640, 'process_height': 480, 'use_pref_counter': False}
        
        tag_node_name = "1:ReId"
        node._slot_id[tag_node_name] = 1
        node._slot_names[tag_node_name] = {1: "player1"}
        
        # Simulate adding slots (without UI)
        node._slot_id[tag_node_name] = 3
        node._slot_names[tag_node_name][2] = "player2"
        node._slot_names[tag_node_name][3] = "player3"
        
        # Check names
        assert node._slot_names[tag_node_name][1] == "player1"
        assert node._slot_names[tag_node_name][2] == "player2"
        assert node._slot_names[tag_node_name][3] == "player3"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
