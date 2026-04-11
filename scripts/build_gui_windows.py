#!/usr/bin/env python3
"""
Windows-GUI-Build: pip, PyInstaller, EXE nach dist/.

Läuft vollständig in einem Python-Prozess (kein CMD-Nach-PyInstaller,
das in manchen Hosts mit PowerShell zu Parser-Meldungen wie "." führt).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _repo_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _running_gui_lock() -> bool:
    """True, wenn PerlentaucherGUI.exe als Prozess läuft (wie tasklist|find im BAT)."""
    try:
        p = subprocess.run(
            'tasklist /FI "IMAGENAME eq PerlentaucherGUI.exe" 2>nul | find /I "PerlentaucherGUI.exe" >nul',
            shell=True,
            cwd=_repo_root(),
        )
        return p.returncode == 0
    except OSError:
        return False


def _run(cmd: list[str], cwd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=cwd)


def main() -> int:
    if sys.platform != "win32":
        print("Dieses Skript ist für Windows gedacht.", file=sys.stderr)
        return 2

    root = _repo_root()
    os.chdir(root)

    if _running_gui_lock():
        print(
            "FEHLER: PerlentaucherGUI.exe läuft noch.\n"
            "Bitte Anwendung beenden und erneut bauen (sonst EndUpdateResourceW / gesperrte EXE).",
            file=sys.stderr,
        )
        return 1

    dist_tmp = os.path.join(root, "dist_pyinstaller_tmp")
    dist_dir = os.path.join(root, "dist")
    exe_name = "PerlentaucherGUI.exe"
    src_exe = os.path.join(dist_tmp, exe_name)
    dst_exe = os.path.join(dist_dir, exe_name)

    print("Projektverzeichnis:", root, flush=True)

    _run([sys.executable, "-m", "pip", "install", "--upgrade", "pyinstaller"], root)
    _run([sys.executable, "-m", "pip", "install", "-r", "requirements-gui.txt"], root)

    if os.path.isdir(dist_tmp):
        shutil.rmtree(dist_tmp, ignore_errors=True)

    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "build.spec",
            "--clean",
            "--distpath",
            dist_tmp,
        ],
        root,
    )

    if not os.path.isfile(src_exe):
        print("FEHLER: Erwartete Datei fehlt:", src_exe, file=sys.stderr)
        return 1

    os.makedirs(dist_dir, exist_ok=True)
    if os.path.isfile(dst_exe):
        try:
            os.remove(dst_exe)
        except OSError as e:
            print("FEHLER: Konnte alte dist-EXE nicht löschen:", e, file=sys.stderr)
            return 1

    try:
        shutil.move(src_exe, dst_exe)
    except OSError:
        shutil.copy2(src_exe, dst_exe)
        try:
            os.remove(src_exe)
        except OSError:
            pass

    if not os.path.isfile(dst_exe):
        print("FEHLER: dist-EXE fehlt nach Verschieben/Kopieren.", file=sys.stderr)
        return 1

    shutil.rmtree(dist_tmp, ignore_errors=True)

    print("\nBuild abgeschlossen.", flush=True)
    print("  Datei:", dst_exe, flush=True)
    print("  Größe:", os.path.getsize(dst_exe), "Bytes", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
