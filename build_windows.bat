@echo off
REM ============================================================================
REM Script de construction automatique de CV_Studio.exe pour Windows
REM 
REM Ce script clone le repository, installe les dependances et construit l'exe
REM 
REM Prerequis:
REM   - Python 3.7+ installe et dans le PATH
REM   - Git installe et dans le PATH
REM   - Connexion Internet
REM 
REM Usage:
REM   build_windows.bat
REM 
REM Le script va:
REM   1. Cloner le repository CV_Studio (si pas deja fait)
REM   2. Installer les dependances Python
REM   3. Construire l'executable avec PyInstaller
REM   4. L'exe sera dans dist\CV_Studio\CV_Studio.exe
REM ============================================================================

setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo ============================================================================
echo   CV_Studio - Script de Construction Windows
echo   Construction automatique de l'executable .exe
echo ============================================================================
echo.

REM ============================================================================
REM ETAPE 1: Verification de Python
REM ============================================================================
echo [1/6] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   X ERREUR: Python n'est pas installe ou pas dans le PATH
    echo.
    echo   Telechargez Python depuis: https://www.python.org/downloads/
    echo   Assurez-vous de cocher "Add Python to PATH" lors de l'installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   + Python %PYTHON_VERSION% detecte
echo.

REM ============================================================================
REM ETAPE 2: Verification de Git
REM ============================================================================
echo [2/6] Verification de Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo   X ERREUR: Git n'est pas installe ou pas dans le PATH
    echo.
    echo   Telechargez Git depuis: https://git-scm.com/download/win
    pause
    exit /b 1
)

for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
echo   + Git %GIT_VERSION% detecte
echo.

REM ============================================================================
REM ETAPE 3: Clonage du repository (si necessaire)
REM ============================================================================
echo [3/6] Preparation du code source...

REM Si le script est lance depuis le repo clone, on reste la
if exist "main.py" (
    echo   + Deja dans le repository CV_Studio
    set "REPO_DIR=%CD%"
) else if exist "CV_Studio\main.py" (
    echo   + Repository CV_Studio trouve dans le sous-dossier
    cd CV_Studio
    set "REPO_DIR=%CD%"
) else (
    echo   - Clonage du repository depuis GitHub...
    git clone https://github.com/hackolite/CV_Studio.git
    if errorlevel 1 (
        echo   X ERREUR: Echec du clonage du repository
        pause
        exit /b 1
    )
    cd CV_Studio
    set "REPO_DIR=%CD%"
    echo   + Repository clone avec succes
)
echo.

REM ============================================================================
REM ETAPE 4: Installation des dependances
REM ============================================================================
echo [4/6] Installation des dependances Python...
echo   Cela peut prendre plusieurs minutes...
echo.

echo   - Mise a jour de pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1

echo   - Installation de numpy (requis en premier)...
python -m pip install "numpy>=1.21.0" --no-warn-script-location

echo   - Installation des dependances principales...
python -m pip install -r requirements.txt --no-warn-script-location

echo   - Installation de PyInstaller...
python -m pip install -r requirements-build.txt --no-warn-script-location

echo   + Toutes les dependances sont installees
echo.

REM ============================================================================
REM ETAPE 5: Construction de l'executable
REM ============================================================================
echo [5/6] Construction de l'executable...
echo   Cela peut prendre 5-10 minutes selon votre machine...
echo.

python build_exe.py --clean --skip-package-check
if errorlevel 1 (
    echo.
    echo   X ERREUR: La construction a echoue
    echo   Consultez les messages d'erreur ci-dessus
    pause
    exit /b 1
)

echo.
echo   + Construction terminee avec succes!
echo.

REM ============================================================================
REM ETAPE 6: Verification et resume
REM ============================================================================
echo [6/6] Verification du build...

if exist "dist\CV_Studio\CV_Studio.exe" (
    echo   + CV_Studio.exe cree avec succes!
    echo.
    
    REM Afficher la taille du fichier
    for %%F in ("dist\CV_Studio\CV_Studio.exe") do (
        set /a SIZE_MB=%%~zF/1048576
        echo   Taille de l'executable: !SIZE_MB! MB
    )
    
    echo.
    echo ============================================================================
    echo   CONSTRUCTION TERMINEE!
    echo ============================================================================
    echo.
    echo   Votre executable est pret:
    echo     Emplacement: %CD%\dist\CV_Studio\
    echo     Fichier:     CV_Studio.exe
    echo.
    echo   Pour lancer l'application:
    echo     cd dist\CV_Studio
    echo     CV_Studio.exe
    echo.
    echo   Pour distribuer:
    echo     1. Compressez le dossier dist\CV_Studio en ZIP
    echo     2. Partagez l'archive
    echo     3. Les utilisateurs extraient et lancent CV_Studio.exe
    echo.
    echo ============================================================================
    echo.
    
    REM Demander si l'utilisateur veut lancer l'exe
    set /p LAUNCH="Voulez-vous lancer CV_Studio maintenant? (O/N): "
    if /i "!LAUNCH!"=="O" (
        echo.
        echo   Lancement de CV_Studio...
        start "" "dist\CV_Studio\CV_Studio.exe"
    )
) else (
    echo   X ERREUR: CV_Studio.exe n'a pas ete cree
    echo   Verifiez les messages d'erreur ci-dessus
    pause
    exit /b 1
)

echo.
echo Appuyez sur une touche pour quitter...
pause >nul
