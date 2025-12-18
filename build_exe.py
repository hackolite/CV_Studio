#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for CV_Studio executable

This script automates the process of building a standalone .exe for CV_Studio
using PyInstaller. It includes all necessary dependencies, ONNX models, and
node resources.

Usage:
    python build_exe.py [options]

Options:
    --clean         Clean build directories before building
    --onefile       Create a single executable file (slower startup)
    --windowed      Hide console window (GUI only mode)
    --debug         Build with debug information
    --icon ICON     Path to icon file (.ico)
    --help          Show this help message

Examples:
    # Standard build (creates CV_Studio folder with exe and dependencies)
    python build_exe.py

    # Clean build
    python build_exe.py --clean

    # Single file exe (no separate folder, but slower startup)
    python build_exe.py --onefile

    # GUI mode without console window
    python build_exe.py --windowed

    # With custom icon
    python build_exe.py --icon CV_Studio.ico
"""

import os
import sys
import shutil
import subprocess
import argparse


def print_banner():
    """Print build script banner"""
    print("=" * 70)
    print("  CV_Studio - Executable Build Script")
    print("  Building standalone .exe with PyInstaller")
    print("=" * 70)
    print()


def check_requirements():
    """Check if required tools are installed"""
    print("[1/7] Checking requirements...")
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        return False
    
    print(f"  ✓ Python {sys.version.split()[0]}")
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
        print(f"  ✓ PyInstaller installed")
    except ImportError:
        print("  ✗ PyInstaller not found")
        print("\nInstalling PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        print("  ✓ PyInstaller installed")
    
    # Check required packages
    # Map of package names to their import names
    required_packages = {
        'dearpygui': 'dearpygui',
        'opencv-python': 'cv2',
        'onnxruntime-gpu': 'onnxruntime',
        'numpy': 'numpy',
        'mediapipe': 'mediapipe',
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✓ {package_name}")
        except ImportError:
            missing_packages.append(package_name)
            print(f"  ✗ {package_name}")
    
    if missing_packages:
        print(f"\nWARNING: Missing packages: {', '.join(missing_packages)}")
        print("Install them with: pip install -r requirements.txt")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            return False
    
    print()
    return True


def clean_build_directories():
    """Clean previous build artifacts"""
    print("[2/7] Cleaning build directories...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"  - Removing {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Clean __pycache__ directories recursively
    # Use a list to avoid modification during iteration
    pycache_dirs = []
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_dirs.append(os.path.join(root, dir_name))
    
    for dir_path in pycache_dirs:
        if os.path.exists(dir_path):
            print(f"  - Removing {dir_path}")
            shutil.rmtree(dir_path)
    
    print("  ✓ Clean complete\n")


def modify_spec_file(args):
    """Modify spec file based on command line arguments"""
    print("[3/7] Configuring build...")
    
    spec_file = 'CV_Studio.spec'
    
    if not os.path.exists(spec_file):
        print(f"  ERROR: {spec_file} not found!")
        return False
    
    with open(spec_file, 'r') as f:
        spec_content = f.read()
    
    # Modify console setting for windowed mode
    if args.windowed:
        import re
        spec_content = re.sub(
            r'console=True,\s*#.*',
            'console=False,  # Console hidden (windowed mode)',
            spec_content
        )
        print("  - Windowed mode enabled (no console)")
    
    # Add icon if specified
    if args.icon:
        if os.path.exists(args.icon):
            import re
            spec_content = re.sub(
                r"icon=None,\s*#.*",
                f"icon='{args.icon}',",
                spec_content
            )
            print(f"  - Custom icon: {args.icon}")
        else:
            print(f"  WARNING: Icon file not found: {args.icon}")
    
    # Handle onefile mode
    if args.onefile:
        print("  - Single file mode requested")
        print("  NOTE: Onefile mode requires manual spec file modification")
        print("  Please edit CV_Studio.spec and change:")
        print("    1. exe: exclude_binaries=False")
        print("    2. Remove or comment out the COLLECT section")
        print("  For now, building with standard (folder) mode...")
    
    # Write modified spec file
    with open(spec_file, 'w') as f:
        f.write(spec_content)
    
    print("  ✓ Configuration complete\n")
    return True


def build_executable(args):
    """Run PyInstaller to build the executable"""
    print("[4/7] Building executable...")
    print("  This may take several minutes...\n")
    
    spec_file = 'CV_Studio.spec'
    
    # Build PyInstaller command
    cmd = [sys.executable, '-m', 'PyInstaller', spec_file]
    
    if args.debug:
        cmd.append('--debug=all')
        print("  - Debug mode enabled")
    
    # Run PyInstaller
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print("\n  ✓ Build successful!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Build failed with error code {e.returncode}")
        return False


def create_documentation():
    """Create README for the built executable"""
    print("[5/7] Creating documentation...")
    
    readme_content = """# CV_Studio - Standalone Executable

## Running CV_Studio

Simply double-click `CV_Studio.exe` to launch the application.

## Command Line Options

You can also run CV_Studio from the command line with options:

```
CV_Studio.exe [options]

Options:
  --setting <path>        Path to custom settings.json file
  --use_debug_print       Enable debug output
  --unuse_async_draw      Disable asynchronous drawing
```

## Examples

```
# Run with default settings
CV_Studio.exe

# Run with custom configuration
CV_Studio.exe --setting my_settings.json

# Run with debug output
CV_Studio.exe --use_debug_print
```

## Directory Structure

