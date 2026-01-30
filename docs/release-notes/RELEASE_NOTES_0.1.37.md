# Release v0.1.37

## Verbesserungen

### Episodenerkennung
- Verbesserte Erkennung von Episodeninformationen im Titel
  - Unterstützung für (X/Y) Format (z.B. "Bad Banks (1/6)")
  - Priorisierung der (X/Y) Erkennung vor SxxExx Format
  - Fallback auf Erkennung ohne Staffel/Episode wenn kein Format gefunden

## Technische Änderungen
- Überarbeitung der `extract_episode_info` Funktion
  - Neue Logik für die Reihenfolge der Formatprüfung
  - Implementierung der (X/Y) Mustererkennung

---
*Datum: [DATUM]*

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.37)
