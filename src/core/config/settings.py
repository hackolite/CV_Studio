#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Centralized configuration management"""

import json
from typing import Dict, Any, Optional
from pathlib import Path

from ...utils.logging import get_logger
from ...utils.exceptions import NodeConfigurationError

logger = get_logger(__name__)


class Settings:
    """
    Centralized settings management for CV Studio
    
    This class handles loading, saving, and accessing application settings.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings
        
        Args:
            config_file: Optional path to configuration file
        """
        self._settings: Dict[str, Any] = self._get_default_settings()
        
        if config_file:
            self.load_from_file(config_file)
    
    @staticmethod
    def _get_default_settings() -> Dict[str, Any]:
        """Get default settings"""
        return {
            'webcam_width': 640,
            'webcam_height': 480,
            'process_width': 320,
            'process_height': 240,
            'editor_width': 1280,
            'editor_height': 720,
            'use_gpu': False,
            'use_pref_counter': False,
            'device_no_list': [],
            'camera_capture_list': [],
            'serial_device_no_list': [],
            'serial_connection_list': [],
            'use_serial': False,
        }
    
    def load_from_file(self, config_file: str):
        """
        Load settings from a JSON file
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.warning(f"Config file not found: {config_file}, using defaults")
            return
        
        try:
            with open(config_path, 'r') as f:
                loaded_settings = json.load(f)
                self._settings.update(loaded_settings)
                logger.info(f"Loaded settings from {config_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_file}: {e}")
            raise NodeConfigurationError("settings", f"Invalid JSON in config file: {e}")
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")
            raise NodeConfigurationError("settings", f"Error loading config: {e}")
    
    def save_to_file(self, config_file: str):
        """
        Save settings to a JSON file
        
        Args:
            config_file: Path to configuration file
        """
        config_path = Path(config_file)
        
        try:
            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Filter out non-serializable objects
            serializable_settings = {
                k: v for k, v in self._settings.items()
                if not isinstance(v, (object,)) or isinstance(v, (str, int, float, bool, list, dict, type(None)))
            }
            
            with open(config_path, 'w') as f:
                json.dump(serializable_settings, f, indent=2)
                logger.info(f"Saved settings to {config_file}")
        except Exception as e:
            logger.error(f"Error saving config file {config_file}: {e}")
            raise NodeConfigurationError("settings", f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set a setting value
        
        Args:
            key: Setting key
            value: Setting value
        """
        self._settings[key] = value
        logger.debug(f"Set setting {key} = {value}")
    
    def update(self, settings: Dict[str, Any]):
        """
        Update multiple settings at once
        
        Args:
            settings: Dictionary of settings to update
        """
        self._settings.update(settings)
        logger.debug(f"Updated {len(settings)} settings")
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings
        
        Returns:
            Dictionary of all settings
        """
        return self._settings.copy()
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self._settings = self._get_default_settings()
        logger.info("Reset settings to defaults")
