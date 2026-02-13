#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CV_Studio - Unified Build Script
=================================

A clean, consolidated build script for creating CV_Studio executables using PyInstaller.
This script combines the best practices from all previous build scripts into a single,
maintainable solution.

Features:
- Cross-platform support (Windows, Linux, macOS)
- Automatic dependency checking and installation
- CPU/GPU build modes
- Clean, consistent output formatting
- Comprehensive error handling
- Command-line interface with options

Usage:
    python build_unified.py [options]

Options:
    --clean              Clean build directories before building
    --cpu                Use CPU-only dependencies (no CUDA)
    --windowed           Hide console window (GUI only)
    --icon ICON          Path to icon file (.ico)
    --skip-checks        Skip dependency checks (CI/CD mode)
    --help               Show this help message

Examples:
    # Standard build (GPU support)
    python build_unified.py --clean

    # CPU-only build
    python build_unified.py --clean --cpu

    # GUI mode without console
    python build_unified.py --windowed

    # CI/CD build
    python build_unified.py --clean --skip-checks
"""

import os
import sys
import shutil
import subprocess
import argparse
import re
from pathlib import Path

# Increase recursion limit for PyInstaller's module analysis
# PyInstaller performs deep analysis of Python modules during the build process.
# Large libraries like Pandas, NumPy, or complex node structures can have deep
# import hierarchies that exceed Python's default recursion limit (1000).
# Setting to 5000 prevents "RecursionError: maximum recursion depth exceeded"
# during the build process. This is a standard practice for PyInstaller builds
# with complex dependencies.
sys.setrecursionlimit(5000)

# Terminal colors for better output
class Colors:
    """ANSI color codes for terminal output"""
    # Try to enable ANSI colors on Windows 10+
    colors_enabled = True
    
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except (AttributeError, OSError):
            # Failed to enable ANSI colors on Windows
            # Colors will still be output but may not render
            colors_enabled = False
    
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header"""
    width = 70
    print()
    print(Colors.CYAN + "=" * width + Colors.END)
    print(Colors.CYAN + Colors.BOLD + text.center(width) + Colors.END)
    print(Colors.CYAN + "=" * width + Colors.END)
    print()


def print_step(step_num, total_steps, message):
    """Print a build step with formatting"""
    print(f"\n{Colors.BOLD}[{step_num}/{total_steps}] {message}{Colors.END}")
    print("-" * 60)


def print_success(message):
    """Print a success message"""
    print(f"{Colors.GREEN}  ✓ {message}{Colors.END}")


def print_error(message):
    """Print an error message"""
    print(f"{Colors.RED}  ✗ {message}{Colors.END}")


def print_warning(message):
    """Print a warning message"""
    print(f"{Colors.YELLOW}  ⚠ {message}{Colors.END}")


def print_info(message):
    """Print an informational message"""
    print(f"{Colors.BLUE}  → {message}{Colors.END}")


def check_python_version():
    """Check if Python version meets requirements"""
    if sys.version_info < (3, 7):
        print_error(f"Python 3.7+ required, found {sys.version}")
        return False
    print_success(f"Python {sys.version.split()[0]}")
    return True


def check_pyinstaller():
    """Check if PyInstaller is installed, install if needed"""
    try:
        import PyInstaller
        print_success("PyInstaller available")
        return True
    except ImportError:
        print_warning("PyInstaller not found, installing...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "pyinstaller>=5.0.0"],
                check=True,
                capture_output=True
            )
            print_success("PyInstaller installed")
            return True
        except subprocess.CalledProcessError as e:
            print_error(f"Failed to install PyInstaller: {e}")
            return False


