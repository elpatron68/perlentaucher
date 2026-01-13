# Release v0.1.29

### Neue Features
- macOS: Universal Binary (universal2) für Intel- und Apple-Silicon-Unterstützung

### Verbesserungen
- Verbesserte README.md Dokumentation:
  - Ergänzung von Vorwort und Projektbeschreibung
  - Aktualisierung der CI/CD-Pipeline-Beschreibung
  - Optimierte Strukturierung der Nutzungsdokumentation
  - Korrektur von Schreibfehlern und Verbesserung von Formulierungen

### Bugfixes
- Behebung des nicht funktionierenden Download-Links nach Update-Prüfung durch Hinzufügen des QUrl-Imports
- Korrektur der macOS Build-Konfiguration:
  - Entfernung von --windowed und --target-arch aus PyInstaller-Aufruf
  - Korrektes Setzen von target_arch='universal2' nur für macOS

### Technische Änderungen
- Restrukturierung des Projekts:
  - Verschiebung aller Quellcode-Dateien in src/ Ordner
  - Verschiebung der Docker-Dateien in docker/ Ordner
  - Aktualisierung der Importpfade in build.spec
- Entfernung veralteter CI/CD-Konfiguration (.woodpecker.yml)

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.29)
