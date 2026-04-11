@echo off
setlocal EnableExtensions
REM Build-Script für Windows-GUI (immer relativ zu diesem Skript: Repo-Root)

cd /d "%~dp0.."
if errorlevel 1 (
    echo FEHLER: Projektverzeichnis konnte nicht gesetzt werden.
    pause
    exit /b 1
)
echo Projektverzeichnis: %CD%
echo.

REM Wenn die GUI laeuft, ist die EXE gesperrt: EndUpdateResourceW / Fehler 110, teils leere oder alte Datei
tasklist /FI "IMAGENAME eq PerlentaucherGUI.exe" 2>nul | find /I "PerlentaucherGUI.exe" >nul
if not errorlevel 1 (
    echo FEHLER: PerlentaucherGUI.exe laeuft noch.
    echo         Bitte Anwendung beenden und das Skript erneut ausfuehren.
    echo         Hinweis: PyInstaller kann sonst das Manifest nicht in die EXE schreiben.
    pause
    exit /b 1
)

echo Building Perlentaucher GUI for Windows...
echo.

REM Stelle sicher, dass PyInstaller installiert ist
python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo FEHLER: pip install pyinstaller fehlgeschlagen.
    pause
    exit /b 1
)

REM Installiere GUI-Abhängigkeiten
python -m pip install -r requirements-gui.txt
if errorlevel 1 (
    echo FEHLER: pip install requirements-gui.txt fehlgeschlagen.
    pause
    exit /b 1
)

REM Zuerst in temporaeres Verzeichnis bauen (vermeidet halb ueberschriebene dist\*.exe bei Sperre)
set "DIST_TMP=dist_pyinstaller_tmp"
if exist "%DIST_TMP%" rmdir /s /q "%DIST_TMP%"
if errorlevel 1 (
    echo WARNUNG: Konnte altes Verzeichnis %DIST_TMP% nicht vollstaendig loeschen.
)

pyinstaller build.spec --clean --distpath "%DIST_TMP%"
if errorlevel 1 (
    echo FEHLER: PyInstaller ist mit Fehlercode beendet worden.
    pause
    exit /b 1
)

if not exist "%DIST_TMP%\PerlentaucherGUI.exe" (
    echo FEHLER: Erwartete Datei fehlt: %DIST_TMP%\PerlentaucherGUI.exe
    pause
    exit /b 1
)

if not exist dist mkdir dist
if exist dist\PerlentaucherGUI.exe (
    del /f /q dist\PerlentaucherGUI.exe
    if errorlevel 1 (
        echo FEHLER: Konnte alte dist\PerlentaucherGUI.exe nicht loeschen (Datei gesperrt?).
        pause
        exit /b 1
    )
)

move /Y "%DIST_TMP%\PerlentaucherGUI.exe" dist\PerlentaucherGUI.exe
if errorlevel 1 (
    echo FEHLER: Konnte EXE nicht nach dist\ verschieben.
    pause
    exit /b 1
)

rmdir /s /q "%DIST_TMP%" 2>nul

echo.
echo Build abgeschlossen.
for %%F in ("dist\PerlentaucherGUI.exe") do echo   Datei: %%~fF  Groesse: %%~zF Bytes  Zeit: %%~tF
echo.
pause
