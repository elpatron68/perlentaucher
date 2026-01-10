"""
Blog List Panel für die GUI-Anwendung.
Zeigt RSS-Feed-Einträge in einer scrollbaren Liste mit Checkboxen an.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QLabel, QMessageBox,
    QComboBox, QLineEdit, QAbstractItemView, QInputDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
import sys
import os
import feedparser
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Importiere die Core-Funktionalität
# Füge das Parent-Verzeichnis zum Python-Pfad hinzu
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
import perlentaucher as core

from gui.utils.feedparser_helpers import get_entry_attr, make_entry_compatible


class BlogListPanel(QWidget):
    """Panel für die Blog-Liste."""
    
    entries_loaded = pyqtSignal(list)  # Signal wenn Einträge geladen wurden
    
    def __init__(self, config_manager, parent=None):
        """
        Initialisiert das Blog List Panel.
        
        Args:
            config_manager: Instance von ConfigManager
            parent: Parent Widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self.entries = []  # Liste von Entry-Dictionaries
        self._init_ui()
        
        # Auto-Lade beim Start (nach kurzer Verzögerung um UI zu initialisieren)
        # Lade automatisch die letzten 30 Tage beim Start der GUI
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, lambda: self._load_rss_feed(days=30))
    
    def _init_ui(self):
        """Initialisiert die UI-Komponenten."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.load_rss_btn = QPushButton("RSS-Feed laden (Letzte 30 Tage)")
        self.load_rss_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; font-weight: bold; }")
        self.load_rss_btn.clicked.connect(lambda: self._load_rss_feed(days=30))
        
        self.refresh_btn = QPushButton("Aktualisieren")
        self.refresh_btn.clicked.connect(lambda: self._load_rss_feed(days=30))
        
        self.load_older_btn = QPushButton("Ältere Einträge nachladen...")
        self.load_older_btn.setToolTip("Lädt Einträge älter als 30 Tage nach")
        self.load_older_btn.clicked.connect(self._load_older_entries)
        
        self.select_all_btn = QPushButton("Alle auswählen")
        self.select_all_btn.clicked.connect(self._select_all)
        
        self.deselect_all_btn = QPushButton("Alle abwählen")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        
        toolbar.addWidget(self.load_rss_btn)
        toolbar.addWidget(self.refresh_btn)
        toolbar.addWidget(self.load_older_btn)
        toolbar.addWidget(self.select_all_btn)
        toolbar.addWidget(self.deselect_all_btn)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Alle", "Neu", "Bereits verarbeitet", "Filme", "Serien"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Suche nach Titel...")
        self.search_edit.textChanged.connect(self._apply_filter)
        
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addWidget(QLabel("Suche:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addStretch()
        
        toolbar.addLayout(filter_layout)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Status-Label
        self.status_label = QLabel("Noch keine Einträge geladen. Klicken Sie auf 'RSS-Feed laden'.")
        layout.addWidget(self.status_label)
        
        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Auswählen", "Titel", "Filmtitel/Serie", "Jahr", "Typ", "Status", "Link"
        ])
        
        # Stelle sicher, dass die Tabelle vertikal skalierbar ist
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Spaltenbreiten einstellen
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Titel
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Filmtitel
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Jahr
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Typ
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Link
        
        self.table.setColumnWidth(0, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table, stretch=1)  # Stretch-Faktor für vertikale Skalierung
        
        self.setLayout(layout)
    
    def _filter_entries_by_date(self, entries, days: int) -> List:
        """
        Filtert Einträge nach Veröffentlichungsdatum (letzte N Tage).
        
        Args:
            entries: Liste von feedparser Entry-Objekten
            days: Anzahl der Tage (nur Einträge der letzten N Tage)
            
        Returns:
            Gefilterte Liste von Einträgen
        """
        if days is None or days <= 0:
            return entries  # Keine Filterung wenn days=None oder <=0
        
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_entries = []
        entries_without_date = 0
        entries_older_than_cutoff = 0
        
        for entry in entries:
            # Hole Veröffentlichungsdatum - feedparser verwendet published_parsed oder updated_parsed
            published = get_entry_attr(entry, 'published_parsed')
            if not published:
                # Fallback: updated_parsed
                published = get_entry_attr(entry, 'updated_parsed')
            
            if published:
                try:
                    # published_parsed ist ein time.struct_time Objekt
                    from time import mktime
                    published_dt = datetime.fromtimestamp(mktime(published))
                    
                    # Debug: Zeige Datum des ersten Eintrags
                    if len(filtered_entries) == 0 and entries_older_than_cutoff == 0:
                        logging.debug(f"Erster Eintrag Datum: {published_dt}, Cutoff: {cutoff_date}")
                    
                    if published_dt >= cutoff_date:
                        filtered_entries.append(entry)
                    else:
                        entries_older_than_cutoff += 1
                        # Debug: Zeige warum Eintrag herausgefiltert wurde
                        age_days = (datetime.now() - published_dt).days
                        if entries_older_than_cutoff <= 3:  # Nur erste 3 für Debug
                            logging.debug(f"Eintrag herausgefiltert: {age_days} Tage alt (Datum: {published_dt})")
                except (ValueError, TypeError, OSError) as e:
                    # Falls Parsing fehlschlägt, behalte Eintrag (besser zu viele als zu wenig)
                    logging.debug(f"Datum-Parsing-Fehler für Entry: {e}, behalte Eintrag")
                    filtered_entries.append(entry)
            else:
                # Wenn kein Datum vorhanden, behalte Eintrag (besser zu viele als zu wenig)
                entries_without_date += 1
                filtered_entries.append(entry)
        
        if entries_without_date > 0:
            logging.debug(f"{entries_without_date} Einträge ohne Datum (behalten)")
        if entries_older_than_cutoff > 0:
            logging.debug(f"{entries_older_than_cutoff} Einträge älter als {days} Tage (herausgefiltert)")
        
        return filtered_entries
    
    def _load_rss_feed(self, days: Optional[int] = 30, append: bool = False):
        """
        Lädt den RSS-Feed und zeigt die Einträge an.
        
        Args:
            days: Anzahl der Tage für Filterung (None = alle Einträge)
            append: Wenn True, werden neue Einträge zu bestehenden hinzugefügt (keine Duplikate)
        """
        try:
            rss_url = self.config_manager.get('rss_feed_url', 'https://nexxtpress.de/author/mediathekperlen/feed/')
            
            # Versuche mehr Einträge zu bekommen, wenn Feed-URL WordPress ist
            # WordPress unterstützt ?posts_per_page= Parameter (max 50)
            # Füge Parameter hinzu wenn nicht bereits vorhanden
            if 'posts_per_page' not in rss_url and 'nexxtpress.de' in rss_url:
                # Füge Parameter hinzu um mehr Einträge zu bekommen
                separator = '&' if '?' in rss_url else '?'
                rss_url_with_limit = f"{rss_url}{separator}posts_per_page=50"
                logging.debug(f"Versuche RSS-Feed mit erhöhtem Limit: {rss_url_with_limit}")
            else:
                rss_url_with_limit = rss_url
            
            self.load_rss_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.load_older_btn.setEnabled(False)
            
            if days:
                self.status_label.setText(f"Lade RSS-Feed (letzte {days} Tage) von {rss_url}...")
            else:
                self.status_label.setText(f"Lade RSS-Feed (alle Einträge) von {rss_url}...")
            
            # Force UI update
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Parse RSS Feed - verwende requests für besseres SSL-Handling
            # feedparser.parse() kann direkt URLs laden, aber nutzt urllib
            # Stattdessen laden wir mit requests (nutzt certifi) und parsen dann
            try:
                import requests
                import certifi
                
                # Lade Feed mit requests für besseres SSL/CA-Zertifikate-Handling
                response = requests.get(rss_url_with_limit, timeout=10, verify=True)
                response.raise_for_status()
                # Parse den Feed-Inhalt mit feedparser
                feed = feedparser.parse(response.content)
            except ImportError:
                # Fallback: Direkt mit feedparser (ohne requests)
                feed = feedparser.parse(rss_url_with_limit)
            except requests.exceptions.SSLError as e:
                error_msg = f"SSL-Fehler beim Laden des RSS-Feeds: {str(e)}"
                logging.error(error_msg, exc_info=True)
                self.status_label.setText(f"Fehler: SSL-Problem")
                QMessageBox.critical(
                    self,
                    "SSL-Fehler",
                    f"{error_msg}\n\n"
                    f"Mögliche Lösungen:\n"
                    f"- CA-Zertifikate installieren:\n"
                    f"  Fedora/RHEL: sudo dnf install ca-certificates\n"
                    f"- System-Bibliotheken aktualisieren:\n"
                    f"  sudo dnf update openssl\n"
                    f"- Prüfe ob certifi installiert ist:\n"
                    f"  pip install certifi"
                )
                self.load_rss_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.load_older_btn.setEnabled(True)
                return
            except requests.exceptions.RequestException as e:
                error_msg = f"Netzwerkfehler beim Laden des RSS-Feeds: {str(e)}"
                logging.error(error_msg, exc_info=True)
                self.status_label.setText(f"Fehler: Netzwerkproblem")
                QMessageBox.critical(
                    self,
                    "Netzwerkfehler",
                    f"{error_msg}\n\n"
                    f"Mögliche Ursachen:\n"
                    f"- Keine Internetverbindung\n"
                    f"- Firewall blockiert Verbindung\n"
                    f"- Feed-URL ist ungültig"
                )
                self.load_rss_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.load_older_btn.setEnabled(True)
                return
            except Exception as e:
                error_msg = f"Fehler beim Laden des RSS-Feeds: {str(e)}"
                logging.error(error_msg, exc_info=True)
                self.status_label.setText(f"Fehler: {error_msg}")
                QMessageBox.critical(
                    self, 
                    "Fehler beim Laden des RSS-Feeds",
                    f"Der RSS-Feed konnte nicht geladen werden:\n\n{error_msg}\n\n"
                    f"Mögliche Ursachen:\n"
                    f"- Netzwerkverbindung fehlt\n"
                    f"- SSL-Zertifikate fehlen\n"
                    f"- Feed-URL ist ungültig\n\n"
                    f"Details siehe Log."
                )
                self.load_rss_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.load_older_btn.setEnabled(True)
                return
            
            # Prüfe ob Feed geladen wurde (feedparser gibt leeren Feed bei Fehlern zurück)
            if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                error_msg = "RSS-Feed ist leer oder konnte nicht geparst werden"
                logging.warning(error_msg)
                self.status_label.setText(error_msg)
                QMessageBox.warning(self, "Warnung", error_msg)
                self.load_rss_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self.load_older_btn.setEnabled(True)
                return
            
            feed_with_limit_count = len(feed.entries) if hasattr(feed, 'entries') else 0
            
            # Falls Parameter hinzugefügt wurde, vergleiche mit Original-URL
            if rss_url_with_limit != rss_url:
                feed_original = feedparser.parse(rss_url)
                original_count = len(feed_original.entries)
                
                # Verwende den Feed mit mehr Einträgen
                if original_count > feed_with_limit_count:
                    feed = feed_original
                    logging.info(f"Original Feed liefert mehr Einträge: {original_count} vs {feed_with_limit_count}")
                    rss_url_used = rss_url
                elif feed_with_limit_count > original_count:
                    logging.info(f"Feed mit Parameter liefert mehr Einträge: {feed_with_limit_count} vs {original_count}")
                    rss_url_used = rss_url_with_limit
                else:
                    # Beide liefern gleich viele - verwende den mit Parameter (vielleicht gibt es mehr, aber Server begrenzt)
                    logging.info(f"Beide Feeds liefern {feed_with_limit_count} Einträge (Server-Begrenzung)")
                    rss_url_used = rss_url_with_limit
            else:
                rss_url_used = rss_url
            
            if feed.bozo:
                QMessageBox.warning(self, "Warnung", "Beim Parsen des RSS-Feeds ist ein Fehler aufgetreten, fahre fort...")
            
            # WICHTIG: feed.entries enthält ALLE Einträge, die der RSS-Feed zurückgibt
            # Viele RSS-Feeds limitieren die Anzahl selbst (z.B. nur die neuesten 10-20 Einträge)
            # Das ist eine Feed-Begrenzung auf Server-Seite, nicht unsere Filterung
            total_entries_from_feed = len(feed.entries)
            
            # Debug: Zeige Datum des ersten und letzten Eintrags
            if feed.entries:
                first_entry = feed.entries[0]
                last_entry = feed.entries[-1]
                first_pub = get_entry_attr(first_entry, 'published', 'unbekannt')
                last_pub = get_entry_attr(last_entry, 'published', 'unbekannt')
                logging.debug(f"Erster Eintrag: {first_pub}, Letzter Eintrag: {last_pub}")
            
            logging.info(f"RSS-Feed liefert {total_entries_from_feed} Einträge vom Feed-Server")
            
            # Filtere nach Datum wenn days angegeben
            # WICHTIG: Wenn der Feed selbst nur wenige Einträge liefert (<=15),
            # zeige ALLE verfügbaren Einträge, da Server-Begrenzung bereits Filterung ist
            status_text = None  # Initialisiere Variable
            
            if days and days > 0:
                feed_entries_filtered = self._filter_entries_by_date(feed.entries, days)
                filtered_count = len(feed_entries_filtered)
                removed_count = total_entries_from_feed - filtered_count
                
                # Wenn Feed nur wenige Einträge liefert, zeige alle (Server-Begrenzung ist bereits Filterung)
                if total_entries_from_feed <= 15:
                    # Zeige alle verfügbaren Einträge, da Feed selbst schon begrenzt ist
                    logging.info(
                        f"Feed liefert nur {total_entries_from_feed} Einträge (Server-Begrenzung). "
                        f"Zeige alle verfügbaren Einträge."
                    )
                    feed_entries = feed.entries  # Zeige alle verfügbaren
                    filtered_count = total_entries_from_feed
                    removed_count = 0
                    status_text = f"Feed: {total_entries_from_feed} Einträge (alle verfügbaren - Server-Begrenzung)"
                else:
                    # Normale Filterung wenn Feed viele Einträge liefert
                    feed_entries = feed_entries_filtered
                    status_text = f"Feed: {total_entries_from_feed} total → {filtered_count} in den letzten {days} Tagen"
                    if removed_count > 0:
                        status_text += f" ({removed_count} älter herausgefiltert)"
                    
                    # Warnung wenn alle Einträge herausgefiltert wurden (nur wenn Feed viele liefert)
                    if filtered_count == 0 and total_entries_from_feed > 0:
                        status_text += f" ⚠️ Alle Einträge älter als {days} Tage!"
                        QMessageBox.information(
                            self,
                            "Keine Einträge in Zeitraum",
                            f"Alle {total_entries_from_feed} Einträge vom Feed sind älter als {days} Tage.\n\n"
                            f"Nutzen Sie 'Ältere Einträge nachladen...' und geben Sie mehr Tage ein "
                            f"(oder lassen Sie das Feld leer für alle Einträge)."
                        )
                
                self.status_label.setText(status_text)
                logging.info(f"Nach {days}-Tage-Filter: {filtered_count} Einträge (von {total_entries_from_feed} total, {removed_count} entfernt)")
                
                # Hinweis-Dialog nur wenn Feed begrenzt ist UND beim ersten Laden (nicht append)
                if total_entries_from_feed <= 15 and not append:
                    QMessageBox.information(
                        self,
                        "Hinweis: RSS-Feed Begrenzung",
                        f"Der RSS-Feed liefert nur {total_entries_from_feed} Einträge.\n\n"
                        f"Dies ist eine Begrenzung auf Server-Seite (WordPress-RSS-Feeds sind "
                        f"standardmäßig auf 10-20 Einträge begrenzt).\n\n"
                        f"Es werden alle verfügbaren Einträge angezeigt.\n\n"
                        f"Um mehr Einträge zu sehen, müsste der Feed-Administrator das Limit "
                        f"erhöhen (bis max. 50 möglich).",
                        QMessageBox.StandardButton.Ok
                    )
            else:
                feed_entries = feed.entries
                self.status_label.setText(f"Feed: {total_entries_from_feed} Einträge total (keine Datums-Filterung)")
                logging.info(f"Keine Datums-Filterung: {total_entries_from_feed} Einträge")
                
                # Hinweis wenn der Feed nur wenige Einträge zurückgibt
                if total_entries_from_feed <= 15:
                    logging.info(
                        f"RSS-Feed liefert nur {total_entries_from_feed} Einträge. "
                        f"Dies ist wahrscheinlich eine Begrenzung des Feed-Servers."
                    )
            
            # Lade State-Datei um verarbeitete Einträge zu erkennen (nur wenn no_state nicht aktiviert)
            no_state = self.config_manager.get('no_state', False)
            if no_state:
                state_file = None
                processed_entries = set()
                state_data = {'entries': {}}
            else:
                state_file = self.config_manager.get('state_file', '.perlentaucher_state.json')
                processed_entries = core.load_processed_entries(state_file) if state_file else set()
                state_data = core.load_state_file(state_file) if state_file else {'entries': {}}
            
            # Wenn append=True, starte mit bestehenden Einträgen und verhindere Duplikate
            if append:
                existing_entry_ids = {e['entry_id'] for e in self.entries}
            else:
                existing_entry_ids = set()
                self.entries = []
            
            # Parse Einträge
            new_count = 0
            for entry in feed_entries:
                # Verwende Wrapper-Funktion für robusten Zugriff auf Entry-Attribute
                entry_id = get_entry_attr(entry, 'id') or get_entry_attr(entry, 'link') or get_entry_attr(entry, 'title', '')
                is_processed = entry_id in processed_entries
                
                # Extrahiere Filmtitel
                title = get_entry_attr(entry, 'title', '')
                movie_title = None
                year = None
                
                # Suche nach Filmtitel in Anführungszeichen
                match = re.search(r'\u201E(.+?)(?:[\u201C\u201D\u0022])', title)
                if not match:
                    match = re.search(r'"([^"]+?)"', title)
                
                if match:
                    movie_title = match.group(1)
                    year = core.extract_year_from_title(title)
                
                # Hole Status aus State-Datei
                status = "Neu"
                if is_processed:
                    entry_state = state_data.get('entries', {}).get(entry_id, {})
                    status_map = {
                        'download_success': '✓ Erfolgreich',
                        'download_failed': '✗ Fehlgeschlagen',
                        'not_found': '✗ Nicht gefunden',
                        'title_extraction_failed': '✗ Titel-Fehler',
                        'skipped': '⏭ Übersprungen'
                    }
                    status = status_map.get(entry_state.get('status', 'unknown'), 'Verarbeitet')
                
                # Prüfe ob es eine Serie ist
                # Erstelle kompatibles Entry-Objekt für is_series()
                entry_dict = make_entry_compatible(entry)
                metadata = {}  # Wird später gefüllt wenn Metadata verfügbar ist
                is_series = core.is_series(entry_dict, metadata)
                
                entry_link = get_entry_attr(entry, 'link', '')
                
                # Überspringe Duplikate wenn append=True
                if entry_id in existing_entry_ids:
                    continue
                
                entry_data = {
                    'entry_id': entry_id,
                    'entry': entry,  # Speichere original entry für später
                    'entry_link': entry_link,
                    'rss_title': title,
                    'movie_title': movie_title,
                    'year': year,
                    'is_processed': is_processed,
                    'status': status,
                    'is_series': is_series,
                    'metadata': metadata
                }
                
                self.entries.append(entry_data)
                existing_entry_ids.add(entry_id)
                new_count += 1
            
            self._populate_table()
            if append and new_count > 0:
                self.status_label.setText(f"{new_count} neue Einträge geladen. Gesamt: {len(self.entries)} Einträge.")
            else:
                self.status_label.setText(f"{len(self.entries)} Einträge geladen.")
            self.entries_loaded.emit(self.entries)
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden des RSS-Feeds:\n{str(e)}")
            self.status_label.setText("Fehler beim Laden des RSS-Feeds.")
        finally:
            self.load_rss_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self.load_older_btn.setEnabled(True)
    
    def _load_older_entries(self):
        """Lädt ältere Einträge nach (älter als 30 Tage)."""
        # Dialog für Anzahl Tage
        days_text, ok = QInputDialog.getText(
            self,
            "Ältere Einträge nachladen",
            "Einträge der letzten wie vielen Tage laden?\n(Leer lassen für alle Einträge):",
            text="60"
        )
        
        if not ok:
            return
        
        if days_text.strip() == "":
            # Alle Einträge laden
            days = None
        else:
            try:
                days = int(days_text.strip())
                if days <= 0:
                    QMessageBox.warning(self, "Ungültiger Wert", "Die Anzahl der Tage muss eine positive Zahl sein!")
                    return
            except ValueError:
                QMessageBox.warning(self, "Ungültiger Wert", "Bitte geben Sie eine gültige Zahl ein!")
                return
        
        # Lade Einträge und füge sie zu bestehenden hinzu (append=True)
        self._load_rss_feed(days=days, append=True)
    
    def _populate_table(self):
        """Füllt die Tabelle mit den Einträgen."""
        filtered_entries = self._get_filtered_entries()
        
        self.table.setRowCount(len(filtered_entries))
        
        for row, entry_data in enumerate(filtered_entries):
            # Checkbox - standardmäßig deaktiviert
            checkbox = QCheckBox()
            checkbox.setChecked(False)  # Alle Checkboxen standardmäßig deaktiviert
            self.table.setCellWidget(row, 0, checkbox)
            
            # Titel
            title_item = QTableWidgetItem(entry_data['rss_title'])
            self.table.setItem(row, 1, title_item)
            
            # Filmtitel
            movie_title = entry_data.get('movie_title', 'Nicht extrahiert')
            movie_item = QTableWidgetItem(movie_title if movie_title else 'Nicht extrahiert')
            if not movie_title:
                movie_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 2, movie_item)
            
            # Jahr
            year = entry_data.get('year')
            year_item = QTableWidgetItem(str(year) if year else '')
            self.table.setItem(row, 3, year_item)
            
            # Typ
            type_item = QTableWidgetItem("Serie" if entry_data.get('is_series') else "Film")
            self.table.setItem(row, 4, type_item)
            
            # Status
            status_item = QTableWidgetItem(entry_data['status'])
            if '✓' in entry_data['status']:
                status_item.setForeground(Qt.GlobalColor.green)
            elif '✗' in entry_data['status']:
                status_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 5, status_item)
            
            # Link
            link = entry_data.get('entry_link', '')
            link_item = QTableWidgetItem(link[:50] + '...' if len(link) > 50 else link)
            self.table.setItem(row, 6, link_item)
            
            # Speichere Entry-Daten in der Zeile
            self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, entry_data)
    
    def _get_filtered_entries(self) -> List[Dict]:
        """Gibt gefilterte Einträge zurück."""
        entries = self.entries.copy()
        
        # Filter nach Status/Typ
        filter_text = self.filter_combo.currentText()
        if filter_text == "Neu":
            entries = [e for e in entries if not e['is_processed']]
        elif filter_text == "Bereits verarbeitet":
            entries = [e for e in entries if e['is_processed']]
        elif filter_text == "Filme":
            entries = [e for e in entries if not e.get('is_series', False)]
        elif filter_text == "Serien":
            entries = [e for e in entries if e.get('is_series', False)]
        
        # Suche
        search_text = self.search_edit.text().lower()
        if search_text:
            entries = [
                e for e in entries
                if search_text in e.get('rss_title', '').lower() or
                   search_text in e.get('movie_title', '').lower()
            ]
        
        return entries
    
    def _apply_filter(self):
        """Wendet den Filter an und aktualisiert die Tabelle."""
        self._populate_table()
    
    def _select_all(self):
        """Wählt alle sichtbaren Einträge aus."""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)
    
    def _deselect_all(self):
        """Wählt alle sichtbaren Einträge ab."""
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)
    
    def get_selected_entries(self) -> List[Dict]:
        """Gibt eine Liste der ausgewählten Einträge zurück."""
        selected = []
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                # Hole Entry-Daten aus der Zeile
                title_item = self.table.item(row, 1)
                if title_item:
                    entry_data = title_item.data(Qt.ItemDataRole.UserRole)
                    if entry_data:
                        selected.append(entry_data)
        return selected
    
    def update_entry_status(self, entry_id: str, status: str):
        """Aktualisiert den Status eines Eintrags in der Tabelle."""
        for row in range(self.table.rowCount()):
            title_item = self.table.item(row, 1)
            if title_item:
                entry_data = title_item.data(Qt.ItemDataRole.UserRole)
                if entry_data and entry_data['entry_id'] == entry_id:
                    status_item = self.table.item(row, 5)
                    if status_item:
                        status_item.setText(status)
                        if '✓' in status:
                            status_item.setForeground(Qt.GlobalColor.green)
                        elif '✗' in status:
                            status_item.setForeground(Qt.GlobalColor.red)
                    break
