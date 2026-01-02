#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests to verify that vision model nodes handle exceptions gracefully and still return image data"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_object_detection_has_exception_handling_with_return():
    """Test that object detection exception handler returns proper data"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that there's an exception handler
    assert 'except Exception as e:' in content, \
        "Object detection should have exception handling"
    
    # Check that the exception handler logs errors
    exception_section = content.split('except Exception as e:')[1].split('def ')[0]
    assert 'logger.error' in exception_section and 'exc_info=True' in exception_section, \
        "Object detection should log errors with stack trace"
    
    # Check that the exception handler returns data
    assert 'return {"image":' in exception_section, \
        "Object detection exception handler should return a dictionary with image"


def test_pose_estimation_has_exception_handling_with_return():
    """Test that pose estimation has exception handling that returns proper data"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_pose_estimation.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check that update method has try-except
    assert 'def update(' in content, \
        "Pose estimation should have update method"
    
    update_section = content.split('def update(')[1].split('def close(')[0]
    
    # Check that there's an exception handler
    assert 'except Exception as e:' in update_section, \
        "Pose estimation update should have exception handling"
    
    # Check that the exception handler logs errors
    exception_section = update_section.split('except Exception as e:')[1]
    assert 'logger.error' in exception_section and 'exc_info=True' in exception_section, \
        "Pose estimation should log errors with stack trace"
    
    # Check that the exception handler returns data
    assert 'return {"image":' in exception_section, \
        "Pose estimation exception handler should return a dictionary with image"


def test_both_nodes_return_frame_on_exception():
    """Test that both nodes return the input frame when an exception occurs"""
    
    for node_file, node_name in [
        ('node_object_detection.py', 'object detection'),
        ('node_pose_estimation.py', 'pose estimation')
    ]:
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'node', 'DLNode', node_file
        )
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check that exception handler returns frame
        exception_section = content.split('except Exception as e:')[-1].split('def ')[0]
        assert 'return {' in exception_section, \
            f"{node_name} exception handler should return a dictionary"
        assert '"image"' in exception_section, \
            f"{node_name} exception handler should return image key"
        assert '"json"' in exception_section, \
            f"{node_name} exception handler should return json key"
        assert '"audio"' in exception_section, \
            f"{node_name} exception handler should return audio key"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
