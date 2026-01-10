#!/usr/bin/env python3
"""
Perlentaucher GUI - Grafische Benutzeroberfläche für Perlentaucher.

Startet die PyQt6-basierte GUI-Anwendung.
"""
import sys
import os

# Stelle sicher, dass das GUI-Package gefunden wird
sys.path.insert(0, os.path.dirname(__file__))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    print("PyQt6 ist nicht installiert!")
    print("Installieren Sie PyQt6 mit: pip install PyQt6")
    sys.exit(1)

from gui.config_manager import ConfigManager
from gui.main_window import MainWindow


def main():
    """Haupt-Funktion für die GUI-Anwendung."""
    # Erstelle QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Perlentaucher GUI")
    app.setOrganizationName("Perlentaucher")
    
    # Stelle sicher, dass High-DPI-Skalierung aktiviert ist
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    # Lade Konfiguration
    config_manager = ConfigManager()
    
    # Erstelle Hauptfenster
    window = MainWindow(config_manager)
    window.show()
    
    # Starte Event-Loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
