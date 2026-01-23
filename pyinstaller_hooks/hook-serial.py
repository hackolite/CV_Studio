# PyInstaller hook for pyserial
# This ensures all serial (pyserial) modules are properly included in the build

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules from serial package
hiddenimports = collect_submodules('serial')

# Collect any data files (if needed)
datas = collect_data_files('serial')
