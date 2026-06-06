#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple integration test for Operator node logic
Tests the core operation logic without GUI dependencies
"""


def apply_operation(value_a, value_b, operation):
    """Apply the selected operation to two values."""
    try:
        a = float(value_a)
        b = float(value_b)
        
        if operation == 'Addition (+)':
            return a + b
        elif operation == 'Subtraction (-)':
            return a - b
        elif operation == 'Multiplication (*)':
            return a * b
        elif operation == 'Division (/)':
            # Handle division by zero
            if b == 0:
                return float('inf') if a >= 0 else float('-inf')
            return a / b
        else:
            return 0.0
    except (ValueError, TypeError):
        return 0.0


def process_json_data(json_a, json_b, operation):
    """Process two JSON dictionaries with the given operation."""
    if not isinstance(json_a, dict) or not isinstance(json_b, dict):
        return None
    
    if operation == 'Fusion':
        result = {}
        for key, value in json_a.items():
            result['A_' + key] = value
        for key, value in json_b.items():
            result['B_' + key] = value
        return result
    
    result = {}
    
    # Get all keys that exist in both dictionaries
    common_keys = set(json_a.keys()) & set(json_b.keys())
    
    # Process only numeric values
    for key in common_keys:
        value_a = json_a[key]
        value_b = json_b[key]
        
        # Only process numeric values (int or float)
        if isinstance(value_a, (int, float)) and isinstance(value_b, (int, float)):
            result[key] = apply_operation(value_a, value_b, operation)
    
    return result


def test_addition():
    """Test addition operation"""
    result = apply_operation(5.0, 3.0, 'Addition (+)')
    assert result == 8.0, f"Expected 8.0, got {result}"
    print("✓ Addition test passed")


def test_subtraction():
    """Test subtraction operation"""
    result = apply_operation(10.0, 3.0, 'Subtraction (-)')
    assert result == 7.0, f"Expected 7.0, got {result}"
    print("✓ Subtraction test passed")


def test_multiplication():
    """Test multiplication operation"""
    result = apply_operation(4.0, 5.0, 'Multiplication (*)')
    assert result == 20.0, f"Expected 20.0, got {result}"
    print("✓ Multiplication test passed")


def test_division():
    """Test division operation"""
    result = apply_operation(20.0, 4.0, 'Division (/)')
    assert result == 5.0, f"Expected 5.0, got {result}"
    print("✓ Division test passed")


def test_division_by_zero():
    """Test division by zero returns infinity"""
    result = apply_operation(10.0, 0.0, 'Division (/)')
    assert result == float('inf'), f"Expected inf, got {result}"
    
    result_neg = apply_operation(-10.0, 0.0, 'Division (/)')
    assert result_neg == float('-inf'), f"Expected -inf, got {result_neg}"
    print("✓ Division by zero test passed")


def test_invalid_values():
    """Test operation with invalid values returns 0"""
    result = apply_operation('invalid', 3.0, 'Addition (+)')
    assert result == 0.0, f"Expected 0.0, got {result}"
    print("✓ Invalid values test passed")


def test_iou_like_data():
    """Test with IOU-like performance data"""
    json_a = {
        'diff_score': 0.5,
        'mean_iou': 0.75,
        'loss': 2.5,
        'count_diff': 3,
    }
    
    json_b = {
        'diff_score': 0.3,
        'mean_iou': 0.85,
        'loss': 1.5,
        'count_diff': 2,
    }
    
    result = process_json_data(json_a, json_b, 'Addition (+)')
    
    assert result is not None, "Result should not be None"
    assert 'diff_score' in result, "Result should contain 'diff_score'"
    assert 'mean_iou' in result, "Result should contain 'mean_iou'"
    assert 'loss' in result, "Result should contain 'loss'"
    assert 'count_diff' in result, "Result should contain 'count_diff'"
    
    # Verify calculations (addition)
    assert result['diff_score'] == 0.8, f"Expected 0.8, got {result['diff_score']}"
    assert result['mean_iou'] == 1.6, f"Expected 1.6, got {result['mean_iou']}"
    assert result['loss'] == 4.0, f"Expected 4.0, got {result['loss']}"
    assert result['count_diff'] == 5, f"Expected 5, got {result['count_diff']}"
    
    print("✓ IOU-like data test passed")


def test_subtraction_operation():
    """Test subtraction with realistic data"""
    json_a = {
        'value1': 10.0,
        'value2': 20.0,
    }
    
    json_b = {
        'value1': 3.0,
        'value2': 8.0,
    }
    
    result = process_json_data(json_a, json_b, 'Subtraction (-)')
    
    assert result is not None, "Result should not be None"
    assert result['value1'] == 7.0, f"Expected 7.0, got {result['value1']}"
    assert result['value2'] == 12.0, f"Expected 12.0, got {result['value2']}"
    
    print("✓ Subtraction operation test passed")


def test_no_matching_keys():
    """Test when inputs have no matching keys"""
    json_a = {
        'metric_a': 5.0,
        'metric_b': 10.0,
    }
    
    json_b = {
        'metric_c': 3.0,
        'metric_d': 8.0,
    }
    
    result = process_json_data(json_a, json_b, 'Addition (+)')
    
    # Result should be empty dict (no matching keys)
    assert result == {}, f"Expected empty dict, got {result}"
    
    print("✓ No matching keys test passed")


def test_filters_non_numeric():
    """Test that non-numeric values are filtered out"""
    json_a = {
        'numeric_value': 5.0,
        'string_value': 'hello',
        'list_value': [1, 2, 3],
    }
    
    json_b = {
        'numeric_value': 3.0,
        'string_value': 'world',
        'list_value': [4, 5, 6],
    }
    
    result = process_json_data(json_a, json_b, 'Addition (+)')
    
    # Only numeric_value should be in result
    assert result is not None, "Result should not be None"
    assert 'numeric_value' in result, "Result should contain 'numeric_value'"
    assert 'string_value' not in result, "Result should not contain 'string_value'"
    assert 'list_value' not in result, "Result should not contain 'list_value'"
    assert result['numeric_value'] == 8.0, f"Expected 8.0, got {result['numeric_value']}"
    
    print("✓ Non-numeric filtering test passed")


def test_fusion_basic():
    """Test fusion operation merges both JSONs with A_/B_ prefixes"""
    json_a = {
        'mean_iou': 0.75,
        'loss': 2.5,
    }
    
    json_b = {
        'mean_iou': 0.85,
        'loss': 1.5,
    }
    
    result = process_json_data(json_a, json_b, 'Fusion')
    
    assert result is not None, "Result should not be None"
    assert 'A_mean_iou' in result, "Result should contain 'A_mean_iou'"
    assert 'A_loss' in result, "Result should contain 'A_loss'"
    assert 'B_mean_iou' in result, "Result should contain 'B_mean_iou'"
    assert 'B_loss' in result, "Result should contain 'B_loss'"
    assert result['A_mean_iou'] == 0.75
    assert result['A_loss'] == 2.5
    assert result['B_mean_iou'] == 0.85
    assert result['B_loss'] == 1.5
    assert len(result) == 4
    
    print("✓ Fusion basic test passed")


def test_fusion_different_keys():
    """Test fusion with different keys in A and B"""
    json_a = {
        'metric_a': 1.0,
    }
    
    json_b = {
        'metric_b': 2.0,
    }
    
    result = process_json_data(json_a, json_b, 'Fusion')
    
    assert result is not None
    assert 'A_metric_a' in result
    assert 'B_metric_b' in result
    assert result['A_metric_a'] == 1.0
    assert result['B_metric_b'] == 2.0
    assert len(result) == 2
    
    print("✓ Fusion different keys test passed")


def test_fusion_preserves_all_types():
    """Test fusion preserves non-numeric values too"""
    json_a = {
        'score': 0.9,
        'label': 'cat',
    }
    
    json_b = {
        'score': 0.7,
        'label': 'dog',
    }
    
    result = process_json_data(json_a, json_b, 'Fusion')
    
    assert result is not None
    assert result['A_score'] == 0.9
    assert result['A_label'] == 'cat'
    assert result['B_score'] == 0.7
    assert result['B_label'] == 'dog'
    
    print("✓ Fusion preserves all types test passed")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Running Operator Node Logic Tests")
    print("="*60 + "\n")
    
    test_addition()
    test_subtraction()
    test_multiplication()
    test_division()
    test_division_by_zero()
    test_invalid_values()
    test_iou_like_data()
    test_subtraction_operation()
    test_no_matching_keys()
    test_filters_non_numeric()
    test_fusion_basic()
    test_fusion_different_keys()
    test_fusion_preserves_all_types()
    
    print("\n" + "="*60)
    print("All tests passed! ✓")
    print("="*60 + "\n")
