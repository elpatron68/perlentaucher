# Release v0.1.53

## Neue Features
- Keine neuen Features in diesem Release.

## Verbesserungen
- Minimale Pythonversion erhöht: Das Projekt erfordert jetzt mindestens Python 3.8.
- Aktualisierung der `requirements.txt`: `uvicorn[standard]` auf Version `>=0.23.0` festgelegt.
- Aktueller Link auf den Forgejo Runner implementiert.

## Bugfixes
- Syntaxfehler in Mermaid Flowchart behoben.

## Technische Änderungen
- CI-Änderungen: GitHub Actions auf Node.js-24-kompatible Versionen aktualisiert. 
  - `upload-artifact` auf Version 6, `download-artifact` auf Version 7 und `action-gh-release` auf Version 3 aktualisiert, um die Deprecation-Warnung für Node 20 auf den Runnern zu beheben.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.53)
