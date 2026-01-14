#!/usr/bin/env python3
"""
Perlentaucher GUI - Grafische Benutzeroberfläche für Perlentaucher.

Startet die PyQt6-basierte GUI-Anwendung.
"""
import sys
import os

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
except ImportError:
    print("PyQt6 ist nicht installiert!")
    print("Installieren Sie PyQt6 mit: pip install PyQt6")
    sys.exit(1)

# Imports so anpassen, dass sie sowohl im Paket-Kontext (normaler Aufruf)
# als auch im PyInstaller-Executable (kein Paketkontext) funktionieren.
try:
    # Paket-Import (z.B. beim Ausführen innerhalb von src als Modul)
    from .gui.config_manager import ConfigManager
    from .gui.main_window import MainWindow
except ImportError:
    # Fallback für PyInstaller / Standalone-Executable:
    # In diesem Kontext existiert kein Paket-Elternteil mehr,
    # die Module liegen aber weiterhin unter dem Paketnamen `src`.
    from src.gui.config_manager import ConfigManager
    from src.gui.main_window import MainWindow


def resource_path(relative_path):
    """
    Gibt den absoluten Pfad zu einer Ressource zurück.
    Funktioniert sowohl für normale Ausführung als auch für PyInstaller-Executables.
    
    Args:
        relative_path: Relativer Pfad zur Ressource (z.B. 'assets/icon_256.png')
    
    Returns:
        Absoluter Pfad zur Ressource
    """
    try:
        # PyInstaller erstellt ein temporäres Verzeichnis und speichert den Pfad in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Normale Ausführung: Verwende das Verzeichnis der Hauptdatei
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


def main():
    """Haupt-Funktion für die GUI-Anwendung."""
    # Erstelle QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("Perlentaucher GUI")
    app.setOrganizationName("Perlentaucher")
    
    # Setze Anwendungs-Icon
    icon_path = resource_path('assets/icon_256.png')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # In PyQt6 ist High-DPI-Skalierung standardmäßig aktiviert
    # Die alten Attribute (AA_EnableHighDpiScaling, AA_UseHighDpiPixmaps) existieren nicht mehr
    
    # Lade Konfiguration
    config_manager = ConfigManager()
    
    # Erstelle Hauptfenster
    window = MainWindow(config_manager)
    window.show()
    
    # Starte Event-Loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
