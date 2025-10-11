#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for logging utilities"""

import pytest
import logging
import tempfile
import os
from src.utils.logging import setup_logging, get_logger


def test_get_logger():
    """Test getting a logger instance"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_setup_logging_default():
    """Test setup_logging with default parameters"""
    logger = setup_logging()
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.INFO


def test_setup_logging_custom_level():
    """Test setup_logging with custom level"""
    logger = setup_logging(level=logging.DEBUG)
    assert logger.level == logging.DEBUG


def test_setup_logging_with_file():
    """Test setup_logging with log file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = setup_logging(log_file=log_file)
        test_message = "Test log message"
        logger.info(test_message)
        
        # Check that file was created and contains the message
        assert os.path.exists(log_file)
        with open(log_file, 'r') as f:
            content = f.read()
            assert test_message in content
    finally:
        # Cleanup
        if os.path.exists(log_file):
            os.remove(log_file)


def test_setup_logging_custom_format():
    """Test setup_logging with custom format"""
    custom_format = '%(levelname)s - %(message)s'
    logger = setup_logging(format_string=custom_format)
    assert isinstance(logger, logging.Logger)


def test_logger_output():
    """Test that logger produces output"""
    logger = get_logger('test_logger')
    logger.setLevel(logging.INFO)
    
    # This should not raise any exceptions
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
