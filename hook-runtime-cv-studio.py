#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Runtime hook for CV_Studio PyInstaller build

This hook ensures that the application directories are properly added to
sys.path at runtime, allowing proper module imports from the _internal directory.
"""

import sys
import os

# Get the directory where the executable is located
if getattr(sys, 'frozen', False):
    # Running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    
    # Add the bundle directory to sys.path if not already there
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
    
    # Ensure that node, node_editor, and src directories are accessible
    for subdir in ['node', 'node_editor', 'src']:
        subdir_path = os.path.join(bundle_dir, subdir)
        if os.path.exists(subdir_path) and subdir_path not in sys.path:
            sys.path.insert(0, subdir_path)
