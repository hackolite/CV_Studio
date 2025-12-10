#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Logging configuration for CV Studio"""

import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime


def get_logs_directory() -> Path:
    """
    Get or create the logs directory.
    
    Creates a 'logs' directory in the project root if it doesn't exist.
    
    Returns:
        Path to the logs directory
    """
    # Get project root (2 levels up from this file: src/utils/logging.py -> .)
    project_root = Path(__file__).parent.parent.parent
    logs_dir = project_root / 'logs'
    
    # Create logs directory if it doesn't exist
    logs_dir.mkdir(exist_ok=True)
    
    return logs_dir


def setup_logging(
    level: int = logging.ERROR,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
    enable_file_logging: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Args:
        level: Logging level (default: ERROR for production)
        log_file: Optional specific file path to write logs (if None, creates timestamped log)
        format_string: Custom format string for log messages
        enable_file_logging: Whether to enable file logging (default: True)
        max_bytes: Maximum size of log file before rotation (default: 10 MB)
        backup_count: Number of backup log files to keep (default: 5)
        
    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler - always enabled
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation (optional)
    if enable_file_logging:
        logs_dir = get_logs_directory()
        
        if log_file is None:
            # Create timestamped log file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = logs_dir / f'cv_studio_{timestamp}.log'
        else:
            # Use provided log file path
            log_file = Path(log_file)
            if not log_file.is_absolute():
                log_file = logs_dir / log_file
        
        # Ensure parent directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use RotatingFileHandler for automatic log rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # Log the log file location
        root_logger.info(f"Logging to file: {log_file}")
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def cleanup_old_logs(max_age_days: int = 30):
    """
    Clean up old log files.
    
    Args:
        max_age_days: Maximum age of log files to keep (default: 30 days)
    """
    import time
    
    logs_dir = get_logs_directory()
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    deleted_count = 0
    for log_file in logs_dir.glob('*.log*'):
        if log_file.is_file():
            file_age = current_time - log_file.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger = get_logger(__name__)
                    logger.warning(f"Failed to delete old log file {log_file}: {e}")
    
    if deleted_count > 0:
        logger = get_logger(__name__)
        logger.info(f"Cleaned up {deleted_count} old log files")
