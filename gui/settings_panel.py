"""
Settings Panel für die GUI-Anwendung.
Stellt alle konfigurierbaren Optionen als UI-Elemente dar.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
    QComboBox, QPushButton, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt
import os
from typing import Dict, Callable


class SettingsPanel(QWidget):
    """Panel für Einstellungen."""
    
    def __init__(self, config_manager, parent=None):
        """
        Initialisiert das Settings Panel.
        
        Args:
            config_manager: Instance von ConfigManager
            parent: Parent Widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialisiert die UI-Komponenten."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Download-Einstellungen
        download_group = QGroupBox("Download-Einstellungen")
        download_layout = QFormLayout()
        
        self.download_dir_edit = QLineEdit()
        self.download_dir_edit.setReadOnly(True)
        self.download_dir_btn = QPushButton("Durchsuchen...")
        self.download_dir_btn.clicked.connect(lambda: self._select_directory(self.download_dir_edit))
        download_dir_layout = QHBoxLayout()
        download_dir_layout.setContentsMargins(0, 0, 0, 0)
        download_dir_layout.addWidget(self.download_dir_edit, 1)  # Stretch-Faktor für Textfeld
        download_dir_layout.addWidget(self.download_dir_btn, 0)  # Kein Stretch für Button
        self.download_dir_widget = QWidget()
        self.download_dir_widget.setLayout(download_dir_layout)
        download_layout.addRow("Download-Verzeichnis:", self.download_dir_widget)
        
        # Hinweis: Limit wurde entfernt - es werden automatisch die letzten 30 Tage geladen
        info_label = QLabel("Hinweis: Beim Laden werden automatisch alle Einträge der letzten 30 Tage abgerufen.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        download_layout.addRow("", info_label)
        
        self.state_file_edit = QLineEdit()
        download_layout.addRow("State-Datei:", self.state_file_edit)
        
        # State-Tracking Checkbox
        self.no_state_checkbox = QCheckBox()
        self.no_state_checkbox.setText("State-Tracking deaktivieren (--no-state)")
        self.no_state_checkbox.toggled.connect(self._on_no_state_toggled)
        download_layout.addRow("", self.no_state_checkbox)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        # Medien-Präferenzen
        preferences_group = QGroupBox("Medien-Präferenzen")
        preferences_layout = QFormLayout()
        
        self.sprache_combo = QComboBox()
        self.sprache_combo.addItems(["deutsch", "englisch", "egal"])
        preferences_layout.addRow("Bevorzugte Sprache:", self.sprache_combo)
        
        self.audiodeskription_combo = QComboBox()
        self.audiodeskription_combo.addItems(["mit", "ohne", "egal"])
        preferences_layout.addRow("Audiodeskription:", self.audiodeskription_combo)
        
        self.serien_download_combo = QComboBox()
        self.serien_download_combo.addItems(["erste", "staffel", "keine"])
        preferences_layout.addRow("Serien-Download:", self.serien_download_combo)
        
        self.serien_dir_edit = QLineEdit()
        self.serien_dir_edit.setReadOnly(True)
        self.serien_dir_btn = QPushButton("Durchsuchen...")
        self.serien_dir_btn.clicked.connect(lambda: self._select_directory(self.serien_dir_edit))
        serien_dir_layout = QHBoxLayout()
        serien_dir_layout.setContentsMargins(0, 0, 0, 0)
        serien_dir_layout.addWidget(self.serien_dir_edit, 1)  # Stretch-Faktor für Textfeld
        serien_dir_layout.addWidget(self.serien_dir_btn, 0)  # Kein Stretch für Button
        self.serien_dir_widget = QWidget()
        self.serien_dir_widget.setLayout(serien_dir_layout)
        preferences_layout.addRow("Serien-Verzeichnis:", self.serien_dir_widget)
        
        preferences_group.setLayout(preferences_layout)
        layout.addWidget(preferences_group)
        
        # API-Keys
        api_group = QGroupBox("API-Keys (optional)")
        api_layout = QFormLayout()
        
        self.tmdb_api_key_edit = QLineEdit()
        self.tmdb_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.tmdb_api_key_edit.setPlaceholderText("TMDB API-Key eingeben")
        api_layout.addRow("TMDB API-Key:", self.tmdb_api_key_edit)
        
        self.omdb_api_key_edit = QLineEdit()
        self.omdb_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.omdb_api_key_edit.setPlaceholderText("OMDb API-Key eingeben")
        api_layout.addRow("OMDb API-Key:", self.omdb_api_key_edit)
        
        # Sichtbarkeit für Passwort-Felder
        self.tmdb_show_btn = QPushButton("Anzeigen")
        self.tmdb_show_btn.setCheckable(True)
        self.tmdb_show_btn.toggled.connect(
            lambda checked: self.tmdb_api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        api_layout.addRow("", self.tmdb_show_btn)
        
        self.omdb_show_btn = QPushButton("Anzeigen")
        self.omdb_show_btn.setCheckable(True)
        self.omdb_show_btn.toggled.connect(
            lambda checked: self.omdb_api_key_edit.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        api_layout.addRow("", self.omdb_show_btn)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        # Benachrichtigungen
        notify_group = QGroupBox("Benachrichtigungen")
        notify_layout = QFormLayout()
        
        self.notify_edit = QLineEdit()
        self.notify_edit.setPlaceholderText("z.B. mailto://user:pass@example.com oder discord://webhook_id/webhook_token")
        notify_layout.addRow("Apprise-URL:", self.notify_edit)
        
        notify_group.setLayout(notify_layout)
        layout.addWidget(notify_group)
        
        # Logging
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()
        
        self.loglevel_combo = QComboBox()
        self.loglevel_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addRow("Log-Level:", self.loglevel_combo)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # RSS Feed URL
        rss_group = QGroupBox("RSS-Feed")
        rss_layout = QFormLayout()
        
        self.rss_feed_edit = QLineEdit()
        rss_layout.addRow("RSS-Feed URL:", self.rss_feed_edit)
        
        rss_group.setLayout(rss_layout)
        layout.addWidget(rss_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Einstellungen speichern")
        self.save_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; font-weight: bold; }")
        self.save_btn.clicked.connect(self._save_settings)
        
        self.reset_btn = QPushButton("Auf Standard zurücksetzen")
        self.reset_btn.clicked.connect(self._reset_settings)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def _select_directory(self, line_edit: QLineEdit):
        """Öffnet einen Verzeichnis-Auswahl-Dialog."""
        current_dir = line_edit.text() or os.path.expanduser("~")
        # Wenn relativer Pfad, konvertiere zu absolutem für Dialog
        if not os.path.isabs(current_dir):
            project_root = getattr(self.config_manager, 'project_root', os.getcwd())
            current_dir = os.path.join(project_root, current_dir)
            if not os.path.exists(current_dir):
                current_dir = os.path.expanduser("~")
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Verzeichnis auswählen",
            current_dir
        )
        if directory:
            # Wenn Dialog im Projekt-Root oder Unterordner, speichere als relativen Pfad
            project_root = getattr(self.config_manager, 'project_root', os.getcwd())
            try:
                rel_path = os.path.relpath(directory, project_root)
                # Nur wenn Pfad relativ ist (nicht mit .. beginnt), verwende relativen Pfad
                if not rel_path.startswith('..'):
                    line_edit.setText(rel_path)
                else:
                    line_edit.setText(directory)  # Absoluter Pfad
            except ValueError:
                # Falls relativer Pfad nicht möglich (verschiedene Laufwerke auf Windows)
                line_edit.setText(directory)
    
    def _on_no_state_toggled(self, checked: bool):
        """Wird aufgerufen wenn no_state Checkbox getoggled wird."""
        # Deaktiviere State-Datei Feld wenn no_state aktiviert ist
        self.state_file_edit.setEnabled(not checked)
    
    def _load_settings(self):
        """Lädt die Einstellungen aus dem Config Manager."""
        config = self.config_manager.get_all()
        
        self.download_dir_edit.setText(config.get('download_dir', './downloads'))
        self.state_file_edit.setText(config.get('state_file', '.perlentaucher_state.json'))
        
        # no_state Option
        no_state = config.get('no_state', False)
        self.no_state_checkbox.setChecked(no_state)
        self._on_no_state_toggled(no_state)
        
        sprache = config.get('sprache', 'deutsch')
        index = self.sprache_combo.findText(sprache)
        if index >= 0:
            self.sprache_combo.setCurrentIndex(index)
        
        audiodeskription = config.get('audiodeskription', 'egal')
        index = self.audiodeskription_combo.findText(audiodeskription)
        if index >= 0:
            self.audiodeskription_combo.setCurrentIndex(index)
        
        serien_download = config.get('serien_download', 'erste')
        index = self.serien_download_combo.findText(serien_download)
        if index >= 0:
            self.serien_download_combo.setCurrentIndex(index)
        
        # serien_dir: Wenn leer oder gleich download_dir, zeige leer (wird beim Speichern auf download_dir gesetzt)
        serien_dir = config.get('serien_dir', '')
        download_dir = config.get('download_dir', './downloads')
        if not serien_dir or serien_dir == download_dir:
            serien_dir = ''  # Zeige leer wenn gleich download_dir
        self.serien_dir_edit.setText(serien_dir)
        self.tmdb_api_key_edit.setText(config.get('tmdb_api_key', ''))
        self.omdb_api_key_edit.setText(config.get('omdb_api_key', ''))
        self.notify_edit.setText(config.get('notify', ''))
        
        loglevel = config.get('loglevel', 'INFO')
        index = self.loglevel_combo.findText(loglevel)
        if index >= 0:
            self.loglevel_combo.setCurrentIndex(index)
        
        self.rss_feed_edit.setText(config.get('rss_feed_url', 'https://nexxtpress.de/author/mediathekperlen/feed/'))
        
        # no_state Option
        no_state = config.get('no_state', False)
        self.no_state_checkbox.setChecked(no_state)
        self._on_no_state_toggled(no_state)
    
    def _save_settings(self):
        """Speichert die aktuellen Einstellungen."""
        # Hole serien_dir - wenn leer, verwende download_dir (wie Quickstart-Scripts)
        serien_dir = self.serien_dir_edit.text().strip()
        download_dir = self.download_dir_edit.text().strip()
        if not serien_dir:
            serien_dir = download_dir  # Leeres serien_dir = verwende download_dir
        
        config = {
            'download_dir': download_dir,
            'state_file': self.state_file_edit.text(),
            'no_state': self.no_state_checkbox.isChecked(),
            'sprache': self.sprache_combo.currentText(),
            'audiodeskription': self.audiodeskription_combo.currentText(),
            'serien_download': self.serien_download_combo.currentText(),
            'serien_dir': serien_dir,
            'tmdb_api_key': self.tmdb_api_key_edit.text(),
            'omdb_api_key': self.omdb_api_key_edit.text(),
            'notify': self.notify_edit.text(),
            'loglevel': self.loglevel_combo.currentText(),
            'rss_feed_url': self.rss_feed_edit.text()
        }
        
        # Validierung
        if not config['download_dir']:
            QMessageBox.warning(self, "Fehler", "Download-Verzeichnis muss angegeben werden!")
            return
        
        # Akzeptiere sowohl relative als auch absolute Pfade (wie Quickstart-Scripts)
        # Relative Pfade werden relativ zum Projekt-Root interpretiert
        
        self.config_manager.update(config)
        if self.config_manager.save():
            QMessageBox.information(self, "Erfolg", "Einstellungen wurden gespeichert!")
        else:
            QMessageBox.warning(self, "Fehler", "Fehler beim Speichern der Einstellungen!")
    
    def _reset_settings(self):
        """Setzt die Einstellungen auf Standard-Werte zurück."""
        reply = QMessageBox.question(
            self,
            "Zurücksetzen",
            "Möchten Sie wirklich alle Einstellungen auf Standard-Werte zurücksetzen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.config_manager.reset_to_defaults()
            self.config_manager.save()
            self._load_settings()
            QMessageBox.information(self, "Erfolg", "Einstellungen wurden zurückgesetzt!")
    
    def get_config(self) -> Dict:
        """Gibt die aktuellen UI-Werte als Dictionary zurück (ohne zu speichern)."""
        serien_dir = self.serien_dir_edit.text().strip()
        download_dir = self.download_dir_edit.text().strip()
        if not serien_dir:
            serien_dir = download_dir  # Leeres serien_dir = verwende download_dir
        
        return {
            'download_dir': download_dir,
            'state_file': self.state_file_edit.text(),
            'no_state': self.no_state_checkbox.isChecked(),
            'sprache': self.sprache_combo.currentText(),
            'audiodeskription': self.audiodeskription_combo.currentText(),
            'serien_download': self.serien_download_combo.currentText(),
            'serien_dir': serien_dir,
            'tmdb_api_key': self.tmdb_api_key_edit.text(),
            'omdb_api_key': self.omdb_api_key_edit.text(),
            'notify': self.notify_edit.text(),
            'loglevel': self.loglevel_combo.currentText(),
            'rss_feed_url': self.rss_feed_edit.text()
        }
