# Release v0.1.31

### Verbesserungen
- macOS Artifact-Upload ist nun optional und hat eine reduzierte Aufbewahrungszeit von 7 Tagen
- Optimierte Artifact-Upload-Pfade für Windows/Linux/macOS durch spezifische Pfadangaben statt Wildcards

### Bugfixes
- Pillow wird nun korrekt als Universal Binary für macOS installiert
- Korrigierte Icon-Format-Konvertierung (.ico zu .icns) auf macOS durch Installation von Pillow
- Behobene Build-Probleme für macOS Universal Binaries mit PyYAML

### Technische Änderungen
- Entfernte veraltete hidden imports:
  - `requests.packages.urllib3`
  - `requests.packages.urllib3.util.ssl_`
- Build-Pipeline-Optimierungen für macOS Universal Binaries
- Hinzugefügte `continue-on-error` Option für macOS Artifact-Upload zur Vermeidung von Build-Fehlern bei Speicherquoten-Überschreitung

*Hinweis: Dieses Release konzentriert sich hauptsächlich auf Verbesserungen der Build-Pipeline und Korrekturen für macOS Universal Binary Builds.*

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.31)
