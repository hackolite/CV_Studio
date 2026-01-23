#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyInstaller hook for PIL/Pillow package

This hook ensures that PIL.ImageGrab and all PIL dependencies are properly
included, especially on Windows where ImageGrab requires additional handling.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all PIL submodules, including ImageGrab
hiddenimports = collect_submodules('PIL')

# Ensure ImageGrab is explicitly included
if 'PIL.ImageGrab' not in hiddenimports:
    hiddenimports.append('PIL.ImageGrab')

# Collect PIL data files
datas = collect_data_files('PIL')
