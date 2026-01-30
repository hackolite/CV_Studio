#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for CV_Studio executable using PyInstaller

This script automates the process of building a standalone .exe for CV_Studio
on Windows. It handles path management for frozen executables, cleanup of
build artifacts, and PyInstaller configuration.

Features:
- Path management using sys._MEIPASS for frozen executables
- Automatic cleanup of build/, dist/, and .spec files
- PyInstaller optimization with --onefile, --windowed, --noconfirm
- Support for assets/ folder and icon.ico
- Increased recursion limit for large libraries (Pandas, Tkinter)
- Clear console logging at each step

Usage:
    python build.py

The script will build main.py into a standalone executable.
"""

import os
import sys
import shutil
import subprocess

# ============================================================================
# ROBUSTNESS: Increase recursion limit for large libraries (Pandas, Tkinter)
# ============================================================================
# PyInstaller performs deep analysis of Python modules during the build process.
# Large libraries like Pandas, NumPy, or Tkinter have complex import hierarchies
# that can exceed Python's default recursion limit (1000). Setting 5000 prevents
# "RecursionError: maximum recursion depth exceeded" during the build process.
sys.setrecursionlimit(5000)


# ============================================================================
# PATH MANAGEMENT: Function to handle sys._MEIPASS for PyInstaller
# ============================================================================
# NOTE: This utility function is provided here as a reference implementation.
# It should be copied to your main application code (e.g., main.py) to handle
# resource paths correctly in frozen executables. The build script itself
# does not use this function, but it demonstrates the pattern needed for
# finding assets and config files in both script and .exe modes.
def get_resource_path(relative_path):
    """
    Get the absolute path to a resource, works for both development and frozen mode.
    
    When running as a script, returns the path relative to the script directory.
    When running as a PyInstaller executable (.exe), returns the path relative to
    the temporary directory where PyInstaller extracts files (sys._MEIPASS).
    
    Args:
        relative_path (str): Relative path to the resource (e.g., 'assets/image.png')
    
    Returns:
        str: Absolute path to the resource
    
    Example:
        icon_path = get_resource_path('icon.ico')
        config_path = get_resource_path('config/settings.json')
        assets_dir = get_resource_path('assets')
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # This is only available when running as a frozen executable
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment (script mode)
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


# ============================================================================
# LOGGING: Console message functions for clear feedback
# ============================================================================
def log_step(step_num, total_steps, message):
    """Log a build step with clear formatting."""
    print(f"\n[{step_num}/{total_steps}] {message}")
    print("=" * 60)


def log_info(message):
    """Log an informational message."""
    print(f"  ➤ {message}")


def log_success(message):
    """Log a success message."""
    print(f"  ✓ {message}")


def log_warning(message):
    """Log a warning message."""
    print(f"  ⚠ {message}")


def log_error(message):
    """Log an error message."""
    print(f"  ✗ {message}")


# ============================================================================
# CLEANUP: Remove build artifacts before new compilation
# ============================================================================
def cleanup_build_artifacts():
    """
    Clean up previous build artifacts to avoid conflicts.
    
    Removes:
    - build/ directory (PyInstaller build cache)
    - dist/ directory (PyInstaller output)
    - *.spec files (PyInstaller spec files, except CV_Studio.spec if preserved)
    """
    log_step(1, 3, "Nettoyage des artefacts de build précédents...")
    
    # Get the base directory (where the script is located)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Directories to remove
    dirs_to_clean = ['build', 'dist']
    
    for dir_name in dirs_to_clean:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            log_info(f"Suppression du dossier: {dir_name}/")
            try:
                shutil.rmtree(dir_path)
                log_success(f"Dossier {dir_name}/ supprimé")
            except Exception as e:
                log_error(f"Erreur lors de la suppression de {dir_name}/: {e}")
                return False
        else:
            log_info(f"Dossier {dir_name}/ non trouvé (déjà propre)")
    
    # Remove .spec files generated by PyInstaller, except CV_Studio.spec which is version-controlled
    spec_files = [f for f in os.listdir(base_dir) if f.endswith('.spec') and f != 'CV_Studio.spec']
    for spec_file in spec_files:
        spec_path = os.path.join(base_dir, spec_file)
        log_info(f"Suppression du fichier: {spec_file}")
        try:
            os.remove(spec_path)
            log_success(f"Fichier {spec_file} supprimé")
        except Exception as e:
            log_error(f"Erreur lors de la suppression de {spec_file}: {e}")
            return False
    
    if not spec_files:
        log_info("Aucun fichier .spec à supprimer (déjà propre)")
    
    log_success("Nettoyage terminé avec succès")
    return True


