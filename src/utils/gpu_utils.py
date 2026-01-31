#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""GPU detection and validation utilities for CV Studio"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


def check_gpu_availability() -> Tuple[bool, List[str], str]:
    """
    Check if GPU support is available through ONNX Runtime.
    
    Returns:
        Tuple of (is_available, available_providers, message)
        - is_available: True if GPU provider is available
        - available_providers: List of available execution providers
        - message: Human-readable status message
    """
    try:
        import onnxruntime as ort
        
        available_providers = ort.get_available_providers()
        
        # Check for CUDA (NVIDIA GPU) support
        has_cuda = 'CUDAExecutionProvider' in available_providers
        
        if has_cuda:
            message = "GPU support is available (CUDA)"
            logger.info(message)
            logger.info(f"Available providers: {', '.join(available_providers)}")
            return True, available_providers, message
        else:
            message = "GPU support is not available. Only CPU execution will be used."
            logger.warning(message)
            logger.info(f"Available providers: {', '.join(available_providers)}")
            logger.info("Note: GPU support is not available. Install onnxruntime-gpu for GPU acceleration.")
            return False, available_providers, message
            
    except ImportError as e:
        message = f"ONNX Runtime is not installed: {e}"
        logger.error(message)
        return False, [], message
    except Exception as e:
        message = f"Error checking GPU availability: {e}"
        logger.error(message)
        return False, [], message


def get_execution_providers(use_gpu: bool = False) -> List[str]:
    """
    Get appropriate execution providers based on GPU availability and user preference.
    
    Args:
        use_gpu: Whether to attempt to use GPU if available
        
    Returns:
        List of execution providers in order of preference
    """
    if not use_gpu:
        logger.debug("GPU usage disabled by configuration, using CPU only")
        return ['CPUExecutionProvider']
    
    is_available, available_providers, _ = check_gpu_availability()
    
    if is_available and 'CUDAExecutionProvider' in available_providers:
        logger.info("Using GPU execution (CUDA)")
        return ['CUDAExecutionProvider', 'CPUExecutionProvider']
    else:
        logger.info("Using CPU execution")
        return ['CPUExecutionProvider']


def log_gpu_info():
    """
    Log detailed GPU information for diagnostics.
    """
    is_available, providers, message = check_gpu_availability()
    
    logger.info("=" * 50)
    logger.info("GPU Support Information")
    logger.info("=" * 50)
    logger.info(f"Status: {message}")
    
    if providers:
        logger.info(f"Available ONNX Runtime providers:")
        for provider in providers:
            logger.info(f"  - {provider}")
    
    try:
        import onnxruntime as ort
        logger.info(f"ONNX Runtime version: {ort.__version__}")
    except Exception:
        pass
    
    logger.info("=" * 50)
