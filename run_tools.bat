@echo off
title PokemonPRO Tools
cd /d "%~dp0"
echo.
echo [1] Calibrate Move Slots ROI
echo [2] Team Builder
echo [3] Full Tools UI
echo.
set /p choice="Chon menu (1-3): "

if "%choice%"=="1" (
    python src/tools/calibrate_move_slots.py
) else if "%choice%"=="2" (
    python src/team_builder/team_builder_ui.py
) else if "%choice%"=="3" (
    python src/tools/ui_main.py
) else (
    echo Lua chon khong hop le!
    pause
)
