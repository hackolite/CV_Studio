#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for Settings"""

import pytest
import json
import tempfile
import os
from src.core.config.settings import Settings
from src.utils.exceptions import NodeConfigurationError


def test_settings_default():
    """Test settings with default values"""
    settings = Settings()
    assert settings.get('webcam_width') == 640
    assert settings.get('webcam_height') == 480
    assert settings.get('use_gpu') == False


def test_settings_get():
    """Test getting settings"""
    settings = Settings()
    width = settings.get('webcam_width')
    assert width == 640
    
    # Test with default
    value = settings.get('nonexistent', 'default')
    assert value == 'default'


def test_settings_set():
    """Test setting values"""
    settings = Settings()
    settings.set('webcam_width', 1920)
    assert settings.get('webcam_width') == 1920


def test_settings_update():
    """Test updating multiple settings"""
    settings = Settings()
    updates = {
        'webcam_width': 1920,
        'webcam_height': 1080,
        'use_gpu': True
    }
    settings.update(updates)
    
    assert settings.get('webcam_width') == 1920
    assert settings.get('webcam_height') == 1080
    assert settings.get('use_gpu') == True


def test_settings_get_all():
    """Test getting all settings"""
    settings = Settings()
    all_settings = settings.get_all()
    
    assert 'webcam_width' in all_settings
    assert 'webcam_height' in all_settings
    assert isinstance(all_settings, dict)


def test_settings_save_and_load():
    """Test saving and loading settings from file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        config_file = f.name
    
    try:
        # Create settings and save
        settings1 = Settings()
        settings1.set('webcam_width', 1920)
        settings1.set('use_gpu', True)
        settings1.save_to_file(config_file)
        
        # Load into new settings instance
        settings2 = Settings(config_file)
        assert settings2.get('webcam_width') == 1920
        assert settings2.get('use_gpu') == True
    finally:
        if os.path.exists(config_file):
            os.remove(config_file)


def test_settings_load_nonexistent_file():
    """Test loading from non-existent file"""
    settings = Settings('/path/to/nonexistent/file.json')
    # Should use defaults
    assert settings.get('webcam_width') == 640


def test_settings_reset_to_defaults():
    """Test resetting to default values"""
    settings = Settings()
    settings.set('webcam_width', 1920)
    settings.set('use_gpu', True)
    
    settings.reset_to_defaults()
    
    assert settings.get('webcam_width') == 640
    assert settings.get('use_gpu') == False


def test_settings_save_creates_directory():
    """Test that save creates the directory if it doesn't exist"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_file = os.path.join(temp_dir, 'subdir', 'config.json')
        
        settings = Settings()
        settings.save_to_file(config_file)
        
        assert os.path.exists(config_file)


def test_settings_invalid_json():
    """Test loading invalid JSON file"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        f.write("invalid json {")
        config_file = f.name
    
    try:
        with pytest.raises(NodeConfigurationError):
            Settings(config_file)
    finally:
        os.remove(config_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
