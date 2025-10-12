#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for GPU utilities"""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.gpu_utils import (
    check_gpu_availability,
    get_execution_providers,
    log_gpu_info
)


def test_check_gpu_availability_with_cuda():
    """Test GPU availability check when CUDA is available"""
    # Mock the onnxruntime module import
    mock_ort = MagicMock()
    mock_ort.get_available_providers.return_value = [
        'CUDAExecutionProvider',
        'CPUExecutionProvider'
    ]
    
    with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
        is_available, providers, message = check_gpu_availability()
        
        assert is_available is True
        assert 'CUDAExecutionProvider' in providers
        assert 'CUDA' in message


def test_check_gpu_availability_without_cuda():
    """Test GPU availability check when only CPU is available"""
    mock_ort = MagicMock()
    mock_ort.get_available_providers.return_value = ['CPUExecutionProvider']
    
    with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
        is_available, providers, message = check_gpu_availability()
        
        assert is_available is False
        assert 'CPUExecutionProvider' in providers
        assert 'not available' in message.lower()


def test_check_gpu_availability_import_error():
    """Test GPU availability check when onnxruntime is not installed"""
    # Remove onnxruntime from sys.modules if it exists
    with patch.dict('sys.modules', {'onnxruntime': None}):
        # Force ImportError by making the import fail
        with patch('builtins.__import__', side_effect=ImportError("No module named 'onnxruntime'")):
            is_available, providers, message = check_gpu_availability()
            
            assert is_available is False
            assert providers == []
            assert 'not installed' in message.lower() or 'ONNX Runtime' in message


def test_get_execution_providers_gpu_enabled():
    """Test getting execution providers when GPU is enabled and available"""
    with patch('src.utils.gpu_utils.check_gpu_availability') as mock_check:
        mock_check.return_value = (
            True,
            ['CUDAExecutionProvider', 'CPUExecutionProvider'],
            'GPU available'
        )
        
        providers = get_execution_providers(use_gpu=True)
        
        assert 'CUDAExecutionProvider' in providers
        assert 'CPUExecutionProvider' in providers


def test_get_execution_providers_gpu_disabled():
    """Test getting execution providers when GPU is disabled"""
    providers = get_execution_providers(use_gpu=False)
    
    assert providers == ['CPUExecutionProvider']
    assert 'CUDAExecutionProvider' not in providers


def test_get_execution_providers_gpu_enabled_but_unavailable():
    """Test getting execution providers when GPU is requested but not available"""
    with patch('src.utils.gpu_utils.check_gpu_availability') as mock_check:
        mock_check.return_value = (
            False,
            ['CPUExecutionProvider'],
            'GPU not available'
        )
        
        providers = get_execution_providers(use_gpu=True)
        
        assert providers == ['CPUExecutionProvider']
        assert 'CUDAExecutionProvider' not in providers


def test_log_gpu_info():
    """Test that log_gpu_info doesn't raise exceptions"""
    mock_ort = MagicMock()
    mock_ort.get_available_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    mock_ort.__version__ = '1.12.0'
    
    with patch.dict('sys.modules', {'onnxruntime': mock_ort}):
        # Should not raise any exceptions
        log_gpu_info()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