```
CV_Studio/
├── CV_Studio.exe           # Main executable
├── node/                   # Node implementations
│   ├── DLNode/            # Deep learning nodes (includes ONNX models)
│   ├── InputNode/         # Input nodes
│   ├── ProcessNode/       # Processing nodes
│   └── ...
├── node_editor/           # Node editor core
│   ├── font/             # Fonts
│   └── setting/          # Configuration files
├── src/                   # Source utilities
└── _internal/            # Python runtime and dependencies
```

## ONNX Models

The following ONNX models are included for object detection:

- YOLOX (nano, tiny, small variants)
- YOLO11
- FreeYOLO
- Tennis YOLO
- And more...

All models are located in: `node/DLNode/object_detection/*/model/`

## Troubleshooting

### Application won't start
- Make sure all files in the CV_Studio folder are present
- Try running from command line to see error messages
- Check that your GPU drivers are up to date (for ONNX GPU acceleration)

### ONNX models not found
- Verify that the `node/DLNode` directory structure is intact
- All .onnx files should be in their respective model folders

### Performance issues
- Disable GPU acceleration if you don't have a compatible GPU
- Reduce video resolution in settings
- Use smaller ONNX models (nano/tiny variants)

### Missing DLLs
- Install Visual C++ Redistributable:
  https://aka.ms/vs/17/release/vc_redist.x64.exe

## Support

For issues and questions:
- GitHub: https://github.com/hackolite/CV_Studio
- Issues: https://github.com/hackolite/CV_Studio/issues

## License

CV_Studio is licensed under Apache License 2.0.
Individual nodes and models may have their own licenses.
"""
    
    dist_dir = 'dist/CV_Studio'
    if os.path.exists(dist_dir):
        readme_path = os.path.join(dist_dir, 'README.txt')
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        print(f"  ✓ Created {readme_path}\n")


def create_installer(args):
    """Create Windows installer using Inno Setup"""
    if not args.installer:
        return True
    
    print("[6/7] Creating Windows installer...")
    
    # Check if Inno Setup is installed
    inno_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    iscc_path = None
    for path in inno_paths:
        if os.path.exists(path):
            iscc_path = path
            break
    
    if not iscc_path:
        print("  ⚠ Inno Setup not found!")
        print("  Please install Inno Setup from: https://jrsoftware.org/isdl.php")
        print("  Or compile installer.iss manually using Inno Setup Compiler")
        return False
    
    print(f"  ✓ Found Inno Setup: {iscc_path}")
    
    # Check if installer script exists
    if not os.path.exists('installer.iss'):
        print("  ✗ installer.iss not found!")
        return False
    
    print("  - Compiling installer...")
    
    try:
        result = subprocess.run(
            [iscc_path, 'installer.iss'],
            check=True,
            capture_output=True,
            text=True
        )
        print("  ✓ Installer created successfully!\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Installer compilation failed:")
        print(f"  {e.stderr}")
        return False


def print_summary(args):
    """Print build summary"""
    print("=" * 70)
    print("  BUILD COMPLETE!")
    print("=" * 70)
    print()
    print("Your executable is ready:")
    print("  📁 Location: dist/CV_Studio/")
    print("  🚀 Run:      dist/CV_Studio/CV_Studio.exe")
    print()
    
    if args.installer and os.path.exists('installer_output'):
        print("Windows Installer:")
        installer_files = [f for f in os.listdir('installer_output') if f.endswith('.exe')]
        if installer_files:
            print(f"  📀 Installer: installer_output/{installer_files[0]}")
            print()
    
    print("Distribution:")
    print("  📦 The entire 'dist/CV_Studio' folder can be distributed")
    print("  📋 Includes all ONNX models and node resources")
    print("  💻 Users just need to run CV_Studio.exe")
    print()
    
    if args.installer and os.path.exists('installer_output'):
        print("  OR distribute the Windows installer:")
        if installer_files:
            print(f"  📀 {installer_files[0]}")
            print("  💾 Professional installation with Start Menu shortcuts")
        print()
    
    print("Next steps:")
    print("  1. Test the executable: cd dist/CV_Studio && CV_Studio.exe")
    print("  2. Check all nodes work, especially ONNX object detection")
    print("  3. Zip the CV_Studio folder for distribution")
    if args.installer:
        print("  4. Or distribute the installer from installer_output/")
    print()
    print("Documentation:")
    print("  📖 BUILD_EXE_GUIDE.md - Complete guide (English)")
    print("  📖 BUILD_EXE_GUIDE_FR.md - Guide complet (Français)")
    print("  ⚡ BUILD_EXE_QUICKREF.md - Quick reference")
    print()
    print("=" * 70)


def main():
    """Main build script"""
    parser = argparse.ArgumentParser(
        description='Build CV_Studio standalone executable',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directories before building')
    parser.add_argument('--onefile', action='store_true',
                       help='Create a single executable file (slower startup)')
    parser.add_argument('--windowed', action='store_true',
                       help='Hide console window (GUI only mode)')
    parser.add_argument('--debug', action='store_true',
                       help='Build with debug information')
    parser.add_argument('--icon', type=str, default=None,
                       help='Path to icon file (.ico)')
    parser.add_argument('--installer', action='store_true',
                       help='Create Windows installer using Inno Setup')
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Clean if requested
    if args.clean:
        clean_build_directories()
    
    # Configure build
    if not modify_spec_file(args):
        sys.exit(1)
    
    # Build
    if not build_executable(args):
        sys.exit(1)
    
    # Create documentation
    create_documentation()
    
    # Create installer if requested
    if args.installer:
        installer_success = create_installer(args)
        if not installer_success:
            print("\n⚠ Warning: Installer creation failed, but executable is ready")
    
    # Print summary
    print_summary(args)


if __name__ == '__main__':
    main()
