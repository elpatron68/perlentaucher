"""
Hauptfenster für die GUI-Anwendung.
Integriert alle Panels in einem Tab-Widget.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMenu, QStatusBar, QMessageBox,
    QDialog, QVBoxLayout, QLabel, QPushButton, QButtonGroup, QRadioButton, QSizePolicy,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QRect
from PyQt6.QtGui import QAction
from typing import Dict, Optional
import sys
import os

from gui.settings_panel import SettingsPanel
from gui.blog_list_panel import BlogListPanel
from gui.download_panel import DownloadPanel
from gui.config_manager import ConfigManager


class MainWindow(QMainWindow):
    """Hauptfenster der GUI-Anwendung."""
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        """
        Initialisiert das Hauptfenster.
        
        Args:
            config_manager: Instance von ConfigManager
            parent: Parent Widget
        """
        super().__init__(parent)
        self.config_manager = config_manager
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialisiert die UI-Komponenten."""
        self.setWindowTitle("Perlentaucher GUI")
        
        # Lade gespeicherte Fenstergröße und Position
        self._restore_window_geometry()
        
        # Stelle sicher, dass das Fenster in beide Richtungen resizable ist
        self.setMinimumSize(QSize(800, 600))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Menüleiste
        self._create_menu_bar()
        
        # Tab-Widget
        self.tabs = QTabWidget()
        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCentralWidget(self.tabs)
        
        # Neue Reihenfolge: 1. Feed, 2. Downloads, 3. Einstellungen
        # Blog-Liste Panel (Feed) - Tab 0
        self.blog_list_panel = BlogListPanel(self.config_manager)
        self.blog_list_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs.addTab(self.blog_list_panel, "📰 Feed")
        
        # Download Panel - Tab 1
        self.download_panel = DownloadPanel()
        self.download_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs.addTab(self.download_panel, "⬇️ Downloads")
        
        # Einstellungen Panel - Tab 2
        self.settings_panel = SettingsPanel(self.config_manager)
        self.settings_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tabs.addTab(self.settings_panel, "⚙️ Einstellungen")
        
        # Statusleiste
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bereit")
        
        # Öffne beim Start den richtigen Tab:
        # - Einstellungen-Tab wenn keine Konfigurationsdatei gefunden wurde
        # - Feed-Tab (Tab 0) wenn Konfigurationsdatei existiert
        self._set_initial_tab()
    
    def _create_menu_bar(self):
        """Erstellt die Menüleiste."""
        menubar = self.menuBar()
        
        # Datei-Menü
        file_menu = menubar.addMenu("Datei")
        
        save_action = QAction("Einstellungen speichern", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_settings)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Beenden", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Download-Menü
        download_menu = menubar.addMenu("Download")
        
        start_action = QAction("Ausgewählte Downloads starten", self)
        start_action.setShortcut("F5")
        start_action.triggered.connect(self._start_selected_downloads)
        download_menu.addAction(start_action)
        
        cancel_action = QAction("Alle Downloads abbrechen", self)
        cancel_action.setShortcut("Esc")
        cancel_action.triggered.connect(self._cancel_all_downloads)
        download_menu.addAction(cancel_action)
        
        # Hilfe-Menü
        help_menu = menubar.addMenu("Hilfe")
        
        about_action = QAction("Über", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _connect_signals(self):
        """Verbindet Signale zwischen Panels."""
        # Wenn Blog-Liste Einträge lädt, aktiviere Download-Button
        self.blog_list_panel.entries_loaded.connect(self._on_entries_loaded)
        
        # Verbinde Download-Button mit Start-Funktion
        self.download_panel.start_downloads_btn.clicked.connect(self._start_selected_downloads)
    
    def _set_initial_tab(self):
        """Setzt den initialen Tab beim Start."""
        # Prüfe ob Konfigurationsdatei existiert
        config_file_exists = os.path.exists(self.config_manager.config_file)
        
        if config_file_exists:
            # Konfiguration vorhanden: Öffne Feed-Tab (Tab 0)
            self.tabs.setCurrentIndex(0)
            self.status_bar.showMessage("Konfiguration geladen. Feed-Tab geöffnet.", 3000)
        else:
            # Keine Konfiguration: Öffne Einstellungen-Tab (Tab 2)
            self.tabs.setCurrentIndex(2)
            self.status_bar.showMessage("Keine Konfigurationsdatei gefunden. Bitte Einstellungen vornehmen.", 5000)
    
    def _on_entries_loaded(self, entries):
        """Wird aufgerufen wenn Einträge geladen wurden."""
        # Aktiviere Download-Button wenn Einträge vorhanden
        if entries:
            self.download_panel.start_downloads_btn.setEnabled(True)
        else:
            self.download_panel.start_downloads_btn.setEnabled(False)
    
    def _save_settings(self):
        """Speichert die Einstellungen."""
        self.settings_panel._save_settings()
        self.status_bar.showMessage("Einstellungen gespeichert.", 3000)
    
    def _start_selected_downloads(self):
        """Startet die ausgewählten Downloads."""
        # Hole ausgewählte Einträge aus Blog-Liste
        selected_entries = self.blog_list_panel.get_selected_entries()
        
        if not selected_entries:
            QMessageBox.warning(self, "Keine Auswahl", "Bitte wählen Sie mindestens einen Eintrag in der Blog-Liste aus!")
            return
        
        # Prüfe ob Serien dabei sind
        series_entries = [e for e in selected_entries if e.get('is_series', False)]
        
        # Wenn Serien dabei sind, zeige Dialog zur Auswahl
        series_download_mode = {}  # entry_id -> 'erste' oder 'staffel'
        if series_entries:
            for entry in series_entries:
                choice = self._ask_series_download_mode(entry)
                if choice is None:  # Benutzer hat abgebrochen
                    return
                series_download_mode[entry['entry_id']] = choice
        
        # Hole aktuelle Konfiguration
        config = self.settings_panel.get_config()
        
        # Starte Downloads mit Serien-Auswahl
        self.download_panel.start_downloads(selected_entries, config, series_download_mode=series_download_mode)
        
        # Wechsle zum Download-Tab (Tab 1 in neuer Reihenfolge)
        self.tabs.setCurrentIndex(1)
        
        self.status_bar.showMessage(f"{len(selected_entries)} Download(s) gestartet.", 3000)
    
    def _ask_series_download_mode(self, entry_data: Dict) -> Optional[str]:
        """
        Zeigt einen Dialog zur Auswahl des Serien-Download-Modus.
        
        Args:
            entry_data: Dictionary mit Entry-Daten
            
        Returns:
            'erste' für nur erste Episode, 'staffel' für alle Episoden, None wenn abgebrochen
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Serien-Download Auswahl")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout()
        
        # Titel-Label
        series_title = entry_data.get('movie_title', entry_data.get('rss_title', 'Unbekannte Serie'))
        title_label = QLabel(f"<h3>{series_title}</h3>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        info_label = QLabel("Wie möchten Sie diese Serie herunterladen?")
        layout.addWidget(info_label)
        
        # Radio-Buttons
        button_group = QButtonGroup()
        
        first_ep_radio = QRadioButton("Nur erste Episode")
        first_ep_radio.setChecked(True)  # Standard
        button_group.addButton(first_ep_radio, 0)
        layout.addWidget(first_ep_radio)
        
        all_ep_radio = QRadioButton("Alle verfügbaren Episoden")
        button_group.addButton(all_ep_radio, 1)
        layout.addWidget(all_ep_radio)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QVBoxLayout()
        ok_btn = QPushButton("Download starten")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_row = QVBoxLayout()
        button_row.addWidget(ok_btn)
        button_row.addWidget(cancel_btn)
        layout.addLayout(button_row)
        
        dialog.setLayout(layout)
        
        # Zeige Dialog
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if all_ep_radio.isChecked():
                return 'staffel'
            else:
                return 'erste'
        else:
            return None
    
    def _cancel_all_downloads(self):
        """Bricht alle Downloads ab."""
        self.download_panel._cancel_all_downloads()
        self.status_bar.showMessage("Alle Downloads abgebrochen.", 3000)
    
    def _show_about(self):
        """Zeigt das About-Dialog."""
        try:
            import _version
            version = _version.__version__
        except ImportError:
            version = "unknown"
        
        about_text = f"""
        <h2>Perlentaucher GUI</h2>
        <p>Version {version}</p>
        <p>Eine grafische Benutzeroberfläche für Perlentaucher.</p>
        <p>Automatischer Download von Film-Empfehlungen aus dem RSS-Feed Mediathekperlen.</p>
        <p><a href="https://codeberg.org/elpatron/Perlentaucher">GitHub Repository</a></p>
        <p>Lizenz: MIT</p>
        """
        
        QMessageBox.about(self, "Über Perlentaucher GUI", about_text)
    
    def closeEvent(self, event):
        """Wird aufgerufen wenn das Fenster geschlossen wird."""
        # Prüfe ob aktive Downloads laufen
        if self.download_panel.active_downloads:
            reply = QMessageBox.question(
                self,
                "Downloads aktiv",
                "Es laufen noch aktive Downloads. Möchten Sie wirklich beenden?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            # Breche alle Downloads ab
            for entry_id in list(self.download_panel.active_downloads.keys()):
                self.download_panel._cancel_download(entry_id)
        
        # Speichere Fenstergröße und Position
        self._save_window_geometry()
        
        # Speichere Einstellungen
        self.config_manager.save()
        
        event.accept()
    
    def _restore_window_geometry(self):
        """Stellt die gespeicherte Fenstergröße und Position wieder her."""
        x = self.config_manager.get('gui_window_x')
        y = self.config_manager.get('gui_window_y')
        width = self.config_manager.get('gui_window_width', 1200)
        height = self.config_manager.get('gui_window_height', 800)
        
        # Prüfe ob Werte gültig sind (nicht None und innerhalb des Bildschirms)
        if x is not None and y is not None:
            # Prüfe ob Position innerhalb des Bildschirms liegt
            app = QApplication.instance()
            if app:
                screens = app.screens()
                if screens:
                    # Verwende primären Bildschirm
                    screen = screens[0]
                    screen_geometry = screen.geometry()
                    
                    # Stelle sicher, dass Position gültig ist
                    if (screen_geometry.left() <= x <= screen_geometry.right() and
                        screen_geometry.top() <= y <= screen_geometry.bottom()):
                        # Stelle sicher, dass mindestens ein Teil des Fensters sichtbar ist
                        # (z.B. nicht komplett außerhalb)
                        if (x + width >= screen_geometry.left() and
                            y + height >= screen_geometry.top()):
                            self.setGeometry(x, y, width, height)
                            return
        
        # Fallback: Standard-Größe und Position (zentriert auf Bildschirm)
        default_width = 1200
        default_height = 800
        app = QApplication.instance()
        if app and app.screens():
            screen = app.screens()[0]
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - default_width) // 2 + screen_geometry.left()
            y = (screen_geometry.height() - default_height) // 2 + screen_geometry.top()
            self.setGeometry(x, y, default_width, default_height)
        else:
            # Fallback falls kein Bildschirm gefunden
            self.setGeometry(100, 100, default_width, default_height)
    
    def _save_window_geometry(self):
        """Speichert die aktuelle Fenstergröße und Position."""
        geometry = self.geometry()
        self.config_manager.set('gui_window_x', geometry.x())
        self.config_manager.set('gui_window_y', geometry.y())
        self.config_manager.set('gui_window_width', geometry.width())
        self.config_manager.set('gui_window_height', geometry.height())
