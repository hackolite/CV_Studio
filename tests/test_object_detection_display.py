#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test object detection node image display structure and logic"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_object_detection_consolidated_frame_processing():
    """Test that frame processing logic is consolidated properly"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the update method
    update_start = content.find('def update(', content.find('class Node(Node):'))
    update_end = content.find('def close(', update_start)
    update_method = content[update_start:update_end]
    
    # Verify that bboxes, scores, class_ids definition and usage are in the same block
    # Find the main frame processing block (after result = {})
    result_init = update_method.find('result = {}')
    processing_section = update_method[result_init:]
    
    # In the processing section, there should be one main frame block
    import re
    frame_checks_after_result = list(re.finditer(r'if frame is not None:', processing_section))
    
    # Should have exactly 1 frame processing block after result initialization
    assert len(frame_checks_after_result) == 1, \
        f"Should have exactly 1 main frame processing block, found {len(frame_checks_after_result)}"
    
    # Verify that bboxes, scores, class_ids usage comes after definition in same block
    bboxes_def = update_method.find('bboxes, scores, class_ids = ')
    bboxes_usage_in_draw = update_method.find('self.draw_object_detection_info')
    texture_update = update_method.find('dpg_set_value(tag_node_output_image, texture)')
    
    assert bboxes_def > 0, "Should define bboxes, scores, class_ids"
    assert bboxes_usage_in_draw > 0, "Should use variables in draw_object_detection_info"
    assert bboxes_usage_in_draw > bboxes_def, "Variable usage should come after definition"
    assert texture_update > bboxes_usage_in_draw, "Texture update should come after drawing"
    
    # Verify all are in the same if block by checking indentation consistency
    # Extract lines between bboxes_def and texture_update
    processing_logic = update_method[bboxes_def:texture_update+100]
    
    # Should not have another "if frame is not None:" in the middle
    additional_frame_checks = processing_logic.count('if frame is not None:')
    assert additional_frame_checks == 0, \
        f"Should not have additional 'if frame is not None:' blocks in processing logic, found {additional_frame_checks}"


def test_object_detection_file_has_add_image():
    """Test that the object detection file contains dpg.add_image call"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check for image widget creation
    assert 'dpg.add_image(' in content, "Should have dpg.add_image() call to display image"
    
    # Check for texture creation
    assert 'dpg.add_raw_texture(' in content, "Should create texture with dpg.add_raw_texture()"
    
    # Check for texture update
    assert 'dpg_set_value(' in content, "Should update texture with dpg_set_value()"
    assert 'convert_cv_to_dpg' in content, "Should convert OpenCV image to DPG texture"


def test_object_detection_attribute_order():
    """Test that node attributes are in the correct order"""
    
    file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'node', 'DLNode', 'node_object_detection.py'
    )
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find the add_node method
    add_node_start = content.find('def add_node(')
    add_node_end = content.find('class Node(Node):', add_node_start)
    add_node_method = content[add_node_start:add_node_end]
    
    # Check that image output attribute exists
    assert 'tag_node_output_image_name' in add_node_method or 'tag_node_output01_name' in add_node_method, \
        "Should have output image attribute"
    
    # Check that dpg.add_image is in an output attribute
    assert 'dpg.mvNode_Attr_Output' in add_node_method, "Should have output attribute"
    assert 'dpg.add_image(' in add_node_method, "Should add image widget in output attribute"
    
    # Verify the texture tag matches the image widget tag
    # Extract the texture tag and image widget tag
    import re
    texture_match = re.search(r'dpg\.add_raw_texture\([^,]+,[^,]+,[^,]+,\s*tag=([^,\)]+)', add_node_method)
    image_match = re.search(r'dpg\.add_image\(([^\)]+)\)', add_node_method)
    
    if texture_match and image_match:
        texture_tag = texture_match.group(1).strip()
        image_tag = image_match.group(1).strip()
        assert texture_tag == image_tag, f"Texture tag {texture_tag} should match image tag {image_tag}"


if __name__ == '__main__':
    test_object_detection_consolidated_frame_processing()
    print("✓ test_object_detection_consolidated_frame_processing passed")
    
    test_object_detection_file_has_add_image()
    print("✓ test_object_detection_file_has_add_image passed")
    
    test_object_detection_attribute_order()
    print("✓ test_object_detection_attribute_order passed")
    
    print("\nAll tests passed!")
