import argparse
import logging
import os
import re
import sys
import requests
import feedparser
import json
from datetime import datetime

try:
    import apprise
    APPRISE_AVAILABLE = True
except ImportError:
    APPRISE_AVAILABLE = False

# Configuration
RSS_FEED_URL = "https://nexxtpress.de/author/mediathekperlen/feed/"
MVW_API_URL = "https://mediathekviewweb.de/api/query"

# Logging setup
def setup_logging(level_name):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def load_processed_entries(state_file):
    """Lädt die Liste der bereits verarbeiteten Einträge."""
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(data.get('processed_entries', []))
        except Exception as e:
            logging.warning(f"Fehler beim Laden der Status-Datei: {e}")
            return set()
    return set()

def save_processed_entry(state_file, entry_id):
    """Speichert einen Eintrag als verarbeitet."""
    processed = load_processed_entries(state_file)
    processed.add(entry_id)
    
    data = {
        'processed_entries': list(processed),
        'last_updated': datetime.now().isoformat()
    }
    
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Status-Datei: {e}")

def send_notification(apprise_url, title, body, notification_type="info"):
    """
    Sendet eine Benachrichtigung via Apprise.
    
    Args:
        apprise_url: Apprise-URL (z.B. "mailto://user:pass@example.com" oder "discord://webhook_id/webhook_token")
        title: Titel der Benachrichtigung
        body: Inhalt der Benachrichtigung
        notification_type: "success", "error", "warning" oder "info"
    """
    if not apprise_url or not APPRISE_AVAILABLE:
        return
    
    try:
        apobj = apprise.Apprise()
        apobj.add(apprise_url)
        
        # Emoji basierend auf Typ
        emoji_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        emoji = emoji_map.get(notification_type, "ℹ️")
        
        formatted_title = f"{emoji} {title}"
        
        success = apobj.notify(
            body=body,
            title=formatted_title,
        )
        
        if success:
            logging.debug(f"Benachrichtigung erfolgreich gesendet: {title}")
        else:
            logging.warning(f"Fehler beim Senden der Benachrichtigung: {title}")
    except Exception as e:
        logging.error(f"Fehler beim Senden der Benachrichtigung: {e}")

def parse_rss_feed(limit, state_file=None):
    logging.info(f"Parse RSS-Feed: {RSS_FEED_URL}")
    feed = feedparser.parse(RSS_FEED_URL)
    
    if feed.bozo:
        logging.warning("Beim Parsen des RSS-Feeds ist ein Fehler aufgetreten, fahre fort...")
    
    entries = feed.entries[:limit]
    logging.info(f"{len(entries)} Einträge gefunden (Limit: {limit})")
    
    # Lade bereits verarbeitete Einträge
    processed_entries = load_processed_entries(state_file) if state_file else set()
    
    movies = []
    new_entries = []
    skipped_count = 0
    
    for entry in entries:
        # Verwende entry.id oder entry.link als eindeutige Identifikation
        entry_id = entry.get('id') or entry.get('link') or entry.get('title', '')
        
        # Prüfe, ob Eintrag bereits verarbeitet wurde
        if entry_id in processed_entries:
            logging.debug(f"Eintrag bereits verarbeitet, überspringe: '{entry.title}'")
            skipped_count += 1
            continue
        
        title = entry.title
        # Regex to extract title from 'Director - „Movie" (Year)' or similar
        # Looking for content inside „..." - unterstützt verschiedene Anführungszeichen-Varianten
        # Suche nach öffnendem „ (U+201E) und dann alles bis zum nächsten Anführungszeichen
        # Unterstützt: „ " (U+201E + U+201C), „ " (U+201E + U+201D), „ " (U+201E + normales ")
        # Verwendet Unicode-Escape-Sequenzen für bessere Kompatibilität
        # U+201E = „, U+201C = ", U+201D = ", U+0022 = "
        match = re.search(r'\u201E(.+?)(?:[\u201C\u201D\u0022])', title)
        # Fallback: Normale Anführungszeichen
        if not match:
            match = re.search(r'"([^"]+?)"', title)
        if match:
            movie_title = match.group(1)
            logging.debug(f"Extracted movie title: '{movie_title}' from '{title}'")
            movies.append(movie_title)
            # Speichere entry_id, entry und link für Benachrichtigungen
            entry_link = entry.get('link', '')
            new_entries.append((entry_id, entry, entry_link))
        else:
            # Debug: Zeige die tatsächlichen Zeichen im Titel
            logging.warning(f"Konnte Filmtitel nicht aus RSS-Eintrag extrahieren: '{title}'")
            logging.debug(f"Titel (repr): {repr(title)}")
            # Zeige Unicode-Codepoints der Anführungszeichen
            for i, char in enumerate(title):
                if ord(char) in [0x201C, 0x201D, 0x201E, 0x201F, 0x2033, 0x2036, 0x275D, 0x275E, 34]:
                    logging.debug(f"  Position {i}: '{char}' (U+{ord(char):04X})")
            # Auch Einträge ohne extrahierbaren Filmtitel als verarbeitet markieren,
            # damit sie nicht immer wieder versucht werden
            if state_file:
                save_processed_entry(state_file, entry_id)
    
    if skipped_count > 0:
        logging.info(f"{skipped_count} Einträge wurden bereits verarbeitet und übersprungen")
    
    return movies, new_entries