# ============================================================================
# BUILD: Compile with PyInstaller
# ============================================================================
def build_executable():
    """
    Build the executable using PyInstaller with optimized settings.
    
    Options used:
    - --onefile: Create a single executable file
    - --windowed: No console window (GUI application)
    - --noconfirm: Overwrite output directory without confirmation
    - --add-data: Include assets/ folder and other resources
    - --icon: Use custom icon if available
    
    Returns:
        bool: True if build succeeded, False otherwise
    """
    log_step(2, 3, "Compilation avec PyInstaller...")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(base_dir, 'main.py')
    
    # Verify main.py exists
    if not os.path.exists(main_script):
        log_error(f"Le fichier main.py n'a pas été trouvé: {main_script}")
        return False
    
    log_info(f"Script principal: {main_script}")
    
    # Build PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',        # Single executable file
        '--windowed',       # No console window (GUI mode)
        '--noconfirm',      # Overwrite without asking
        '--name', 'CV_Studio',  # Output name
    ]
    
    # Add assets folder if it exists
    assets_dir = os.path.join(base_dir, 'assets')
    if os.path.exists(assets_dir) and os.path.isdir(assets_dir):
        # Use the appropriate separator for the platform
        separator = ';' if sys.platform == 'win32' else ':'
        cmd.extend(['--add-data', f'{assets_dir}{separator}assets'])
        log_info(f"Dossier assets/ inclus: {assets_dir}")
    else:
        log_warning("Dossier assets/ non trouvé, il sera ignoré")
    
    # Add icon if it exists
    icon_path = os.path.join(base_dir, 'icon.ico')
    if os.path.exists(icon_path):
        cmd.extend(['--icon', icon_path])
        log_info(f"Icône personnalisée incluse: {icon_path}")
    else:
        log_warning("Fichier icon.ico non trouvé, l'icône par défaut sera utilisée")
    
    # Add the main script
    cmd.append(main_script)
    
    log_info("Lancement de PyInstaller...")
    log_info(f"Commande: {' '.join(cmd)}")
    print()
    
    # Run PyInstaller
    try:
        result = subprocess.run(
            cmd,
            check=True,
            cwd=base_dir
        )
        log_success("Compilation PyInstaller terminée avec succès")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Échec de la compilation PyInstaller (code: {e.returncode})")
        return False
    except FileNotFoundError:
        log_error("PyInstaller n'est pas installé. Installez-le avec: pip install pyinstaller")
        return False


# ============================================================================
# SUMMARY: Display build results
# ============================================================================
BOX_WIDTH = 58  # Width of the summary box (excluding border characters)


def _pad_line(text, width=BOX_WIDTH):
    """Pad a line to fit within the box, ensuring proper alignment."""
    # Account for content that might be shorter or longer than expected
    padding_needed = width - len(text)
    if padding_needed < 0:
        # Truncate if too long
        return text[:width]
    return text + " " * padding_needed


def display_summary(success):
    """
    Display the build summary with clear status indication.
    
    Args:
        success (bool): Whether the build was successful
    """
    log_step(3, 3, "Résumé de la compilation")
    
    if success:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        exe_path = os.path.join(base_dir, 'dist', 'CV_Studio.exe')
        
        print()
        print("╔" + "═" * BOX_WIDTH + "╗")
        print("║" + _pad_line("        BUILD RÉUSSI ! ✓") + "║")
        print("╠" + "═" * BOX_WIDTH + "╣")
        
        if os.path.exists(exe_path):
            # Get file size
            size_bytes = os.path.getsize(exe_path)
            size_mb = size_bytes / (1024 * 1024)
            print("║" + _pad_line("  Exécutable créé: dist/CV_Studio.exe") + "║")
            print("║" + _pad_line(f"  Taille: {size_mb:.1f} MB") + "║")
        else:
            print("║" + _pad_line("  Exécutable: dist/CV_Studio.exe") + "║")
        
        print("╠" + "═" * BOX_WIDTH + "╣")
        print("║" + _pad_line("  Pour lancer l'application:") + "║")
        print("║" + _pad_line("    .\\dist\\CV_Studio.exe") + "║")
        print("╚" + "═" * BOX_WIDTH + "╝")
        print()
    else:
        print()
        print("╔" + "═" * BOX_WIDTH + "╗")
        print("║" + _pad_line("        BUILD ÉCHOUÉ ! ✗") + "║")
        print("╠" + "═" * BOX_WIDTH + "╣")
        print("║" + _pad_line("  Vérifiez les erreurs ci-dessus.") + "║")
        print("║" + _pad_line("  Assurez-vous que:") + "║")
        print("║" + _pad_line("    - PyInstaller est installé (pip install pyinstaller)") + "║")
        print("║" + _pad_line("    - main.py existe dans le répertoire courant") + "║")
        print("║" + _pad_line("    - Les dépendances sont installées") + "║")
        print("╚" + "═" * BOX_WIDTH + "╝")
        print()


# ============================================================================
# MAIN: Entry point
# ============================================================================
def main():
    """
    Main function to orchestrate the build process.
    
    Steps:
    1. Cleanup - Remove previous build artifacts
    2. Compile - Build executable with PyInstaller
    3. Summary - Display build results
    """
    print()
    print("╔" + "═" * BOX_WIDTH + "╗")
    print("║" + _pad_line("    CV_Studio - Script de Build PyInstaller") + "║")
    print("║" + _pad_line("           Automatisation Windows") + "║")
    print("╚" + "═" * BOX_WIDTH + "╝")
    
    # Show recursion limit setting
    log_info(f"Limite de récursion augmentée à: {sys.getrecursionlimit()}")
    
    # Step 1: Cleanup
    if not cleanup_build_artifacts():
        display_summary(False)
        sys.exit(1)
    
    # Step 2: Build
    success = build_executable()
    
    # Step 3: Summary
    display_summary(success)
    
    if not success:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
