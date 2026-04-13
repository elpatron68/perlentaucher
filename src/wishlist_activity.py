"""
Gemeinsamer Aktivitäts-/Verlauf (CLI, GUI, Wishlist-Web): JSON im Download-Ordner.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

_lock = threading.Lock()
MAX_ENTRIES = 400

ACTIVITY_FILENAME = ".perlentaucher_activity.json"
LEGACY_WISHLIST_ACTIVITY = ".perlentaucher_wishlist_activity.json"

Level = Literal["info", "success", "warning", "error"]


def default_activity_path(download_dir: Optional[str] = None) -> str:
    """Pfad zur Aktivitätsdatei (ohne Legacy-Migration)."""
    base = download_dir or os.getcwd()
    return os.path.join(base, ACTIVITY_FILENAME)


def resolve_activity_path(download_dir: Optional[str] = None) -> str:
    """
    Pfad zur Aktivitätsdatei. Migriert einmalig von .perlentaucher_wishlist_activity.json
    falls die neue Datei noch nicht existiert.
    """
    base = download_dir or os.getcwd()
    new_p = os.path.join(base, ACTIVITY_FILENAME)
    old_p = os.path.join(base, LEGACY_WISHLIST_ACTIVITY)
    if not os.path.exists(new_p) and os.path.exists(old_p):
        try:
            shutil.copy2(old_p, new_p)
        except OSError as e:
            logging.debug(f"Aktivitäts-Legacy-Migration übersprungen: {e}")
    return new_p


def _load(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"version": 2, "entries": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "entries" not in data:
            data = {"version": 2, "entries": []}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Aktivitätslog konnte nicht gelesen werden ({path}): {e}")
        return {"version": 2, "entries": []}


def _save(path: str, data: Dict[str, Any]) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def append_activity(
    path: str,
    action: str,
    label: str,
    detail: str = "",
    level: Level = "info",
    source: str = "cli",
) -> None:
    """Fügt einen Eintrag am Anfang ein (neueste zuerst beim Lesen)."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "label": (label or "")[:500],
        "detail": (detail or "")[:2000],
        "level": level,
        "source": (source or "cli")[:32],
    }
    with _lock:
        data = _load(path)
        entries: List[Dict[str, Any]] = data.get("entries", [])
        entries.insert(0, entry)
        data["entries"] = entries[:MAX_ENTRIES]
        data["version"] = 2
        _save(path, data)


def log_activity_event(
    download_dir: Optional[str],
    action: str,
    label: str,
    detail: str = "",
    level: Level = "info",
    source: str = "cli",
) -> None:
    """Schreibt ein Ereignis in den gemeinsamen Log unter ``download_dir``."""
    if not download_dir:
        return
    try:
        append_activity(resolve_activity_path(download_dir), action, label, detail, level, source)
    except OSError as e:
        logging.debug(f"Aktivitätslog konnte nicht geschrieben werden: {e}")


def log_wishlist_item_result(
    download_dir: Optional[str],
    title: str,
    ok: bool,
    code: str,
    source: str = "cli",
) -> None:
    """Ergebnis von ``process_one_wishlist_item`` protokollieren."""
    if not download_dir:
        return
    if ok and code == "success":
        log_activity_event(download_dir, "wishlist_download", title, "Download abgeschlossen", "success", source)
        return
    if code == "debug":
        log_activity_event(download_dir, "wishlist_download", title, "Debug: kein echter Download", "info", source)
        return
    if code == "not_found":
        log_activity_event(download_dir, "wishlist_download", title, "Kein Mediathek-Treffer", "warning", source)
        return
    if code == "not_found_item":
        log_activity_event(download_dir, "wishlist_download", title, "Wishlist-Eintrag nicht gefunden", "warning", source)
        return
    if code == "serien_skipped":
        log_activity_event(download_dir, "wishlist_download", title, "Serien-Download ist deaktiviert", "warning", source)
        return
    if ok:
        log_activity_event(download_dir, "wishlist_download", title, f"OK (code={code})", "success", source)
    else:
        log_activity_event(download_dir, "wishlist_download", title, f"Fehlgeschlagen (code={code})", "error", source)


def list_activity(path: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Liefert die neuesten Einträge zuerst."""
    lim = max(1, min(int(limit), 200))
    with _lock:
        data = _load(path)
    entries = data.get("entries", [])
    return entries[:lim]


def clear_activity(path: str) -> None:
    with _lock:
        _save(path, {"version": 2, "entries": []})


def summarize_probe_for_log(probe: Dict[str, Any]) -> tuple[str, Level]:
    """Kurzbeschreibung und Schwere für Log nach probe_wishlist_item."""
    st = probe.get("status") or ""
    if st == "not_found":
        return "Kein Treffer in der Mediathek", "warning"
    if st == "probe_error":
        return probe.get("message") or "Mediathek-Prüfung fehlgeschlagen", "warning"
    if st == "serien_skipped":
        return probe.get("message") or "Serien-Download deaktiviert", "warning"
    if st == "staffel_available":
        n = int(probe.get("episode_count") or 0)
        return f"Staffel gefunden (~{n} Episoden)", "success"
    if st == "ambiguous":
        return "Mehrere Treffer — Auswahl nötig", "info"
    if st == "clear":
        return "Treffer gefunden", "success"
    return f"Status: {st}", "info"
