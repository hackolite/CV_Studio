#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Launch script for CV_Studio from root directory

This script launches CV_Studio from the internal directory structure.
It's useful for development and testing before building the .exe.
"""
import sys
import os

# Add internal directory to Python path
internal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'internal')
if internal_dir not in sys.path:
    sys.path.insert(0, internal_dir)

# Change to internal directory so relative paths work correctly
os.chdir(internal_dir)

# Import and run main
if __name__ == "__main__":
    from main import main
    main()
