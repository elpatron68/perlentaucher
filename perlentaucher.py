import argparse
import logging
import os
import re
import sys
import requests
import feedparser
import json
from datetime import datetime
from typing import Optional, Dict, Tuple

try:
    import apprise
    APPRISE_AVAILABLE = True
except ImportError:
    APPRISE_AVAILABLE = False

# Versions-Import
try:
    from _version import __version__
except ImportError:
    __version__ = "unknown"

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
    """
    Lädt die Liste der bereits verarbeiteten Einträge.
    Unterstützt sowohl alte (nur processed_entries Liste) als auch neue Datenstruktur.
    """
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Neue Struktur mit 'entries' Dictionary
                if 'entries' in data:
                    return set(data['entries'].keys())
                # Alte Struktur mit 'processed_entries' Liste (Rückwärtskompatibilität)
                return set(data.get('processed_entries', []))
        except Exception as e:
            logging.warning(f"Fehler beim Laden der Status-Datei: {e}")
            return set()
    return set()

def load_state_file(state_file):
    """
    Lädt die komplette State-Datei mit allen Details.
    
    Returns:
        Dictionary mit 'entries' (dict) und 'last_updated' (str)
    """
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Konvertiere alte Struktur zu neuer
                if 'entries' not in data and 'processed_entries' in data:
                    entries = {}
                    for entry_id in data.get('processed_entries', []):
                        entries[entry_id] = {
                            'status': 'unknown',
                            'timestamp': data.get('last_updated', datetime.now().isoformat())
                        }
                    data['entries'] = entries
                return data
        except Exception as e:
            logging.warning(f"Fehler beim Laden der Status-Datei: {e}")
    return {'entries': {}, 'last_updated': datetime.now().isoformat()}

def save_processed_entry(state_file, entry_id, status=None, movie_title=None, filename=None, is_series=False, episodes=None):
    """
    Speichert einen Eintrag als verarbeitet mit Status und weiteren Details.
    
    Args:
        state_file: Pfad zur State-Datei
        entry_id: Eindeutige ID des RSS-Eintrags
        status: Status des Eintrags ('download_success', 'download_failed', 'not_found', 'title_extraction_failed', 'skipped')
        movie_title: Filmtitel oder Serientitel (optional)
        filename: Dateiname der heruntergeladenen Datei (optional)
        is_series: True wenn es sich um eine Serie handelt (optional)
        episodes: Liste von heruntergeladenen Episoden (z.B. ["S01E01", "S01E02"]) (optional)
    """
    data = load_state_file(state_file)
    
    # Erstelle oder aktualisiere Eintrag
    if 'entries' not in data:
        data['entries'] = {}
    
    entry_data = {
        'status': status or 'unknown',
        'timestamp': datetime.now().isoformat()
    }
    
    if movie_title:
        entry_data['movie_title'] = movie_title
    if filename:
        entry_data['filename'] = filename
    if is_series:
        entry_data['is_series'] = True
    if episodes:
        entry_data['episodes'] = episodes
    
    data['entries'][entry_id] = entry_data
    data['last_updated'] = datetime.now().isoformat()
    
    # Für Rückwärtskompatibilität: processed_entries Liste beibehalten
    data['processed_entries'] = list(data['entries'].keys())
    
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Fehler beim Speichern der Status-Datei: {e}")

def extract_year_from_title(title: str) -> Optional[int]:
    """
    Extrahiert das Jahr aus einem RSS-Feed-Titel im Format 'Director - „Movie" (Year)' oder 'Movie (Year)'.
    
    Args:
        title: Der RSS-Feed-Titel
        
    Returns:
        Das Jahr als Integer oder None, wenn kein Jahr gefunden wurde
    """
    # Suche nach Jahreszahlen in Klammern: (YYYY)
    match = re.search(r'\((\d{4})\)', title)
    if match:
        try:
            year = int(match.group(1))
            # Plausibilitätsprüfung: Jahr sollte zwischen 1900 und aktuelles Jahr + 10 sein
            current_year = datetime.now().year
            if 1900 <= year <= current_year + 10:
                return year
        except ValueError:
            pass
    return None

