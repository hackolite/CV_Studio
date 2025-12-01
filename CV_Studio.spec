# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for CV_Studio

This spec file builds a standalone .exe for CV_Studio with:
- All nodes (Input, Process, DL, Audio, etc.)
- ONNX models for object detection
- DearPyGUI resources
- Fonts and configuration files
- All required Python dependencies

Usage:
    pyinstaller CV_Studio.spec

The .exe will be created in the 'dist/CV_Studio' directory.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the base directory
block_cipher = None
base_path = os.path.abspath('.')

# Collect all submodules for key packages
hiddenimports = []
hiddenimports += collect_submodules('dearpygui')
hiddenimports += collect_submodules('cv2')
hiddenimports += collect_submodules('onnxruntime')
hiddenimports += collect_submodules('mediapipe')
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('librosa')
hiddenimports += collect_submodules('soundfile')
hiddenimports += collect_submodules('matplotlib')

# Add explicit hidden imports for node modules
hiddenimports += [
    'node',
    'node.InputNode',
    'node.ProcessNode',
    'node.DLNode',
    'node.AudioProcessNode',
    'node.AudioModelNode',
    'node.StatsNode',
    'node.TimeseriesNode',
    'node.TriggerNode',
    'node.RouterNode',
    'node.ActionNode',
    'node.OverlayNode',
    'node.TrackerNode',
    'node.VisualNode',
    'node.VideoNode',
    'node.timestamped_queue',
    'node.queue_adapter',
    'node.basenode',
    'node_editor',
    'node_editor.node_editor',
    'node_editor.util',
    'node_editor.style',
    'src',
    'src.utils',
    'src.utils.logging',
    'src.utils.gpu_utils',
    'src.core',
]

# Collect data files
datas = []

# Add node directory with all subdirectories and files
datas.append(('node', 'node'))

# Add node_editor directory
datas.append(('node_editor', 'node_editor'))

# Add src directory
datas.append(('src', 'src'))

# Add specific ONNX models (recursive include)
# This ensures all .onnx files in the DLNode directories are included
for root, dirs, files in os.walk('node/DLNode'):
    for file in files:
        if file.endswith('.onnx'):
            src_path = os.path.join(root, file)
            dest_path = os.path.dirname(root)
            datas.append((src_path, dest_path))

# Add fonts
datas.append(('node_editor/font', 'node_editor/font'))

# Add setting files
datas.append(('node_editor/setting', 'node_editor/setting'))

# Collect data files from packages that need them
datas += collect_data_files('dearpygui')
datas += collect_data_files('mediapipe')
datas += collect_data_files('onnxruntime')

# Binary excludes - exclude unnecessary binaries
binaries = []

a = Analysis(
    ['main.py'],
    pathex=[base_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PyQt5',
        'PySide2',
        'PySide6',
        'wx',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pytest',
        'unittest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CV_Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon='icon.ico' if you have an icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CV_Studio',
)
