#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Environment configuration utilities for secure API key management.

This module provides utilities for loading and managing environment variables
from .env files, with a focus on security best practices.
"""

import os
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[Path] = None) -> bool:
    """
    Load environment variables from .env file.
    
    Args:
        env_path: Optional path to .env file. If None, searches for .env in project root.
        
    Returns:
        bool: True if .env file was loaded successfully, False otherwise.
        
    Example:
        >>> load_env_file()
        True
        >>> api_key = get_env_variable('AIS_STREAM_API_KEY')
    """
    try:
        from dotenv import load_dotenv
        
        if env_path is None:
            # Default: look for .env in project root
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            env_path = project_root / '.env'
        
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            return True
        else:
            # .env file doesn't exist, but that's okay - env vars might be set another way
            return False
            
    except ImportError:
        # python-dotenv not installed, but that's okay - env vars might be set another way
        return False
    except Exception as e:
        print(f"Warning: Error loading .env file: {e}")
        return False


def get_env_variable(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable value.
    
    Args:
        key: Environment variable name
        default: Default value if variable is not set
        
    Returns:
        str or None: Environment variable value or default
        
    Example:
        >>> api_key = get_env_variable('AIS_STREAM_API_KEY', 'default_key')
        >>> url = get_env_variable('AIS_STREAM_URL', 'wss://stream.aisstream.io/v0/stream')
    """
    return os.getenv(key, default)


def get_ais_config() -> dict:
    """
    Get AIS stream configuration from environment variables.
    
    Returns:
        dict: Configuration dictionary with keys:
            - api_key: AIS stream API key
            - url: WebSocket URL
            - bounding_box: Default bounding box (as string, needs JSON parsing)
            
    Example:
        >>> config = get_ais_config()
        >>> api_key = config['api_key']
        >>> url = config['url']
    """
    # Try to load .env file if not already loaded
    load_env_file()
    
    return {
        'api_key': get_env_variable('AIS_STREAM_API_KEY'),
        'url': get_env_variable('AIS_STREAM_URL', 'wss://stream.aisstream.io/v0/stream'),
        'bounding_box': get_env_variable('AIS_STREAM_BOUNDING_BOX'),
    }


def is_api_key_configured() -> bool:
    """
    Check if AIS stream API key is configured.
    
    Returns:
        bool: True if API key is set, False otherwise
        
    Example:
        >>> if not is_api_key_configured():
        ...     print("Please set AIS_STREAM_API_KEY environment variable")
    """
    load_env_file()
    api_key = get_env_variable('AIS_STREAM_API_KEY')
    return api_key is not None and api_key != ''
