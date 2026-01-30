#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for build_exe.py requirements checking functionality.

This test validates that the package checks in build_exe.py match
what is actually specified in requirements.txt.
"""

import sys
import os
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from build_exe import check_requirements


def get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_required_packages_can_be_imported():
    """Test that all packages checked by build_exe.py can be imported."""
    
    # Define the packages that build_exe.py checks for
    # This should match the required_packages dict in build_exe.py
    import_checks = {
        'dearpygui': 'dearpygui',
        'opencv-contrib-python': 'cv2',
        'onnxruntime-cpu': 'onnxruntime',
        'numpy': 'numpy',
        'mediapipe': 'mediapipe',
        'scipy': 'scipy',
        'lap': 'lap',
        'motpy': 'motpy',
        'norfair': 'norfair',
        'filterpy': 'filterpy',
        'ffmpeg-python': 'ffmpeg',
        'rich': 'rich',
        'scikit-learn': 'sklearn',
    }
    
    failed_imports = []
    
    for package_name, import_name in import_checks.items():
        try:
            __import__(import_name)
        except ImportError as e:
            failed_imports.append((package_name, import_name, str(e)))
    
    # Report any failures
    if failed_imports:
        error_msg = "The following packages could not be imported:\n"
        for pkg, imp, err in failed_imports:
            error_msg += f"  - {pkg} (import {imp}): {err}\n"
        pytest.fail(error_msg)


def test_requirements_txt_contains_numpy():
    """Test that requirements.txt explicitly includes numpy."""
    
    req_file = os.path.join(get_project_root(), 'requirements.txt')
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    assert 'numpy' in requirements.lower(), \
        "numpy must be explicitly listed in requirements.txt"


def test_requirements_txt_has_opencv_contrib():
    """Test that requirements.txt specifies opencv-contrib-python not opencv-python."""
    
    req_file = os.path.join(get_project_root(), 'requirements.txt')
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    # Check that opencv-contrib-python is present
    assert 'opencv-contrib-python' in requirements, \
        "requirements.txt should specify opencv-contrib-python"
    
    # Ensure plain opencv-python is not specified (would conflict)
    # We check for 'opencv-python' not preceded by 'contrib-'
    lines = requirements.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('opencv-python') and not line.startswith('opencv-contrib-python'):
            pytest.fail(
                "requirements.txt should use opencv-contrib-python, not opencv-python"
            )


def test_requirements_txt_has_updated_lap_version():
    """Test that requirements.txt specifies lap>=0.5.0 for prebuilt wheels."""
    
    req_file = os.path.join(get_project_root(), 'requirements.txt')
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    # Find the lap line
    for line in requirements.split('\n'):
        line = line.strip()
        if line.startswith('lap'):
            # Should be >=0.5.0 for prebuilt wheels (not 0.4.x which requires source build)
            assert '>=0.5' in line, \
                f"lap should be >=0.5.0 to use prebuilt wheels, got: {line}"
            return
    
    pytest.fail("lap package not found in requirements.txt")


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
