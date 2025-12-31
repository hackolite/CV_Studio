#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for display speed optimizations.
Tests the new texture conversion caching and improved performance.
"""
import sys
import os
import time
import numpy as np
import cv2

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from node.basenode import Node


class TestTextureConversionOptimization:
    """Test optimized texture conversion"""
    
    def test_convert_cv_to_dpg_basic(self):
        """Test basic texture conversion works"""
        node = Node()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        texture = node.convert_cv_to_dpg(image, 320, 240)
        
        # Check output shape
        assert texture is not None
        assert isinstance(texture, np.ndarray)
        assert texture.dtype == np.float32
        # 320x240x3 = 230400
        assert len(texture) == 320 * 240 * 3
        
    def test_convert_cv_to_dpg_values(self):
        """Test texture conversion produces correct values"""
        node = Node()
        # Create test image with known values
        image = np.ones((100, 100, 3), dtype=np.uint8) * 255  # White image
        
        texture = node.convert_cv_to_dpg(image, 50, 50)
        
        # All values should be 1.0 (255/255)
        assert np.allclose(texture, 1.0, atol=0.01)
        
    def test_convert_cv_to_dpg_cached_initialization(self):
        """Test cached conversion initializes correctly"""
        node = Node()
        
        # Check cache variables exist
        assert hasattr(node, '_texture_cache')
        assert hasattr(node, '_texture_cache_hash')
        assert hasattr(node, '_last_texture_update')
        assert hasattr(node, '_texture_update_interval')
        
        # Check initial values
        assert node._texture_cache is None
        assert node._texture_cache_hash is None
        assert node._last_texture_update == 0
        assert node._texture_update_interval == 0.033  # 30 FPS
        
    def test_convert_cv_to_dpg_cached_first_call(self):
        """Test first call to cached conversion"""
        node = Node()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        texture = node.convert_cv_to_dpg_cached(image, 320, 240)
        
        # Check texture is created
        assert texture is not None
        assert len(texture) == 320 * 240 * 3
        
        # Check cache is populated
        assert node._texture_cache is not None
        assert node._texture_cache_hash is not None
        assert node._last_texture_update > 0
        
    def test_convert_cv_to_dpg_cached_reuse(self):
        """Test cached conversion reuses cached texture"""
        node = Node()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # First call
        texture1 = node.convert_cv_to_dpg_cached(image, 320, 240)
        hash1 = node._texture_cache_hash
        time1 = node._last_texture_update
        
        # Second call immediately (within throttle interval)
        time.sleep(0.001)  # Small delay
        texture2 = node.convert_cv_to_dpg_cached(image, 320, 240)
        hash2 = node._texture_cache_hash
        time2 = node._last_texture_update
        
        # Should return cached texture
        assert hash1 == hash2  # Same hash
        assert time1 == time2  # No update
        assert np.array_equal(texture1, texture2)  # Same data
        
    def test_convert_cv_to_dpg_cached_update_on_change(self):
        """Test cached conversion updates when image changes"""
        node = Node()
        image1 = np.zeros((480, 640, 3), dtype=np.uint8)
        image2 = np.ones((480, 640, 3), dtype=np.uint8) * 255
        
        # First call with black image
        texture1 = node.convert_cv_to_dpg_cached(image1, 320, 240)
        hash1 = node._texture_cache_hash
        
        # Second call with white image
        texture2 = node.convert_cv_to_dpg_cached(image2, 320, 240)
        hash2 = node._texture_cache_hash
        
        # Should update cache
        assert hash1 != hash2  # Different hash
        assert not np.array_equal(texture1, texture2)  # Different data
        
    def test_convert_cv_to_dpg_cached_throttling(self):
        """Test throttling limits update frequency"""
        node = Node()
        node._texture_update_interval = 0.1  # 100ms throttle for test
        
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # First call
        texture1 = node.convert_cv_to_dpg_cached(image, 320, 240)
        time1 = node._last_texture_update
        
        # Second call immediately with different image
        time.sleep(0.01)  # 10ms - within throttle
        image2 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        texture2 = node.convert_cv_to_dpg_cached(image2, 320, 240)
        time2 = node._last_texture_update
        
        # Should NOT update due to throttling
        assert time1 == time2  # No update
        
        # Third call after throttle interval
        time.sleep(0.11)  # 110ms - after throttle
        image3 = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        texture3 = node.convert_cv_to_dpg_cached(image3, 320, 240)
        time3 = node._last_texture_update
        
        # Should update after throttle interval
        assert time3 > time2  # Updated
        
    def test_convert_cv_to_dpg_cached_force_update(self):
        """Test force_update parameter bypasses cache"""
        node = Node()
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # First call
        texture1 = node.convert_cv_to_dpg_cached(image, 320, 240)
        time1 = node._last_texture_update
        
        # Second call with force_update
        time.sleep(0.001)
        texture2 = node.convert_cv_to_dpg_cached(image, 320, 240, force_update=True)
        time2 = node._last_texture_update
        
        # Should update despite same image and throttle
        assert time2 > time1  # Updated
        
    def test_performance_improvement(self):
        """Test that cached conversion is faster than regular conversion"""
        node = Node()
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Warmup
        node.convert_cv_to_dpg(image, 320, 240)
        
        # Measure regular conversion (10 calls)
        start = time.time()
        for _ in range(10):
            node.convert_cv_to_dpg(image, 320, 240)
        regular_time = time.time() - start
        
        # Measure cached conversion (10 calls, should hit cache 9 times)
        start = time.time()
        for _ in range(10):
            node.convert_cv_to_dpg_cached(image, 320, 240)
        cached_time = time.time() - start
        
        # Cached should be significantly faster (at least 2x)
        # Note: First call creates cache, rest hit cache
        print(f"Regular: {regular_time:.4f}s, Cached: {cached_time:.4f}s")
        assert cached_time < regular_time * 0.5  # At least 50% faster


class TestColorCaching:
    """Test color calculation caching in object detection"""
    
    def test_color_cache_initialization(self):
        """Test color cache is initialized"""
        from node.DLNode.node_object_detection import Node as ObjDetNode
        
        # Check class variable exists
        assert hasattr(ObjDetNode, '_color_cache')
        assert isinstance(ObjDetNode._color_cache, dict)
        
    def test_get_color_cached_caches_result(self):
        """Test get_color_cached caches color calculations"""
        from node.DLNode.node_object_detection import Node as ObjDetNode
        
        node = ObjDetNode()
        
        # Clear cache
        node._color_cache.clear()
        
        # First call should compute and cache
        color1 = node.get_color_cached(5)
        assert 5 in node._color_cache
        
        # Second call should use cache
        color2 = node.get_color_cached(5)
        assert color1 == color2
        
        # Cache should only have one entry
        assert len(node._color_cache) == 1
        
    def test_get_color_cached_multiple_classes(self):
        """Test color cache works for multiple class IDs"""
        from node.DLNode.node_object_detection import Node as ObjDetNode
        
        node = ObjDetNode()
        node._color_cache.clear()
        
        # Cache multiple colors
        colors = {}
        for class_id in [0, 1, 5, 10, 50]:
            colors[class_id] = node.get_color_cached(class_id)
        
        # Check all cached
        assert len(node._color_cache) == 5
        
        # Check colors are consistent
        for class_id, expected_color in colors.items():
            assert node.get_color_cached(class_id) == expected_color


def test_all_dl_nodes_have_cached_conversion():
    """Test that all DL nodes use cached conversion"""
    import re
    
    dl_node_files = [
        'node/DLNode/node_object_detection.py',
        'node/DLNode/node_face_detection.py',
        'node/DLNode/node_classification.py',
        'node/DLNode/node_pose_estimation.py',
        'node/DLNode/node_semantic_segmentation.py',
    ]
    
    for filepath in dl_node_files:
        full_path = os.path.join(os.path.dirname(__file__), '..', filepath)
        with open(full_path, 'r') as f:
            content = f.read()
            
        # Check that file uses convert_cv_to_dpg_cached
        assert 'convert_cv_to_dpg_cached' in content, \
            f"{filepath} should use convert_cv_to_dpg_cached"
        
        print(f"✓ {filepath} uses cached conversion")


if __name__ == '__main__':
    # Run tests
    import pytest
    pytest.main([__file__, '-v'])
