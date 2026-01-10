"""
Konfigurations-Manager für die GUI-Anwendung.
Verwaltet das Laden und Speichern von Einstellungen in einer JSON-Datei.
Nutzt die gleiche Konfigurationsdatei wie die Quickstart-Scripts (.perlentaucher_config.json).
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional


class ConfigManager:
    """Verwaltet die Konfiguration der GUI-Anwendung."""
    
    DEFAULT_CONFIG = {
        "download_dir": "./downloads",
        "loglevel": "INFO",
        "sprache": "deutsch",
        "audiodeskription": "egal",
        "state_file": ".perlentaucher_state.json",
        "no_state": False,
        "notify": "",
        "tmdb_api_key": "",
        "omdb_api_key": "",
        "serien_download": "erste",
        "serien_dir": "",
        "rss_feed_url": "https://nexxtpress.de/author/mediathekperlen/feed/",  # GUI-spezifisch
        # GUI-spezifische Fenster-Einstellungen (werden von CLI-Scripts ignoriert)
        "gui_window_x": None,
        "gui_window_y": None,
        "gui_window_width": 1200,
        "gui_window_height": 800
        # Hinweis: "limit" wurde entfernt - es werden automatisch die letzten 30 Tage geladen
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialisiert den Config Manager.
        
        Args:
            config_file: Pfad zur Konfigurationsdatei. 
                        Standard: .perlentaucher_config.json (im Projekt-Root)
        """
        if config_file is None:
            # Versuche Projekt-Root zu finden (wo perlentaucher.py liegt)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)  # Ein Level höher (von gui/ zu root)
            
            # Fallback: Versuche via perlentaucher_gui.py zu finden
            # Wenn perlentaucher_gui.py im gleichen Verzeichnis wie perlentaucher.py ist
            main_script_path = os.path.join(project_root, "perlentaucher_gui.py")
            if os.path.exists(main_script_path):
                project_root = os.path.dirname(os.path.abspath(main_script_path))
            
            # Fallback: Versuche via sys.argv[0] wenn vorhanden
            if hasattr(sys, 'argv') and len(sys.argv) > 0:
                main_script = sys.argv[0]
                if main_script and (os.path.exists(main_script) or os.path.basename(main_script) == 'perlentaucher_gui.py'):
                    main_script_abs = os.path.abspath(main_script)
                    if os.path.exists(main_script_abs):
                        project_root = os.path.dirname(main_script_abs)
                    else:
                        # Wenn script nicht existiert (z.B. bei PyInstaller), verwende CWD
                        project_root = os.getcwd()
            
            config_file = os.path.join(project_root, ".perlentaucher_config.json")
        else:
            # Konvertiere zu absolutem Pfad
            if not os.path.isabs(config_file):
                config_file = os.path.abspath(config_file)
        
        self.config_file = config_file
        self.project_root = os.path.dirname(config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self) -> Dict:
        """
        Lädt die Konfiguration aus der Datei.
        
        Returns:
            Dictionary mit den Einstellungen
        """
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge mit Defaults, damit neue Optionen hinzugefügt werden können
                    self.config.update(loaded_config)
                    # Stelle sicher, dass alle Keys vorhanden sind
                    for key in self.DEFAULT_CONFIG:
                        if key not in self.config:
                            self.config[key] = self.DEFAULT_CONFIG[key]
                    # Stelle sicher, dass GUI-spezifische Felder vorhanden sind
                    if "rss_feed_url" not in self.config:
                        self.config["rss_feed_url"] = self.DEFAULT_CONFIG["rss_feed_url"]
                    # GUI-spezifische Fenster-Einstellungen
                    for gui_key in ["gui_window_x", "gui_window_y", "gui_window_width", "gui_window_height"]:
                        if gui_key not in self.config:
                            self.config[gui_key] = self.DEFAULT_CONFIG[gui_key]
            except (json.JSONDecodeError, IOError) as e:
                print(f"Fehler beim Laden der Konfiguration: {e}")
                print("Verwende Standard-Konfiguration.")
        else:
            # Erstelle Standard-Konfiguration nur wenn Datei nicht existiert
            # (muss nicht automatisch erstellt werden, da Quickstart-Script sie erstellt)
            pass
        
        return self.config
    
    def save(self) -> bool:
        """
        Speichert die aktuelle Konfiguration in die Datei.
        Entfernt GUI-spezifische Felder (rss_feed_url) vor dem Speichern,
        damit die Datei kompatibel mit Quickstart-Scripts bleibt.
        
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        try:
            # Stelle sicher, dass das Verzeichnis existiert
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Erstelle eine Kopie für das Speichern
            # GUI-spezifische Felder (gui_window_*, rss_feed_url) werden mitgespeichert,
            # aber von Quickstart-Scripts ignoriert (JSON.parse() ignoriert unbekannte Keys)
            save_config = self.config.copy()
            
            # Konvertiere None-Werte für JSON-Kompatibilität (None wird als null gespeichert)
            # JSON unterstützt null, aber Python None wird automatisch zu null konvertiert
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(save_config, f, indent=2, ensure_ascii=False)
            
            # Setze sichere Berechtigungen auf Linux/macOS (600 = nur Eigentümer)
            if sys.platform != 'win32':
                try:
                    os.chmod(self.config_file, 0o600)
                except (OSError, AttributeError):
                    pass  # Ignoriere Fehler bei Berechtigungsänderung
            
            return True
        except IOError as e:
            print(f"Fehler beim Speichern der Konfiguration: {e}")
            return False
    
    def get(self, key: str, default=None):
        """
        Gibt einen Konfigurationswert zurück.
        
        Args:
            key: Der Konfigurationsschlüssel
            default: Standardwert wenn Key nicht vorhanden
            
        Returns:
            Der Konfigurationswert oder default
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value) -> None:
        """
        Setzt einen Konfigurationswert.
        
        Args:
            key: Der Konfigurationsschlüssel
            value: Der neue Wert
        """
        self.config[key] = value
    
    def get_all(self) -> Dict:
        """
        Gibt die komplette Konfiguration zurück.
        
        Returns:
            Dictionary mit allen Einstellungen
        """
        return self.config.copy()
    
    def update(self, new_config: Dict) -> None:
        """
        Aktualisiert die Konfiguration mit neuen Werten.
        
        Args:
            new_config: Dictionary mit zu aktualisierenden Werten
        """
        self.config.update(new_config)
    
    def reset_to_defaults(self) -> None:
        """Setzt die Konfiguration auf Standard-Werte zurück."""
        self.config = self.DEFAULT_CONFIG.copy()
