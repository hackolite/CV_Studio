#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for build.py to ensure it properly uses CV_Studio.spec with hidden imports.

This test validates that build.py correctly references CV_Studio.spec and that
the spec file includes necessary hidden imports like cv2, onnxruntime, etc.
"""

import sys
import os
import pytest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_project_root():
    """Get the project root directory (parent of tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_cv_studio_spec_exists():
    """Test that CV_Studio.spec file exists in the project root."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    assert os.path.exists(spec_file), "CV_Studio.spec file must exist"


def test_cv_studio_spec_has_cv2_hidden_import():
    """Test that CV_Studio.spec includes cv2 as a hidden import."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    # Check for cv2 in hidden imports
    assert 'cv2' in content, "CV_Studio.spec must include cv2"
    
    # Check that collect_submodules is used for cv2
    assert "collect_submodules('cv2')" in content or 'collect_submodules("cv2")' in content, \
        "CV_Studio.spec should use collect_submodules('cv2') to include all cv2 modules"


def test_cv_studio_spec_has_critical_hidden_imports():
    """Test that CV_Studio.spec includes all critical hidden imports."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    critical_imports = [
        'cv2',              # OpenCV - the main issue being fixed
        'onnxruntime',      # For ONNX model inference
        'numpy',            # NumPy arrays
        'dearpygui',        # GUI framework
        'mediapipe',        # Media processing
    ]
    
    missing_imports = []
    for import_name in critical_imports:
        if import_name not in content:
            missing_imports.append(import_name)
    
    if missing_imports:
        pytest.fail(
            f"CV_Studio.spec is missing critical imports: {', '.join(missing_imports)}"
        )


def test_cv_studio_spec_has_runtime_hook():
    """Test that CV_Studio.spec includes the runtime hook."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    assert 'hook-runtime-cv-studio.py' in content, \
        "CV_Studio.spec must include hook-runtime-cv-studio.py for proper path management"


def test_runtime_hook_exists():
    """Test that the runtime hook file exists."""
    hook_file = os.path.join(get_project_root(), 'hook-runtime-cv-studio.py')
    assert os.path.exists(hook_file), "hook-runtime-cv-studio.py must exist"


def test_cv_studio_spec_includes_data_files():
    """Test that CV_Studio.spec includes necessary data files."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    # Check for data files configuration
    assert 'datas' in content, "CV_Studio.spec must define datas list"
    
    # Check for key directories
    critical_data_dirs = [
        'node',         # Node implementations and ONNX models
        'node_editor',  # Node editor core
        'src',          # Source utilities
    ]
    
    for dir_name in critical_data_dirs:
        # Check if directory is referenced in datas
        assert f"'{dir_name}'" in content or f'"{dir_name}"' in content, \
            f"CV_Studio.spec must include '{dir_name}' directory in datas"


def test_build_py_references_spec_file():
    """Test that build.py uses CV_Studio.spec."""
    build_py = os.path.join(get_project_root(), 'build.py')
    
    with open(build_py, 'r') as f:
        content = f.read()
    
    # Check that build.py references CV_Studio.spec
    assert 'CV_Studio.spec' in content, \
        "build.py must reference CV_Studio.spec file"
    
    # Check that the build_executable function uses the spec file
    assert 'spec_file = os.path.join(base_dir, ' in content, \
        "build.py should define spec_file variable"
    
    # Check that PyInstaller is invoked with the spec file
    assert 'PyInstaller' in content and 'spec_file' in content, \
        "build.py should pass spec_file to PyInstaller"


def test_collect_submodules_imported_in_spec():
    """Test that CV_Studio.spec imports collect_submodules for proper module collection."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    assert 'collect_submodules' in content, \
        "CV_Studio.spec must import and use collect_submodules"
    
    assert 'from PyInstaller.utils.hooks import' in content, \
        "CV_Studio.spec must import collect_submodules from PyInstaller.utils.hooks"


def test_cv_studio_spec_has_analysis_section():
    """Test that CV_Studio.spec has proper Analysis section."""
    spec_file = os.path.join(get_project_root(), 'CV_Studio.spec')
    
    with open(spec_file, 'r') as f:
        content = f.read()
    
    # Check for Analysis configuration
    assert 'Analysis' in content, "CV_Studio.spec must have Analysis section"
    assert 'hiddenimports=hiddenimports' in content, \
        "CV_Studio.spec must pass hiddenimports to Analysis"


def test_both_build_scripts_exist():
    """Test that both build.py and build_exe.py exist."""
    root = get_project_root()
    
    build_py = os.path.join(root, 'build.py')
    build_exe_py = os.path.join(root, 'build_exe.py')
    
    assert os.path.exists(build_py), "build.py must exist"
    assert os.path.exists(build_exe_py), "build_exe.py must exist"


def test_build_scripts_comparison_doc_exists():
    """Test that documentation explaining the difference between scripts exists."""
    root = get_project_root()
    
    # Check for any documentation that explains the build scripts
    comparison_doc = os.path.join(root, 'BUILD_SCRIPTS_COMPARISON.md')
    
    assert os.path.exists(comparison_doc), \
        "BUILD_SCRIPTS_COMPARISON.md should exist to explain the difference between build scripts"


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