def search_tmdb(movie_title: str, year: Optional[int], api_key: str, search_type: str = "both") -> Optional[Dict]:
    """
    Sucht nach einem Film oder einer Serie in The Movie Database (TMDB).
    
    Args:
        movie_title: Der Filmtitel oder Serientitel
        year: Optional - Das Jahr
        api_key: TMDB API-Key
        search_type: "movie", "tv", oder "both" (Standard: "both")
        
    Returns:
        Dictionary mit 'tmdb_id', 'year' und 'content_type' oder None bei Fehler
    """
    if not api_key:
        return None
    
    # Suche nach Film
    if search_type in ["movie", "both"]:
        try:
            url = "https://api.themoviedb.org/3/search/movie"
            params = {
                "api_key": api_key,
                "query": movie_title,
                "language": "de-DE"
            }
            if year:
                params["year"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if results:
                first_result = results[0]
                tmdb_id = first_result.get("id")
                result_year = first_result.get("release_date", "")[:4] if first_result.get("release_date") else None
                
                if tmdb_id:
                    logging.debug(f"TMDB Film-Match gefunden: '{movie_title}' -> tmdbid-{tmdb_id}")
                    return {
                        "tmdb_id": tmdb_id,
                        "year": int(result_year) if result_year and result_year.isdigit() else year,
                        "content_type": "movie"
                    }
        except requests.RequestException as e:
            logging.debug(f"TMDB API-Fehler (Film) für '{movie_title}': {e}")
        except Exception as e:
            logging.debug(f"Unerwarteter Fehler bei TMDB-Suche (Film) für '{movie_title}': {e}")
    
    # Suche nach Serie
    if search_type in ["tv", "both"]:
        try:
            url = "https://api.themoviedb.org/3/search/tv"
            params = {
                "api_key": api_key,
                "query": movie_title,
                "language": "de-DE"
            }
            if year:
                params["first_air_date_year"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            if results:
                first_result = results[0]
                tmdb_id = first_result.get("id")
                result_year = first_result.get("first_air_date", "")[:4] if first_result.get("first_air_date") else None
                
                if tmdb_id:
                    logging.debug(f"TMDB Serie-Match gefunden: '{movie_title}' -> tmdbid-{tmdb_id}")
                    return {
                        "tmdb_id": tmdb_id,
                        "year": int(result_year) if result_year and result_year.isdigit() else year,
                        "content_type": "tv"
                    }
        except requests.RequestException as e:
            logging.debug(f"TMDB API-Fehler (Serie) für '{movie_title}': {e}")
        except Exception as e:
            logging.debug(f"Unerwarteter Fehler bei TMDB-Suche (Serie) für '{movie_title}': {e}")
    
    return None

def search_omdb(movie_title: str, year: Optional[int], api_key: str, search_type: str = "both") -> Optional[Dict]:
    """
    Sucht nach einem Film oder einer Serie in OMDb API.
    
    Args:
        movie_title: Der Filmtitel oder Serientitel
        year: Optional - Das Jahr
        api_key: OMDb API-Key
        search_type: "movie", "series", oder "both" (Standard: "both")
        
    Returns:
        Dictionary mit 'imdb_id', 'year' und 'content_type' oder None bei Fehler
    """
    if not api_key:
        return None
    
    # Suche nach Film
    if search_type in ["movie", "both"]:
        try:
            url = "http://www.omdbapi.com/"
            params = {
                "apikey": api_key,
                "t": movie_title,
                "type": "movie"
            }
            if year:
                params["y"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response") == "True" and data.get("imdbID"):
                content_type = data.get("Type", "").lower()
                imdb_id = data.get("imdbID")
                result_year = data.get("Year")
                
                if imdb_id:
                    logging.debug(f"OMDB Film-Match gefunden: '{movie_title}' -> {imdb_id}")
                    return {
                        "imdb_id": imdb_id,
                        "year": int(result_year) if result_year and result_year.isdigit() else year,
                        "content_type": "movie" if content_type == "movie" else "movie"
                    }
        except requests.RequestException as e:
            logging.debug(f"OMDB API-Fehler (Film) für '{movie_title}': {e}")
        except Exception as e:
            logging.debug(f"Unerwarteter Fehler bei OMDB-Suche (Film) für '{movie_title}': {e}")
    
    # Suche nach Serie
    if search_type in ["series", "both"]:
        try:
            url = "http://www.omdbapi.com/"
            params = {
                "apikey": api_key,
                "t": movie_title,
                "type": "series"
            }
            if year:
                params["y"] = year
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("Response") == "True" and data.get("imdbID"):
                content_type = data.get("Type", "").lower()
                imdb_id = data.get("imdbID")
                result_year = data.get("Year")
                
                if imdb_id:
                    logging.debug(f"OMDB Serie-Match gefunden: '{movie_title}' -> {imdb_id}")
                    return {
                        "imdb_id": imdb_id,
                        "year": int(result_year) if result_year and result_year.isdigit() else year,
                        "content_type": "tv" if content_type == "series" else "tv"
                    }
        except requests.RequestException as e:
            logging.debug(f"OMDB API-Fehler (Serie) für '{movie_title}': {e}")
        except Exception as e:
            logging.debug(f"Unerwarteter Fehler bei OMDB-Suche (Serie) für '{movie_title}': {e}")
    
    return None

def get_metadata(movie_title: str, year: Optional[int], tmdb_api_key: Optional[str], omdb_api_key: Optional[str]) -> Dict:
    """
    Holt Metadata für einen Film oder eine Serie von TMDB oder OMDB.
    
    Args:
        movie_title: Der Filmtitel oder Serientitel
        year: Optional - Das Jahr (aus RSS-Feed extrahiert)
        tmdb_api_key: Optional - TMDB API-Key
        omdb_api_key: Optional - OMDb API-Key
        
    Returns:
        Dictionary mit:
        - 'year': Jahr (aus RSS-Feed oder Provider)
        - 'provider_id': String im Format '[tmdbid-123]' oder '[imdbid-tt123456]' oder None
        - 'content_type': "movie", "tv", oder "unknown"
    """
    result = {
        "year": year,
        "provider_id": None,
        "content_type": "unknown"
    }
    
    # Versuche zuerst TMDB
    if tmdb_api_key:
        tmdb_result = search_tmdb(movie_title, year, tmdb_api_key, search_type="both")
        if tmdb_result:
            result["year"] = tmdb_result.get("year") or year
            result["content_type"] = tmdb_result.get("content_type", "unknown")
            tmdb_id = tmdb_result.get("tmdb_id")
            if tmdb_id:
                result["provider_id"] = f"[tmdbid-{tmdb_id}]"
                return result
    
    # Fallback: Versuche OMDB
    if omdb_api_key:
        omdb_result = search_omdb(movie_title, year, omdb_api_key, search_type="both")
        if omdb_result:
            result["year"] = omdb_result.get("year") or year
            result["content_type"] = omdb_result.get("content_type", "unknown")
            imdb_id = omdb_result.get("imdb_id")
            if imdb_id:
                result["provider_id"] = f"[imdbid-{imdb_id}]"
                return result
    
    return result

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

def is_series(entry, metadata: Optional[Dict] = None) -> bool:
    """
    Prüft, ob ein RSS-Feed-Eintrag eine Serie ist.
    
    Args:
        entry: RSS-Feed-Eintrag
        metadata: Optional - Metadata-Dictionary mit 'content_type' und 'provider_id'
        
    Returns:
        True wenn es sich um eine Serie handelt, sonst False
    """
    # Priorität 1: RSS-Feed-Kategorie "TV-Serien"
    categories = entry.get('tags', [])
    if isinstance(categories, list):
        for tag in categories:
            if isinstance(tag, dict):
                tag_term = tag.get('term', '').lower()
            else:
                tag_term = str(tag).lower()
            if 'tv-serie' in tag_term or 'serie' in tag_term:
                logging.debug(f"Serie erkannt über RSS-Kategorie: {tag_term}")
                return True
    
    # Priorität 2: Provider-ID-Prüfung (wenn Metadata verfügbar)
    if metadata:
        content_type = metadata.get("content_type", "unknown")
        if content_type == "tv":
            logging.debug(f"Serie erkannt über Provider-ID: {metadata.get('provider_id')}")
            return True
        # Wenn es ein Film ist, ist es keine Serie
        elif content_type == "movie":
            return False
    
    # Priorität 3: Titel-Muster-Prüfung
    title = entry.get('title', '').lower()
    series_indicators = ['serie', 'series', 'staffel', 'folge', 'episode']
    for indicator in series_indicators:
        if indicator in title:
            logging.debug(f"Serie erkannt über Titel-Muster: '{indicator}' in '{title}'")
            return True
    
    return False

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
            # Extrahiere Jahr aus dem RSS-Feed-Titel
            year = extract_year_from_title(title)
            logging.debug(f"Extracted movie title: '{movie_title}' from '{title}'" + (f" (Jahr: {year})" if year else ""))
            movies.append((movie_title, year))
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
                save_processed_entry(state_file, entry_id, status='title_extraction_failed', movie_title=title)
    
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

def calculate_title_similarity(search_title: str, result_title: str) -> float:
    """
    Berechnet die Ähnlichkeit zwischen Suchtitel und Ergebnis-Titel.
    Gibt einen Wert zwischen 0.0 (keine Übereinstimmung) und 1.0 (exakte Übereinstimmung) zurück.
    """
    search_lower = search_title.lower().strip()
    result_lower = result_title.lower().strip()
    
    # Exakte Übereinstimmung (nach Normalisierung)
    if search_lower == result_lower:
        return 1.0
    
    # Exakte Übereinstimmung wenn Suchtitel im Ergebnis-Titel enthalten ist
    # (z.B. "Spencer" in "Spencer (2021)")
    if search_lower in result_lower:
        # Bonus wenn der Titel am Anfang steht
        if result_lower.startswith(search_lower):
            return 0.95
        return 0.85
    
    # Umgekehrt: Ergebnis-Titel im Suchtitel enthalten
    if result_lower in search_lower:
        return 0.80
    
    # Wortweise Übereinstimmung
    search_words = set(search_lower.split())
    result_words = set(result_lower.split())
    
    if not search_words or not result_words:
        return 0.0
    
    # Berechne Jaccard-Ähnlichkeit (Schnittmenge / Vereinigungsmenge)
    intersection = search_words & result_words
    union = search_words | result_words
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    # Wenn alle Suchwörter im Ergebnis enthalten sind, erhöhe den Score
    if search_words.issubset(result_words):
        jaccard = min(1.0, jaccard * 1.3)
    
    return jaccard

def score_movie(movie_data, prefer_language, prefer_audio_desc, search_title: str = None, search_year: Optional[int] = None, metadata: Dict = None):
    """
    Bewertet einen Film basierend auf den Präferenzen und Titelübereinstimmung.
    Höhere Punktzahl = bessere Übereinstimmung.
    
    Args:
        movie_data: Die Filmdaten von MediathekViewWeb
        prefer_language: "deutsch", "englisch" oder "egal"
        prefer_audio_desc: "mit", "ohne" oder "egal"
        search_title: Der gesuchte Filmtitel (optional, für Titelübereinstimmung)
        search_year: Das gesuchte Jahr (optional, für Jahr-Übereinstimmung)
        metadata: Dictionary mit 'provider_id' (tmdbid-XXX oder imdbid-XXX) für exaktes Matching
    """
    score = 0
    
    # TITELÜBEREINSTIMMUNG - höchste Priorität (10000+ Punkte)
    if search_title:
        result_title = movie_data.get("title", "")
        title_similarity = calculate_title_similarity(search_title, result_title)
        # Titelübereinstimmung ist sehr wichtig - multipliziere mit hohem Faktor
        score += title_similarity * 10000
    
    # METADATA-MATCHING - sehr hohe Priorität (50000+ Punkte)
    # Wenn wir eine TMDB/IMDB-ID haben, prüfe ob der Film diese ID enthält
    if metadata and metadata.get("provider_id"):
        provider_id = metadata.get("provider_id")
        # Entferne Klammern: [tmdbid-123] -> tmdbid-123
        provider_id_clean = provider_id.strip("[]")
        
        # Extrahiere die ID-Nummer (z.B. "123" aus "tmdbid-123" oder "tt123456" aus "imdbid-tt123456")
        id_match = re.search(r'(\d+)$', provider_id_clean)
        if id_match:
            id_number = id_match.group(1)
            provider_type = provider_id_clean.split('-')[0].lower() if '-' in provider_id_clean else None
            
            # Prüfe in title, topic und description
            title = movie_data.get("title", "").lower()
            topic = movie_data.get("topic", "").lower()
            description = movie_data.get("description", "").lower()
            combined_text = f"{title} {topic} {description}"
            
            # Suche nach verschiedenen Formaten: tmdbid-123, tmdbid:123, [tmdbid-123], etc.
            search_patterns = [
                provider_id_clean.lower(),  # Original-Format
                id_number,  # Nur die ID-Nummer
            ]
            
            if provider_type:
                search_patterns.extend([
                    f"{provider_type}-{id_number}",
                    f"{provider_type}:{id_number}",
                    f"{provider_type} {id_number}",
                ])
            
            for pattern in search_patterns:
                if pattern in combined_text:
                    score += 50000  # Sehr hohe Punktzahl für exaktes Metadata-Matching
                    logging.debug(f"Metadata-Match gefunden: {pattern} in '{movie_data.get('title')}'")
                    break
    
    # JAHR-ÜBEREINSTIMMUNG - hohe Priorität (5000+ Punkte)
    if search_year:
        # Versuche Jahr aus verschiedenen Feldern zu extrahieren
        title = movie_data.get("title", "")
        topic = movie_data.get("topic", "")
        description = movie_data.get("description", "")
        
        # Suche nach Jahreszahlen in Klammern: (YYYY)
        year_match = re.search(r'\((\d{4})\)', f"{title} {topic} {description}")
        if year_match:
            result_year = int(year_match.group(1))
            if result_year == search_year:
                score += 5000  # Exakte Jahresübereinstimmung
            elif abs(result_year - search_year) <= 1:
                score += 2000  # Jahr ±1 ist auch gut
            elif abs(result_year - search_year) <= 2:
                score += 500  # Jahr ±2 ist noch akzeptabel
    
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

def search_mediathek(movie_title, prefer_language="deutsch", prefer_audio_desc="egal", notify_url=None, entry_link=None, year: Optional[int] = None, metadata: Dict = None):
    """
    Sucht nach einem Film in MediathekViewWeb und wählt die beste Fassung
    basierend auf den Präferenzen und Titelübereinstimmung aus.
    
    Args:
        movie_title: Der Filmtitel zum Suchen
        prefer_language: "deutsch", "englisch" oder "egal"
        prefer_audio_desc: "mit", "ohne" oder "egal"
        notify_url: Optional - Apprise-URL für Benachrichtigungen
        entry_link: Optional - Link zum Blog-Eintrag für Benachrichtigungen
        year: Optional - Das Jahr des Films (für bessere Matching)
        metadata: Optional - Dictionary mit 'provider_id' (tmdbid-XXX oder imdbid-XXX) für exaktes Matching
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
            # Benachrichtigung für keine Ergebnisse
            if notify_url and APPRISE_AVAILABLE:
                body = f"Keine Ergebnisse in der Mediathek gefunden:\n\n"
                body += f"📽️ {movie_title}\n"
                if entry_link:
                    body += f"\n🔗 Blog-Eintrag: {entry_link}"
                send_notification(notify_url, "Film nicht gefunden", body, "warning")
            return None
        
        # Bewerte alle Ergebnisse
        scored_results = []
        for result in results:
            try:
                score = score_movie(result, prefer_language, prefer_audio_desc, 
                                  search_title=movie_title, search_year=year, metadata=metadata)
                scored_results.append((score, result))
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten eines Ergebnisses für '{movie_title}': {e}")
                continue
        
        if not scored_results:
            logging.warning(f"Keine gültigen Ergebnisse für '{movie_title}' gefunden")
            # Benachrichtigung für erfolglose Suche
            if notify_url and APPRISE_AVAILABLE:
                body = f"Keine gültigen Ergebnisse für Film gefunden:\n\n"
                body += f"📽️ {movie_title}\n"
                body += f"ℹ️ Es wurden Ergebnisse gefunden, aber keine konnten verarbeitet werden.\n"
                if entry_link:
                    body += f"\n🔗 Blog-Eintrag: {entry_link}"
                send_notification(notify_url, "Suche erfolglos", body, "warning")
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

def extract_episode_info(movie_data, series_title: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extrahiert Staffel- und Episoden-Nummer aus MediathekViewWeb-Daten.
    
    Args:
        movie_data: Die Filmdaten von MediathekViewWeb
        series_title: Der Serientitel (für Filterung)
        
    Returns:
        Tuple (season, episode) oder (None, None) wenn nicht gefunden
    """
    title = movie_data.get("title", "")
    topic = movie_data.get("topic", "")
    description = movie_data.get("description", "")
    
    text = f"{title} {topic} {description}"
    
    # Pattern 1: S01E01, S1E1, S 01 E 01
    pattern1 = re.search(r'[Ss](\d+)[\s]*[Ee](\d+)', text)
    if pattern1:
        season = int(pattern1.group(1))
        episode = int(pattern1.group(2))
        logging.debug(f"Episoden-Info gefunden (S01E01 Format): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    # Pattern 2: Staffel 1 Episode 1, Staffel 1, Episode 1
    pattern2 = re.search(r'[Ss]taffel\s+(\d+)[\s,]*[Ee]pisode\s+(\d+)', text, re.IGNORECASE)
    if pattern2:
        season = int(pattern2.group(1))
        episode = int(pattern2.group(2))
        logging.debug(f"Episoden-Info gefunden (Staffel/Episode Format): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    # Pattern 2a: Saison 1 (1/8), Staffel 1 (1/8), Saison 1 (1/30) - französisches/deutsches Format
    pattern2a = re.search(r'(?:[Ss]aison|[Ss]taffel)\s+(\d+)\s*\((\d+)/\d+\)', text, re.IGNORECASE)
    if pattern2a:
        season = int(pattern2a.group(1))
        episode = int(pattern2a.group(2))
        logging.debug(f"Episoden-Info gefunden (Saison/Staffel X (Y/Z) Format): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    # Pattern 2b: The Return (1/18), (1/18) - Format ohne Staffel-Nummer (Staffel wird als 3 angenommen für "The Return")
    pattern2b = re.search(r'\((\d+)/\d+\)', text)
    if pattern2b and ('return' in text.lower() or 'the return' in text.lower()):
        episode = int(pattern2b.group(1))
        # "The Return" ist Staffel 3
        season = 3
        logging.debug(f"Episoden-Info gefunden (The Return Format): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    # Pattern 3: Folge 1, Folge 01 (nur Episode, Staffel wird als 1 angenommen)
    pattern3 = re.search(r'[Ff]olge\s+(\d+)', text)
    if pattern3:
        episode = int(pattern3.group(1))
        logging.debug(f"Episoden-Info gefunden (Folge Format): S01E{episode:02d}")
        return (1, episode)
    
    # Pattern 4: Episode 1, Episode 01 (nur Episode, Staffel wird als 1 angenommen)
    pattern4 = re.search(r'[Ee]pisode\s+(\d+)', text)
    if pattern4:
        episode = int(pattern4.group(1))
        logging.debug(f"Episoden-Info gefunden (Episode Format): S01E{episode:02d}")
        return (1, episode)
    
    # Pattern 5: 1x01, 1.01
    pattern5 = re.search(r'(\d+)[x.](\d+)', text)
    if pattern5:
        season = int(pattern5.group(1))
        episode = int(pattern5.group(2))
        logging.debug(f"Episoden-Info gefunden (1x01 Format): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    return (None, None)

def format_episode_filename(series_title: str, season: Optional[int], episode: Optional[int], metadata: Dict) -> str:
    """
    Generiert Dateinamen für eine Episode im Format 'Serientitel (Jahr) - S01E01 [provider_id].ext'
    
    Args:
        series_title: Der Serientitel
        season: Staffel-Nummer
        episode: Episoden-Nummer
        metadata: Dictionary mit 'year' und 'provider_id'
        
    Returns:
        Dateiname ohne Extension
    """
    # Clean filename - entferne problematische Zeichen
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', series_title)
    
    filename_parts = [safe_title]
    
    # Füge Jahr hinzu, falls vorhanden
    year = metadata.get("year")
    if year:
        filename_parts.append(f"({year})")
    
    # Füge Staffel/Episode hinzu
    if season is not None and episode is not None:
        filename_parts.append(f"- S{season:02d}E{episode:02d}")
    elif episode is not None:
        filename_parts.append(f"- E{episode:02d}")
    
    # Füge Provider-ID hinzu, falls vorhanden
    provider_id = metadata.get("provider_id")
    if provider_id:
        filename_parts.append(provider_id)
    
    return " ".join(filename_parts)

def get_series_directory(series_base_dir: str, series_title: str, year: Optional[int]) -> str:
    """
    Erstellt und gibt den Serien-Unterordner zurück.
    
    Args:
        series_base_dir: Basis-Verzeichnis für Serien (aus --serien-dir oder --download-dir)
        series_title: Der Serientitel
        year: Optional - Das Jahr der Serie
        
    Returns:
        Pfad zum Serien-Unterordner: series_base_dir/[Titel] (Jahr)/
    """
    # Clean title - entferne problematische Zeichen
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', series_title)
    
    # Baue Unterordner-Namen: [Titel] (Jahr)
    dir_parts = [safe_title]
    if year:
        dir_parts.append(f"({year})")
    
    dir_name = " ".join(dir_parts)
    series_dir = os.path.join(series_base_dir, dir_name)
    
    # Erstelle Verzeichnis falls nicht vorhanden
    if not os.path.exists(series_dir):
        try:
            os.makedirs(series_dir)
            logging.info(f"Serien-Verzeichnis erstellt: {series_dir}")
        except OSError as e:
            logging.error(f"Konnte Serien-Verzeichnis nicht erstellen {series_dir}: {e}")
            raise
    
    return series_dir

def search_mediathek_series(series_title: str, prefer_language: str = "deutsch", prefer_audio_desc: str = "egal", 
                            notify_url: Optional[str] = None, entry_link: Optional[str] = None, 
                            year: Optional[int] = None, metadata: Optional[Dict] = None) -> list:
    """
    Sucht nach allen Episoden einer Serie in MediathekViewWeb.
    
    Args:
        series_title: Der Serientitel
        prefer_language: "deutsch", "englisch" oder "egal"
        prefer_audio_desc: "mit", "ohne" oder "egal"
        notify_url: Optional - Apprise-URL für Benachrichtigungen
        entry_link: Optional - Link zum Blog-Eintrag
        year: Optional - Das Jahr der Serie
        metadata: Optional - Dictionary mit 'provider_id' und 'content_type'
        
    Returns:
        Liste von Episoden-Daten (sortiert nach Score), oder leere Liste wenn keine gefunden
    """
    logging.info(f"Suche in MediathekViewWeb nach Serie: '{series_title}'")
    payload = {
        "queries": [
            {
                "fields": ["title", "topic"],
                "query": series_title
            }
        ],
        "sortBy": "size",
        "sortOrder": "desc",
        "future": False,
        "offset": 0,
        "size": 100  # Mehr Ergebnisse für Serien (können viele Episoden haben)
    }
    
    try:
        response = requests.post(MVW_API_URL, json=payload, headers={"Content-Type": "text/plain"}, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("result", {}).get("results", [])
        if not results:
            logging.warning(f"Keine Ergebnisse gefunden für Serie '{series_title}'")
            if notify_url and APPRISE_AVAILABLE:
                body = f"Keine Ergebnisse in der Mediathek gefunden:\n\n"
                body += f"📺 {series_title}\n"
                if entry_link:
                    body += f"\n🔗 Blog-Eintrag: {entry_link}"
                send_notification(notify_url, "Serie nicht gefunden", body, "warning")
            return []
        
        # Filtere Ergebnisse: Nur die, die den Serientitel enthalten
        series_title_lower = series_title.lower()
        filtered_results = []
        for result in results:
            title = result.get("title", "").lower()
            topic = result.get("topic", "").lower()
            # Prüfe ob Serientitel im Titel oder Topic enthalten ist
            if series_title_lower in title or series_title_lower in topic:
                filtered_results.append(result)
        
        if not filtered_results:
            logging.warning(f"Keine Episoden für Serie '{series_title}' gefunden")
            if notify_url and APPRISE_AVAILABLE:
                body = f"Keine Episoden für Serie gefunden:\n\n"
                body += f"📺 {series_title}\n"
                if entry_link:
                    body += f"\n🔗 Blog-Eintrag: {entry_link}"
                send_notification(notify_url, "Keine Episoden gefunden", body, "warning")
            return []
        
        # Bewerte alle Episoden
        scored_results = []
        for result in filtered_results:
            try:
                score = score_movie(result, prefer_language, prefer_audio_desc,
                                  search_title=series_title, search_year=year, metadata=metadata)
                scored_results.append((score, result))
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten einer Episode für '{series_title}': {e}")
                continue
        
        if not scored_results:
            logging.warning(f"Keine gültigen Episoden für '{series_title}' gefunden")
            return []
        
        # Sortiere nach Punktzahl (höchste zuerst)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        # Extrahiere nur die Episoden-Daten (ohne Score)
        episodes = [result for score, result in scored_results]
        
        logging.info(f"{len(episodes)} Episoden für Serie '{series_title}' gefunden")
        return episodes
        
    except requests.RequestException as e:
        logging.error(f"Netzwerkfehler bei der Suche nach Serie '{series_title}': {e}")
        return []
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Ungültige Antwort von MediathekViewWeb für Serie '{series_title}': {e}")
        return []
    except Exception as e:
        logging.error(f"Unerwarteter Fehler bei der Suche nach Serie '{series_title}': {e}")
        return []

def download_content(movie_data, download_dir, content_title: str, metadata: Dict, is_series: bool = False, 
                     series_base_dir: Optional[str] = None, season: Optional[int] = None, 
                     episode: Optional[int] = None):
    """
    Lädt einen Film oder eine Episode herunter.
    
    Args:
        movie_data: Die Filmdaten von MediathekViewWeb
        download_dir: Download-Verzeichnis (für Filme) oder Basis-Verzeichnis (für Serien)
        content_title: Der ursprüngliche Filmtitel oder Serientitel aus dem RSS-Feed
        metadata: Dictionary mit 'year' und 'provider_id' (von get_metadata())
        is_series: True wenn es sich um eine Serie handelt
        series_base_dir: Optional - Basis-Verzeichnis für Serien (wenn is_series=True)
        season: Optional - Staffel-Nummer (für Serien)
        episode: Optional - Episoden-Nummer (für Serien)
    
    Returns:
        tuple: (success: bool, title: str, filepath: str)
    """
    url = movie_data.get("url_video")
    title = movie_data.get("title")
    
    # Bestimme Ziel-Verzeichnis
    if is_series and series_base_dir:
        # Für Serien: Verwende series_base_dir und erstelle Unterordner
        target_dir = get_series_directory(series_base_dir, content_title, metadata.get("year"))
        # Generiere Episode-Dateinamen
        base_filename = format_episode_filename(content_title, season, episode, metadata)
    else:
        # Für Filme: Verwende download_dir direkt
        target_dir = download_dir
        # Verwende den ursprünglichen Filmtitel aus RSS-Feed für Dateinamen
        base_title = content_title
        
        # Clean filename - entferne problematische Zeichen
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', base_title)
        
        # Baue Dateinamen im Jellyfin/Plex-Format: "Movie Name (year) [provider_id].ext"
        filename_parts = [safe_title]
        
        # Füge Jahr hinzu, falls vorhanden
        year = metadata.get("year")
        if year:
            filename_parts.append(f"({year})")
        
        # Füge Provider-ID hinzu, falls vorhanden
        provider_id = metadata.get("provider_id")
        if provider_id:
            filename_parts.append(provider_id)
        
        # Baue Dateinamen zusammen
        base_filename = " ".join(filename_parts)
    
    # Try to guess extension
    ext = "mp4"
    if url.endswith(".mkv"): ext = "mkv"
    if url.endswith(".mp4"): ext = "mp4"
    
    filename = f"{base_filename}.{ext}"
    filepath = os.path.join(target_dir, filename)

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
    parser.add_argument("--tmdb-api-key", default=None,
                       help="TMDB API-Key für Metadata-Abfrage (optional, kann auch über Umgebungsvariable TMDB_API_KEY gesetzt werden)")
    parser.add_argument("--omdb-api-key", default=None,
                       help="OMDb API-Key für Metadata-Abfrage (optional, kann auch über Umgebungsvariable OMDB_API_KEY gesetzt werden)")
    parser.add_argument("--serien-download", default="erste", choices=["erste", "staffel", "keine"],
                       help="Download-Verhalten für Serien: 'erste' (nur erste Episode), 'staffel' (gesamte Staffel), 'keine' (überspringen)")
    parser.add_argument("--serien-dir", default=None,
                       help="Basis-Verzeichnis für Serien-Downloads (Standard: --download-dir). Episoden werden in Unterordnern [Titel] (Jahr)/ gespeichert")
    
    args = parser.parse_args()
    
    # Unterstützung für Umgebungsvariablen
    args.tmdb_api_key = args.tmdb_api_key or os.environ.get('TMDB_API_KEY')
    args.omdb_api_key = args.omdb_api_key or os.environ.get('OMDB_API_KEY')
    
    setup_logging(args.loglevel)
    
    # Version beim Start ausgeben
    logging.info(f"Perlentaucher v{__version__}")
    
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
    
    for i, movie_data in enumerate(movies):
        entry_id, entry, entry_link = new_entries[i]
        movie_title, year = movie_data if isinstance(movie_data, tuple) else (movie_data, None)
        
        # Hole Metadata VOR der Suche, damit wir sie für besseres Matching nutzen können
        metadata = get_metadata(movie_title, year, args.tmdb_api_key, args.omdb_api_key)
        
        # Prüfe ob es sich um eine Serie handelt
        is_series_entry = is_series(entry, metadata)
        
        # Verarbeite basierend auf Serien-Download-Option
        if is_series_entry:
            if args.serien_download == "keine":
                logging.info(f"Überspringe Serie '{movie_title}' (--serien-download=keine)")
                if state_file:
                    save_processed_entry(state_file, entry_id, status='skipped', movie_title=movie_title, is_series=True)
                continue
            elif args.serien_download == "erste":
                # Lade nur erste Episode (aktuelles Verhalten)
                result = search_mediathek(movie_title, prefer_language=args.sprache, prefer_audio_desc=args.audiodeskription, 
                                         notify_url=args.notify, entry_link=entry_link, year=year, metadata=metadata)
                if result:
                    # Extrahiere Episode-Info für Dateinamen
                    season, episode = extract_episode_info(result, movie_title)
                    # Bestimme series_base_dir
                    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
                    success, title, filepath = download_content(result, args.download_dir, movie_title, metadata, 
                                                               is_series=True, series_base_dir=series_base_dir,
                                                               season=season, episode=episode)
                    # Markiere Eintrag als verarbeitet nach Download-Versuch
                    if state_file:
                        status = 'download_success' if success else 'download_failed'
                        filename = os.path.basename(filepath) if filepath else None
                        save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, 
                                           filename=filename, is_series=True)
                        logging.debug(f"Eintrag als verarbeitet markiert: '{entry.title}' (Status: {status})")
                    
                    # Benachrichtigung senden
                    if args.notify:
                        if success:
                            body = f"Episode erfolgreich heruntergeladen:\n\n"
                            body += f"📺 {title}\n"
                            body += f"💾 {filepath}\n"
                            if entry_link:
                                body += f"\n🔗 Blog-Eintrag: {entry_link}"
                            send_notification(args.notify, "Download erfolgreich", body, "success")
                        else:
                            body = f"Download fehlgeschlagen:\n\n"
                            body += f"📺 {title}\n"
                            if entry_link:
                                body += f"\n🔗 Blog-Eintrag: {entry_link}"
                            send_notification(args.notify, "Download fehlgeschlagen", body, "error")
                else:
                    logging.warning(f"Überspringe Serie '{movie_title}' - nicht in der Mediathek gefunden.")
                    if state_file:
                        save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title, is_series=True)
                    continue
            elif args.serien_download == "staffel":
                # Lade alle Episoden der Staffel
                episodes = search_mediathek_series(movie_title, prefer_language=args.sprache, 
                                                  prefer_audio_desc=args.audiodeskription,
                                                  notify_url=args.notify, entry_link=entry_link, 
                                                  year=year, metadata=metadata)
                if episodes:
                    # Bestimme series_base_dir
                    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
                    
                    # Sortiere Episoden nach Staffel/Episode
                    episodes_with_info = []
                    for episode_data in episodes:
                        season, episode_num = extract_episode_info(episode_data, movie_title)
                        episodes_with_info.append((season, episode_num, episode_data))
                    
                    # Sortiere: zuerst nach Staffel, dann nach Episode (None wird als 0 behandelt für Sortierung)
                    episodes_with_info.sort(key=lambda x: (x[0] or 0, x[1] or 0))
                    
                    total_episodes = len(episodes_with_info)
                    downloaded_count = 0
                    failed_count = 0
                    
                    logging.info(f"Starte Download von {total_episodes} Episoden für '{movie_title}'")
                    
                    for season, episode_num, episode_data in episodes_with_info:
                        if season is None or episode_num is None:
                            logging.warning(f"Überspringe Episode ohne Staffel/Episoden-Info: '{episode_data.get('title')}'")
                            continue
                        
                        success, title, filepath = download_content(episode_data, args.download_dir, movie_title, metadata,
                                                                     is_series=True, series_base_dir=series_base_dir,
                                                                     season=season, episode=episode_num)
                        if success:
                            downloaded_count += 1
                        else:
                            failed_count += 1
                        
                        # Markiere Episode in State-Datei
                        if state_file:
                            episode_id = f"{entry_id}_S{season:02d}E{episode_num:02d}"
                            status = 'download_success' if success else 'download_failed'
                            filename = os.path.basename(filepath) if filepath else None
                            save_processed_entry(state_file, episode_id, status=status, 
                                                movie_title=f"{movie_title} S{season:02d}E{episode_num:02d}", 
                                                filename=filename)
                    
                    # Markiere Haupt-Eintrag als verarbeitet
                    if state_file:
                        status = 'download_success' if downloaded_count > 0 else 'download_failed'
                        episodes_list = [f"S{s:02d}E{e:02d}" for s, e, _ in episodes_with_info if s is not None and e is not None]
                        save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, 
                                            is_series=True, episodes=episodes_list)
                    
                    # Benachrichtigung für Staffel-Download
                    if args.notify:
                        body = f"Staffel-Download abgeschlossen:\n\n"
                        body += f"📺 {movie_title}\n"
                        body += f"✅ {downloaded_count}/{total_episodes} Episoden erfolgreich\n"
                        if failed_count > 0:
                            body += f"❌ {failed_count} Episoden fehlgeschlagen\n"
                        if entry_link:
                            body += f"\n🔗 Blog-Eintrag: {entry_link}"
                        notification_type = "success" if failed_count == 0 else "warning"
                        send_notification(args.notify, "Staffel-Download abgeschlossen", body, notification_type)
                    
                    continue
                else:
                    # Keine Episoden gefunden
                    if state_file:
                        save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title, is_series=True)
                    continue
        else:
            # Normale Film-Verarbeitung
            result = search_mediathek(movie_title, prefer_language=args.sprache, prefer_audio_desc=args.audiodeskription, 
                                     notify_url=args.notify, entry_link=entry_link, year=year, metadata=metadata)
            if result:
                success, title, filepath = download_content(result, args.download_dir, movie_title, metadata, is_series=False)
                # Markiere Eintrag als verarbeitet nach Download-Versuch
                if state_file:
                    status = 'download_success' if success else 'download_failed'
                    filename = os.path.basename(filepath) if filepath else None
                    save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, filename=filename)
                    logging.debug(f"Eintrag als verarbeitet markiert: '{entry.title}' (Status: {status})")
                
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
                logging.warning(f"Überspringe '{movie_title}' - nicht in der Mediathek gefunden.")
                # Auch nicht gefundene Filme als verarbeitet markieren, damit sie nicht immer wieder versucht werden
                if state_file:
                    save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title)
                    logging.debug(f"Eintrag als verarbeitet markiert (Film nicht gefunden): '{entry.title}'")
                # Hinweis: Benachrichtigung wird bereits in search_mediathek() gesendet

if __name__ == "__main__":
    main()
