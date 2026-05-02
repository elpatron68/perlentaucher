# Changelog

Basierend auf dem Git-Verlauf des Repos [Perlentaucher](https://codeberg.org/elpatron/Perlentaucher) relativ zum Tag [`v0.1.47`](https://codeberg.org/elpatron/Perlentaucher/commits/tag/v0.1.47).

---

## [Unreleased]

### Infrastruktur

- `release.ps1`: Schalter `-SkipRelease` überspringt GitHub-Release (`gh`) und Codeberg-Release (API); Version bump, Tag, Push und Docker-Build laufen weiter.

---

## [0.1.47] – 2026-05-02

Vergleich: `v0.1.46` … `v0.1.47` (lokal: `git log v0.1.46^{}..v0.1.47^{}`).

### Mediathek & Serien

- Serien-Mediathek: Matching verbessert; Docker-Doku aktualisiert (`9688371`).
- Serien-Mediathek: breitere API-Nutzung und Topic-Scoring; Unraid-Build/Deploy-Skripte (`422e96e`).
- Merge: Serien-Suche/Wishlist-Zweig zusammengeführt (Konfliktauflösung, keine Nautilus-Sonderlogik) (`f22405b`).
- Serien-Matching: Schema aus Staffel-1-Treffern ableiten und irrelevante MVW-Treffer vor dem Scoring filtern (`6142a7b`).
- Sender-Mediathek: Links aus RSS (optional Blog-Artikel nachladen) für Referenz-Matching und weniger Off-Topic-Treffer (`4c48c31`).
- Automatische Nummerierung von Episoden ohne parsbare Staffel/Episode wird zurückgeschraubt, wenn bereits genügend gültige Episoden erkannt sind – weniger False Positives (CLI, Feed, Wishlist, GUI) (`864a5d6`).
- Filmtitel: Ähnlichkeit und Substring-Checks nutzen `normalize_search_title` (z. B. Akzentvarianten wie Fantômas/Fantomas) (`6614152`).

### HLS / ffmpeg / Downloads

- HLS-Streams (`.m3u8`): Download und Remux nach MP4 über **ffmpeg** (CLI, Wishlist, Wishlist-Web-Env, Docker-Image mit ffmpeg; Konfiguration `--ffmpeg-path` / `FFMPEG_PATH` / GUI-Feld) (`40ac3f0`).
- Nach Abbruch oder Fehler: kein „Phantom-Pfad“ mehr in Benachrichtigungen; gelöschte Partieldateien konsistent (`5db366b`).
- GUI: ffmpeg beim Start ermitteln (`ensure_ffmpeg_path_at_startup`: PATH, `FFMPEG_PATH`, Pfad normalisieren); Windows: kein Konsolenfenster für den ffmpeg-Prozess (`fe33369`).

### GUI

- RSS-Jahr aus dem Feed bleibt maßgeblich; TMDB überschreibt es nicht; Sender-Link-Fetch per Blog-Artikel standardmäßig an (`6c3fbb5`).
- Externe Benachrichtigungen (Ntfy/Apprise) in der **GUI** deaktiviert – nur noch CLI als Kanal (PyInstaller/Plugin-Pfade) (`6ed8917`).
- Zuvor: Apprise/Ntfy für RSS-Feed und GUI wieder vollständiger Kontext; Feed-Pushes bei Erfolg, Fehler und „bereits vorhanden“ (`0ec0314`).
- Blog-Post-Link in Feed-Download-Benachrichtigungen (`14b4df0`).

### Benachrichtigungen

- Wishlist: „nicht gefunden“-Meldungen unterdrücken, wenn Mediathek-Suche im Wishlist-Kontext (`3d3df27`).
- Kein Apprise-Push bei Filmen unter der Titel-Ähnlichkeitsschwelle (`2fded8b`).

### Wishlist-Web

- Verlauf: einklappbar, API-Filter und Paginierung (`0f227f4`).
- Footer: Git-Describe; bei „dirty“ Working Tree Kurz-Commit-ID (`31d84a3`, `ebba410`).

### Tests & Dokumentation

- Coverage: Kern ohne GUI, Schwelle 30 %, Tests für `wishlist_activity` (`fd3c937`).
- Doku: Kern vs. vollständige Coverage; Tabellenformatierung (`e7907c3`, `0afba49`).
- Skript-Doku: Unraid nach Deploy — Container neu anlegen statt nur neu starten (`8638ca2`).

### Sonstiges / Infrastruktur

- Kleine Skript-/Konfig-Fixes (IP-Adresse, ausführbar machen) (`fda51c0`, `df9a109`).
- Wishlist/Web/GUI: Probe-Fehler, Eintrag behalten, Thread-Ausnahmen (`01b2914`).

---

## Referenz

| Tag      | Commit (annotiert `^{}`) |
|----------|---------------------------|
| `v0.1.47` | Version bump 0.1.47 (`406db8c`) |

Links: [Commits zu Tag v0.1.47](https://codeberg.org/elpatron/Perlentaucher/commits/tag/v0.1.47)
