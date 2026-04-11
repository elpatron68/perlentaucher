"""
Wishlist-Tab: Einträge verwalten und Downloads anstoßen.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QLabel,
    QAbstractItemView,
    QListWidget,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Projekt-Root (wie download_panel/thread_manager: gui/ -> src/ -> root), nicht nur src/
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def wishlist_path_from_config(config: Dict) -> str:
    from src.wishlist_core import default_wishlist_path

    custom = (config.get("wishlist_file") or "").strip()
    if custom:
        return custom
    return default_wishlist_path(config.get("download_dir", "."))


class WishlistProcessThread(QThread):
    finished_ok = pyqtSignal(int, int)

    def __init__(self, wishlist_path: str, args_obj: object, parent=None):
        super().__init__(parent)
        self.wishlist_path = wishlist_path
        self.args_obj = args_obj

    def run(self):
        from src.wishlist_core import process_wishlist_items

        p, s = process_wishlist_items(self.wishlist_path, self.args_obj, remove_on_success=True)
        self.finished_ok.emit(p, s)


class WishlistCheckThread(QThread):
    items_ready = pyqtSignal(list)

    def __init__(self, wishlist_path: str, config: Dict, parent=None):
        super().__init__(parent)
        self.wishlist_path = wishlist_path
        self.config = config

    def run(self):
        from src.wishlist_core import check_wishlist_availability

        avail, _total = check_wishlist_availability(
            self.wishlist_path,
            sprache=self.config.get("sprache", "deutsch"),
            audiodeskription=self.config.get("audiodeskription", "egal"),
            serien_download=self.config.get("serien_download", "erste"),
            tmdb_api_key=self.config.get("tmdb_api_key") or None,
            omdb_api_key=self.config.get("omdb_api_key") or None,
        )
        self.items_ready.emit([x.to_dict() for x in avail])


class WishlistProbeAfterAddThread(QThread):
    """Mediathek-Probe nach neuem Eintrag (blockiert GUI nicht)."""

    result_ready = pyqtSignal(object)

    def __init__(self, item, config: Dict, parent=None):
        super().__init__(parent)
        self._item = item
        self._config = config

    def run(self):
        from src.wishlist_core import probe_wishlist_item

        r = probe_wishlist_item(
            self._item,
            sprache=self._config.get("sprache", "deutsch"),
            audiodeskription=self._config.get("audiodeskription", "egal"),
            serien_download=self._config.get("serien_download", "erste"),
            tmdb_api_key=self._config.get("tmdb_api_key") or None,
            omdb_api_key=self._config.get("omdb_api_key") or None,
        )
        self.result_ready.emit(r)


class WishlistDownloadOneItemThread(QThread):
    """Lädt genau einen Wishlist-Eintrag (optional Treffer-Index)."""

    done = pyqtSignal(bool, str)

    def __init__(
        self,
        wishlist_path: str,
        item_id: str,
        args_obj: object,
        candidate_index: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self._path = wishlist_path
        self._item_id = item_id
        self._args_obj = args_obj
        self._candidate_index = candidate_index

    def run(self):
        from src.wishlist_core import process_one_wishlist_item

        ok, code = process_one_wishlist_item(
            self._path,
            self._item_id,
            self._args_obj,
            candidate_index=self._candidate_index,
            remove_on_success=True,
        )
        self.done.emit(ok, code)


class WishlistPanel(QWidget):
    """Wishlist mit Tabelle und Aktionen."""

    # Signal: Einträge sind in der Mediathek verfügbar (Startup-Check)
    availability_found = pyqtSignal(list)
    # Nach automatischer Verarbeitung beim Start (processed, successes)
    startup_process_finished = pyqtSignal(int, int)

    def __init__(self, get_config_callable, parent=None):
        """
        Args:
            get_config_callable: callable -> Dict (z.B. settings_panel.get_config)
        """
        super().__init__(parent)
        self._get_config = get_config_callable
        self._process_thread: Optional[WishlistProcessThread] = None
        self._startup_process_thread: Optional[WishlistProcessThread] = None
        self._probe_add_thread: Optional[WishlistProbeAfterAddThread] = None
        self._download_one_thread: Optional[WishlistDownloadOneItemThread] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        info = QLabel(
            "Filme und Serien, die noch nicht in der öffentlichen Mediathek sind. "
            "Mit „Verarbeiten“ wird gesucht und bei Treffer heruntergeladen."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("Hinzufügen…")
        self.btn_remove = QPushButton("Entfernen")
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_process = QPushButton("Verarbeiten (Download)")
        self.btn_download_sel = QPushButton("Auswahl wie Feed herunterladen")
        for b in (
            self.btn_add,
            self.btn_remove,
            self.btn_refresh,
            self.btn_process,
            self.btn_download_sel,
        ):
            toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Titel", "Jahr", "Typ", "Notiz", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.btn_add.clicked.connect(self._on_add)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_process.clicked.connect(self._on_process)
        self.btn_download_sel.clicked.connect(self._on_download_like_feed)

    def refresh(self):
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        from src.wishlist_core import list_items

        try:
            items = list_items(path)
        except Exception as e:
            logging.warning(f"Wishlist laden: {e}")
            QMessageBox.warning(self, "Wishlist", str(e))
            return

        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(it.title))
            self.table.setItem(row, 1, QTableWidgetItem(str(it.year) if it.year else ""))
            typ = "Serie" if it.kind == "series" else "Film"
            self.table.setItem(row, 2, QTableWidgetItem(typ))
            self.table.setItem(row, 3, QTableWidgetItem(it.note))
            self.table.setItem(row, 4, QTableWidgetItem(it.id))
        self.table.resizeColumnsToContents()

    def _selected_id(self) -> Optional[str]:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        r = rows[0].row()
        id_item = self.table.item(r, 4)
        return id_item.text() if id_item else None

    def _on_add(self):
        d = QDialog(self)
        d.setWindowTitle("Wishlist-Eintrag")
        form = QFormLayout(d)
        title_e = QLineEdit()
        year_e = QLineEdit()
        year_e.setPlaceholderText("optional")
        kind_c = QComboBox()
        kind_c.addItems(["Film", "Serie"])
        note_e = QLineEdit()
        form.addRow("Titel:", title_e)
        form.addRow("Jahr:", year_e)
        form.addRow("Typ:", kind_c)
        form.addRow("Notiz:", note_e)
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Abbrechen")
        h = QHBoxLayout()
        h.addWidget(btn_ok)
        h.addWidget(btn_cancel)
        form.addRow(h)
        btn_ok.clicked.connect(d.accept)
        btn_cancel.clicked.connect(d.reject)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        t = title_e.text().strip()
        if not t:
            QMessageBox.warning(self, "Wishlist", "Bitte einen Titel eingeben.")
            return
        year = None
        if year_e.text().strip():
            try:
                year = int(year_e.text().strip())
            except ValueError:
                QMessageBox.warning(self, "Wishlist", "Jahr ungültig.")
                return
        kind = "series" if kind_c.currentIndex() == 1 else "movie"
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        from src.wishlist_core import add_item

        item = add_item(path, t, year, kind, note=note_e.text().strip())
        self.refresh()
        self._start_probe_after_add(item)

    def _start_probe_after_add(self, item):
        cfg = self._get_config()
        self._probe_add_thread = WishlistProbeAfterAddThread(item, cfg)
        self._probe_add_thread.result_ready.connect(
            lambda r, iid=item.id: self._on_probe_after_add_result(r, iid)
        )
        self._probe_add_thread.start()

    def _on_probe_after_add_result(self, probe: dict, item_id: str):
        if probe.get("status") == "serien_skipped":
            QMessageBox.information(
                self,
                "Wishlist",
                probe.get("message", "Serien-Download ist deaktiviert."),
            )
            return
        if probe.get("status") == "not_found":
            QMessageBox.information(
                self,
                "Wishlist",
                "Kein passender Treffer in der Mediathek gefunden. "
                "Der Eintrag bleibt auf der Liste — du kannst später „Verarbeiten“ nutzen.",
            )
            return
        if probe.get("status") == "staffel_available":
            n = int(probe.get("episode_count") or 0)
            reply = QMessageBox.question(
                self,
                "Wishlist",
                f"In der Mediathek wurden etwa {n} Episoden gefunden.\n\n"
                "Gesamte Staffel jetzt herunterladen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._start_download_one_item(item_id, 0)
            return

        cands = probe.get("candidates") or []
        if not cands:
            return

        st = probe.get("status")
        cand_idx = 0
        if st == "ambiguous":
            dlg = QDialog(self)
            dlg.setWindowTitle("Treffer auswählen")
            v = QVBoxLayout(dlg)
            v.addWidget(
                QLabel("Mehrere mögliche Treffer — bitte die passende Fassung wählen:")
            )
            lw = QListWidget()
            for c in cands:
                lw.addItem(
                    f"{c['title']}  (Ähnlichkeit {c['title_similarity']:.2f}, Score {c['score']:.0f})"
                )
            lw.setCurrentRow(0)
            v.addWidget(lw)
            bb = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
            )
            bb.accepted.connect(dlg.accept)
            bb.rejected.connect(dlg.reject)
            v.addWidget(bb)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            cand_idx = lw.currentRow()
        else:
            top = cands[0]
            reply = QMessageBox.question(
                self,
                "Wishlist",
                f"In der Mediathek gefunden:\n„{top['title']}“\n\nJetzt herunterladen?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            cand_idx = 0

        self._start_download_one_item(item_id, cand_idx)

    def _start_download_one_item(self, item_id: str, candidate_index: int):
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        args_obj = self._build_process_args(cfg)
        self._download_one_thread = WishlistDownloadOneItemThread(
            path, item_id, args_obj, candidate_index
        )
        self._download_one_thread.done.connect(self._on_download_one_item_done)
        self._download_one_thread.start()

    def _on_download_one_item_done(self, ok: bool, code: str):
        if ok and code == "success":
            QMessageBox.information(
                self,
                "Wishlist",
                "Download erfolgreich. Der Eintrag wurde von der Wishlist entfernt.",
            )
        elif ok and code == "debug":
            QMessageBox.information(
                self,
                "Wishlist",
                "Debug-Modus: Es wurde kein Download durchgeführt.",
            )
        else:
            QMessageBox.warning(
                self,
                "Wishlist",
                f"Download nicht erfolgreich (Code: {code}). Der Eintrag bleibt auf der Liste.",
            )
        self.refresh()

    def _on_remove(self):
        iid = self._selected_id()
        if not iid:
            QMessageBox.information(self, "Wishlist", "Bitte eine Zeile auswählen.")
            return
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        from src.wishlist_core import remove_item

        if remove_item(path, iid):
            self.refresh()
        else:
            QMessageBox.warning(self, "Wishlist", "Eintrag konnte nicht entfernt werden.")

    def _build_process_args(self, cfg: Dict):
        class A:
            pass

        a = A()
        a.sprache = cfg.get("sprache", "deutsch")
        a.audiodeskription = cfg.get("audiodeskription", "egal")
        a.serien_download = cfg.get("serien_download", "erste")
        a.tmdb_api_key = cfg.get("tmdb_api_key") or None
        a.omdb_api_key = cfg.get("omdb_api_key") or None
        a.notify = cfg.get("notify") or None
        a.debug_no_download = cfg.get("debug_no_download", False)
        a.download_dir = cfg.get("download_dir", ".")
        a.serien_dir = cfg.get("serien_dir") or None
        a.no_state = cfg.get("no_state", False)
        a.state_file = cfg.get("state_file", ".perlentaucher_state.json")
        return a

    def _on_process(self):
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        args_obj = self._build_process_args(cfg)
        self.btn_process.setEnabled(False)
        self._process_thread = WishlistProcessThread(path, args_obj)
        self._process_thread.finished_ok.connect(self._on_process_done)
        self._process_thread.start()

    def _on_process_done(self, processed: int, successes: int):
        self.btn_process.setEnabled(True)
        QMessageBox.information(
            self,
            "Wishlist",
            f"Verarbeitet: {processed}, erfolgreiche Downloads: {successes}.",
        )
        self.refresh()

    def _on_download_like_feed(self):
        """Startet Download-Tab mit synthetischen Einträgen (wie Feed)."""
        iid = self._selected_id()
        if not iid:
            QMessageBox.information(self, "Wishlist", "Bitte eine Zeile auswählen.")
            return
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        from src.wishlist_core import list_items

        items = {it.id: it for it in list_items(path)}
        it = items.get(iid)
        if not it:
            return
        entry = {
            "entry_id": f"wishlist_gui:{it.id}",
            "entry": {"title": it.title, "tags": [{"term": "TV-Serien"}] if it.kind == "series" else []},
            "movie_title": it.title,
            "year": it.year,
            "metadata": {},
            "entry_link": "",
            "rss_title": it.title,
            "is_series_override": True if it.kind == "series" else False,
        }
        self.download_like_feed_requested.emit(entry, cfg)

    # Wird in MainWindow mit download_panel.start_downloads verbunden
    download_like_feed_requested = pyqtSignal(object, object)

    def run_startup_check(self):
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        self._check_thread = WishlistCheckThread(path, cfg)
        self._check_thread.items_ready.connect(self._on_startup_items)
        self._check_thread.start()

    def run_startup_process(self):
        """Wishlist wie „Verarbeiten“ im Hintergrund (ohne Modal-Dialog, für Programmstart)."""
        cfg = self._get_config()
        path = wishlist_path_from_config(cfg)
        args_obj = self._build_process_args(cfg)
        self._startup_process_thread = WishlistProcessThread(path, args_obj)
        self._startup_process_thread.finished_ok.connect(self._on_startup_process_done)
        self._startup_process_thread.start()

    def _on_startup_process_done(self, processed: int, successes: int):
        self.refresh()
        self.startup_process_finished.emit(processed, successes)

    def _on_startup_items(self, items: List[dict]):
        if items:
            self.availability_found.emit(items)

