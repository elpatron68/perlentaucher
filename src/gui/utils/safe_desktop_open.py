"""
Öffnet URLs und lokale Ordner über System-Helfer ohne geerbte Linker-Umgebung von PyInstaller.

Bundled Linux-GUIs setzen häufig LD_LIBRARY_PATH; Kindprozesse wie ``xdg-open`` → ``/bin/sh``
können sonst inkompatible libreadline laden (symbol lookup error).
Analog können unter macOS DYLD-Variablen problematisch sein — für externe Helfer bereinigen wir die Umgebung.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from typing import Dict, Iterable

_LOG = logging.getLogger(__name__)

_LINUX_STRIP: Iterable[str] = (
    "LD_LIBRARY_PATH",
    "ORIG_LD_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
)
_DARWIN_STRIP: Iterable[str] = (
    "DYLD_LIBRARY_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_FORCE_FLAT_NAMESPACE",
)


def _sanitized_env_for_external_process() -> Dict[str, str]:
    env = dict(os.environ)
    if sys.platform.startswith("linux"):
        for k in _LINUX_STRIP:
            env.pop(k, None)
    elif sys.platform == "darwin":
        for k in _DARWIN_STRIP:
            env.pop(k, None)
    return env


def _spawn_detached(argv: list[str], env: Dict[str, str]) -> bool:
    prog = argv[0]
    if os.sep not in prog and shutil.which(prog) is None:
        return False
    try:
        subprocess.Popen(
            argv,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=sys.platform != "win32",
        )
        return True
    except OSError as exc:
        _LOG.warning("Konnte nicht starten: %s (%s)", argv, exc)
        return False


def _open_url_qt(url: str) -> bool:
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices

        return bool(QDesktopServices.openUrl(QUrl(url)))
    except ImportError:
        pass
    try:
        import webbrowser

        return bool(webbrowser.open(url))
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Fallback webbrowser.open fehlgeschlagen: %s", exc)
        return False


def open_url(url: str) -> bool:
    """
    Öffnet eine URL (http/https/…) mit dem Standard-Handler des Systems.
    Unter Linux ohne geerbtes LD_LIBRARY_PATH; unter macOS ohne DYLD-* für Hilfsprogramme.
    """
    url = (url or "").strip()
    if not url:
        return False

    if sys.platform.startswith("linux"):
        env = _sanitized_env_for_external_process()
        for argv in (["xdg-open", url], ["gio", "open", url]):
            if shutil.which(argv[0]) and _spawn_detached(argv, env):
                return True
        return _open_url_qt(url)

    if sys.platform == "darwin":
        env = _sanitized_env_for_external_process()
        if _spawn_detached(["open", url], env):
            return True
        return _open_url_qt(url)

    if sys.platform == "win32":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except OSError:
            pass
        return _open_url_qt(url)

    return _open_url_qt(url)


def open_folder(path: str) -> bool:
    """Öffnet einen bestehenden Ordner im Dateimanager (wie Explorer/Finder/Dolphin …)."""
    folder = os.path.abspath(path)
    if not folder or not os.path.isdir(folder):
        return False

    if sys.platform == "win32":
        try:
            os.startfile(folder)  # type: ignore[attr-defined]
            return True
        except OSError:
            return False

    env = _sanitized_env_for_external_process()
    if sys.platform == "darwin":
        if _spawn_detached(["open", folder], env):
            return True
        return False

    for argv in (["xdg-open", folder], ["gio", "open", folder]):
        if shutil.which(argv[0]) and _spawn_detached(argv, env):
            return True
    return False
