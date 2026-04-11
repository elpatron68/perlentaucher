# Release v0.1.44

## Weitere Änderungen

- Serien: Staffel/Episode aus (S02/E01) vor (1/6) und Folge n
- Serien: Original-Titel-Marker (Originalversion) stark abwerten vs. Dateigr├Â├ƒe
- Sprache: (Originalversion) wie Originalton erkennen (ONE/ARD)
- Windows-GUI-Build: Ablauf in build_gui_windows.py (fix PS '.' / dist-Kopie)
- find wie zuvor gegen laufende GUI
- build_gui_windows: PyInstaller via python -m (Skript laeuft nach Build weiter)
- build_gui_windows: for-Schleife entfernt, move+copy-Fallback, Pfad pr├╝fen
- GUI: Ordner ├Âffnen f├╝r Serien-Staffel-Download (Serienverzeichnis)
- Spracherkennung: OmU/OV vs. Synchron, kein False Positive 'deutschen'
- Windows-GUI-Build: Repo-Root, Prozess-Check, temporaeres distpath
- Serien-Download: strengeres Matching, Trailer-Filter, Episoden-Parsing

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/Perlentaucher/commits/v0.1.44)