def has_audio_description(movie_data):
    """Prüft, ob ein Film Audiodeskription hat."""
    title = movie_data.get("title", "").lower()
    description = movie_data.get("description", "").lower()
    topic = movie_data.get("topic", "").lower()
    
    # Suche nach typischen Begriffen für Audiodeskription
    audio_desc_keywords = [
        "audiodeskription", "audio-deskription", "hörfilm", 
        "hörfassung", "ad ", " mit ad", "audiodeskriptive"
    ]
    
    text = f"{title} {description} {topic}"
    return any(keyword in text for keyword in audio_desc_keywords)

def detect_language(movie_data):
    """Erkennt die Sprache eines Films (deutsch/englisch/unbekannt)."""
    title = movie_data.get("title", "").lower()
    description = movie_data.get("description", "").lower()
    topic = movie_data.get("topic", "").lower()
    
    text = f"{title} {description} {topic}"
    
    # Englische Indikatoren
    english_keywords = [
        "omdt", "omdt.", "om u", "original mit deutschen untertiteln",
        "originalfassung", "englisch", "english", "ov ", " o.v.",
        "original version", "originalfassung"
    ]
    
    # Deutsche Indikatoren (oft implizit, aber manchmal explizit)
    german_keywords = [
        "dt.", "deutsch", "df", "deutsche fassung", 
        "synchronfassung", "synchronisiert"
    ]
    
    has_english = any(keyword in text for keyword in english_keywords)
    has_german = any(keyword in text for keyword in german_keywords)
    
    if has_english and not has_german:
        return "englisch"
    elif has_german or (not has_english and not has_german):
        # Wenn keine explizite Sprache angegeben, annehmen dass es Deutsch ist
        return "deutsch"
    else:
        return "unbekannt"

def score_movie(movie_data, prefer_language, prefer_audio_desc):
    """
    Bewertet einen Film basierend auf den Präferenzen.
    Höhere Punktzahl = bessere Übereinstimmung.
    """
    score = 0
    
    # Basis-Punktzahl: Dateigröße (größer = besser, normalisiert)
    size = movie_data.get("size") or 0
    if size is not None:
        score += size / (1024 * 1024 * 1024)  # GB als Basis
    
    # Sprache-Präferenz
    language = detect_language(movie_data)
    if prefer_language == "deutsch" and language == "deutsch":
        score += 1000
    elif prefer_language == "englisch" and language == "englisch":
        score += 1000
    elif prefer_language == "egal":
        score += 500  # Neutrale Punktzahl
    
    # Audiodeskription-Präferenz
    has_ad = has_audio_description(movie_data)
    if prefer_audio_desc == "mit" and has_ad:
        score += 500
    elif prefer_audio_desc == "ohne" and not has_ad:
        score += 500
    elif prefer_audio_desc == "egal":
        score += 250  # Neutrale Punktzahl
    
    return score

