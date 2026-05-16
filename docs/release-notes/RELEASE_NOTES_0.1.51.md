# Release v0.1.51

## Neue Features
- **Staffel-Download**: Der Staffel-Dialog erzwingt jetzt den Staffel-Modus unabhängig von `serien_download=erste`. Die Wishlist wählt pro Staffel/Episode die beste Variante nach den Einstellungen aus (Funktion: `pick_best_series_episodes_per_slot`).

## Verbesserungen
- **Serien-Suche**: Die Serien-Suche nutzt nun sowohl die API als auch den MVW-Feed parallel. Dadurch wird sichergestellt, dass kurze Suchbegriffe nicht an einem einzelnen API-Fehltreffer hängen bleiben. Ein-Wort-Titel werden strenger gefiltert, um Verwechslungen mit Sendungsdaten zu vermeiden.

## Bugfixes
- **Staffel-Download**: Behebung eines Problems beim Download von Staffeln mit Sprache/AD und der Auswahl der besten Fassung pro Episode.

## Technische Änderungen
- **MVW-Feed**: Integration des MVW-Feeds mit der API für eine verbesserte Suche und genauere Ergebnisse.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.51)
