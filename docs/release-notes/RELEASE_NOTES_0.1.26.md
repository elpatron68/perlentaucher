# Release v0.1.26

## Neue Features
- Update-Check Funktionalität für die GUI-App hinzugefügt:
  - Automatische Prüfung beim Start (2s verzögert)
  - Manuelle Prüfung über den "Über"-Dialog
  - Update-Dialog bei verfügbarer neuer Version
  - Öffnet Download-URL im Browser

## Verbesserungen
- Verbesserte Verarbeitung der RSS-Feeds:
  - Nicht-Film-Empfehlungen (z.B. "In eigener Sache") werden herausgefiltert
  - Jahreszahlen aus RSS-Feed-Titeln werden nun auch ohne TMDB/OMDB API für Dateinamen verwendet

## Bugfixes
- GUI-App stürzt nicht mehr beim Start ab (Fehler: 'config is not defined' beim Laden des RSS-Feeds behoben)
- GUI-App beendet sich nicht mehr automatisch nach dem letzten Download
- Doppelte Asset-Uploads bei Codeberg-Releases behoben

## Technische Änderungen
- Variable `state_file` statt undefiniertem `config` in `blog_list_panel` implementiert

---
*Hinweis: Dieses Release enthält wichtige Stabilitätsverbesserungen und neue Funktionen für die GUI-App.*

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.26)
