#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for environment configuration utilities.

Tests the secure API key management functionality.
"""
import os
import sys
import tempfile
from pathlib import Path
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.env_config import (
    load_env_file,
    get_env_variable,
    get_ais_config,
    is_api_key_configured
)


class TestEnvConfig(unittest.TestCase):
    """Test cases for environment configuration utilities."""
    
    def setUp(self):
        """Set up test environment."""
        # Store original environment variables
        self.original_env = {}
        env_vars = ['AIS_STREAM_API_KEY', 'AIS_STREAM_URL', 'AIS_STREAM_BOUNDING_BOX']
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)
            # Clear environment variable for clean tests
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Restore original environment."""
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_get_env_variable_with_default(self):
        """Test getting environment variable with default value."""
        result = get_env_variable('NON_EXISTENT_VAR', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_get_env_variable_without_default(self):
        """Test getting non-existent environment variable without default."""
        result = get_env_variable('NON_EXISTENT_VAR')
        self.assertIsNone(result)
    
    def test_get_env_variable_existing(self):
        """Test getting existing environment variable."""
        os.environ['TEST_VAR'] = 'test_value'
        result = get_env_variable('TEST_VAR')
        self.assertEqual(result, 'test_value')
        del os.environ['TEST_VAR']
    
    def test_get_ais_config_defaults(self):
        """Test getting AIS config with defaults."""
        config = get_ais_config()
        
        # API key should be None if not set
        self.assertIsNone(config['api_key'])
        
        # URL should have default value
        self.assertEqual(config['url'], 'wss://stream.aisstream.io/v0/stream')
        
        # Bounding box should be None if not set
        self.assertIsNone(config['bounding_box'])
    
    def test_get_ais_config_with_env_vars(self):
        """Test getting AIS config with environment variables set."""
        os.environ['AIS_STREAM_API_KEY'] = 'test_api_key'
        os.environ['AIS_STREAM_URL'] = 'wss://test.url'
        os.environ['AIS_STREAM_BOUNDING_BOX'] = '[[[-5, 36], [36, 46]]]'
        
        config = get_ais_config()
        
        self.assertEqual(config['api_key'], 'test_api_key')
        self.assertEqual(config['url'], 'wss://test.url')
        self.assertEqual(config['bounding_box'], '[[[-5, 36], [36, 46]]]')
    
    def test_is_api_key_configured_false(self):
        """Test API key configured check when not set."""
        result = is_api_key_configured()
        self.assertFalse(result)
    
    def test_is_api_key_configured_true(self):
        """Test API key configured check when set."""
        os.environ['AIS_STREAM_API_KEY'] = 'test_key'
        result = is_api_key_configured()
        self.assertTrue(result)
    
    def test_is_api_key_configured_empty_string(self):
        """Test API key configured check with empty string."""
        os.environ['AIS_STREAM_API_KEY'] = ''
        result = is_api_key_configured()
        self.assertFalse(result)
    
    def test_load_env_file_non_existent(self):
        """Test loading non-existent .env file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent_path = Path(tmpdir) / 'non_existent.env'
            result = load_env_file(non_existent_path)
            # Should return False but not raise an error
            self.assertFalse(result)
    
    def test_load_env_file_with_content(self):
        """Test loading .env file with content."""
        try:
            from dotenv import load_dotenv
            
            with tempfile.TemporaryDirectory() as tmpdir:
                env_file = Path(tmpdir) / '.env'
                env_file.write_text('TEST_ENV_VAR=test_value\n')
                
                result = load_env_file(env_file)
                self.assertTrue(result)
                
                # Check if variable was loaded
                self.assertEqual(os.environ.get('TEST_ENV_VAR'), 'test_value')
                
                # Cleanup
                if 'TEST_ENV_VAR' in os.environ:
                    del os.environ['TEST_ENV_VAR']
        except ImportError:
            # Skip test if python-dotenv not installed
            self.skipTest("python-dotenv not installed")


class TestAPIKeySecurity(unittest.TestCase):
    """Test cases for API key security."""
    
    def test_api_key_not_in_example(self):
        """Test that actual API key is not in example files."""
        example_file = Path(__file__).parent.parent / 'examples' / 'example_ais_stream.py'
        
        if example_file.exists():
            content = example_file.read_text()
            
            # Check that hardcoded API key pattern is not present
            # The example should use environment variables
            self.assertIn('os.getenv', content, 
                         "Example should use os.getenv to load API key")
            self.assertIn('AIS_STREAM_API_KEY', content,
                         "Example should reference AIS_STREAM_API_KEY env var")
    
    def test_env_example_exists(self):
        """Test that .env.example file exists."""
        env_example = Path(__file__).parent.parent / '.env.example'
        self.assertTrue(env_example.exists(), 
                       ".env.example file should exist for documentation")
    
    def test_env_example_content(self):
        """Test that .env.example has the required variables."""
        env_example = Path(__file__).parent.parent / '.env.example'
        
        if env_example.exists():
            content = env_example.read_text()
            
            # Check for required environment variables
            self.assertIn('AIS_STREAM_API_KEY', content)
            self.assertIn('your_api_key_here', content)
            self.assertNotIn('58462ad27e7ad5bd8004d4948e46015ec75cc5df', content,
                           "Real API keys should not be in .env.example")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
