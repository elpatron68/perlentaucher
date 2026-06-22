# Changelog

Basierend auf dem Git-Verlauf des Repos [Perlentaucher](https://codeberg.org/elpatron/Perlentaucher) relativ zum Tag [`v0.1.47`](https://codeberg.org/elpatron/Perlentaucher/commits/tag/v0.1.47).

---

## [Unreleased]

---

## [0.1.55] – 2026-06-22

Vergleich: `v0.1.54` … `v0.1.55` (lokal: `git log v0.1.54^{}..v0.1.55^{}`).

### Sonstiges

- Keine funktionalen Änderungen gegenüber 0.1.54; nur Version-Bump (`486db2f`).

---

## [0.1.54] – 2026-06-22

Vergleich: `v0.1.53` … `v0.1.54` (lokal: `git log v0.1.53^{}..v0.1.54^{}`).

### GUI / Downloads

- Beim ersten Download aus der GUI wurde das Zielverzeichnis (`downloads`) nicht angelegt; der erste Versuch schlug fehl, der zweite klappte. `build_download_filepath` erstellt das Verzeichnis jetzt bei Bedarf (`4878d0a`, PR #8).

---

## [0.1.53] – 2026-06-22

Vergleich: `v0.1.52` … `v0.1.53` (lokal: `git log v0.1.52^{}..v0.1.53^{}`).

### Dokumentation & Quickstart

- Minimale Pythonversion in Quickstart-Skripten und Doku auf **3.8+** angehoben (uvicorn `>=0.23.0` unterstützt Python 3.7 nicht mehr) (`1ae2d97`, PR #7).
- Forgejo-Runner-Download-Link in `docs/cicd.md` auf `code.forgejo.org` aktualisiert (`44d4b98`, PR #6).
- Mermaid-Syntaxfehler im Programmablauf-Flowchart behoben (`b8802ce`, PR #6).

### CI

- `build-gui.yml`: GitHub Actions auf Node.js-24-kompatible Versionen (`upload-artifact` v6, `download-artifact` v7, `action-gh-release` v3) (`9d4ba2c`).

---

## [0.1.52] – 2026-05-16

Vergleich: `v0.1.51` … `v0.1.52` (lokal: `git log v0.1.51^{}..v0.1.52^{}`).

### Mediathek & Serien

- MVW-Titelsuche robuster: kompakte Buchstabenfolgen, Untertitel nach Gedankenstrich, API zuerst Titelfeld (`d16e7e5`).

### GUI

- Externes Öffnen von URLs/Ordnern ohne PyInstaller-`LD_LIBRARY_PATH`-Probleme unter Linux/macOS (`safe_desktop_open`) (`d16e7e5`).

### Build & Infrastruktur

- Linux-GUI-Build: projektweites `.venv` (PEP 668); `build_gui_linux.sh` ausführbar (`ac0eb72`, `c75d1ec`).
- `.gitignore`: Log-Dateien, VSCode-Einstellungen, `.cursor/` (`60bc8d6`, `ac0eb72`).

---

## [0.1.51] – 2026-05-16

Vergleich: `v0.1.50` … `v0.1.51` (lokal: `git log v0.1.50^{}..v0.1.51^{}`).

### Mediathek & Serien

- Serien-Suche: MVW-Feed und API parallel; Ein-Wort-Titel strenger gefiltert, um Verwechslungen zu vermeiden (`0c2fe7d`).

### Wishlist & Staffel-Download

- Staffel-Download: pro Episode beste Variante nach Sprache/AD-Einstellungen; Staffel-Modus unabhängig von `serien_download=erste` (`5abed11`).

---

## [0.1.50] – 2026-05-07

Vergleich: `v0.1.49` … `v0.1.50` (lokal: `git log v0.1.49^{}..v0.1.50^{}`).

### GUI

- RSS-Laden: `fetch_article=False` fest verdrahtet, damit alte Config-Werte (`resolve_sender_link_fetch=true`) den Start nicht erneut blockieren (`cc9a165`).

---

## [0.1.49] – 2026-05-07

Vergleich: `v0.1.48` … `v0.1.49` (lokal: `git log v0.1.48^{}..v0.1.49^{}`).

### GUI

- RSS-Initialladen: Standard für `resolve_sender_link_fetch` auf `false`; kein synchrones Artikelfetching im GUI-Thread mehr (Fix für ~30s Hänger bei Timeout) (`015b61a`).

---

## [0.1.48] – 2026-05-02

Vergleich: `v0.1.47` … `v0.1.48` (lokal: `git log v0.1.47^{}..v0.1.48^{}`).

### Infrastruktur

- `release.ps1`: Schalter `-SkipRelease` überspringt GitHub-Release (`gh`) und Codeberg-Release (API); Version bump, Tag, Push und Docker-Build laufen weiter (`63e6c8b`).
- `release.ps1`: Einrückung in SkipRelease-Zweigen vereinheitlicht (`e3cb99e`).
- CHANGELOG versioniert; Unreleased-Einträge für `-SkipRelease` dokumentiert (`6cfb55b`).

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

| Tag       | Commit (annotiert `^{}`) |
|-----------|---------------------------|
| `v0.1.55` | Version bump 0.1.55 (`486db2f`) |
| `v0.1.54` | Version bump 0.1.54 (`8cf5d75`) |
| `v0.1.53` | Version bump 0.1.53 (`6b92361`) |
| `v0.1.52` | Version bump 0.1.52 (`70cbed2`) |
| `v0.1.51` | Version bump 0.1.51 (`275b28e`) |
| `v0.1.50` | Version bump 0.1.50 (`802b1e6`) |
| `v0.1.49` | Version bump 0.1.49 (`32f0c18`) |
| `v0.1.48` | Version bump 0.1.48 (`e4d3b69`) |
| `v0.1.47` | Version bump 0.1.47 (`406db8c`) |

Links: [Commits zu Tag v0.1.55](https://codeberg.org/elpatron/Perlentaucher/commits/tag/v0.1.55)
