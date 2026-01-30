# ============================================================================
# Script de construction automatique de CV_Studio.exe pour Windows (PowerShell)
# 
# Ce script clone le repository, installe les dependances et construit l'exe
# 
# Prerequis:
#   - Python 3.7+ installe et dans le PATH
#   - Git installe et dans le PATH
#   - Connexion Internet
# 
# Usage:
#   .\build_windows.ps1
#   
#   Ou si vous avez des problemes d'execution de scripts:
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1
# 
# Le script va:
#   1. Cloner le repository CV_Studio (si pas deja fait)
#   2. Installer les dependances Python
#   3. Construire l'executable avec PyInstaller
#   4. L'exe sera dans dist\CV_Studio\CV_Studio.exe
# ============================================================================

# Configuration de l'encodage UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Activer les couleurs dans la console
$PSStyle.OutputRendering = [System.Management.Automation.OutputRendering]::Ansi

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  CV_Studio - Script de Construction Windows (PowerShell)" -ForegroundColor Cyan
Write-Host "  Construction automatique de l'executable .exe" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# ETAPE 1: Verification de Python
# ============================================================================
Write-Host "[1/6] Verification de Python..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ $pythonVersion detecte" -ForegroundColor Green
} catch {
    Write-Host "  ✗ ERREUR: Python n'est pas installe ou pas dans le PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Telechargez Python depuis: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "  Assurez-vous de cocher 'Add Python to PATH' lors de l'installation" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}
Write-Host ""

# ============================================================================
# ETAPE 2: Verification de Git
# ============================================================================
Write-Host "[2/6] Verification de Git..." -ForegroundColor Yellow

try {
    $gitVersion = git --version 2>&1
    Write-Host "  ✓ $gitVersion detecte" -ForegroundColor Green
} catch {
    Write-Host "  ✗ ERREUR: Git n'est pas installe ou pas dans le PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Telechargez Git depuis: https://git-scm.com/download/win" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}
Write-Host ""

# ============================================================================
# ETAPE 3: Clonage du repository (si necessaire)
# ============================================================================
Write-Host "[3/6] Preparation du code source..." -ForegroundColor Yellow

# Si le script est lance depuis le repo clone, on reste la
if (Test-Path "main.py") {
    Write-Host "  ✓ Deja dans le repository CV_Studio" -ForegroundColor Green
    $repoDir = Get-Location
} elseif (Test-Path "CV_Studio\main.py") {
    Write-Host "  ✓ Repository CV_Studio trouve dans le sous-dossier" -ForegroundColor Green
    Set-Location CV_Studio
    $repoDir = Get-Location
} else {
    Write-Host "  - Clonage du repository depuis GitHub..." -ForegroundColor Cyan
    git clone https://github.com/hackolite/CV_Studio.git
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ ERREUR: Echec du clonage du repository" -ForegroundColor Red
        Read-Host "Appuyez sur Entree pour quitter"
        exit 1
    }
    Set-Location CV_Studio
    $repoDir = Get-Location
    Write-Host "  ✓ Repository clone avec succes" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# ETAPE 4: Installation des dependances
# ============================================================================
Write-Host "[4/6] Installation des dependances Python..." -ForegroundColor Yellow
Write-Host "  Cela peut prendre plusieurs minutes..." -ForegroundColor Cyan
Write-Host ""

Write-Host "  - Mise a jour de pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip setuptools wheel 2>&1 | Out-Null

Write-Host "  - Installation de numpy (requis en premier)..." -ForegroundColor Cyan
python -m pip install "numpy>=1.21.0" --no-warn-script-location | Out-Null

Write-Host "  - Installation des dependances principales..." -ForegroundColor Cyan
python -m pip install -r requirements.txt --no-warn-script-location | Out-Null

Write-Host "  - Installation de PyInstaller..." -ForegroundColor Cyan
python -m pip install -r requirements-build.txt --no-warn-script-location | Out-Null

Write-Host "  ✓ Toutes les dependances sont installees" -ForegroundColor Green
Write-Host ""

# ============================================================================
# ETAPE 5: Construction de l'executable
# ============================================================================
Write-Host "[5/6] Construction de l'executable..." -ForegroundColor Yellow
Write-Host "  Cela peut prendre 5-10 minutes selon votre machine..." -ForegroundColor Cyan
Write-Host ""

python build_exe.py --clean --skip-package-check
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  ✗ ERREUR: La construction a echoue" -ForegroundColor Red
    Write-Host "  Consultez les messages d'erreur ci-dessus" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

Write-Host ""
Write-Host "  ✓ Construction terminee avec succes!" -ForegroundColor Green
Write-Host ""

# ============================================================================
# ETAPE 6: Verification et resume
# ============================================================================
Write-Host "[6/6] Verification du build..." -ForegroundColor Yellow

if (Test-Path "dist\CV_Studio\CV_Studio.exe") {
    Write-Host "  ✓ CV_Studio.exe cree avec succes!" -ForegroundColor Green
    Write-Host ""
    
    # Afficher la taille
    $exeSize = (Get-Item "dist\CV_Studio\CV_Studio.exe").Length
    $sizeMB = [math]::Round($exeSize / 1MB, 2)
    Write-Host "  Taille de l'executable: $sizeMB MB" -ForegroundColor Cyan
    
    # Afficher la taille totale du dossier
    $totalSize = (Get-ChildItem dist\CV_Studio -Recurse | Measure-Object -Property Length -Sum).Sum
    $totalSizeMB = [math]::Round($totalSize / 1MB, 2)
    Write-Host "  Taille totale du dossier: $totalSizeMB MB" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host "  CONSTRUCTION TERMINEE!" -ForegroundColor Green
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Votre executable est pret:" -ForegroundColor White
    Write-Host "    📁 Emplacement: $repoDir\dist\CV_Studio\" -ForegroundColor Cyan
    Write-Host "    🚀 Fichier:     CV_Studio.exe" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Pour lancer l'application:" -ForegroundColor White
    Write-Host "    cd dist\CV_Studio" -ForegroundColor Gray
    Write-Host "    .\CV_Studio.exe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Pour distribuer:" -ForegroundColor White
    Write-Host "    1. Compressez le dossier dist\CV_Studio en ZIP" -ForegroundColor Gray
    Write-Host "    2. Partagez l'archive" -ForegroundColor Gray
    Write-Host "    3. Les utilisateurs extraient et lancent CV_Studio.exe" -ForegroundColor Gray
    Write-Host ""
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host ""
    
    # Demander si l'utilisateur veut lancer l'exe
    $launch = Read-Host "Voulez-vous lancer CV_Studio maintenant? (O/N)"
    if ($launch -eq "O" -or $launch -eq "o") {
        Write-Host ""
        Write-Host "  🚀 Lancement de CV_Studio..." -ForegroundColor Cyan
        Start-Process "dist\CV_Studio\CV_Studio.exe"
    }
} else {
    Write-Host "  ✗ ERREUR: CV_Studio.exe n'a pas ete cree" -ForegroundColor Red
    Write-Host "  Verifiez les messages d'erreur ci-dessus" -ForegroundColor Yellow
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

Write-Host ""
Write-Host "Script termine. Appuyez sur Entree pour quitter..." -ForegroundColor Gray
Read-Host
