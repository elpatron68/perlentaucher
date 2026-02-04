"""
Download Panel für die GUI-Anwendung.
Zeigt aktive Downloads mit Progress Bars und Log-Ausgabe.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QLabel, QProgressBar,
    QAbstractItemView, QMessageBox, QSizePolicy, QLineEdit, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt6.QtGui import QFont
from typing import Dict, List, Optional
import logging
import os
import subprocess
import sys
from datetime import datetime


class DownloadPanel(QWidget):
    """Panel für Download-Status."""

    search_download_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initialisiert das Download Panel.
        
        Args:
            parent: Parent Widget
        """
        super().__init__(parent)
        self.active_downloads = {}  # entry_id -> DownloadThread
        self.download_rows = {}  # entry_id -> row index
        self._init_ui()
        
        # Log Handler für Textausgabe
        self.log_handler = TextEditLogHandler(self.log_text)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def _init_ui(self):
        """Initialisiert die UI-Komponenten."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.start_downloads_btn = QPushButton("Ausgewählte Downloads starten")
        self.start_downloads_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }")
        self.start_downloads_btn.setEnabled(False)
        
        self.cancel_all_btn = QPushButton("Alle Downloads abbrechen")
        self.cancel_all_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 8px; }")
        self.cancel_all_btn.setEnabled(False)
        self.cancel_all_btn.clicked.connect(self._cancel_all_downloads)
        
        self.clear_log_btn = QPushButton("Log löschen")
        self.clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        
        toolbar.addWidget(self.start_downloads_btn)
        toolbar.addWidget(self.cancel_all_btn)
        toolbar.addWidget(self.clear_log_btn)
        toolbar.addStretch()
        
        # Status-Label
        self.status_label = QLabel("Bereit. Wählen Sie Downloads im Blog-Liste-Tab aus.")
        toolbar.addWidget(self.status_label)
        
        layout.addLayout(toolbar)

        # Suchbegriff: Film suchen und herunterladen
        search_layout = QHBoxLayout()
        self.search_line = QLineEdit()
        self.search_line.setPlaceholderText("Filmtitel suchen (z.B. The Quiet Girl)")
        self.search_line.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_line)
        self.search_download_btn = QPushButton("Film suchen und herunterladen")
        self.search_download_btn.setStyleSheet("QPushButton { padding: 6px 12px; }")
        self.search_download_btn.clicked.connect(self._on_search_download_clicked)
        search_layout.addWidget(self.search_download_btn)
        layout.addLayout(search_layout)
        
        # Download-Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Titel", "Fortschritt", "Status", "Geschwindigkeit", "Aktion"
        ])
        
        # Stelle sicher, dass die Tabelle vertikal skalierbar ist
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Titel
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Fortschritt
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Status - feste Breite
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Geschwindigkeit
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Aktion
        
        # Setze feste Breite für Status-Spalte (verhindert springende Spaltenbreite)
        self.table.setColumnWidth(2, 150)
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        
        layout.addWidget(self.table, stretch=1)  # Stretch-Faktor für vertikale Skalierung
        
        # Log-Ausgabe
        log_label = QLabel("Log-Ausgabe:")
        layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        self.log_text.setMinimumHeight(100)
        self.log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.log_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)
    
    def _on_table_context_menu(self, pos):
        """Zeigt Kontextmenü für die Tabelle; bei erfolgreichem Download: 'Ordner öffnen'."""
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        title_item = self.table.item(row, 0)
        filepath = getattr(title_item, "_filepath", None) if title_item else None
        menu = QMenu(self)
        open_folder_action = menu.addAction("Ordner öffnen")
        open_folder_action.setEnabled(bool(filepath))
        if filepath:
            open_folder_action.triggered.connect(lambda: self._open_folder_for_file(filepath))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_folder_for_file(self, filepath: str):
        """Öffnet den Ordner der Datei im systemeigenen Dateimanager (plattformunabhängig)."""
        folder = os.path.abspath(os.path.dirname(filepath))
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(
                self,
                "Ordner nicht gefunden",
                f"Der Ordner existiert nicht oder ist nicht erreichbar:\n{folder}",
            )
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=True)
            else:
                subprocess.run(["xdg-open", folder], check=True)
        except (OSError, subprocess.CalledProcessError) as e:
            logging.warning(f"Ordner konnte nicht geöffnet werden: {e}")
            QMessageBox.warning(
                self,
                "Ordner öffnen",
                f"Der Ordner konnte nicht geöffnet werden:\n{e}",
            )

    def _on_search_download_clicked(self):
        """Reagiert auf Klick 'Film suchen und herunterladen': prüft Suchtext und sendet Signal."""
        search_term = (self.search_line.text() or "").strip()
        if not search_term:
            QMessageBox.warning(
                self,
                "Kein Suchbegriff",
                "Bitte geben Sie einen Filmtitel oder Suchbegriff ein.",
            )
            return
        self.search_download_requested.emit(search_term)

    def start_downloads(self, entries: List[Dict], config: Dict, series_download_mode: Optional[Dict] = None):
        """
        Startet Downloads für die ausgewählten Einträge.
        
        Args:
            entries: Liste von Entry-Dictionaries
            config: Konfigurations-Dictionary
            series_download_mode: Optional - Dictionary mit entry_id -> 'erste' oder 'staffel' für Serien
        """
        if not entries:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie mindestens einen Eintrag aus!")
            return
        
        # Speichere Config für State-Datei-Updates
        self._config = config
        
        # Import hier um Circular Import zu vermeiden
        from .utils.thread_manager import DownloadThread
        
        for entry_data in entries:
            entry_id = entry_data['entry_id']
            
            # Überspringe bereits verarbeitete, es sei denn Benutzer möchte erneut versuchen
            if entry_data.get('is_processed'):
                reply = QMessageBox.question(
                    self,
                    "Bereits verarbeitet",
                    f"'{entry_data.get('movie_title', entry_data['rss_title'])}' wurde bereits verarbeitet.\n"
                    "Trotzdem herunterladen?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    continue
            
            # Hole Metadata wenn API-Keys vorhanden (aber behalte Jahr aus RSS-Feed)
            if entry_data.get('movie_title'):
                movie_title = entry_data['movie_title']
                year = entry_data.get('year')
                tmdb_key = config.get('tmdb_api_key')
                omdb_key = config.get('omdb_api_key')
                
                # Importiere core-Modul
                import sys
                import os
                src_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                if src_dir not in sys.path:
                    sys.path.insert(0, src_dir)
                from src import perlentaucher as core
                
                # Hole Metadata (das Jahr aus RSS-Feed wird beibehalten wenn keine API verwendet wird)
                # get_metadata() initialisiert bereits mit year aus RSS-Feed
                metadata = core.get_metadata(movie_title, year, tmdb_key, omdb_key)
                # Stelle sicher, dass Jahr aus RSS-Feed verwendet wird wenn API kein Jahr zurückgibt
                if not metadata.get('year') and year:
                    metadata['year'] = year
                entry_data['metadata'] = metadata
                
                # Aktualisiere is_series basierend auf Metadata
                entry_obj = entry_data.get('entry')
                if entry_obj:
                    entry_data['is_series'] = core.is_series(entry_obj, metadata)
            
            # Bestimme Serien-Download-Modus für diesen Eintrag
            series_mode = None
            if entry_data.get('is_series', False):
                if series_download_mode and entry_id in series_download_mode:
                    series_mode = series_download_mode[entry_id]
                else:
                    # Fallback auf Config-Einstellung
                    series_mode = config.get('serien_download', 'erste')
            
            # Erstelle Download-Thread
            thread = DownloadThread(entry_data, config, series_download_mode=series_mode)
            
            # Verbinde Signals mit Lambda-Funktionen (entry_id wird als Closure erfasst)
            # WICHTIG: Verwende explizite Parameter-Namen, um Referenz-Probleme zu vermeiden
            thread.download_started.connect(lambda title, eid=entry_id: self._on_download_started(eid, title))
            thread.progress_updated.connect(lambda progress, status, eid=entry_id: self._on_progress_updated(eid, progress, status))
            thread.download_finished.connect(lambda success, title, filepath, error, eid=entry_id: 
                                           self._on_download_finished(eid, success, title, filepath, error))
            
            # Füge zur Tabelle hinzu
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.download_rows[entry_id] = row
            
            title_item = QTableWidgetItem(entry_data.get('movie_title', entry_data['rss_title']))
            # Speichere Entry-Daten für späteren Zugriff
            title_item._entry_data = entry_data
            self.table.setItem(row, 0, title_item)
            
            # Progress Bar
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            self.table.setCellWidget(row, 1, progress_bar)
            
            status_item = QTableWidgetItem("Wartend...")
            self.table.setItem(row, 2, status_item)
            
            speed_item = QTableWidgetItem("")
            self.table.setItem(row, 3, speed_item)
            
            # Cancel-Button
            cancel_btn = QPushButton("Abbrechen")
            cancel_btn.clicked.connect(lambda checked, eid=entry_id: self._cancel_download(eid))
            self.table.setCellWidget(row, 4, cancel_btn)
            
            # Speichere Thread
            self.active_downloads[entry_id] = thread
            
            # Starte Download
            thread.start()
            logging.info(f"Download gestartet: {entry_data.get('movie_title', entry_data['rss_title'])}")
        
        self.status_label.setText(f"{len(entries)} Download(s) gestartet.")
        self.start_downloads_btn.setEnabled(False)
        self.cancel_all_btn.setEnabled(True)
    
    def _on_download_started(self, entry_id: str, title: str):
        """Wird aufgerufen wenn ein Download gestartet wird."""
        if entry_id in self.download_rows:
            row = self.download_rows[entry_id]
            status_item = self.table.item(row, 2)
            if status_item:
                status_item.setText("Läuft...")
                status_item.setForeground(Qt.GlobalColor.blue)
    
    def _on_progress_updated(self, entry_id: str, progress: int, status: str):
        """Wird aufgerufen wenn sich der Download-Fortschritt aktualisiert."""
        if entry_id in self.download_rows:
            row = self.download_rows[entry_id]
            
            # Update Progress Bar
            progress_bar = self.table.cellWidget(row, 1)
            if progress_bar:
                progress_bar.setValue(progress)
            
            # Update Status
            status_item = self.table.item(row, 2)
            if status_item:
                status_item.setText(status)
            
            # Update Speed (vereinfacht - könnte berechnet werden)
            speed_item = self.table.item(row, 3)
            if speed_item and "MB" in status:
                speed_item.setText(status)
    
    def _on_download_finished(self, entry_id: str, success: bool, title: str, filepath: str, error: str):
        """Wird aufgerufen wenn ein Download abgeschlossen ist."""
        try:
            if entry_id not in self.download_rows:
                logging.warning(f"Download-Finished: entry_id {entry_id} nicht in download_rows gefunden")
                return
            
            row = self.download_rows[entry_id]
            
            # Hole Entry-Daten um State-Datei zu aktualisieren
            entry_data = None
            title_item = self.table.item(row, 0)
            if title_item:
                # Versuche Entry-Daten aus UserData zu holen (falls gespeichert)
                entry_data = getattr(title_item, '_entry_data', None)
            
            # Normalisiere filepath (kann None oder leerer String sein)
            filepath = filepath if filepath else ""
            
            # Debug-Modus: Downloads werden übersprungen, State-Datei nicht anfassen
            config = getattr(self, '_config', {})
            debug_no_download = config.get('debug_no_download', False)
            skip_state_update = debug_no_download and error == "DEBUG_NO_DOWNLOAD"
            
            # Update Status
            status_item = self.table.item(row, 2)
            if status_item:
                if success:
                    if skip_state_update:
                        status_item.setText("Debug: übersprungen")
                        status_item.setForeground(Qt.GlobalColor.gray)
                        logging.info(f"DEBUG-MODUS: Download übersprungen: {title}")
                        # Keine State-Datei-Updates im Debug-Modus
                        # Trotzdem Progress auf 100 setzen und aufräumen
                    else:
                        # Prüfe ob es ein Staffel-Download war (mehrere Episoden)
                        # Staffel-Downloads haben typischerweise "Episoden" im Titel und keinen einzelnen filepath
                        is_series_download = (
                            entry_data and 
                            entry_data.get('is_series', False) and 
                            (not filepath or not filepath.strip()) and 
                            "Episoden" in (title or "")
                        )
                        
                        if is_series_download:
                            # Staffel-Download - State-Datei wurde bereits im Thread aktualisiert
                            status_text = "✓ Erfolgreich"
                            if error and error.strip():
                                status_text += f" ({error})"
                            elif title and "Episoden" in title:
                                # Extrahiere nur den relevanten Teil (z.B. "3/5 Episoden")
                                import re
                                match = re.search(r'(\d+/\d+\s+Episoden)', title)
                                if match:
                                    status_text += f" ({match.group(1)})"
                            status_item.setText(status_text)
                        else:
                            # Einzelner Download
                            status_item.setText("✓ Erfolgreich")
                            # Aktualisiere State-Datei für erfolgreichen Download
                            if entry_data:
                                try:
                                    self._update_state_file(entry_id, entry_data, 'download_success', filepath if filepath else None)
                                except Exception as e:
                                    logging.warning(f"Fehler beim Aktualisieren der State-Datei: {e}")
                        
                        status_item.setForeground(Qt.GlobalColor.green)
                        # Dateipfad für Kontextmenü "Ordner öffnen" speichern
                        if filepath and filepath.strip() and title_item:
                            title_item._filepath = filepath.strip()
                        # Sichere Logging-Ausgabe (filepath kann leer sein)
                        log_msg = f"Download erfolgreich: {title}"
                        if filepath and filepath.strip():
                            log_msg += f" -> {filepath}"
                        logging.info(log_msg)
                else:
                    status_text = f"✗ Fehlgeschlagen"
                    if error and error.strip():
                        # Kürze sehr lange Fehlermeldungen für bessere Anzeige
                        error_short = error[:100] + "..." if len(error) > 100 else error
                        status_text += f": {error_short}"
                    status_item.setText(status_text)
                    status_item.setForeground(Qt.GlobalColor.red)
                    logging.error(f"Download fehlgeschlagen: {title} - {error}")
                    
                    # Prüfe ob Staffel-Download (State-Datei wurde bereits im Thread aktualisiert)
                    is_series_download = entry_data and entry_data.get('is_series', False) and error and "Episoden" in error
                    
                    if not is_series_download:
                        # Aktualisiere State-Datei für fehlgeschlagenen Download
                        if entry_data:
                            try:
                                if error and "nicht gefunden" in error.lower():
                                    self._update_state_file(entry_id, entry_data, 'not_found', None)
                                else:
                                    self._update_state_file(entry_id, entry_data, 'download_failed', None)
                            except Exception as e:
                                logging.warning(f"Fehler beim Aktualisieren der State-Datei: {e}")
            
            # Update Progress Bar
            progress_bar = self.table.cellWidget(row, 1)
            if progress_bar:
                progress_bar.setValue(100 if success else 0)
            
            # Entferne Cancel-Button
            self.table.setCellWidget(row, 4, None)
            
            # WICHTIG: Räume Thread ordnungsgemäß auf, bevor wir ihn entfernen
            # Dies verhindert, dass die App sich beendet, wenn alle Downloads fertig sind
            if entry_id in self.active_downloads:
                thread = self.active_downloads[entry_id]
                # Warte darauf, dass der Thread vollständig beendet ist (falls er noch läuft)
                # Der Thread sollte bereits beendet sein, da das Signal nur nach run() gesendet wird
                if thread.isRunning():
                    logging.warning(f"Thread für {entry_id} läuft noch, warte auf Beendigung...")
                    thread.wait(5000)  # Warte max. 5 Sekunden
                    if thread.isRunning():
                        logging.error(f"Thread für {entry_id} konnte nicht beendet werden!")
                        # Breche Thread ab
                        thread.terminate()
                        thread.wait(1000)
                
                # Trenne alle Signal-Verbindungen, um Referenzen zu lösen und Memory Leaks zu vermeiden
                # WICHTIG: Dies verhindert, dass Signal-Verbindungen die App am Beenden hindern
                try:
                    # Versuche alle Signal-Verbindungen zu trennen (ignoriere Fehler)
                    thread.download_started.disconnect()
                except (TypeError, RuntimeError):
                    pass
                
                try:
                    thread.progress_updated.disconnect()
                except (TypeError, RuntimeError):
                    pass
                
                try:
                    thread.download_finished.disconnect()
                except (TypeError, RuntimeError):
                    pass
                
                # Entferne Thread aus Dictionary (dies sollte die letzte Referenz sein)
                del self.active_downloads[entry_id]
                
                # Setze Thread-Referenz auf None, um Garbage Collection zu ermöglichen
                # (aber nicht unbedingt notwendig, da del bereits die Referenz entfernt)
                thread = None
            
            # Entferne auch aus download_rows
            if entry_id in self.download_rows:
                del self.download_rows[entry_id]
            
            # Update Status-Label
            active_count = len(self.active_downloads)
            if active_count == 0:
                self.status_label.setText("Alle Downloads abgeschlossen.")
                self.start_downloads_btn.setEnabled(True)
                self.cancel_all_btn.setEnabled(False)
            else:
                self.status_label.setText(f"{active_count} Download(s) aktiv.")
                
        except Exception as e:
            logging.error(f"Fehler in _on_download_finished: {e}", exc_info=True)
            # Versuche zumindest den Status zu aktualisieren, auch wenn etwas schief ging
            try:
                if entry_id in self.download_rows:
                    row = self.download_rows[entry_id]
                    status_item = self.table.item(row, 2)
                    if status_item:
                        status_item.setText("✗ Fehler")
                        status_item.setForeground(Qt.GlobalColor.red)
            except:
                pass
    
    def _update_state_file(self, entry_id: str, entry_data: Dict, status: str, filepath: Optional[str]):
        """Aktualisiert die State-Datei nach einem Download."""
        try:
            import sys
            import os
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
            import perlentaucher as core
            
            # Hole Config aus Settings (wird übergeben)
            config = getattr(self, '_config', {})
            no_state = config.get('no_state', False)
            if no_state:
                # State-Tracking ist deaktiviert, überspringe Update
                return
            
            state_file = config.get('state_file', '.perlentaucher_state.json')
            if not state_file:
                return
            
            movie_title = entry_data.get('movie_title', entry_data.get('rss_title', ''))
            is_series = entry_data.get('is_series', False)
            
            # Sichere Dateipfad-Prüfung (verhindert Crash bei None oder leerem String)
            filename = None
            if filepath and filepath.strip():
                try:
                    if os.path.exists(filepath):
                        filename = os.path.basename(filepath)
                except (OSError, ValueError, TypeError) as e:
                    logging.warning(f"Fehler beim Prüfen des Dateipfads '{filepath}': {e}")
                    filename = None
            
            core.save_processed_entry(
                state_file,
                entry_id,
                status=status,
                movie_title=movie_title,
                filename=filename,
                is_series=is_series
            )
        except Exception as e:
            logging.warning(f"Konnte State-Datei nicht aktualisieren: {e}", exc_info=True)
    
    def _cancel_download(self, entry_id: str):
        """Bricht einen einzelnen Download ab."""
        if entry_id in self.active_downloads:
            thread = self.active_downloads[entry_id]
            thread.cancel()
            thread.wait(1000)  # Warte max. 1 Sekunde
            
            if entry_id in self.download_rows:
                row = self.download_rows[entry_id]
                status_item = self.table.item(row, 2)
                if status_item:
                    status_item.setText("Abgebrochen")
                    status_item.setForeground(Qt.GlobalColor.gray)
            
            if entry_id in self.active_downloads:
                del self.active_downloads[entry_id]
            
            logging.info(f"Download abgebrochen: {entry_id}")
    
    def _cancel_all_downloads(self):
        """Bricht alle aktiven Downloads ab."""
        reply = QMessageBox.question(
            self,
            "Alle abbrechen",
            "Möchten Sie wirklich alle Downloads abbrechen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            entry_ids = list(self.active_downloads.keys())
            for entry_id in entry_ids:
                self._cancel_download(entry_id)
            
            self.status_label.setText("Alle Downloads abgebrochen.")
            self.start_downloads_btn.setEnabled(True)
            self.cancel_all_btn.setEnabled(False)


class LogEmitter(QObject):
    """Qt-Signal-Emitter für thread-sichere Log-Ausgaben."""
    
    log_message = pyqtSignal(str)


class TextEditLogHandler(logging.Handler):
    """Custom Log Handler der thread-sicher in ein QTextEdit schreibt."""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.emitter = LogEmitter()
        self.emitter.log_message.connect(self._append_message)
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', 
                                           datefmt='%H:%M:%S'))
    
    def _append_message(self, msg: str):
        try:
            self.text_widget.append(msg)
            # Auto-Scroll zum Ende
            self.text_widget.verticalScrollBar().setValue(
                self.text_widget.verticalScrollBar().maximum()
            )
        except Exception:
            pass
    
    def emit(self, record):
        """Schreibt Log-Eintrag in das Text-Widget (thread-sicher)."""
        try:
            msg = self.format(record)
            self.emitter.log_message.emit(msg)
        except Exception:
            pass