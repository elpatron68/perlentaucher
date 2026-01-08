# Programmablauf

Das folgende Diagramm zeigt den vollständigen Ablauf des Scripts:

```mermaid
flowchart TD
    Start([Script Start]) --> ParseArgs[Argumente parsen<br/>--download-dir, --limit, --sprache, etc.]
    ParseArgs --> SetupLog[Logging einrichten]
    SetupLog --> CheckDir{Download-<br/>Verzeichnis<br/>vorhanden?}
    CheckDir -->|Nein| CreateDir[Verzeichnis erstellen]
    CheckDir -->|Ja| LoadState
    CreateDir --> LoadState[State-Datei laden<br/>bereits verarbeitete Einträge]
    LoadState --> ParseRSS[RSS-Feed parsen<br/>Mediathekperlen]
    ParseRSS --> FilterNew{Neue<br/>Einträge<br/>vorhanden?}
    FilterNew -->|Nein| End([Ende])
    FilterNew -->|Ja| ExtractTitle[Titel extrahieren<br/>Jahr extrahieren]
    ExtractTitle --> CheckProcessed{Bereits<br/>verarbeitet?}
    CheckProcessed -->|Ja| Skip[Überspringen]
    Skip --> NextEntry{Weitere<br/>Einträge?}
    CheckProcessed -->|Nein| GetMetadata[Metadata abfragen<br/>TMDB/OMDB]
    GetMetadata --> IsSeries{Serie<br/>erkannt?}
    IsSeries -->|Ja| CheckSeriesOption{--serien-download<br/>Option?}
    CheckSeriesOption -->|keine| SkipSeries[Serie überspringen]
    SkipSeries --> MarkProcessed1
    CheckSeriesOption -->|erste| SearchMVW[Suche in MediathekViewWeb<br/>beste Episode]
    CheckSeriesOption -->|staffel| SearchSeries[Suche alle Episoden<br/>MediathekViewWeb]
    SearchSeries --> ExtractEpisodes[Episode-Info extrahieren<br/>Staffel/Episode]
    ExtractEpisodes --> SortEpisodes[Episoden sortieren<br/>nach Staffel/Episode]
    SortEpisodes --> DownloadEpisodes[Alle Episoden<br/>herunterladen]
    DownloadEpisodes --> NotifySeries[Benachrichtigung:<br/>Staffel-Download]
    NotifySeries --> MarkProcessed2
    IsSeries -->|Nein| SearchMVW[Suche in MediathekViewWeb<br/>mit API]
    SearchMVW --> Results{Ergebnisse<br/>gefunden?}
    Results -->|Nein| NotifyNotFound[Benachrichtigung:<br/>Film nicht gefunden]
    NotifyNotFound --> MarkProcessed1[Als verarbeitet markieren]
    MarkProcessed1 --> NextEntry
    Results -->|Ja| ScoreResults[Bewerte alle Ergebnisse<br/>Sprache + Audiodeskription + Größe]
    ScoreResults --> SelectBest[Wähle beste Übereinstimmung<br/>höchste Punktzahl]
    SelectBest --> ExtractEpisodeInfo[Episode-Info extrahieren<br/>falls Serie]
    ExtractEpisodeInfo --> BuildFilename
    SearchMVW --> Results{Ergebnisse<br/>gefunden?}
    BuildFilename{Dateiname<br/>generieren}
    BuildFilename -->|Film| BuildMovieFilename[Film: Name Jahr Provider-ID]
    BuildFilename -->|Serie| BuildSeriesFilename[Serie: Name Jahr - S01E01 Provider-ID<br/>in Unterordner]
    BuildMovieFilename --> CheckFile{Datei bereits<br/>vorhanden?}
    BuildSeriesFilename --> CheckFile
    CheckFile -->|Ja| SkipDownload[Download überspringen]
    SkipDownload --> MarkProcessed2
    CheckFile -->|Nein| Download[Film herunterladen<br/>mit Fortschrittsanzeige]
    Download --> DownloadSuccess{Download<br/>erfolgreich?}
    DownloadSuccess -->|Nein| Cleanup[Partielle Datei löschen]
    Cleanup --> NotifyError[Benachrichtigung:<br/>Download fehlgeschlagen]
    NotifyError --> MarkProcessed2[Als verarbeitet markieren]
    DownloadSuccess -->|Ja| NotifySuccess[Benachrichtigung:<br/>Download erfolgreich]
    NotifySuccess --> MarkProcessed2
    MarkProcessed2 --> NextEntry
    NextEntry -->|Ja| ExtractTitle
    NextEntry -->|Nein| End
    
    style Start fill:#90EE90
    style End fill:#FFB6C1
    style SearchMVW fill:#87CEEB
    style Download fill:#FFD700
    style NotifySuccess fill:#98FB98
    style NotifyError fill:#FFA07A
    style NotifyNotFound fill:#FFA07A
```

