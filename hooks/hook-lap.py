#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyInstaller hook for lap package

The lap (Linear Assignment Problem) package contains compiled C extensions
that need special handling for PyInstaller. This hook ensures the
binary extensions are properly included.
"""

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules, collect_data_files

# Collect all dynamic libraries (compiled C extensions)
binaries = collect_dynamic_libs('lap')

# Collect all submodules
hiddenimports = collect_submodules('lap')

# Collect any data files
datas = collect_data_files('lap')
