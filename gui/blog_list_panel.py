"""
Blog List Panel für die GUI-Anwendung.
Zeigt RSS-Feed-Einträge in einer scrollbaren Liste mit Checkboxen an.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QLabel, QMessageBox,
    QComboBox, QLineEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
import sys
import os
import feedparser
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Importiere die Core-Funktionalität
# Füge das Parent-Verzeichnis zum Python-Pfad hinzu
parent_dir = os.path.dirname(os.path.dirname(__file__))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
import perlentaucher as core


def _get_entry_attr(entry, attr: str, default=None):
    """
    Hilfs-Funktion um Attribute aus feedparser Entry-Objekten zu holen.
    Unterstützt sowohl Dictionary-ähnliche Objekte (.get()) als auch Attribut-Zugriff.
    
    Args:
        entry: feedparser Entry-Objekt
        attr: Attribut-Name
        default: Standardwert wenn nicht gefunden
        
    Returns:
        Attribut-Wert oder default
    """
    # Versuche zuerst .get() Methode (Dictionary-ähnlich)
    if hasattr(entry, 'get'):
        try:
            return entry.get(attr, default)
        except (TypeError, AttributeError):
            pass
    
    # Fallback: Attribut-Zugriff
    if hasattr(entry, attr):
        value = getattr(entry, attr, default)
        return value if value is not None else default
    
    # Fallback: Dictionary-Zugriff mit []
    try:
        return entry[attr]
    except (KeyError, TypeError):
        return default


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
    
    def _init_ui(self):
        """Initialisiert die UI-Komponenten."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.load_rss_btn = QPushButton("RSS-Feed laden")
        self.load_rss_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; padding: 8px; font-weight: bold; }")
        self.load_rss_btn.clicked.connect(self._load_rss_feed)
        
        self.refresh_btn = QPushButton("Aktualisieren")
        self.refresh_btn.clicked.connect(self._load_rss_feed)
        
        self.select_all_btn = QPushButton("Alle auswählen")
        self.select_all_btn.clicked.connect(self._select_all)
        
        self.deselect_all_btn = QPushButton("Alle abwählen")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        
        toolbar.addWidget(self.load_rss_btn)
        toolbar.addWidget(self.refresh_btn)
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
        
        layout.addWidget(self.table)
        
        self.setLayout(layout)
    
    def _load_rss_feed(self):
        """Lädt den RSS-Feed und zeigt die Einträge an."""
        try:
            rss_url = self.config_manager.get('rss_feed_url', 'https://nexxtpress.de/author/mediathekperlen/feed/')
            limit = self.config_manager.get('limit', 10)
            
            self.load_rss_btn.setEnabled(False)
            self.status_label.setText(f"Lade RSS-Feed von {rss_url}...")
            QWidget().repaint()  # Force UI update
            
            # Parse RSS Feed
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                QMessageBox.warning(self, "Warnung", "Beim Parsen des RSS-Feeds ist ein Fehler aufgetreten, fahre fort...")
            
            feed_entries = feed.entries[:limit]
            
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
            
            # Parse Einträge
            self.entries = []
            for entry in feed_entries:
                # Verwende Wrapper-Funktion für robusten Zugriff auf Entry-Attribute
                entry_id = _get_entry_attr(entry, 'id') or _get_entry_attr(entry, 'link') or _get_entry_attr(entry, 'title', '')
                is_processed = entry_id in processed_entries
                
                # Extrahiere Filmtitel
                title = _get_entry_attr(entry, 'title', '')
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
                # Erstelle ein kompatibles Entry-Dictionary für is_series()
                # is_series() erwartet ein Objekt mit .get() Methode
                entry_tags = _get_entry_attr(entry, 'tags', [])
                
                # Erstelle Dictionary-ähnliches Objekt für is_series()
                # Diese Klasse macht feedparser Entry-Objekte kompatibel mit is_series()
                class EntryDict(dict):
                    """Wrapper-Klasse um Entry-Objekt Dictionary-ähnlich zu machen."""
                    def __init__(self, entry, title, tags):
                        self.entry = entry
                        # Speichere wichtige Attribute
                        self._title = title
                        self._tags = tags
                        # Initialisiere dict mit Werten
                        super().__init__({
                            'title': title,
                            'tags': tags
                        })
                    
                    def get(self, key, default=None):
                        # Prüfe zuerst unsere gespeicherten Werte
                        if key == 'title':
                            return self._title
                        elif key == 'tags':
                            return self._tags
                        # Versuche auch original entry
                        return _get_entry_attr(self.entry, key, default)
                    
                    def __getitem__(self, key):
                        # Unterstütze auch [] Zugriff
                        if key in self:
                            return super().__getitem__(key)
                        value = _get_entry_attr(self.entry, key)
                        if value is None:
                            raise KeyError(key)
                        return value
                
                entry_dict = EntryDict(entry, title, entry_tags)
                metadata = {}  # Wird später gefüllt wenn Metadata verfügbar ist
                is_series = core.is_series(entry_dict, metadata)
                
                entry_link = _get_entry_attr(entry, 'link', '')
                
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
            
            self._populate_table()
            self.status_label.setText(f"{len(self.entries)} Einträge geladen.")
            self.entries_loaded.emit(self.entries)
            
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler beim Laden des RSS-Feeds:\n{str(e)}")
            self.status_label.setText("Fehler beim Laden des RSS-Feeds.")
        finally:
            self.load_rss_btn.setEnabled(True)
    
    def _populate_table(self):
        """Füllt die Tabelle mit den Einträgen."""
        filtered_entries = self._get_filtered_entries()
        
        self.table.setRowCount(len(filtered_entries))
        
        for row, entry_data in enumerate(filtered_entries):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(not entry_data['is_processed'])  # Nur neue Einträge standardmäßig ausgewählt
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
