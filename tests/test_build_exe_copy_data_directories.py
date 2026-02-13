#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for build_exe.py copy_data_directories functionality.

This test validates that the copy_data_directories function correctly
handles copying node and node_editor directories from _internal to
the dist root, supporting both PyInstaller 6.x and older behaviors.
"""

import sys
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_exe import copy_data_directories


def get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestCopyDataDirectories:
    """Tests for copy_data_directories function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Store original directory
        self.original_dir = os.getcwd()
        
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)
        
    def teardown_method(self):
        """Clean up test fixtures."""
        os.chdir(self.original_dir)
        shutil.rmtree(self.temp_dir)
    
    def create_pyinstaller_6x_structure(self):
        """Create PyInstaller 6.x structure with directories in _internal."""
        dist_dir = os.path.join(self.temp_dir, 'dist', 'CV_Studio')
        internal_dir = os.path.join(dist_dir, '_internal')
        
        # Create structure
        os.makedirs(internal_dir)
        os.makedirs(os.path.join(internal_dir, 'node'))
        os.makedirs(os.path.join(internal_dir, 'node_editor'))
        
        # Create dummy files
        with open(os.path.join(internal_dir, 'node', '__init__.py'), 'w') as f:
            f.write('# node package')
        with open(os.path.join(internal_dir, 'node_editor', '__init__.py'), 'w') as f:
            f.write('# node_editor package')
            
        return dist_dir
    
    def create_older_pyinstaller_structure(self):
        """Create older PyInstaller structure with directories at dist root."""
        dist_dir = os.path.join(self.temp_dir, 'dist', 'CV_Studio')
        
        # Create structure (no _internal, directories at root)
        os.makedirs(dist_dir)
        os.makedirs(os.path.join(dist_dir, 'node'))
        os.makedirs(os.path.join(dist_dir, 'node_editor'))
        
        # Create dummy files
        with open(os.path.join(dist_dir, 'node', '__init__.py'), 'w') as f:
            f.write('# node package')
        with open(os.path.join(dist_dir, 'node_editor', '__init__.py'), 'w') as f:
            f.write('# node_editor package')
            
        return dist_dir
    
    def test_copy_from_internal_pyinstaller_6x(self):
        """Test copying directories from _internal (PyInstaller 6.x behavior)."""
        dist_dir = self.create_pyinstaller_6x_structure()
        
        # Verify initial state: dirs exist in _internal but not at root
        assert os.path.exists(os.path.join(dist_dir, '_internal', 'node'))
        assert os.path.exists(os.path.join(dist_dir, '_internal', 'node_editor'))
        assert not os.path.exists(os.path.join(dist_dir, 'node'))
        assert not os.path.exists(os.path.join(dist_dir, 'node_editor'))
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify directories were copied to root
        assert os.path.exists(os.path.join(dist_dir, 'node'))
        assert os.path.exists(os.path.join(dist_dir, 'node_editor'))
        
        # Verify files exist in copied directories
        assert os.path.exists(os.path.join(dist_dir, 'node', '__init__.py'))
        assert os.path.exists(os.path.join(dist_dir, 'node_editor', '__init__.py'))
    
    def test_directories_already_at_root(self):
        """Test when directories already exist at dist root (older PyInstaller)."""
        dist_dir = self.create_older_pyinstaller_structure()
        
        # Verify initial state: dirs exist at root
        assert os.path.exists(os.path.join(dist_dir, 'node'))
        assert os.path.exists(os.path.join(dist_dir, 'node_editor'))
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify directories still exist
        assert os.path.exists(os.path.join(dist_dir, 'node'))
        assert os.path.exists(os.path.join(dist_dir, 'node_editor'))
    
    def test_missing_directories_fails(self):
        """Test that function fails when directories are missing."""
        dist_dir = os.path.join(self.temp_dir, 'dist', 'CV_Studio')
        os.makedirs(dist_dir)
        
        # Run function without creating the required directories
        result = copy_data_directories()
        
        # Should fail because directories don't exist
        assert result is False
    
    def test_overwrites_existing_root_directories(self):
        """Test that existing root directories are replaced with _internal copies."""
        dist_dir = self.create_pyinstaller_6x_structure()
        
        # Also create directories at root with different content
        os.makedirs(os.path.join(dist_dir, 'node'))
        os.makedirs(os.path.join(dist_dir, 'node_editor'))
        with open(os.path.join(dist_dir, 'node', 'old_file.py'), 'w') as f:
            f.write('# old file')
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify old file is gone (directory was replaced)
        assert not os.path.exists(os.path.join(dist_dir, 'node', 'old_file.py'))
        
        # Verify new file exists
        assert os.path.exists(os.path.join(dist_dir, 'node', '__init__.py'))


def test_copy_data_directories_function_exists():
    """Test that copy_data_directories function exists in build_exe.py."""
    from build_exe import copy_data_directories
    assert callable(copy_data_directories)


def test_build_exe_step_numbering():
    """Test that build_exe.py has correct 6-step numbering."""
    build_exe_path = os.path.join(get_project_root(), 'build_exe.py')
    
    with open(build_exe_path, 'r') as f:
        content = f.read()
    
    # Check for 6-step numbering
    assert '[1/6]' in content, "Step 1 should be numbered out of 6"
    assert '[2/6]' in content, "Step 2 should be numbered out of 6"
    assert '[3/6]' in content, "Step 3 should be numbered out of 6"
    assert '[4/6]' in content, "Step 4 should be numbered out of 6"
    assert '[5/6]' in content, "Step 5 should be numbered out of 6"
    assert '[6/6]' in content, "Step 6 should be numbered out of 6"


def test_build_exe_calls_copy_data_directories():
    """Test that main() in build_exe.py calls copy_data_directories."""
    build_exe_path = os.path.join(get_project_root(), 'build_exe.py')
    
    with open(build_exe_path, 'r') as f:
        content = f.read()
    
    # Check that copy_data_directories is called
    assert 'copy_data_directories()' in content, \
        "build_exe.py main() should call copy_data_directories()"
    
    # Check that failure is handled
    assert 'if not copy_data_directories():' in content, \
        "build_exe.py should check return value of copy_data_directories()"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
