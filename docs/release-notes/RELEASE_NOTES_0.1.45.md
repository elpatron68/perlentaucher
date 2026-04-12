# Release v0.1.45

## Neue Features

- feat: Favicon und /assets-Icons f├╝r Wishlist-Web-UI
- feat: gemeinsamer Aktivit├ñtsverlauf f├╝r CLI, GUI und Wishlist-Web-UI
- Add exit code handling for wishlist processing in main function
- Feature: Wishlist mit CLI, GUI, Web-UI und Docker-Integration

## Bugfixes

- fix(gui): Wishlist sendet keine Apprise-Benachrichtigungen mehr
- fix: Wishlist-Web Port-Check und README-Hinweise (Windows/venv)
- fix: keine Erfolgs-/Fehler-Pushes fuer RSS-Feed bei --notify
- Fix typo in README.md regarding download directory settings for Wishlist feature.
- Fix: sys.path in wishlist_panel auf Projekt-Root (drei dirname), nicht src/
- Fix: Projekt-Root auf sys.path f├╝r python src/perlentaucher.py

## Technische Änderungen

- CI: GitHub Actions auf checkout@v5 und setup-python@v6 (Node 24)

## Weitere Änderungen

- docs: Programmablauf an RSS-Feed und Notify-Verhalten anpassen
- GUI: WishlistCheckThread-Referenz in WishlistPanel initialisieren
- Tests: Wishlist-Kern und Web-UI abdecken
- Benachrichtigungen: Wishlist-Kontext und ├£berspringen bei vorhandener Datei
- Wishlist: Probe nach Hinzufuegen, Trefferauswahl, README
- Docker: Wishlist-Exit-Code im Zyklus-Log auswerten
- Update README.md to include a tip for using the Wishlist feature to download already available titles from the Mediathek, emphasizing convenience and preference settings.
- GUI: Wishlist optional beim Start automatisch verarbeiten (Standard: an)
- Update .gitignore to include .perlentaucher_wishlist.json
- Wishlist-Web: M├╝lleimer-Icon f├╝r Entfernen, vertikale Tabellen-Ausrichtung
- Wishlist-Web: klare Meldung nach Verf├╝gbarkeitspr├╝fung (inkl. total/API)
- README: Logo per assets/perlerntaucher_512.png einbinden

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/Perlentaucher/commits/v0.1.45)
