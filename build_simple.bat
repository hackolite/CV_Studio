@echo off
REM Build CV_Studio.exe with PyInstaller
REM This script builds the executable from the internal directory structure

echo ====================================
echo Building CV_Studio.exe
echo ====================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Step 1: Installing/updating PyInstaller...
pip install pyinstaller --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo Step 2: Cleaning previous build artifacts...
if exist "dist\CV_Studio" (
    rmdir /s /q "dist\CV_Studio"
    echo Cleaned dist\CV_Studio directory
)
if exist "build" (
    rmdir /s /q "build"
    echo Cleaned build directory
)

echo.
echo Step 3: Running PyInstaller...
pyinstaller CV_Studio_new.spec
if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ====================================
echo Build completed successfully!
echo ====================================
echo.
echo The executable is located at: dist\CV_Studio\CV_Studio.exe
echo.
echo You can copy the entire dist\CV_Studio folder to any location
echo and run CV_Studio.exe from there.
echo.
pause
