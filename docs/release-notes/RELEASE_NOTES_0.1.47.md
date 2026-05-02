```markdown
# Release v0.1.47

## Neue Features
- **HLS m3u8 via ffmpeg**: Unterstützung für HLS m3u8-Streams hinzugefügt.
- **Sender Mediathek Links**: Verwendung von Sender Mediathek-Links für bessere Zuordnung. Extraktion von URLs aus RSS-Einträgen mit optionalem Artikel-Abruf-Fallback.
- **Blog-Post-Link**: Ein Blog-Post-Link wurde in den Feed-Download-Benachrichtigungen integriert, um den `entry_link` an `download_content` und `notify_non_wishlist` weiterzugeben.
- **Wishlist-Web**: 
  - Fußzeile zeigt die Git-Version und bei einem Dirty-Repo die Commit-Kurz-ID an.
  - Verlauf ist jetzt einklappbar, API-Filter und Paginierung wurden hinzugefügt.
- **Benachrichtigungen**: 
  - Unterdrückung von "nicht gefunden"-Benachrichtigungen für Wishlist-Elemente.

## Verbesserungen
- **Titelähnlichkeit in der Film-Mediathek**: Verbesserung der Titelähnlichkeit mit `normalize_search_title`, um Such- und Ergebnistitel nach derselben Normalisierung zu vergleichen (z.B. "Fantomas" vs. "Fantômas").
- **Sender-Link Fallback**: Verbesserung der Sender-Referenz-Zuordnung durch standardmäßige Aktivierung des Artikel-Abruf-Fallbacks.
- **Serien-Matching**: Verbesserung des Serien-Matchings mit inferierter S01-Schema-Logik, um irrelevante Ergebnisse besser zu filtern.
- **RSS Jahr und Sender-Link**: Wahrung des RSS-Jahres für GUI-Feed-Downloads und Verbesserung der Sender-Referenz-Zuordnung.
- **Wunschliste Web-UI**: Behebung von Probe-Fehlern, damit Einträge erhalten bleiben und Thread-Ausnahmen vermieden werden.
- **Kern-Coverage Tests**: Kern-Coverage ohne GUI mit einer Schwelle von 30% und Tests für `wishlist_activity` hinzugefügt.

## Bugfixes
- **FFmpeg Auto-Detect**: Behebung eines Problems mit der automatischen Erkennung von FFmpeg beim Start und Vermeidung der Konsolenausgabe unter Windows.
- **Fehlerbehandlung**: Leeren des Dateipfads und Benachrichtigung ohne Phantom-Pfad nach einem Abbruch oder Fehler.
- **Auto-Nummerierung**: Deaktivierung der automatischen Nummerierung unbekannter Episoden, wenn die Staffel bereits klar ist, um falsche Positiverkennung zu vermeiden.
- **RSS-Feed und GUI Benachrichtigungen**: Vollständige Wiederherstellung von Apprise/Ntfy für RSS-Feed und GUI, einschließlich Push-Benachrichtigungen bei Download-Erfolg, -Fehler und bereits vorhandenen Dateien.
- **Benachrichtigungen**: Kein Apprise-Push bei Treffern unter der Titel-Schwelle (Film).
- **Technische Verbesserungen**: Fix der IP-Adresse und Ausführbarkeit des Scripts sichergestellt.

## Technische Änderungen
- **Dokumentation**: 
  - Coverage-Tabelle ausgerichtet und Dokumentation für Kern vs. vollständige Coverage aktualisiert.
  - Docker-Dokumentation aktualisiert und Unraid-Build/Deploy-Skripte hinzugefügt.
- **Make Script Executable**: Das Skript wurde ausführbar gemacht.
```


---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/v0.1.47)
