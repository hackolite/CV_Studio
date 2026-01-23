#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller hook for pytz package

This hook ensures that pytz timezone data files are included in the build.
Without this, pytz will fail at runtime with import errors.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all pytz data files (timezone database)
datas = collect_data_files('pytz')

# Collect all pytz submodules
hiddenimports = collect_submodules('pytz')
