# Build Scripts Guide / Guide des Scripts de Build

## English

### Available Build Scripts

This repository provides multiple build scripts for different environments:

1. **build.sh** - Bash script for Git Bash (Windows) and Linux/macOS
2. **build_windows.bat** - Windows batch file for CMD
3. **build_windows.ps1** - PowerShell script for Windows
4. **build.py** - Python-based build script (cross-platform)
5. **build_exe.py** - Advanced Python build script with more options

### Using build.sh (Git Bash/Linux/macOS)

```bash
# Build with GPU support (requires CUDA)
./build.sh

# Build with CPU-only support (no CUDA required)
./build.sh --cpu

# Show help
./build.sh --help
```

**Features:**
- ✅ Works on Git Bash (Windows), Linux, and macOS
- ✅ Automatic Python detection (python3 or python)
- ✅ Option to build with CPU-only or GPU support
- ✅ Installs all dependencies automatically
- ✅ Uses CV_Studio.spec for complete configuration
- ✅ Colored output for better readability

**CPU vs GPU Mode:**
- **GPU mode** (default): Installs `onnxruntime-gpu` - requires CUDA
- **CPU mode** (--cpu flag): Installs `onnxruntime` - works on any system

### Dependencies

The script will automatically install:
- PyInstaller (from requirements-build.txt)
- All required Python packages (from requirements.txt or requirements-build-cpu.txt)
- All hidden imports and data files are configured in CV_Studio.spec

### Output

After successful build, you'll find the executable in:
- Windows: `dist/CV_Studio/CV_Studio.exe`
- Linux/macOS: `dist/CV_Studio/CV_Studio`

---

## Français

### Scripts de Build Disponibles

Ce dépôt fournit plusieurs scripts de build pour différents environnements :

1. **build.sh** - Script Bash pour Git Bash (Windows) et Linux/macOS
2. **build_windows.bat** - Fichier batch Windows pour CMD
3. **build_windows.ps1** - Script PowerShell pour Windows
4. **build.py** - Script de build en Python (multi-plateforme)
5. **build_exe.py** - Script de build Python avancé avec plus d'options

### Utilisation de build.sh (Git Bash/Linux/macOS)

```bash
# Build avec support GPU (nécessite CUDA)
./build.sh

# Build avec support CPU uniquement (pas besoin de CUDA)
./build.sh --cpu

# Afficher l'aide
./build.sh --help
```

**Fonctionnalités :**
- ✅ Fonctionne sur Git Bash (Windows), Linux et macOS
- ✅ Détection automatique de Python (python3 ou python)
- ✅ Option pour build avec CPU uniquement ou support GPU
- ✅ Installe toutes les dépendances automatiquement
- ✅ Utilise CV_Studio.spec pour la configuration complète
- ✅ Sortie colorée pour une meilleure lisibilité

**Mode CPU vs GPU :**
- **Mode GPU** (par défaut) : Installe `onnxruntime-gpu` - nécessite CUDA
- **Mode CPU** (drapeau --cpu) : Installe `onnxruntime` - fonctionne sur n'importe quel système

### Dépendances

Le script installera automatiquement :
- PyInstaller (depuis requirements-build.txt)
- Tous les paquets Python requis (depuis requirements.txt ou requirements-build-cpu.txt)
- Toutes les imports cachés et fichiers de données sont configurés dans CV_Studio.spec

### Sortie

Après un build réussi, vous trouverez l'exécutable dans :
- Windows : `dist/CV_Studio/CV_Studio.exe`
- Linux/macOS : `dist/CV_Studio/CV_Studio`

---

## Troubleshooting / Dépannage

### Python not found / Python introuvable
Make sure Python 3.7+ is installed and in your PATH.
Assurez-vous que Python 3.7+ est installé et dans votre PATH.

### Permission denied (Linux/macOS)
Make the script executable first:
Rendez d'abord le script exécutable :
```bash
chmod +x build.sh
```

### CUDA not found (GPU mode)
Use CPU mode instead:
Utilisez le mode CPU à la place :
```bash
./build.sh --cpu
```

### Build fails with dependency errors
Try cleaning pip cache and reinstalling:
Essayez de nettoyer le cache pip et de réinstaller :
```bash
pip cache purge
./build.sh --cpu
```
