#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for CV_Studio executable using PyInstaller

This script automates the process of building a standalone .exe for CV_Studio
on Windows. It uses the CV_Studio.spec file which includes comprehensive
configuration for all dependencies, hidden imports, and data files.

Features:
- Uses CV_Studio.spec for complete dependency configuration
- Includes all hidden imports (cv2, onnxruntime, mediapipe, wordcloud, etc.)
- Optional cleanup of build/, dist/, and .spec files with --clean flag
- Clear console logging at each step
- Runtime hooks for proper path management in frozen executables
- Includes all ONNX models, nodes, fonts, and settings

Usage:
    python build.py                 # Build without cleaning
    python build.py --clean         # Clean build artifacts then build

The script will build main.py into a standalone executable using the
CV_Studio.spec configuration file, ensuring all modules are properly included.
"""

import os
import sys
import shutil
import subprocess
import argparse

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
    
    # Normalize path separators for cross-platform compatibility
    # This handles cases where relative_path uses forward slashes on Windows
    return os.path.normpath(os.path.join(base_path, relative_path))


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
    Build the executable using PyInstaller with the CV_Studio.spec configuration.
    
    The CV_Studio.spec file includes:
    - Hidden imports for cv2, onnxruntime, mediapipe, and all dependencies
    - Data files for node directories, fonts, settings
    - Runtime hooks for proper path management
    - All ONNX models and resources
    
    This ensures all modules, especially cv2, are properly included in the executable.
    
    Returns:
        bool: True if build succeeded, False otherwise
    """
    log_step(2, 3, "Compilation avec PyInstaller...")
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spec_file = os.path.join(base_dir, 'CV_Studio.spec')
    
    # Verify CV_Studio.spec exists
    if not os.path.exists(spec_file):
        log_error(f"Le fichier CV_Studio.spec n'a pas été trouvé: {spec_file}")
        log_info("Veuillez vous assurer que le fichier .spec existe et contient la configuration complète")
        return False
    
    log_info(f"Fichier de configuration: CV_Studio.spec")
    log_info("Ce fichier inclut tous les imports cachés (cv2, onnxruntime, etc.)")
    
    # Build PyInstaller command using the spec file
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',      # Overwrite without asking
        spec_file,          # Use the comprehensive spec file
    ]
    
    log_info("Lancement de PyInstaller avec CV_Studio.spec...")
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
        exe_path = os.path.join(base_dir, 'dist', 'CV_Studio', 'CV_Studio.exe')
        dist_folder = os.path.join(base_dir, 'dist', 'CV_Studio')
        
        print()
        print("╔" + "═" * BOX_WIDTH + "╗")
        print("║" + _pad_line("        BUILD RÉUSSI ! ✓") + "║")
        print("╠" + "═" * BOX_WIDTH + "╣")
        
        if os.path.exists(exe_path):
            # Get file size
            size_bytes = os.path.getsize(exe_path)
            size_mb = size_bytes / (1024 * 1024)
            print("║" + _pad_line("  Exécutable créé: dist/CV_Studio/CV_Studio.exe") + "║")
            print("║" + _pad_line(f"  Taille de l'exe: {size_mb:.1f} MB") + "║")
            
            # Get folder size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(dist_folder):
                for filename in filenames:
                    fp = os.path.join(dirpath, filename)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            folder_size_mb = total_size / (1024 * 1024)
            print("║" + _pad_line(f"  Taille totale du dossier: {folder_size_mb:.1f} MB") + "║")
        else:
            print("║" + _pad_line("  Exécutable: dist/CV_Studio/CV_Studio.exe") + "║")
        
        print("╠" + "═" * BOX_WIDTH + "╣")
        print("║" + _pad_line("  Pour lancer l'application:") + "║")
        print("║" + _pad_line("    .\\dist\\CV_Studio\\CV_Studio.exe") + "║")
        print("║" + _pad_line("") + "║")
        print("║" + _pad_line("  Le dossier dist/CV_Studio/ contient:") + "║")
        print("║" + _pad_line("    - CV_Studio.exe (exécutable principal)") + "║")
        print("║" + _pad_line("    - _internal/ (dépendances Python et modules)") + "║")
        print("║" + _pad_line("    - node/ (tous les noeuds avec modèles ONNX)") + "║")
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
        print("║" + _pad_line("    - Le fichier CV_Studio.spec existe") + "║")
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
    1. Cleanup - Remove previous build artifacts (when --clean is used)
    2. Compile - Build executable with PyInstaller
    3. Summary - Display build results
    """
    parser = argparse.ArgumentParser(
        description='Build CV_Studio executable with PyInstaller',
    )
    parser.add_argument('--clean', action='store_true',
                        help='Clean build directories before building')
    args = parser.parse_args()

    print()
    print("╔" + "═" * BOX_WIDTH + "╗")
    print("║" + _pad_line("    CV_Studio - Script de Build PyInstaller") + "║")
    print("║" + _pad_line("           Automatisation Windows") + "║")
    print("╚" + "═" * BOX_WIDTH + "╝")
    
    # Show recursion limit setting
    log_info(f"Limite de récursion augmentée à: {sys.getrecursionlimit()}")
    
    # Step 1: Cleanup (when --clean is passed)
    if args.clean:
        if not cleanup_build_artifacts():
            display_summary(False)
            sys.exit(1)
    else:
        log_info("Pas de nettoyage demandé (utilisez --clean pour nettoyer)")
    
    # Step 2: Build
    success = build_executable()
    
    # Step 3: Summary
    display_summary(success)
    
    if not success:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
