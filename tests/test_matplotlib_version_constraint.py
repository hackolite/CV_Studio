#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test for matplotlib version constraint in requirements.txt.

This test validates that matplotlib has a proper version constraint
to ensure prebuilt wheels are used instead of requiring compilation
from source.

Background:
-----------
Without a version constraint, pip may try to install matplotlib 3.0.3
(an old version from 2018) which:
- Doesn't have prebuilt wheels for Python 3.10+
- Requires building from source
- Needs C dependencies (freetype, libpng) which may not be available

Solution:
---------
Specify matplotlib>=3.5.0 which has prebuilt wheels for all modern
Python versions and doesn't require any C compilation.
"""

import os
import re


def get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_matplotlib_has_version_constraint():
    """Test that matplotlib has a minimum version constraint."""
    
    req_file = os.path.join(get_project_root(), 'requirements.txt')
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    # Find the matplotlib line
    matplotlib_line = None
    for line in requirements.split('\n'):
        line = line.strip()
        if line.startswith('matplotlib'):
            matplotlib_line = line
            break
    
    assert matplotlib_line is not None, \
        "matplotlib must be listed in requirements.txt"
    
    # Check that it has a version constraint
    assert '>=' in matplotlib_line, \
        "matplotlib must have a minimum version constraint (e.g., matplotlib>=3.5.0)"


def test_matplotlib_version_is_modern():
    """Test that matplotlib version constraint is at least 3.5.0."""
    
    req_file = os.path.join(get_project_root(), 'requirements.txt')
    
    with open(req_file, 'r') as f:
        requirements = f.read()
    
    # Find the matplotlib line
    for line in requirements.split('\n'):
        line = line.strip()
        if line.startswith('matplotlib'):
            # Extract version constraint (patch version is optional)
            match = re.search(r'>=(\d+)\.(\d+)(?:\.(\d+))?', line)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                # Patch version is optional, default to 0 if not specified
                patch = int(match.group(3)) if match.group(3) else 0
                
                # Verify version is at least 3.5.0
                assert major >= 3, \
                    f"matplotlib version must be at least 3.x, got {major}.x"
                
                if major == 3:
                    assert minor >= 5, \
                        f"matplotlib 3.x version must be at least 3.5, got 3.{minor}"
                
                return
    
    # If we get here, we didn't find a proper version constraint
    assert False, "matplotlib must have a version constraint like >=3.5.0"


if __name__ == '__main__':
    # Run tests manually
    print("Testing matplotlib version constraint...")
    
    try:
        test_matplotlib_has_version_constraint()
        print("✓ test_matplotlib_has_version_constraint passed")
    except AssertionError as e:
        print(f"✗ test_matplotlib_has_version_constraint failed: {e}")
        exit(1)
    
    try:
        test_matplotlib_version_is_modern()
        print("✓ test_matplotlib_version_is_modern passed")
    except AssertionError as e:
        print(f"✗ test_matplotlib_version_is_modern failed: {e}")
        exit(1)
    
    print("\n✓ All tests passed!")
