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
import ast
import re
import pytest
import shutil
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_exe import copy_data_directories


def get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def temp_build_dir(tmp_path, monkeypatch):
    """Fixture providing a temporary build directory for testing."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestCopyDataDirectories:
    """Tests for copy_data_directories function."""
    
    def create_pyinstaller_6x_structure(self, temp_dir):
        """Create PyInstaller 6.x structure with directories in _internal."""
        dist_dir = temp_dir / 'dist' / 'CV_Studio'
        internal_dir = dist_dir / '_internal'
        
        # Create structure
        internal_dir.mkdir(parents=True)
        (internal_dir / 'node').mkdir()
        (internal_dir / 'node_editor').mkdir()
        
        # Create dummy files
        (internal_dir / 'node' / '__init__.py').write_text('# node package')
        (internal_dir / 'node_editor' / '__init__.py').write_text('# node_editor package')
            
        return dist_dir
    
    def create_older_pyinstaller_structure(self, temp_dir):
        """Create older PyInstaller structure with directories at dist root."""
        dist_dir = temp_dir / 'dist' / 'CV_Studio'
        
        # Create structure (no _internal, directories at root)
        dist_dir.mkdir(parents=True)
        (dist_dir / 'node').mkdir()
        (dist_dir / 'node_editor').mkdir()
        
        # Create dummy files
        (dist_dir / 'node' / '__init__.py').write_text('# node package')
        (dist_dir / 'node_editor' / '__init__.py').write_text('# node_editor package')
            
        return dist_dir
    
    def test_copy_from_internal_pyinstaller_6x(self, temp_build_dir):
        """Test copying directories from _internal (PyInstaller 6.x behavior)."""
        dist_dir = self.create_pyinstaller_6x_structure(temp_build_dir)
        
        # Verify initial state: dirs exist in _internal but not at root
        assert (dist_dir / '_internal' / 'node').exists()
        assert (dist_dir / '_internal' / 'node_editor').exists()
        assert not (dist_dir / 'node').exists()
        assert not (dist_dir / 'node_editor').exists()
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify directories were copied to root
        assert (dist_dir / 'node').exists()
        assert (dist_dir / 'node_editor').exists()
        
        # Verify files exist in copied directories
        assert (dist_dir / 'node' / '__init__.py').exists()
        assert (dist_dir / 'node_editor' / '__init__.py').exists()
    
    def test_directories_already_at_root(self, temp_build_dir):
        """Test when directories already exist at dist root (older PyInstaller)."""
        dist_dir = self.create_older_pyinstaller_structure(temp_build_dir)
        
        # Verify initial state: dirs exist at root
        assert (dist_dir / 'node').exists()
        assert (dist_dir / 'node_editor').exists()
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify directories still exist
        assert (dist_dir / 'node').exists()
        assert (dist_dir / 'node_editor').exists()
    
    def test_missing_directories_fails(self, temp_build_dir):
        """Test that function fails when directories are missing."""
        dist_dir = temp_build_dir / 'dist' / 'CV_Studio'
        dist_dir.mkdir(parents=True)
        
        # Run function without creating the required directories
        result = copy_data_directories()
        
        # Should fail because directories don't exist
        assert result is False
    
    def test_overwrites_existing_root_directories(self, temp_build_dir):
        """Test that existing root directories are replaced with _internal copies."""
        dist_dir = self.create_pyinstaller_6x_structure(temp_build_dir)
        
        # Also create directories at root with different content
        (dist_dir / 'node').mkdir()
        (dist_dir / 'node_editor').mkdir()
        (dist_dir / 'node' / 'old_file.py').write_text('# old file')
        
        # Run function
        result = copy_data_directories()
        
        # Verify result
        assert result is True
        
        # Verify old file is gone (directory was replaced)
        assert not (dist_dir / 'node' / 'old_file.py').exists()
        
        # Verify new file exists
        assert (dist_dir / 'node' / '__init__.py').exists()


def test_copy_data_directories_function_exists():
    """Test that copy_data_directories function exists in build_exe.py."""
    from build_exe import copy_data_directories
    assert callable(copy_data_directories)


def test_build_exe_step_numbering():
    """Test that build_exe.py has consistent step numbering pattern.
    
    Verifies that all steps follow the pattern [n/N] where N is the total
    number of steps and n ranges from 1 to N.
    """
    build_exe_path = os.path.join(get_project_root(), 'build_exe.py')
    
    with open(build_exe_path, 'r') as f:
        content = f.read()
    
    # Find all step patterns [n/N] and extract the total number
    step_pattern = re.compile(r'\[(\d+)/(\d+)\]')
    matches = step_pattern.findall(content)
    
    assert len(matches) > 0, "build_exe.py should contain step numbers"
    
    # Get the total steps from the first match
    total_steps = int(matches[0][1])
    
    # Verify all step numbers are consistent and sequential
    step_numbers = set()
    for step_num, total in matches:
        assert int(total) == total_steps, \
            f"All steps should have same total ({total_steps}), but found {total}"
        step_numbers.add(int(step_num))
    
    # Verify we have all steps from 1 to total_steps
    expected_steps = set(range(1, total_steps + 1))
    assert step_numbers == expected_steps, \
        f"Expected steps {expected_steps}, but found {step_numbers}"


def test_build_exe_calls_copy_data_directories():
    """Test that build_exe.py calls copy_data_directories using AST parsing.
    
    Uses AST parsing to verify the actual function call exists in code,
    not just in comments.
    """
    build_exe_path = os.path.join(get_project_root(), 'build_exe.py')
    
    with open(build_exe_path, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Find all function calls in the AST
    function_calls = set()
    
    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name):
                function_calls.add(node.func.id)
            self.generic_visit(node)
    
    CallVisitor().visit(tree)
    
    assert 'copy_data_directories' in function_calls, \
        "build_exe.py should call copy_data_directories()"


def test_build_exe_handles_copy_failure():
    """Test that build_exe.py handles copy_data_directories failure.
    
    Verifies that the return value is checked using AST parsing.
    """
    build_exe_path = os.path.join(get_project_root(), 'build_exe.py')
    
    with open(build_exe_path, 'r') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Look for 'if not copy_data_directories()' pattern
    class NotCallVisitor(ast.NodeVisitor):
        def __init__(self):
            self.found_check = False
        
        def visit_If(self, node):
            # Check for 'if not func()' pattern
            if isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not):
                if isinstance(node.test.operand, ast.Call):
                    if isinstance(node.test.operand.func, ast.Name):
                        if node.test.operand.func.id == 'copy_data_directories':
                            self.found_check = True
            self.generic_visit(node)
    
    visitor = NotCallVisitor()
    visitor.visit(tree)
    
    assert visitor.found_check, \
        "build_exe.py should check return value of copy_data_directories()"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
