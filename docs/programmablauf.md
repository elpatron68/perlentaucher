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
    FilterNew -->|Ja| ExtractTitle[Filmtitel extrahieren<br/>Jahr extrahieren]
    ExtractTitle --> CheckProcessed{Bereits<br/>verarbeitet?}
    CheckProcessed -->|Ja| Skip[Überspringen]
    Skip --> NextEntry{Weitere<br/>Einträge?}
    CheckProcessed -->|Nein| SearchMVW[Suche in MediathekViewWeb<br/>mit API]
    SearchMVW --> Results{Ergebnisse<br/>gefunden?}
    Results -->|Nein| NotifyNotFound[Benachrichtigung:<br/>Film nicht gefunden]
    NotifyNotFound --> MarkProcessed1[Als verarbeitet markieren]
    MarkProcessed1 --> NextEntry
    Results -->|Ja| ScoreResults[Bewerte alle Ergebnisse<br/>Sprache + Audiodeskription + Größe]
    ScoreResults --> SelectBest[Wähle beste Übereinstimmung<br/>höchste Punktzahl]
    SelectBest --> GetMetadata{Metadata Provider<br/>konfiguriert?}
    GetMetadata -->|TMDB vorhanden| QueryTMDB[TMDB API abfragen<br/>Jahr + tmdb_id]
    GetMetadata -->|OMDB vorhanden| QueryOMDB[OMDb API abfragen<br/>Jahr + imdb_id]
    GetMetadata -->|Kein Provider| NoMetadata
    QueryTMDB --> BuildFilename{Build Filename}
    QueryOMDB --> BuildFilename
    NoMetadata[Keine Metadata] --> BuildFilename
    BuildFilename[Dateiname generieren<br/>Name Jahr Provider-ID]
    BuildFilename --> CheckFile{Datei bereits<br/>vorhanden?}
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

3. **Filmtitel-Extraktion**: Aus jedem RSS-Eintrag wird der Filmtitel (in Anführungszeichen) und das Jahr extrahiert.

4. **MediathekViewWeb Suche**: Für jeden neuen Filmtitel wird die MediathekViewWeb API durchsucht.

5. **Bewertung & Auswahl**: Alle gefundenen Ergebnisse werden basierend auf deinen Präferenzen bewertet:
   - **Sprache** (Deutsch/Englisch/Egal): +1000 Punkte bei Übereinstimmung
   - **Audiodeskription** (Mit/Ohne/Egal): +500 Punkte bei Übereinstimmung
   - **Dateigröße**: Größere Dateien erhalten höhere Punkte (bessere Qualität)

6. **Metadata-Abfrage** (optional): Falls TMDB oder OMDb API-Keys konfiguriert sind, werden zusätzliche Metadaten (Jahr, Provider-ID) abgerufen.

7. **Dateinamen-Generierung**: Der Dateiname wird im Jellyfin/Plex-kompatiblen Format erstellt: `Filmname (Jahr) [tmdbid-123].mp4`

8. **Download**: Der Film wird heruntergeladen. Falls die Datei bereits existiert, wird der Download übersprungen.

9. **Benachrichtigungen** (optional): Bei Erfolg, Fehler oder wenn kein Film gefunden wurde, können Benachrichtigungen via Apprise gesendet werden.

10. **State-Tracking**: Jeder verarbeitete Eintrag wird in der State-Datei gespeichert, um Doppel-Downloads zu vermeiden.

