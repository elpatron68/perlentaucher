# Release v0.1.9 - Serien-Download-Unterstützung

## 🎬 Hauptfeature: Serien-Download-Unterstützung

Diese Version erweitert Perlentaucher um umfassende Unterstützung für TV-Serien. Das Script kann nun automatisch Serien erkennen und Episoden herunterladen.

### Neue Features

#### Serien-Erkennung
- **Automatische Erkennung** über RSS-Feed-Kategorie "TV-Serien"
- **Provider-ID-Prüfung** über TMDB/OMDB APIs (wenn API-Keys vorhanden)
- **Titel-Muster-Erkennung** als Fallback

#### Konfigurierbare Download-Optionen
- `--serien-download erste`: Lädt nur die erste Episode (Standard)
- `--serien-download staffel`: Lädt alle Episoden einer Staffel
- `--serien-download keine`: Überspringt Serien komplett

#### Neue CLI-Optionen
- `--serien-dir`: Konfigurierbarer Basis-Pfad für Serien-Downloads (Standard: `--download-dir`)
- Episoden werden automatisch in Unterordnern `[Titel] (Jahr)/` gespeichert

#### Intelligente Episode-Extraktion
Unterstützt verschiedene Formate:
- `S01E01`, `S1E1` (Standard-Format)
- `Saison 1 (1/8)`, `Staffel 1 (1/8)` (französisches/deutsches Format)
- `The Return (1/18)` (Format ohne Staffel-Nummer)
- `Episode 1`, `Folge 1`, `Teil 1` (mit Kontext-Erkennung)
- `1x01`, `1.01` (alternative Formate)

#### Dateinamen für Serien
- Format: `[Titel] (Jahr) - S01E01 [provider_id].ext`
- Beispiel: `Twin Peaks (1992) - S01E01 [tmdbid-1923].mp4`
- Jellyfin/Plex-kompatibel

### Verbesserungen

#### MediathekViewWeb-Suche
- **Erweiterte Suche für Serien**: `search_mediathek_series()` findet alle Episoden einer Serie
- **Erhöhte Ergebnisanzahl**: Von 100 auf 500 Ergebnisse für bessere Abdeckung
- **Deduplizierung**: Nur die beste Version jeder Episode wird behalten (basierend auf Score: Sprache, Audiodeskription, Qualität)
- **Sprache und Audiodeskription**: Werden auch bei Serien-Suche berücksichtigt

#### Logging und Diagnose
- **Detaillierte Episoden-Statistik**: Zeigt gefundene Episoden pro Staffel
- **Warnung bei fehlenden Episoden**: Zeigt an, welche Episoden innerhalb einer Staffel fehlen
- **Liste nicht verarbeiteter Episoden**: Episoden ohne Staffel/Episode-Info werden geloggt

#### State-Datei
- Erweitert um Serien-Informationen
- Speichert heruntergeladene Episoden (z.B. `["S01E01", "S01E02"]`)
- Rückwärtskompatibel mit bestehenden State-Dateien

### Technische Änderungen

#### API-Erweiterungen
- **TMDB API**: Unterstützt jetzt auch Serien-Suche (`/search/tv`)
- **OMDb API**: Prüft `Type` Feld für Serien-Erkennung
- **Metadata**: Rückgabe von `content_type` ("movie", "tv", "unknown")

#### Code-Refactoring
- `download_movie()` → `download_content()` (unterstützt Filme und Serien)
- Neue Funktionen:
  - `is_series()`: Serien-Erkennung
  - `search_mediathek_series()`: Serien-Suche
  - `extract_episode_info()`: Episode-Extraktion
  - `format_episode_filename()`: Episode-Dateinamen
  - `get_series_directory()`: Serien-Verzeichnisstruktur

### Dokumentation

- **README.md**: Neue Features, CLI-Optionen und Beispiele dokumentiert
- **docs/docker.md**: Neue Umgebungsvariablen `SERIEN_DOWNLOAD` und `SERIEN_DIR`
- **docs/programmablauf.md**: Programmablauf-Diagramm um Serien-Logik erweitert
- **docs/quickstart.md**: Neue Konfigurationsoptionen für Serien

### Beispiele

**Nur erste Episode herunterladen:**
```bash
python perlentaucher.py --serien-download erste
```

**Gesamte Staffel herunterladen:**
```bash
python perlentaucher.py --serien-download staffel --serien-dir ./Serien
```

**Serien überspringen:**
```bash
python perlentaucher.py --serien-download keine
```

**Mit Docker:**
```bash
docker run -d \
  --name perlentaucher \
  -v /pfad/zu/downloads:/downloads \
  -v /pfad/zu/serien:/serien \
  -e SERIEN_DOWNLOAD=staffel \
  -e SERIEN_DIR=/serien \
  codeberg.org/elpatron/perlentaucher:latest
```

### Breaking Changes

Keine. Alle Änderungen sind rückwärtskompatibel. Das Standard-Verhalten (`--serien-download erste`) entspricht dem bisherigen Verhalten.

### Bekannte Einschränkungen

- Episoden, die nicht in den ersten 500 Ergebnissen der MediathekViewWeb-Suche erscheinen, werden möglicherweise nicht gefunden
- Episoden mit sehr unkonventionellen Titeln können nicht immer korrekt erkannt werden (werden im Log angezeigt)

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/Perlentaucher/commits/master)
