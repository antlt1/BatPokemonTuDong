@echo off
REM Launch Modern UI - PokemonPRO Auto Tool
REM GUI interface using CustomTkinter (Dark Mode, Sidebar + Dashboard)

setlocal enabledelayedexpansion

REM Get the directory of this batch file
set "SCRIPT_DIR=%~dp0"

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Activate venv if exists (optional, adjust path if needed)
REM if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat

REM Setup Tesseract OCR environment
set "TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata"
set "PATH=%PATH%;C:\Program Files\Tesseract-OCR"

REM Run Python script
echo ========================================
echo Starting PokemonPRO Auto Tool (GUI)
echo ========================================
echo.

python launch_gui.py

pause