def search_mediathek(movie_title, prefer_language="deutsch", prefer_audio_desc="egal"):
    """
    Sucht nach einem Film in MediathekViewWeb und wählt die beste Fassung
    basierend auf den Präferenzen aus.
    
    Args:
        movie_title: Der Filmtitel zum Suchen
        prefer_language: "deutsch", "englisch" oder "egal"
        prefer_audio_desc: "mit", "ohne" oder "egal"
    """
    logging.info(f"Suche in MediathekViewWeb nach: '{movie_title}'")
    payload = {
        "queries": [
            {
                "fields": ["title", "topic"],
                "query": movie_title
            }
        ],
        "sortBy": "size",  # Sort by size to get best quality easily
        "sortOrder": "desc",
        "future": False,
        "offset": 0,
        "size": 20  # Mehr Ergebnisse für bessere Auswahl
    }
    
    try:
        response = requests.post(MVW_API_URL, json=payload, headers={"Content-Type": "text/plain"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("result", {}).get("results", [])
        if not results:
            logging.warning(f"Keine Ergebnisse gefunden für '{movie_title}'")
            return None
        
        # Bewerte alle Ergebnisse
        scored_results = []
        for result in results:
            try:
                score = score_movie(result, prefer_language, prefer_audio_desc)
                scored_results.append((score, result))
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten eines Ergebnisses für '{movie_title}': {e}")
                continue
        
        if not scored_results:
            logging.warning(f"Keine gültigen Ergebnisse für '{movie_title}' gefunden")
            return None
        
        # Sortiere nach Punktzahl (höchste zuerst)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        best_match = scored_results[0][1]
        best_score = scored_results[0][0]
        
        language = detect_language(best_match)
        has_ad = has_audio_description(best_match)
        size = best_match.get("size") or 0
        size_mb = size / (1024 * 1024) if size else 0
        
        logging.info(f"Beste Übereinstimmung gefunden: '{best_match.get('title')}' "
                    f"({size_mb:.1f} MB, "
                    f"Sprache: {language}, "
                    f"AD: {'ja' if has_ad else 'nein'}, "
                    f"Score: {best_score:.1f})")
        
        return best_match

    except requests.RequestException as e:
        logging.error(f"Netzwerkfehler bei der Suche nach '{movie_title}': {e}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Ungültige Antwort von MediathekViewWeb für '{movie_title}': {e}")
        return None
    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei der Suche nach '{movie_title}': {e}")
        return None

def download_movie(movie_data, download_dir):
    """
    Lädt einen Film herunter.
    
    Returns:
        tuple: (success: bool, title: str, filepath: str)
    """
    url = movie_data.get("url_video")
    title = movie_data.get("title")
    # Clean filename
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
    # Try to guess extension
    ext = "mp4"
    if url.endswith(".mkv"): ext = "mkv"
    if url.endswith(".mp4"): ext = "mp4"
    
    filename = f"{safe_title}.{ext}"
    filepath = os.path.join(download_dir, filename)

    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        logging.info(f"Datei bereits vorhanden, überspringe Download: '{title}' -> {filepath} ({file_size_mb:.1f} MB)")
        return (True, title, filepath)

    logging.info(f"Starte Download: '{title}' -> {filepath}")
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            total_size_in_bytes = int(r.headers.get('content-length', 0))
            if total_size_in_bytes == 0:
                logging.warning("Content-Length Header fehlt. Fortschritt kann nicht angezeigt werden.")

            with open(filepath, 'wb') as f:
                downloaded = 0
                chunk_size = 8192
                for chunk in r.iter_content(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)
                    # Fortschritt alle 50MB loggen
                    if downloaded % (50 * 1024 * 1024) < chunk_size: # ca. alle 50MB
                         logging.info(f"Heruntergeladen: {downloaded / (1024*1024):.1f} MB ...")
        
        logging.info(f"Download abgeschlossen: {filepath}")
        return (True, title, filepath)

    except Exception as e:
        logging.error(f"Download fehlgeschlagen für '{title}': {e}")
        # Clean up partial file
        if os.path.exists(filepath):
            os.remove(filepath)
        return (False, title, filepath)

def main():
    parser = argparse.ArgumentParser(description="Perlentaucher - RSS Feed Downloader for MediathekViewWeb")
    parser.add_argument("--download-dir", default=os.getcwd(), help="Directory to save downloads")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent RSS posts to modify")
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level")
    parser.add_argument("--sprache", default="deutsch", choices=["deutsch", "englisch", "egal"], 
                       help="Bevorzugte Sprache: deutsch, englisch oder egal (Standard: deutsch)")
    parser.add_argument("--audiodeskription", default="egal", choices=["mit", "ohne", "egal"],
                       help="Bevorzugte Audiodeskription: mit, ohne oder egal (Standard: egal)")
    parser.add_argument("--state-file", default=".perlentaucher_state.json",
                       help="Datei zum Speichern des Verarbeitungsstatus (Standard: .perlentaucher_state.json)")
    parser.add_argument("--no-state", action="store_true",
                       help="Deaktiviert das Tracking bereits verarbeiteter Einträge")
    parser.add_argument("--notify", default=None,
                       help="Apprise-URL für Benachrichtigungen (z.B. 'mailto://user:pass@example.com' oder 'discord://webhook_id/webhook_token')")
    
    args = parser.parse_args()
    
    setup_logging(args.loglevel)
    
    if not os.path.exists(args.download_dir):
        try:
            os.makedirs(args.download_dir)
            logging.info(f"Download-Verzeichnis erstellt: {args.download_dir}")
        except OSError as e:
            logging.critical(f"Could not create download directory {args.download_dir}: {e}")
            sys.exit(1)

    logging.info(f"Präferenzen: Sprache={args.sprache}, Audiodeskription={args.audiodeskription}")

    state_file = None if args.no_state else args.state_file
    if state_file:
        logging.info(f"Status-Datei: {state_file}")

    movies, new_entries = parse_rss_feed(args.limit, state_file=state_file)
    
    if args.notify and not APPRISE_AVAILABLE:
        logging.warning("Apprise ist nicht installiert. Benachrichtigungen werden nicht gesendet.")
        logging.warning("Installiere Apprise mit: pip install apprise")
    
    for i, movie in enumerate(movies):
        entry_id, entry, entry_link = new_entries[i]
        result = search_mediathek(movie, prefer_language=args.sprache, prefer_audio_desc=args.audiodeskription)
        if result:
            success, title, filepath = download_movie(result, args.download_dir)
            # Markiere Eintrag als verarbeitet nach Download-Versuch
            if state_file:
                save_processed_entry(state_file, entry_id)
                logging.debug(f"Eintrag als verarbeitet markiert: '{entry.title}'")
            
            # Benachrichtigung senden
            if args.notify:
                if success:
                    body = f"Film erfolgreich heruntergeladen:\n\n"
                    body += f"📽️ {title}\n"
                    body += f"💾 {filepath}\n"
                    if entry_link:
                        body += f"\n🔗 Blog-Eintrag: {entry_link}"
                    send_notification(args.notify, "Download erfolgreich", body, "success")
                else:
                    body = f"Download fehlgeschlagen:\n\n"
                    body += f"📽️ {title}\n"
                    if entry_link:
                        body += f"\n🔗 Blog-Eintrag: {entry_link}"
                    send_notification(args.notify, "Download fehlgeschlagen", body, "error")
        else:
            logging.warning(f"Überspringe '{movie}' - nicht in der Mediathek gefunden.")
            # Auch nicht gefundene Filme als verarbeitet markieren, damit sie nicht immer wieder versucht werden
            if state_file:
                save_processed_entry(state_file, entry_id)
                logging.debug(f"Eintrag als verarbeitet markiert (Film nicht gefunden): '{entry.title}'")
            
            # Benachrichtigung für nicht gefundenen Film
            if args.notify:
                body = f"Film nicht in der Mediathek gefunden:\n\n"
                body += f"📽️ {movie}\n"
                if entry_link:
                    body += f"\n🔗 Blog-Eintrag: {entry_link}"
                send_notification(args.notify, "Film nicht gefunden", body, "warning")

if __name__ == "__main__":
    main()