**Hauptschritte:**

1. **Initialisierung**: Argumente werden geparst, Logging konfiguriert und das Download-Verzeichnis wird erstellt (falls nicht vorhanden).

2. **RSS-Feed Parsing**: Der RSS-Feed von Mediathekperlen wird gelesen und nach neuen Einträgen durchsucht. Bereits verarbeitete Einträge werden anhand der State-Datei erkannt und übersprungen.

3. **Titel-Extraktion**: Aus jedem RSS-Eintrag wird der Filmtitel oder Serientitel (in Anführungszeichen) und das Jahr extrahiert.

4. **Metadata-Abfrage** (optional): Falls TMDB oder OMDb API-Keys konfiguriert sind, werden zusätzliche Metadaten (Jahr, Provider-ID, content_type) abgerufen. Dies hilft auch bei der Serien-Erkennung.

5. **Serien-Erkennung**: Das Script prüft, ob es sich um eine Serie handelt:
   - RSS-Feed-Kategorie "TV-Serien" (höchste Priorität)
   - Provider-ID-Prüfung über TMDB/OMDB (wenn API-Keys vorhanden)
   - Titel-Muster-Erkennung (Fallback)

6. **Serien-Verarbeitung**: Basierend auf `--serien-download` Option:
   - **`keine`**: Serien werden übersprungen
   - **`erste`**: Nur die erste Episode wird heruntergeladen (wie ein Film)
   - **`staffel`**: Alle Episoden der Serie werden gefunden, sortiert und heruntergeladen

7. **MediathekViewWeb Suche**: 
   - **Für Filme**: Normale Suche nach dem Filmtitel
   - **Für Serien**: `search_mediathek_series()` findet alle Episoden und filtert nach Serientitel

8. **Bewertung & Auswahl**: Alle gefundenen Ergebnisse werden basierend auf deinen Präferenzen bewertet:
   - **Sprache** (Deutsch/Englisch/Egal): +1000 Punkte bei Übereinstimmung
   - **Audiodeskription** (Mit/Ohne/Egal): +500 Punkte bei Übereinstimmung
   - **Dateigröße**: Größere Dateien erhalten höhere Punkte (bessere Qualität)
   - **Titelübereinstimmung**: Sehr hohe Priorität für exakte Übereinstimmungen

9. **Episode-Extraktion** (für Serien): Staffel- und Episoden-Nummer werden aus dem Titel extrahiert (unterstützt verschiedene Formate: S01E01, Saison 1 (1/8), Staffel 1 (1/8), etc.)

10. **Dateinamen-Generierung**: 
    - **Filme**: `Filmname (Jahr) [tmdbid-123].mp4`
    - **Serien**: `[serien-dir]/[Titel] (Jahr)/[Titel] (Jahr) - S01E01 [tmdbid-123].mp4`

11. **Download**: Der Film oder die Episode wird heruntergeladen. Falls die Datei bereits existiert, wird der Download übersprungen.

12. **Benachrichtigungen** (optional): Bei Erfolg, Fehler oder wenn kein Film/Serie gefunden wurde, können Benachrichtigungen via Apprise gesendet werden. Bei Staffel-Downloads wird der Fortschritt angezeigt.

13. **State-Tracking**: Jeder verarbeitete Eintrag wird in der State-Datei gespeichert, um Doppel-Downloads zu vermeiden. Bei Serien werden auch die heruntergeladenen Episoden gespeichert.