def check_dependencies(skip_checks=False, use_cpu=False):
    """Check and optionally install dependencies"""
    print_step(1, 5, "Checking Dependencies")
    
    if not check_python_version():
        return False
    
    if not check_pyinstaller():
        return False
    
    if skip_checks:
        print_info("Skipping dependency checks (CI/CD mode)")
        return True
    
    # Check if requirements file exists
    req_file = "requirements-build-cpu.txt" if use_cpu else "requirements.txt"
    if not Path(req_file).exists():
        print_error(f"Requirements file not found: {req_file}")
        return False
    
    print_info(f"Using requirements: {req_file}")
    print_info("Installing/updating dependencies...")
    
    try:
        # Update pip first
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
            check=True,
            capture_output=True
        )
        
        # Install requirements
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            check=True
        )
        
        print_success("Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def clean_build_artifacts():
    """Clean previous build artifacts"""
    print_step(2, 5, "Cleaning Build Artifacts")
    
    dirs_to_clean = ['build', 'dist']
    cleaned = False
    
    for dir_name in dirs_to_clean:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print_info(f"Removing {dir_name}/")
            shutil.rmtree(dir_path)
            cleaned = True
    
    # Clean pycache recursively
    for pycache in Path('.').rglob('__pycache__'):
        if pycache.is_dir():
            shutil.rmtree(pycache)
    
    if cleaned:
        print_success("Cleanup complete")
    else:
        print_info("Already clean")
    
    return True


def configure_spec_file(windowed=False, icon=None):
    """Configure the spec file with build options"""
    print_step(3, 5, "Configuring Build")
    
    spec_file = Path('CV_Studio.spec')
    
    if not spec_file.exists():
        print_error(f"Spec file not found: {spec_file}")
        return False
    
    print_info(f"Using spec file: {spec_file}")
    
    # Read spec file
    spec_content = spec_file.read_text(encoding='utf-8')
    
    # Modify console setting for windowed mode
    if windowed:
        # Use flexible pattern to handle variations in spacing and trailing comma
        # Matches: console=True, console = True, console=True)
        spec_content = re.sub(
            r'console\s*=\s*True\b',
            'console=False',
            spec_content
        )
        print_info("Console: Hidden (windowed mode)")
    else:
        print_info("Console: Visible")
    
    # Add icon if specified
    if icon:
        icon_path = Path(icon)
        if icon_path.exists():
            # Use flexible pattern to handle variations in spacing and trailing comma
            # Matches: icon=None, icon = None, icon=None)
            spec_content = re.sub(
                r"icon\s*=\s*None\b",
                f"icon='{icon}'",
                spec_content
            )
            print_info(f"Icon: {icon}")
        else:
            print_warning(f"Icon file not found: {icon}")
    
    # Write modified spec file
    spec_file.write_text(spec_content, encoding='utf-8')
    
    print_success("Configuration complete")
    return True


def build_executable():
    """Build the executable using PyInstaller"""
    print_step(4, 5, "Building Executable")
    
    spec_file = Path('CV_Studio.spec')
    
    if not spec_file.exists():
        print_error(f"Spec file not found: {spec_file}")
        return False
    
    print_info("Running PyInstaller (this may take several minutes)...")
    print()
    
    cmd = [sys.executable, '-m', 'PyInstaller', str(spec_file), '--noconfirm']
    
    try:
        result = subprocess.run(cmd, check=True)
        print()
        print_success("Build completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print()
        print_error(f"Build failed with exit code {e.returncode}")
        return False


def post_build_fixes():
    """Apply post-build fixes for directory structure"""
    print_step(5, 5, "Post-Build Fixes")
    
    dist_dir = Path('dist/CV_Studio')
    internal_dir = dist_dir / '_internal'
    
    if not dist_dir.exists():
        print_error("Build output directory not found")
        return False
    
    # Copy node and node_editor from _internal to dist root if needed
    required_dirs = ['node', 'node_editor']
    
    for dir_name in required_dirs:
        src_path = internal_dir / dir_name
        dst_path = dist_dir / dir_name
        
        # If exists in _internal, copy to dist root
        if src_path.exists() and not dst_path.exists():
            print_info(f"Copying {dir_name}/ to dist root")
            shutil.copytree(src_path, dst_path)
            print_success(f"{dir_name}/ copied")
        elif dst_path.exists():
            print_info(f"{dir_name}/ already at dist root")
        else:
            print_warning(f"{dir_name}/ not found")
    
    print_success("Post-build fixes complete")
    return True


def print_build_summary():
    """Print build summary with file information"""
    print()
    print(Colors.GREEN + "=" * 70 + Colors.END)
    print(Colors.GREEN + Colors.BOLD + "BUILD SUCCESSFUL!".center(70) + Colors.END)
    print(Colors.GREEN + "=" * 70 + Colors.END)
    print()
    
    exe_path = Path('dist/CV_Studio/CV_Studio.exe')
    if not exe_path.exists():
        exe_path = Path('dist/CV_Studio/CV_Studio')  # Linux/macOS
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"  📦 Executable: {exe_path}")
        print(f"  📏 Size: {size_mb:.1f} MB")
    else:
        print(f"  📦 Location: dist/CV_Studio/")
    
    print()
    print("  🚀 To run the application:")
    if sys.platform == 'win32':
        print("     cd dist\\CV_Studio")
        print("     CV_Studio.exe")
    else:
        print("     cd dist/CV_Studio")
        print("     ./CV_Studio")
    
    print()
    print("  📋 Distribution:")
    print("     - The entire 'dist/CV_Studio' folder is standalone")
    print("     - Includes all nodes, models, and dependencies")
    print("     - Can be zipped and distributed to users")
    print()
    print(Colors.GREEN + "=" * 70 + Colors.END)
    print()


def main():
    """Main build orchestration"""
    parser = argparse.ArgumentParser(
        description='CV_Studio - Unified Build Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--clean', action='store_true',
                       help='Clean build directories before building')
    parser.add_argument('--cpu', action='store_true',
                       help='Use CPU-only dependencies (no CUDA)')
    parser.add_argument('--windowed', action='store_true',
                       help='Hide console window (GUI only)')
    parser.add_argument('--icon', type=str, default=None,
                       help='Path to icon file (.ico)')
    parser.add_argument('--skip-checks', action='store_true',
                       help='Skip dependency checks (CI/CD mode)')
    
    args = parser.parse_args()
    
    # Change to script directory
    script_dir = Path(__file__).parent.absolute()
    os.chdir(script_dir)
    
    # Print header
    print_header("CV_Studio - Unified Build Script")
    
    if args.cpu:
        print_info("Build mode: CPU-only (no CUDA)")
    else:
        print_info("Build mode: GPU support (CUDA)")
    
    # Step 1: Check dependencies
    if not check_dependencies(skip_checks=args.skip_checks, use_cpu=args.cpu):
        sys.exit(1)
    
    # Step 2: Clean if requested
    if args.clean:
        if not clean_build_artifacts():
            sys.exit(1)
    
    # Step 3: Configure spec file
    if not configure_spec_file(windowed=args.windowed, icon=args.icon):
        sys.exit(1)
    
    # Step 4: Build executable
    if not build_executable():
        sys.exit(1)
    
    # Step 5: Post-build fixes
    if not post_build_fixes():
        sys.exit(1)
    
    # Print summary
    print_build_summary()
    
    sys.exit(0)


if __name__ == '__main__':
    main()
