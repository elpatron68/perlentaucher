# Release v0.1.34

### 🔧 Verbesserungen
- Optimierte Suchfunktion:
  - Verbesserte Vorfilterung durch Substring-Matching
  - Anpassung der Suchanfrage auf title-only
  - Lockerung der Relevanz-Filterung für bessere Suchergebnisse
- Erweiterte Debug-Ausgaben für bessere Nachvollziehbarkeit

### 🐛 Bugfixes
- Korrektur der MediathekViewWeb-API Abfragen durch minimale Queries
- Verbesserte Treffergenauigkeit bei der Suche, speziell für Filme wie "Swiss Army Man"
- Entfernung der zu strikten Relevanz-Filterung

### 🔨 Technische Änderungen
- Automatisierte Versionierung: Build-Scripts lesen Version dynamisch aus _version.py
- Verbesserte Docker-Build Dokumentation
  - Ergänzung der Build-Kontext Informationen im Dockerfile
  - Hinzufügung relevanter Build-Scripts

Diese Version fokussiert sich hauptsächlich auf die Verbesserung der Suchfunktionalität und technische Optimierungen im Build-Prozess.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.34)
