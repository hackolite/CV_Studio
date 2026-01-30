#!/bin/bash
# ============================================================================
# Script de construction CV_Studio - Version Bash pour Git Bash/Linux
# ============================================================================
# 
# Usage:
#   ./build.sh              # Build with GPU support (requires CUDA)
#   ./build.sh --cpu        # Build with CPU-only support (no CUDA required)
#   ./build.sh --help       # Show help message
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
USE_CPU=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --cpu)
            USE_CPU=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --cpu     Build with CPU-only support (no CUDA required)"
            echo "  --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0              # Build with GPU support"
            echo "  $0 --cpu        # Build with CPU-only support"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}============================================================================${NC}"
echo -e "${CYAN}  CV_Studio - Script de Construction (Git Bash/Linux)${NC}"
if [ "$USE_CPU" = true ]; then
    echo -e "${CYAN}  Mode: CPU-only (sans CUDA)${NC}"
else
    echo -e "${CYAN}  Mode: GPU support (avec CUDA)${NC}"
fi
echo -e "${CYAN}============================================================================${NC}"
echo ""

# ============================================================================
# ETAPE 1: Verification de Python
# ============================================================================
echo -e "${YELLOW}[1/6] Verification de Python...${NC}"
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}  [!] ERREUR: Python est introuvable.${NC}"
    exit 1
fi

# Try python3 first, then python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

PY_VERSION=$("$PYTHON_CMD" --version 2>&1)
echo -e "${GREEN}  OK: $PY_VERSION detecte${NC}"

# ============================================================================
# ETAPE 2: Verification de Git (Optionnel si deja dans le dossier)
# ============================================================================
echo -e "${YELLOW}[2/6] Verification de Git...${NC}"
if [ -f "main.py" ]; then
    echo -e "${GREEN}  OK: Deja dans le dossier source, Git n'est pas requis pour le build.${NC}"
elif ! command -v git &> /dev/null; then
    echo -e "${RED}  [!] ERREUR: Git absent et vous n'etes pas dans le dossier source.${NC}"
    exit 1
else
    echo -e "${GREEN}  OK: Git detecte${NC}"
fi

# ============================================================================
# ETAPE 3: Installation des modules requis
# ============================================================================
echo -e "${YELLOW}[3/6] Installation des modules requis...${NC}"
echo "  Mise a jour de pip, setuptools et wheel..."
"$PYTHON_CMD" -m pip install --upgrade pip setuptools wheel

echo "  Installation de PyInstaller..."
"$PYTHON_CMD" -m pip install -r requirements-build.txt

# Install main dependencies based on CPU/GPU mode
if [ "$USE_CPU" = true ]; then
    echo "  Installation des dependances principales (mode CPU)..."
    echo -e "${YELLOW}  Note: Installation de onnxruntime (CPU) au lieu de onnxruntime-gpu${NC}"
    "$PYTHON_CMD" -m pip install -r requirements-build-cpu.txt
else
    echo "  Installation des dependances principales (mode GPU)..."
    "$PYTHON_CMD" -m pip install -r requirements.txt
fi

echo -e "${GREEN}  OK: Tous les modules sont installes${NC}"

# ============================================================================
# ETAPE 4: Nettoyage des builds precedents
# ============================================================================
echo -e "${YELLOW}[4/6] Nettoyage des builds precedents...${NC}"
if [ -d "build" ]; then
    rm -rf build
    echo "  Suppression du dossier build/"
fi
if [ -d "dist" ]; then
    rm -rf dist
    echo "  Suppression du dossier dist/"
fi
echo -e "${GREEN}  OK: Nettoyage termine${NC}"

# ============================================================================
# ETAPE 5: Lancement du Build PyInstaller
# ============================================================================
echo -e "${YELLOW}[5/6] Lancement du Build PyInstaller...${NC}"
echo "  Utilisation du fichier CV_Studio.spec pour la configuration complete..."

# Use the spec file for complete configuration
if [ -f "CV_Studio.spec" ]; then
    "$PYTHON_CMD" -m PyInstaller CV_Studio.spec --noconfirm
else
    echo -e "${RED}  [!] ERREUR: CV_Studio.spec introuvable${NC}"
    exit 1
fi

# ============================================================================
# ETAPE 6: Verification du resultat
# ============================================================================
echo -e "${YELLOW}[6/6] Verification du resultat...${NC}"
if [ -f "dist/CV_Studio/CV_Studio" ] || [ -f "dist/CV_Studio/CV_Studio.exe" ]; then
    echo -e "${GREEN}============================================================================${NC}"
    echo -e "${GREEN}  CONSTRUCTION TERMINEE AVEC SUCCES !${NC}"
    if [ -f "dist/CV_Studio/CV_Studio.exe" ]; then
        echo -e "${GREEN}  Fichier : dist/CV_Studio/CV_Studio.exe${NC}"
    else
        echo -e "${GREEN}  Fichier : dist/CV_Studio/CV_Studio${NC}"
    fi
    echo -e "${GREEN}============================================================================${NC}"
else
    echo -e "${RED}  [!] Le build a echoue - executable non trouve${NC}"
    exit 1
fi

echo ""
echo -e "${CYAN}Build termine. Vous pouvez maintenant tester l'executable.${NC}"
