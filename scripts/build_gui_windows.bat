@echo off
setlocal EnableExtensions
REM Ruft das Python-Build-Skript auf (pip + PyInstaller + Kopie nach dist).
REM Alles in einem Python-Prozess — vermeidet CMD/PowerShell-Probleme nach PyInstaller.

cd /d "%~dp0.."
if errorlevel 1 (
    echo FEHLER: Projektverzeichnis konnte nicht gesetzt werden.
    pause
    exit /b 1
)

python "%~dp0build_gui_windows.py"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
    echo.
    echo FEHLER: Build endete mit Code %EXITCODE%
)
echo.
pause
exit /b %EXITCODE%
