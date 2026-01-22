#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dependency Verification Script for CV_Studio Build

This script verifies that all Python imports in the codebase have corresponding
packages in requirements.txt and are properly configured in the build system.

Usage:
    python verify_dependencies.py
"""

import ast
import os
import re
import sys
from collections import defaultdict


# Mapping of Python import names to pip package names
IMPORT_TO_PACKAGE = {
    # Core dependencies
    'numpy': 'numpy',
    'cv2': 'opencv-contrib-python',
    'onnxruntime': 'onnxruntime-gpu',
    'dearpygui': 'dearpygui',
    'dpg': 'dearpygui',
    'mediapipe': 'mediapipe',
    'google': 'mediapipe',
    'protobuf': 'protobuf',
    
    # Computer vision and ML
    'filterpy': 'filterpy',
    'lap': 'lap',
    'motpy': 'motpy',
    'norfair': 'norfair',
    'scipy': 'scipy',
    'sklearn': 'scikit-learn',
    
    # Media processing
    'pafy': 'pafy',
    'ffmpeg': 'ffmpeg-python',
    'librosa': 'librosa',
    'matplotlib': 'matplotlib',
    'soundfile': 'soundfile',
    'sounddevice': 'sounddevice',
    'PIL': 'Pillow',
    
    # Serial and network
    'serial': 'pyserial',  # CRITICAL: pyserial package provides 'serial' module
    'pymongo': 'pymongo',
    'bson': 'pymongo',
    'dnspython': 'dnspython',
    'requests': 'requests',
    
    # Utilities
    'rich': 'rich',
    'pytz': 'pytz',
    'youtube_dl': 'youtube-dl',
    'yt_dlp': 'yt-dlp',
    'pytest': 'pytest',
    
    # Optional dependencies (wrapped in try-except in code)
    'tensorflow': 'tensorflow (optional)',
    'tflite_runtime': 'tflite-runtime (optional)',
    'aiohttp': 'aiohttp (optional - tests only)',
    'aiortc': 'aiortc (optional - tests only)',
    'av': 'av (optional - tests only)',
    'websockets': 'websockets (optional - tests only)',
    'pandas': 'pandas (optional)',
    'motmetrics': 'motmetrics (optional)',
    
    # Build tools
    'PyInstaller': 'pyinstaller',
}


def extract_imports_from_codebase(exclude_dirs=None):
    """Extract all imports from Python files in the codebase"""
    if exclude_dirs is None:
        exclude_dirs = ['.git', '__pycache__', 'dist', 'build', '.pytest_cache']
    
    imports = defaultdict(set)
    
    for root, dirs, files in os.walk('.'):
        # Skip excluded directories
        if any(skip in root for skip in exclude_dirs):
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        tree = ast.parse(f.read(), filename=filepath)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                module = alias.name.split('.')[0]
                                imports[module].add(filepath)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                module = node.module.split('.')[0]
                                imports[module].add(filepath)
                except:
                    pass
    
    return imports


def read_requirements():
    """Read packages from requirements.txt and requirements-build.txt"""
    packages = set()
    
    for req_file in ['requirements.txt', 'requirements-build.txt']:
        if not os.path.exists(req_file):
            continue
            
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (before >= or ==)
                    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if match:
                        packages.add(match.group(1).lower())
    
    return packages


def verify_build_exe_config():
    """Verify build_exe.py has all required packages in its check"""
    with open('build_exe.py', 'r') as f:
        content = f.read()
    
    # Extract required_packages dictionary
    match = re.search(r'required_packages = \{([^}]+)\}', content, re.DOTALL)
    if not match:
        return False, "Could not find required_packages in build_exe.py"
    
    # Extract package names from the dictionary
    packages = re.findall(r"'([^']+)':\s*'[^']+',?", match.group(1))
    
    return True, set(packages)


def main():
    print("=" * 70)
    print("CV_Studio Dependency Verification")
    print("=" * 70)
    print()
    
    # Extract imports
    print("[1/4] Extracting imports from codebase...")
    imports = extract_imports_from_codebase()
    
    # Categorize imports
    third_party = []
    unmapped = []
    optional = []
    
    for module in sorted(imports.keys()):
        if module in IMPORT_TO_PACKAGE:
            package = IMPORT_TO_PACKAGE[module]
            if '(optional' in package:
                optional.append((module, package))
            else:
                third_party.append((module, package))
        else:
            # Check if it's a project module
            if module not in ['node', 'node_editor', 'src', 'main', 'build_exe', 'sound']:
                unmapped.append(module)
    
    print(f"  Found {len(imports)} unique import modules")
    print(f"  - {len(third_party)} required third-party packages")
    print(f"  - {len(optional)} optional dependencies")
    print(f"  - {len(unmapped)} unmapped (may be stdlib or local)")
    print()
    
    # Read requirements
    print("[2/4] Checking requirements.txt...")
    req_packages = read_requirements()
    print(f"  Found {len(req_packages)} packages in requirements files")
    
    # Check coverage
    missing = []
    for module, package in third_party:
        pkg_lower = package.lower()
        if pkg_lower not in req_packages:
            missing.append(package)
    
    if missing:
        print(f"  ✗ MISSING {len(missing)} packages:")
        for pkg in missing:
            print(f"      - {pkg}")
    else:
        print(f"  ✓ All required packages are in requirements.txt")
    print()
    
    # Verify build_exe.py
    print("[3/4] Verifying build_exe.py configuration...")
    success, result = verify_build_exe_config()
    if success:
        build_packages = result
        print(f"  Found {len(build_packages)} packages checked in build_exe.py")
        
        # Check for critical packages
        critical = ['pyserial', 'pymongo', 'Pillow', 'dearpygui', 'numpy']
        missing_critical = [p for p in critical if p not in build_packages]
        
        if missing_critical:
            print(f"  ✗ MISSING critical packages: {', '.join(missing_critical)}")
        else:
            print(f"  ✓ All critical packages are checked in build_exe.py")
            print(f"  ✓ Including 'pyserial' for serial module support")
    else:
        print(f"  ✗ {result}")
    print()
    
    # Summary
    print("[4/4] Summary...")
    print()
    print("Third-party packages:")
    for module, package in sorted(third_party):
        status = "✓" if package.lower() in req_packages else "✗"
        print(f"  {status} {module:20s} -> {package}")
    
    if optional:
        print()
        print("Optional dependencies (not required for ONNX builds):")
        for module, package in sorted(optional):
            print(f"  ○ {module:20s} -> {package}")
    
    print()
    print("=" * 70)
    if not missing and success:
        print("✓ VERIFICATION PASSED")
        print("All required dependencies are properly configured!")
        return 0
    else:
        print("✗ VERIFICATION FAILED")
        print("Some dependencies need attention.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
