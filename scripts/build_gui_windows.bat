@echo off
REM Build-Script für Windows-GUI

echo Building Perlentaucher GUI for Windows...

REM Stelle sicher, dass PyInstaller installiert ist
python -m pip install --upgrade pyinstaller

REM Installiere GUI-Abhängigkeiten
python -m pip install -r requirements-gui.txt

REM Baue Executable
pyinstaller build.spec --clean

echo.
echo Build abgeschlossen! Executable befindet sich in: dist\PerlentaucherGUI.exe
pause
