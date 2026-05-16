# Release v0.1.52

## Neue Features
- **Staffel-Download**: Der Staffel-Dialog wählt für jede Episode die beste Variante basierend auf den Benutzereinstellungen aus, unabhängig von der globalen Download-Einstellung.

## Verbesserungen
- **Serien-Suche**: Die Suche nutzt nun API und Feed parallel, um die Trefferquote bei kurzen Suchbegriffen zu erhöhen. Ein-Wort-Titel werden strenger gefiltert, um Verwechslungen mit Fremdtiteln zu vermeiden.
- **Robustheit der Titelsuche**: Verbesserte Robustheit der Titelsuche im MVW.

## Bugfixes
- **Staffel-Download**: Korrektur bei der Auswahl der besten Fassung pro Episode im Wishlist-Modus.
  
## Technische Änderungen
- **Version**: Version auf 0.1.51 erhöht.
- **Linux-GUI-Build**: 
  - PEP 668 konformes Projekt-venv hinzugefügt.
  - `build_gui_linux.sh` wurde angepasst, um das venv anzulegen und die erforderlichen Abhängigkeiten zu installieren.
  - `build_gui_linux.sh` ist nun ausführbar (chmod +x).
- **.gitignore**: Aktualisiert, um Log-Dateien und VSCode-Einstellungen zu ignorieren; *.log hinzugefügt.
- **Externes Öffnen**: Die Funktion `safe_desktop_open` wurde implementiert, um URLs und Ordner per `xdg-open/open` unter Linux/macOS zu öffnen, ohne von PyInstaller abhängige Umgebungsvariablen.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.52)
