# Release v0.1.40

### Neue Features
- Filme können jetzt über Suchbegriffe (Titel) heruntergeladen werden
  - Neue Funktion `download_by_search()` im Core
  - Unterstützung via GUI und Kommandozeile (`--search`)
- Ordner öffnen per Doppelklick in der Download-Tabelle für abgeschlossene Downloads

### Verbesserungen
- Verbesserte Titelsuche mit korrekter Umlaut-Behandlung
- Bessere Auffindbarkeit der "Ordner öffnen" Funktion in GUI und Kontextmenü
- Erweiterte Dokumentation:
  - Verbesserte Gatekeeper-Anleitung für macOS
  - Ergänzte plattformspezifische Hinweise
  - Neue Screenshots für macOS (hell und dunkel)
  - Dokumentation der Suchfunktion und `--search`-Parameter

### Technische Änderungen
- Korrektur der Dateinamen für Windows/Linux Builds (PerlentaucherGUI-VERSION-*.exe/.linux)
- Hinweis: `--limit` Parameter wird bei `--search` ignoriert

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.40)
