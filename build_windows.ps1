# ============================================================================
# Script de construction CV_Studio - Version Haute Compatibilite
# ============================================================================

# On force l'encodage pour les accents
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "  CV_Studio - Script de Construction (Compatible Windows PS 5.1)" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

# ============================================================================
# ETAPE 1: Verification de Python
# ============================================================================
Write-Host "[1/6] Verification de Python..." -ForegroundColor Yellow
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "  [!] ERREUR: Python est introuvable." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
} else {
    $pyVer = python --version
    Write-Host "  OK: $pyVer detecte" -ForegroundColor Green
}

# ============================================================================
# ETAPE 2: Verification de Git (Optionnel si deja dans le dossier)
# ============================================================================
Write-Host "[2/6] Verification de Git..." -ForegroundColor Yellow
if (Test-Path "main.py") {
    Write-Host "  OK: Deja dans le dossier source, Git n'est pas requis pour le build." -ForegroundColor Green
} elseif (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "  [!] ERREUR: Git absent et vous n'etes pas dans le dossier source." -ForegroundColor Red
    Read-Host "Appuyez sur Entree pour quitter"
    exit 1
}

# ============================================================================
# ETAPE 4 & 5: Installation et Build
# ============================================================================
Write-Host "[3/6] Installation des modules requis..." -ForegroundColor Yellow
python -m pip install --upgrade pip setuptools wheel
python -m pip install pyinstaller opencv-python

Write-Host "[4/6] Verification des processus en cours..." -ForegroundColor Yellow
$runningProcess = Get-Process -Name "CV_Studio" -ErrorAction SilentlyContinue
if ($runningProcess) {
    Write-Host "  [!] ATTENTION: CV_Studio.exe est en cours d'execution" -ForegroundColor Red
    Write-Host "  Cela peut causer des erreurs de build (fichiers verrouilles)" -ForegroundColor Yellow
    Write-Host "  Fermez toutes les instances de CV_Studio.exe et relancez ce script" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Appuyez sur Entree pour quitter..."
    $null = Read-Host
    exit 1
}

Write-Host "[5/6] Lancement du Build PyInstaller..." -ForegroundColor Yellow
# On force le build direct pour eviter les scripts intermediaires qui cassent
pyinstaller --noconfirm --onedir --windowed --name "CV_Studio" --hidden-import="cv2" main.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "============================================================================" -ForegroundColor Green
    Write-Host "  CONSTRUCTION TERMINEE AVEC SUCCES !" -ForegroundColor Green
    Write-Host "  Fichier : dist\CV_Studio\CV_Studio.exe" -ForegroundColor White
    Write-Host "============================================================================" -ForegroundColor Green
} else {
    Write-Host "  [!] Le build a echoue." -ForegroundColor Red
    Write-Host ""
    Write-Host "Si l'erreur mentionne 'PermissionError' ou 'Acces refuse':" -ForegroundColor Yellow
    Write-Host "  1. Fermez toutes les instances de CV_Studio.exe" -ForegroundColor White
    Write-Host "  2. Fermez l'Explorateur Windows dans le dossier dist" -ForegroundColor White
    Write-Host "  3. Supprimez manuellement le dossier dist si necessaire" -ForegroundColor White
    Write-Host "  4. Relancez ce script" -ForegroundColor White
}

Write-Host "Appuyez sur Entree pour quitter..."
$null = Read-Host
