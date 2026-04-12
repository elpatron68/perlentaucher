import argparse
import logging
import os
import re
import sys
import requests
import feedparser
import json
import semver
import unicodedata
from datetime import datetime
from typing import Optional, Dict, Tuple, List, Any
from urllib.parse import quote

# Projekt-Root auf sys.path, damit „from src.…“ funktioniert (z. B. python src/perlentaucher.py)
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    import apprise
    APPRISE_AVAILABLE = True
except ImportError:
    APPRISE_AVAILABLE = False

# Versions-Import
try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"

from src.wishlist_activity import log_activity_event

# Configuration
RSS_FEED_URL = "https://nexxtpress.de/author/mediathekperlen/feed/"
MVW_API_URL = "https://mediathekviewweb.de/api/query"
MVW_FEED_URL = "https://mediathekviewweb.de/feed"

# Logging setup
def setup_logging(level_name):
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=level,
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def check_for_updates(current_version: str) -> None:
    """
    Prüft, ob eine neuere Version auf Codeberg verfügbar ist.
    Gibt eine Logging-Meldung aus, wenn eine neuere Version gefunden wird.
    
    Args:
        current_version: Die aktuelle Version des Scripts
    """
    try:
        # API-Aufruf zur Codeberg/Gitea API
        response = requests.get(
            "https://codeberg.org/api/v1/repos/elpatron/Perlentaucher/releases/latest",
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        
        # Extrahiere Version aus tag_name
        latest_tag_raw = data.get('tag_name', '')
        if not latest_tag_raw:
            return
        
        # Entferne "v" Präfix für semver-Vergleich
        latest_tag_clean = latest_tag_raw.lstrip('v')
        current_clean = current_version.lstrip('v')
        
        # Überspringe Prüfung wenn aktuelle Version "unknown" ist
        if current_clean == "unknown" or not latest_tag_clean:
            return
        
        # Versionsvergleich mit semver
        comparison = semver.compare(current_clean, latest_tag_clean)
        if comparison < 0:
            # Neuere Version verfügbar
            logging.info(f"⚠️  Eine neuere Version ist verfügbar: {latest_tag_raw} (aktuell: v{current_version})")
            logging.info(f"   Download: https://codeberg.org/elpatron/Perlentaucher/releases/tag/{latest_tag_raw}")
        elif comparison == 0:
            # Aktuelle Version ist die neueste
            logging.info(f"✅ Auf dem neuesten Stand: v{current_version}")
        # Wenn comparison > 0, ist die aktuelle Version neuer (z.B. Entwicklung), keine Meldung nötig
    except Exception:
        # Stillschweigend überspringen bei Fehlern (keine Internetverbindung, API-Fehler, etc.)
        pass

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

def normalize_search_title(title: str) -> str:
    """
    Normalisiert einen Filmtitel für die Suche, indem Sonderzeichen entfernt/normalisiert werden.
    Konvertiert z.B. 'Dalíland' zu 'Daliland' für bessere Suche in MediathekViewWeb.
    
    Behandelt:
    - Akzente/Diakritika (í → i, é → e, etc.), aber NICHT deutsche Umlaute (ä, ö, ü, ß)
    - Typografische Anführungszeichen („ " → ", ' → ')
    - Em/En-Dashes (— → -, – → -)
    - Andere häufige typografische Sonderzeichen
    
    Deutsche Umlaute bleiben erhalten, da MediathekViewWeb mit Original-Umlauten indexiert.
    
    Args:
        title: Der Filmtitel mit möglichen Sonderzeichen
    
    Returns:
        Normalisierter Titel (deutsche Umlaute unverändert)
    """
    if not title:
        return title
    
    # Schritt 1: Normalisiere typografische Anführungszeichen zu Standard-Anführungszeichen
    # Mapping für typografische Anführungszeichen
    quote_mapping = {
        '\u201E': '"',  # „ (deutsches öffnendes Anführungszeichen)
        '\u201C': '"',  # " (englisches öffnendes Anführungszeichen)
        '\u201D': '"',  # " (englisches schließendes Anführungszeichen)
        '\u201F': '"',  # „ (Doppel-Anführungszeichen hochkomma)
        '\u2033': '"',  # " (Doppel-Prim)
        '\u2036': '"',  # „ (Doppel-Prim umgekehrt)
        '\u2018': "'",  # ' (englisches öffnendes einfaches Anführungszeichen)
        '\u2019': "'",  # ' (englisches schließendes einfaches Anführungszeichen, auch Apostroph)
        '\u201A': "'",  # ‚ (einfaches Anführungszeichen unten)
        '\u201B': "'",  # ‛ (einfaches Anführungszeichen oben)
        '\u2032': "'",  # ' (Prim)
        '\u2035': "'",  # ‵ (umgekehrter Prim)
        '\u275D': "'",  # ' (einfaches Anführungszeichen)
        '\u275E': "'",  # ' (einfaches Anführungszeichen)
    }
    
    # Schritt 2: Normalisiere Striche/Dashes
    dash_mapping = {
        '\u2014': '-',  # — (Em-Dash)
        '\u2015': '-',  # ― (horizontal bar)
        '\u2013': '-',  # – (En-Dash)
        '\u2212': '-',  # − (Minus-Zeichen)
    }
    
    # Schritt 3: Normalisiere andere häufige typografische Zeichen
    other_mapping = {
        '\u2026': '...',  # … (Ellipsis)
        '\u00A0': ' ',   # (non-breaking space)
        '\u2009': ' ',   # (thin space)
        '\u2008': ' ',   # (punctuation space)
        '\u2007': ' ',   # (figure space)
        '\u2006': ' ',   # (six-per-em space)
        '\u2005': ' ',   # (four-per-em space)
        '\u2004': ' ',   # (three-per-em space)
        '\u2003': ' ',   # (em space)
        '\u2002': ' ',   # (en space)
        '\u2001': ' ',   # (em quad)
        '\u2000': ' ',   # (en quad)
        '\u200B': '',    # (zero-width space)
        '\uFEFF': '',    # (zero-width no-break space / BOM)
    }
    
    # Kombiniere alle Mappings
    char_mapping = {**quote_mapping, **dash_mapping, **other_mapping}
    
    # Wende Charakter-Mapping an
    normalized = title
    for old_char, new_char in char_mapping.items():
        normalized = normalized.replace(old_char, new_char)
    
    # Schritt 4: Deutsche Umlaute (ä, ö, ü, ß) vor NFKD schützen – bleiben unverändert
    # MediathekViewWeb indexiert mit Original-Umlauten, daher keine ae/oe/ue-Normalisierung
    umlaut_chars = ('ä', 'ö', 'ü', 'Ä', 'Ö', 'Ü', 'ß')
    placeholders = {}
    for i, c in enumerate(umlaut_chars):
        ph = chr(0x01 + i)  # ASCII-kompatible Platzhalter (überleben encode('ascii'))
        placeholders[ph] = c
        normalized = normalized.replace(c, ph)
    
    # Schritt 5: Normalisiere zu NFKD (Normalization Form Compatibility Decomposition)
    # Das trennt Zeichen wie í in i + Akut
    nfkd_form = unicodedata.normalize('NFKD', normalized)
    
    # Schritt 6: Entferne alle Combining Characters (Akzente, Diakritika)
    # und konvertiere zu ASCII (ignoriere Fehler für nicht-ASCII Zeichen)
    normalized = ''.join(c for c in nfkd_form if not unicodedata.combining(c))
    
    # Schritt 7: Finale ASCII-Konvertierung
    try:
        result = normalized.encode('ascii', 'ignore').decode('ascii')
        # Deutsche Umlaute wiederherstellen (Placeholder → Original)
        for ph, c in placeholders.items():
            result = result.replace(ph, c)
        # Entferne überflüssige Leerzeichen (mehrfache Leerzeichen zu einem)
        result = ' '.join(result.split())
        return result
    except (UnicodeEncodeError, UnicodeDecodeError):
        # Falls das fehlschlägt, gib den normalisierten String zurück (bereinigt)
        out = ' '.join(normalized.split())
        for ph, c in placeholders.items():
            out = out.replace(ph, c)
        return out

# Führende Artikel (nominativ/akkusativ/dativ/genitiv, unbestimmt) für Mediathek-Suche ohne Artikel
_GERMAN_LEADING_ARTICLES = frozenset({
    "der", "die", "das", "den", "dem", "des",
    "ein", "eine", "einer", "einem", "einen", "eines",
})
# Nach Artikel-Stripping: Rest darf nicht mit Präposition o. Ä. beginnen (z. B. „Der mit dem Wolf tanzt“)
_NO_ARTICLE_STRIP_IF_REMAINDER_STARTS_WITH = frozenset({
    "mit", "in", "auf", "von", "zu", "bei", "nach", "vor", "über", "unter",
    "und", "oder", "für", "aus", "an", "am", "im", "zum", "zur", "vom", "beim",
    "ins", "ans", "durch", "gegen", "ohne", "um", "bis", "wie", "als",
})


def strip_leading_german_article(title: str) -> Optional[str]:
    """
    Entfernt einen führenden deutscher Artikel, wenn der verbleibende Titel plausibel ist.

    Die Mediathek indexiert Filme oft ohne Artikel („Schachnovelle“), Blogs nennen sie mit
    („Die Schachnovelle“). Titel wie „Der mit dem Wolf tanzt“ werden nicht gekürzt, weil der
    Rest mit einer Präposition beginnt.
    """
    if not title:
        return None
    parts = title.strip().split()
    if len(parts) < 2:
        return None
    if parts[0].lower() not in _GERMAN_LEADING_ARTICLES:
        return None
    remainder = " ".join(parts[1:]).strip()
    if not remainder:
        return None
    first = remainder.split()[0].lower()
    if first in _NO_ARTICLE_STRIP_IF_REMAINDER_STARTS_WITH:
        return None
    return remainder


def mediathek_movie_search_terms(movie_title: str) -> List[str]:
    """
    Reihenfolge der Suchbegriffe für MediathekViewWeb: Original, Normalisierung, ohne Artikel.
    Duplikate werden ausgelassen.
    """
    seen = set()
    out: List[str] = []
    base = (movie_title or "").strip()
    if not base:
        return out

    def add(s: str) -> None:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(base)
    norm = normalize_search_title(base)
    add(norm)
    stripped = strip_leading_german_article(base)
    if stripped:
        add(stripped)
        add(normalize_search_title(stripped))
    return out


def _fetch_mvw_api_movie_results(search_term: str) -> list:
    """
    Fragt die MediathekViewWeb-API mit einem Suchbegriff ab (Feldsuche + einfache query,
    optional normalisierte Variante). Gibt die erste nicht-leere Ergebnisliste zurück.
    """
    normalized_search_title = normalize_search_title(search_term)
    payloads = []
    payloads.append({
        "headers": {"Content-Type": "application/json"},
        "payload": {
            "queries": [
                {"fields": ["title"], "query": search_term}
            ]
        }
    })
    payloads.append({
        "headers": {"Content-Type": "application/json"},
        "payload": {"query": search_term}
    })
    if normalized_search_title != search_term:
        payloads.append({
            "headers": {"Content-Type": "application/json"},
            "payload": {
                "queries": [
                    {"fields": ["title"], "query": normalized_search_title}
                ]
            }
        })
        payloads.append({
            "headers": {"Content-Type": "application/json"},
            "payload": {"query": normalized_search_title}
        })

    results = []
    for payload_entry in payloads:
        try:
            payload = payload_entry.get("payload", {})
            headers = payload_entry.get("headers", {"Content-Type": "application/json"})
            response = requests.post(MVW_API_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            results = data.get("result", {}).get("results", [])
            if results:
                logging.debug(
                    f"MediathekViewWeb-API: {len(results)} Treffer für Suchbegriff '{search_term}'"
                )
                break
        except requests.RequestException as e:
            logging.debug(f"Fehler mit Payload-Format, versuche nächstes: {e}")
            continue
        except (KeyError, ValueError, TypeError) as e:
            logging.debug(f"Ungültige Antwort, versuche nächstes Format: {e}")
            continue
    return results


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

def is_movie_recommendation(entry) -> bool:
    """
    Prüft, ob ein RSS-Feed-Eintrag eine Film-Empfehlung ist (kein "In eigener Sache" o.ä.).
    
    Vereinfachte Logik basierend auf Tags:
    - Film-Empfehlungen haben das Tag "Mediathekperlen" UND keine Nicht-Film-Tags (z.B. "In eigener Sache", "Blog")
    - Nicht-Film-Empfehlungen haben zwar auch "Mediathekperlen", aber zusätzlich spezielle Tags wie "In eigener Sache", "Blog", etc.
    
    Args:
        entry: RSS-Feed-Eintrag (Dictionary-ähnlich mit .get() Methode)
        
    Returns:
        True wenn es sich um eine Film-Empfehlung handelt, sonst False
    """
    # Extrahiere Tags/Kategorien aus dem Eintrag
    categories = entry.get('tags', [])
    if not isinstance(categories, list):
        categories = []
    
    # Sammle alle Tag-Terms (lowercase für Vergleich)
    tag_terms = []
    has_mediathekperlen = False
    
    for tag in categories:
        if isinstance(tag, dict):
            tag_term = tag.get('term', '').strip()
        else:
            tag_term = str(tag).strip()
        if tag_term:
            tag_lower = tag_term.lower()
            tag_terms.append(tag_lower)
            # Prüfe ob "Mediathekperlen" Tag vorhanden ist
            if tag_lower == 'mediathekperlen':
                has_mediathekperlen = True
    
    # Wenn kein "Mediathekperlen" Tag vorhanden ist, ist es keine Film-Empfehlung
    if not has_mediathekperlen:
        logging.debug(f"Kein 'Mediathekperlen' Tag gefunden, behandle als Nicht-Film-Empfehlung")
        return False
    
    # Prüfe auf Tags, die auf Nicht-Film-Empfehlungen hinweisen
    # Diese Tags sollten bei Film-Empfehlungen NICHT vorhanden sein
    non_movie_tags = [
        'in eigener sache',
        'blog',
        'weihnachten',
        'nachruf',
        'ankündigung',
        'ankuendigung'
    ]
    
    for tag_term in tag_terms:
        for non_movie_tag in non_movie_tags:
            if non_movie_tag in tag_term:
                logging.debug(f"Nicht-Film-Empfehlung erkannt: Tag '{tag_term}' enthält '{non_movie_tag}'")
                return False
    
    # Wenn "Mediathekperlen" vorhanden ist und keine Nicht-Film-Tags gefunden wurden,
    # handelt es sich um eine Film-Empfehlung
    logging.debug(f"Film-Empfehlung erkannt: Tag 'Mediathekperlen' vorhanden und keine Nicht-Film-Tags gefunden")
    return True

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
        
        # WICHTIG: Prüfe ob es sich um eine Film-Empfehlung handelt
        # Überspringe Nicht-Film-Empfehlungen (z.B. "In eigener Sache" Beiträge)
        if not is_movie_recommendation(entry):
            logging.debug(f"Nicht-Film-Empfehlung erkannt, überspringe: '{entry.title}'")
            # Markiere als übersprungen in State-Datei (verhindert erneute Prüfung)
            if state_file:
                save_processed_entry(state_file, entry_id, status='skipped', movie_title=entry.title)
            skipped_count += 1
            continue
        
        title = entry.title
        # Regex to extract title from 'Director - „Movie" (Year)' or similar
        # Looking for content inside „..." - unterstützt verschiedene Anführungszeichen-Varianten
        # Suche nach öffnendem „ (U+201E) und dann alles bis zum nächsten Anführungszeichen
        # Unterstützt: „ " (U+201E + U+201C), „ " (U+201E + U+201D), „ " (U+201E + normales ")
        # Verwendet Unicode-Escape-Sequenzen für bessere Kompatibilität
        # U+201E = „, U+201C = ", U+201D = ", U+0022 = ", U+201F = „, U+2033 = ", U+2036 = „
        # Erweitertes Pattern: Unterstützt auch andere Unicode-Anführungszeichen
        match = re.search(r'\u201E(.+?)(?:[\u201C\u201D\u201F\u2033\u2036\u0022])', title)
        # Fallback 1: Normale Anführungszeichen
        if not match:
            match = re.search(r'"([^"]+?)"', title)
        # Fallback 2: Suche nach Text zwischen Anführungszeichen (beliebige Variante)
        if not match:
            # Suche nach Text zwischen öffnendem und schließendem Anführungszeichen
            # Unterstützt: „...", "...", '...', etc.
            match = re.search(r'[\u201E\u201C\u201D\u201F\u2033\u2036\u0022\u2018\u2019\u201A\u201B]([^\u201C\u201D\u201F\u2033\u2036\u0022\u2018\u2019\u201A\u201B]+?)[\u201C\u201D\u201F\u2033\u2036\u0022\u2018\u2019\u201A\u201B]', title)
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

# Synchron / deutsche Fassung (Substring „deutsch“ in „deutschen Untertiteln“ zählt nicht)
_GERMAN_SYNC_RE = re.compile(
    r"\b("
    r"deutsche?\s+fassung|deutschsprachig|"
    r"synchron(isiert|fassung)?|sync\.?\s*fassung|"
    r"dt\.\s*f\b|\bdt\.\s*\(?f\)?|"
    r"\bgdf\b|\bdf\b"
    r")\b",
    re.IGNORECASE,
)

# Originalton / OmU / OmDT / OV / ONE „(Originalversion)“ …
_ORIGINAL_VERSION_RE = re.compile(
    r"\b("
    r"omu|omdt|om\.?\s*u\.?|"
    r"original\s+mit\s+deutschen\s+untertiteln|"
    r"original\s+mit\s+untertiteln|"
    r"originalfassung|originalversion|original\s+version|"
    r"o\.?\s*v\.?|\bov\b|"
    r"englisch|english|"
    r"o[\s-]?ton|originalton"
    r")\b",
    re.IGNORECASE,
)

# Wort „Deutsch“ / „dt.“ (nicht Teil von „deutschen“)
_GERMAN_IMPLICIT_RE = re.compile(r"\b(deutsch|dt\.)\b", re.IGNORECASE)


def detect_language(movie_data):
    """Erkennt die Sprache eines Films (deutsch/englisch/unbekannt)."""
    title = movie_data.get("title", "").lower()
    description = movie_data.get("description", "").lower()
    topic = movie_data.get("topic", "").lower()

    text = f"{title} {description} {topic}"
    title_topic = f"{title} {topic}"

    sync = bool(_GERMAN_SYNC_RE.search(text))
    original = bool(_ORIGINAL_VERSION_RE.search(text))

    if sync and not original:
        return "deutsch"
    if original and not sync:
        return "englisch"
    if sync and original:
        sync_head = bool(_GERMAN_SYNC_RE.search(title_topic))
        orig_head = bool(_ORIGINAL_VERSION_RE.search(title_topic))
        if sync_head and not orig_head:
            return "deutsch"
        if orig_head and not sync_head:
            return "englisch"
        return "unbekannt"

    # Ohne klare Sync-/Original-Marker: konservative Substrings (Wortgrenzen beachten)
    if _GERMAN_IMPLICIT_RE.search(text) and not original:
        return "deutsch"
    if original:
        return "englisch"

    # Keine explizite Sprache: typisch deutschsprachige Mediathek → deutsch
    return "deutsch"


def _title_has_original_broadcast_marker(title: str) -> bool:
    """
    Sender markieren Originalfassung oft im Listings-Titel in Klammern.
    NFKC: volle Breite Klammern wie bei manchen APIs.
    """
    if not title:
        return False
    t = unicodedata.normalize("NFKC", title)
    return bool(
        re.search(
            r"\(originalversion\)|\(original-version\)|\(originalfassung\)|"
            r"\(ov\)|\(o\.\s*v\.\)|\(omu\)|\(omdt\)",
            t,
            re.IGNORECASE,
        )
    )


def get_significant_words(text: str) -> set:
    """
    Extrahiert signifikante Wörter aus einem Text, ignoriert Stopwords.
    
    Args:
        text: Der Text, aus dem Wörter extrahiert werden sollen
    
    Returns:
        Set von signifikanten Wörtern (ohne Stopwords)
    """
    # Deutsche und englische Stopwords, die bei der Titelübereinstimmung ignoriert werden sollten
    stopwords = {
        'die', 'der', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einer', 'einem', 'einen', 'eines',
        'und', 'oder', 'aber', 'doch', 'sondern', 'sowie', 'wie', 'als', 'wenn', 'ob', 'dass',
        'the', 'a', 'an', 'and', 'or', 'but', 'if', 'of', 'to', 'in', 'on', 'at', 'for', 'with',
        'von', 'zu', 'in', 'auf', 'für', 'mit', 'über', 'unter', 'durch', 'bei', 'nach', 'vor',
        'am', 'im', 'zum', 'zur', 'vom', 'beim', 'ins', 'ans', 'durchs', 'übers', 'unters'
    }
    
    words = set(text.lower().split())
    # Entferne Stopwords und sehr kurze Wörter (< 2 Zeichen)
    significant = {w for w in words if w not in stopwords and len(w) >= 2}
    return significant

def calculate_title_similarity(search_title: str, result_title: str) -> float:
    """
    Berechnet die Ähnlichkeit zwischen Suchtitel und Ergebnis-Titel.
    Gibt einen Wert zwischen 0.0 (keine Übereinstimmung) und 1.0 (exakte Übereinstimmung) zurück.
    Ignoriert Stopwords bei der Berechnung.
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
    
    # Extrahiere signifikante Wörter (ohne Stopwords)
    search_significant = get_significant_words(search_title)
    result_significant = get_significant_words(result_title)
    
    # Wenn keine signifikanten Wörter vorhanden sind, verwende alle Wörter
    if not search_significant:
        search_words = set(search_lower.split())
    else:
        search_words = search_significant
    
    if not result_significant:
        result_words = set(result_lower.split())
    else:
        result_words = result_significant
    
    if not search_words or not result_words:
        return 0.0
    
    # Berechne Jaccard-Ähnlichkeit (Schnittmenge / Vereinigungsmenge)
    intersection = search_words & result_words
    union = search_words | result_words
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    # Wenn alle signifikanten Suchwörter im Ergebnis enthalten sind, erhöhe den Score
    if search_significant and search_significant.issubset(result_words):
        jaccard = min(1.0, jaccard * 1.5)
    elif search_words.issubset(result_words):
        jaccard = min(1.0, jaccard * 1.3)
    
    return jaccard


def series_candidate_topic_alignment(series_title: str, movie_data: Dict) -> float:
    """
    Wie gut Topic/Titel die Serie als Sendung identifizieren (0..1).
    Reine Titel-Substring-Treffer ohne passendes Topic werden abgewertet.
    """
    nt = normalize_search_title(series_title).lower().strip()
    if not nt:
        return 0.5
    topic = (movie_data.get("topic") or "").strip()
    title = (movie_data.get("title") or "").strip()
    topic_n = normalize_search_title(topic).lower().strip()
    title_n = normalize_search_title(title).lower().strip()

    if nt == topic_n:
        return 1.0

    topic_tokens = set(re.findall(r"[\wöäüß]+", topic_n, flags=re.I))
    if " " not in nt and nt in topic_tokens:
        return 1.0

    if title_n.startswith(nt + " ") or title_n.startswith(nt + ":") or title_n.startswith(nt + " -"):
        return 0.92
    st_low = series_title.lower().strip()
    if title.lower().strip().startswith(st_low):
        return 0.9

    if nt not in title_n:
        return 0.2

    pos = title_n.find(nt)
    if pos <= 0 or title_n[:pos].strip() in ("", "|", "-", ":", "–"):
        return 0.55
    return 0.35


def calculate_title_similarity_for_series_listing(search_title: str, movie_data: Dict) -> float:
    """Kombiniert Titel-Ähnlichkeit mit Topic-/Serien-Kontext (für Serien-Suche & Wishlist)."""
    t = movie_data.get("title") or ""
    base = calculate_title_similarity(search_title, t)
    align = series_candidate_topic_alignment(search_title, movie_data)
    combined = base * align
    # Episodentitel ohne Seriennamen („Folge 1“), Topic aber = Serie — typisch in der Mediathek
    if align >= 0.9 and base < 0.3:
        return max(combined, align * 0.82)
    return combined


_PROMOTIONAL_TITLE_RE = re.compile(
    r"\b("
    r"trailer|teasers?|vorschau|previews?|making-of|making\s+of|"
    r"behind-the-scenes|behind\s+the\s+scenes|on\s+set|b-roll|b\s+roll|"
    r"clip\s+zur\s+serie|serienclip|staffeltrailer|folgenvorschau|"
    r"sneak\s+peek|exklusivclip|exklusiv-clip|promo\s*clip"
    r")\b",
    re.IGNORECASE,
)


def is_promotional_or_non_episode(movie_data: dict) -> bool:
    """
    Erkennt Trailer, Teaser und typische Promo-Clips (nicht reguläre Episoden).
    """
    if not movie_data:
        return False
    parts = [
        movie_data.get("title") or "",
        movie_data.get("topic") or "",
        movie_data.get("description") or "",
    ]
    blob = " ".join(parts)
    return bool(_PROMOTIONAL_TITLE_RE.search(blob))


def series_mediathek_result_matches(
    series_title: str,
    normalized_search_title: str,
    raw_title: str,
    raw_topic: str,
    raw_desc: str,
    *,
    min_title_similarity_for_description_only: float = 0.2,
) -> bool:
    """
    Prüft, ob ein MediathekViewWeb-Treffer zur Serie gehört.

    Primär: Suchbegriff in Titel oder Topic (inkl. normalisierter Varianten).
    Fallback: Treffer nur in der Beschreibung, dann nur bei ausreichender Titel-Ähnlichkeit
    (verhindert False Positives bei Substrings wie „Veil“ im Fließtext).
    """
    series_title_lower = series_title.lower().strip()
    normalized_lower = normalized_search_title.lower().strip()
    title = raw_title.lower()
    topic = raw_topic.lower()
    desc = raw_desc.lower()
    title_norm = normalize_search_title(raw_title).lower()
    topic_norm = normalize_search_title(raw_topic).lower()
    desc_norm = normalize_search_title(raw_desc).lower()

    in_title_or_topic = (
        series_title_lower in title
        or series_title_lower in topic
        or normalized_lower in title
        or normalized_lower in topic
        or normalized_lower in title_norm
        or normalized_lower in topic_norm
    )
    if in_title_or_topic:
        return True

    in_description = (
        series_title_lower in desc
        or normalized_lower in desc
        or normalized_lower in desc_norm
    )
    if not in_description:
        return False

    sim = calculate_title_similarity(series_title, raw_title)
    return sim >= min_title_similarity_for_description_only


def score_movie(
    movie_data,
    prefer_language,
    prefer_audio_desc,
    search_title: str = None,
    search_year: Optional[int] = None,
    metadata: Dict = None,
    use_series_listing_similarity: bool = False,
):
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
    
    # TITELÜBEREINSTIMMUNG - höchste Priorität (100000+ Punkte)
    # Erhöht von 10000 auf 100000, um sicherzustellen, dass Titelübereinstimmung immer
    # wichtiger ist als andere Faktoren (Dateigröße, Sprache, etc.)
    if search_title:
        result_title = movie_data.get("title", "")
        if use_series_listing_similarity:
            title_similarity = calculate_title_similarity_for_series_listing(search_title, movie_data)
        else:
            title_similarity = calculate_title_similarity(search_title, result_title)
        # Titelübereinstimmung ist sehr wichtig - multipliziere mit sehr hohem Faktor
        score += title_similarity * 100000
    
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
    # Sicherheitsnetz: OmU/OV darf bei klarer Gegenpräferenz nicht nur durch Dateigröße gewinnen
    elif prefer_language == "deutsch" and language == "englisch":
        score -= 2500
    elif prefer_language == "englisch" and language == "deutsch":
        score -= 2500

    # Präferenz „deutsch“: Markierung im Titel (z. B. ONE „(Originalversion)“) muss auch bei
    # geringer Titel-Ähnlichkeit zum Seriennamen und großer Datei die Synchronfassung nicht verdrängen.
    if prefer_language == "deutsch" and _title_has_original_broadcast_marker(movie_data.get("title") or ""):
        score -= 35000
    
    # Audiodeskription-Präferenz
    has_ad = has_audio_description(movie_data)
    if prefer_audio_desc == "mit" and has_ad:
        score += 500
    elif prefer_audio_desc == "ohne" and not has_ad:
        score += 500
    elif prefer_audio_desc == "egal":
        score += 250  # Neutrale Punktzahl
    
    return score

def _log_scored_matches(scored_results, search_title: str, limit: int = 10, label: str = "Matches"):
    """
    Loggt die Top-Matches mit Score für Debug-Ausgaben.
    """
    if not scored_results:
        logging.info(f"DEBUG-MODUS: Keine {label} für '{search_title}'")
        return
    
    top_n = min(limit, len(scored_results))
    logging.info(f"DEBUG-MODUS: Top-{top_n} {label} für '{search_title}':")
    for idx, (score, result) in enumerate(scored_results[:top_n], 1):
        title = result.get("title", "")
        size = result.get("size") or 0
        size_mb = size / (1024 * 1024) if size else 0
        language = detect_language(result)
        has_ad = has_audio_description(result)
        similarity = calculate_title_similarity(search_title, title)
        logging.info(
            f"  {idx}. {title} ({size_mb:.1f} MB, "
            f"Sprache: {language}, AD: {'ja' if has_ad else 'nein'}, "
            f"Score: {score:.1f}, Ähnlichkeit: {similarity:.2f})"
        )


def search_mediathek(movie_title, prefer_language="deutsch", prefer_audio_desc="egal", notify_url=None, notify_source=None, entry_link=None, year: Optional[int] = None, metadata: Dict = None, debug: bool = False):
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
    search_terms = mediathek_movie_search_terms(movie_title)
    if not search_terms:
        logging.warning("Mediathek-Suche: leerer Titel")
        return None

    logging.info(
        f"Suche in MediathekViewWeb nach Film '{movie_title}' "
        f"(Suchvarianten: {', '.join(repr(t) for t in search_terms)})"
    )

    MIN_TITLE_SIMILARITY_FOR_SCORING = 0.1
    MIN_TITLE_SIMILARITY = 0.2
    any_api_hits = False
    last_low_sim_match = None  # (titel, ähnlichkeit) für Abschluss-Log

    for api_term in search_terms:
        results = _fetch_mvw_api_movie_results(api_term)
        if not results:
            continue
        any_api_hits = True
        logging.info(
            f"Gefunden: {len(results)} API-Ergebnisse für Suchbegriff '{api_term}' "
            f"(Anfrage-Titel: '{movie_title}'), Scoring …"
        )

        scored_results = []
        filtered_count = 0
        for result in results:
            try:
                result_title = result.get("title", "")
                title_similarity = calculate_title_similarity(movie_title, result_title)

                normalized_search = movie_title.lower().strip()
                normalized_result = result_title.lower().strip()
                title_contained = normalized_search in normalized_result or normalized_result in normalized_search

                if title_similarity < MIN_TITLE_SIMILARITY_FOR_SCORING and not title_contained:
                    logging.debug(
                        f"Überspringe Ergebnis mit zu niedriger Titel-Ähnlichkeit ({title_similarity:.2f}): "
                        f"'{result_title}'"
                    )
                    filtered_count += 1
                    continue

                score = score_movie(
                    result, prefer_language, prefer_audio_desc,
                    search_title=movie_title, search_year=year, metadata=metadata
                )
                scored_results.append((score, result))
                logging.debug(
                    f"Bewertet: '{result_title}' - Ähnlichkeit: {title_similarity:.2f}, Score: {score:.1f}"
                )
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten eines Ergebnisses für '{movie_title}': {e}")
                continue

        if filtered_count > 0:
            logging.debug(
                f"{filtered_count} Ergebnisse wegen zu niedriger Titel-Ähnlichkeit herausgefiltert "
                f"(Suchbegriff '{api_term}')"
            )

        if not scored_results:
            logging.debug(f"Keine verwertbaren Treffer nach Scoring für Suchbegriff '{api_term}', nächste Variante …")
            continue

        scored_results.sort(key=lambda x: x[0], reverse=True)

        if debug:
            _log_scored_matches(scored_results, movie_title, limit=10, label="Matches")

        best_match = None
        best_score = None
        best_title = None
        title_similarity = None
        for cand_score, cand in scored_results:
            if is_promotional_or_non_episode(cand):
                logging.debug(f"Überspringe Promo/Trailer: '{cand.get('title', '')}'")
                continue
            cand_title = cand.get("title", "")
            cand_sim = calculate_title_similarity(movie_title, cand_title)
            if cand_sim < MIN_TITLE_SIMILARITY:
                continue
            best_match = cand
            best_score = cand_score
            best_title = cand_title
            title_similarity = cand_sim
            break

        if best_match is None:
            non_promo = [
                (s, r) for s, r in scored_results
                if not is_promotional_or_non_episode(r)
            ]
            if non_promo:
                first_np_title = non_promo[0][1].get("title", "")
                first_np_sim = calculate_title_similarity(movie_title, first_np_title)
                last_low_sim_match = (first_np_title, first_np_sim)
                logging.debug(
                    f"Beste Übereinstimmung für '{api_term}' zu schwach oder nur Promo "
                    f"(beste nicht-Promo: '{first_np_title}', Ähnlichkeit {first_np_sim:.2f}) — nächste Variante …"
                )
            else:
                logging.debug(
                    f"Nur Promo-/Trailer-Treffer für Suchbegriff '{api_term}', nächste Variante …"
                )
            continue

        if api_term.strip() != (movie_title or "").strip():
            logging.info(
                f"Treffer mit alternativem Suchbegriff '{api_term}' für angefragten Titel '{movie_title}'"
            )

        language = detect_language(best_match)
        has_ad = has_audio_description(best_match)
        size = best_match.get("size") or 0
        size_mb = size / (1024 * 1024) if size else 0

        logging.info(
            f"Beste Übereinstimmung gefunden: '{best_match.get('title')}' "
            f"({size_mb:.1f} MB, "
            f"Sprache: {language}, "
            f"AD: {'ja' if has_ad else 'nein'}, "
            f"Score: {best_score:.1f}, "
            f"Titel-Ähnlichkeit: {title_similarity:.2f})"
        )
        return best_match

    # Alle Varianten ohne brauchbaren Treffer
    variants_hint = ", ".join(repr(t) for t in search_terms)
    if not any_api_hits:
        logging.warning(f"Keine API-Ergebnisse für '{movie_title}' (Suchvarianten: {variants_hint})")
        if notify_source != "wishlist" and notify_url and APPRISE_AVAILABLE:
            body = "Keine Ergebnisse in der Mediathek gefunden:\n\n"
            body += f"📽️ {movie_title}\n"
            body += f"ℹ️ Versuchte Suchbegriffe: {variants_hint}\n"
            if entry_link:
                body += f"\n🔗 Blog-Eintrag: {entry_link}"
            send_notification(notify_url, "Film nicht gefunden", body, "warning")
        return None

    if last_low_sim_match:
        bt, tsim = last_low_sim_match
        logging.warning(
            f"Keine relevante Übereinstimmung für '{movie_title}': bester Kandidat '{bt}' "
            f"(Ähnlichkeit {tsim:.2f}). Suchvarianten: {variants_hint}"
        )
        if notify_source != "wishlist" and notify_url and APPRISE_AVAILABLE:
            body = "Keine relevante Übereinstimmung gefunden:\n\n"
            body += f"📽️ Gesucht: {movie_title}\n"
            body += f"❌ Bester Kandidat: {bt}\n"
            body += f"ℹ️ Titel-Ähnlichkeit zu niedrig ({tsim:.2f})\n"
            body += f"Versuchte Suchbegriffe: {variants_hint}\n"
            if entry_link:
                body += f"\n🔗 Blog-Eintrag: {entry_link}"
            send_notification(notify_url, "Keine relevante Übereinstimmung", body, "warning")
        return None

    logging.warning(
        f"Keine gültigen Ergebnisse für '{movie_title}' nach Scoring (Suchvarianten: {variants_hint})"
    )
    if notify_source != "wishlist" and notify_url and APPRISE_AVAILABLE:
        body = "Keine gültigen Ergebnisse für Film gefunden:\n\n"
        body += f"📽️ {movie_title}\n"
        body += "ℹ️ Die API lieferte Treffer, aber keine erreichten die Titel-Schwelle.\n"
        body += f"Versuchte Suchbegriffe: {variants_hint}\n"
        if entry_link:
            body += f"\n🔗 Blog-Eintrag: {entry_link}"
        send_notification(notify_url, "Suche erfolglos", body, "warning")
    return None


def list_mediathek_movie_candidates(
    movie_title: str,
    prefer_language: str = "deutsch",
    prefer_audio_desc: str = "egal",
    year: Optional[int] = None,
    metadata: Optional[Dict] = None,
    limit: int = 8,
    for_series: bool = False,
) -> List[Dict[str, Any]]:
    """
    Liefert bis zu ``limit`` Treffer aus MediathekViewWeb (absteigend nach Score),
    vergleichbar mit der Auswahl in search_mediathek, aber ohne nur den ersten Treffer
    zurückzugeben. Für Wishlist-Probe und manuelle Trefferauswahl.

    Jedes Element ist ein Dict mit: score (float), title_similarity (float), title (str), result (API-Dict).
    Leere Liste, wenn nichts Passendes gefunden wurde.

    ``for_series=True``: gleiche breite API-Suche und Filter wie ``search_mediathek_series`` (nicht
    nur Titelfeld-Suche), plus topic-gewichtete Ähnlichkeit — verhindert z. B. Doku-False-Positives.
    """
    metadata = metadata or {}

    MIN_TITLE_SIMILARITY_FOR_SCORING = 0.1
    MIN_TITLE_SIMILARITY = 0.2

    def _score_and_pack_results(results: List[Dict]) -> List[Dict[str, Any]]:
        scored_results: List[Tuple[float, Dict]] = []
        for result in results:
            try:
                result_title = result.get("title", "")
                if for_series:
                    title_similarity = calculate_title_similarity_for_series_listing(movie_title, result)
                else:
                    title_similarity = calculate_title_similarity(movie_title, result_title)
                normalized_search = movie_title.lower().strip()
                normalized_result = result_title.lower().strip()
                title_contained = normalized_search in normalized_result or normalized_result in normalized_search
                if title_similarity < MIN_TITLE_SIMILARITY_FOR_SCORING and not title_contained:
                    continue
                score = score_movie(
                    result,
                    prefer_language,
                    prefer_audio_desc,
                    search_title=movie_title,
                    search_year=year,
                    metadata=metadata,
                    use_series_listing_similarity=for_series,
                )
                scored_results.append((score, result))
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten eines Kandidaten für '{movie_title}': {e}")
                continue

        if not scored_results:
            return []

        scored_results.sort(key=lambda x: x[0], reverse=True)

        out: List[Dict[str, Any]] = []
        for cand_score, cand in scored_results:
            if is_promotional_or_non_episode(cand):
                continue
            cand_title = cand.get("title", "")
            cand_sim = (
                calculate_title_similarity_for_series_listing(movie_title, cand)
                if for_series
                else calculate_title_similarity(movie_title, cand_title)
            )
            if cand_sim < MIN_TITLE_SIMILARITY:
                continue
            out.append(
                {
                    "score": float(cand_score),
                    "title_similarity": float(cand_sim),
                    "title": cand_title,
                    "result": cand,
                }
            )
            if len(out) >= limit:
                break
        return out

    if for_series:
        normalized = _series_api_query_term(movie_title)
        raw = _fetch_mvw_api_series_raw_results(normalized)
        filtered = _filter_series_mvw_results(movie_title, normalized, raw)
        if not filtered:
            feed = _fetch_mvw_feed_results(normalized)
            filtered = _filter_series_mvw_results(movie_title, normalized, feed or [])
        return _score_and_pack_results(filtered)

    search_terms = mediathek_movie_search_terms(movie_title)
    if not search_terms:
        return []

    for api_term in search_terms:
        results = _fetch_mvw_api_movie_results(api_term)
        if not results:
            continue
        out = _score_and_pack_results(results)
        if out:
            return out

    return []


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
    title_topic = f"{title} {topic}".strip()
    text = f"{title} {topic} {description}"

    # Explizite Staffel/Episode (z. B. ONE/ARD „(S02/E01)“) vor Reihenfolge-Zähler „(1/6)“
    # und vor „Folge n“ (sonst oft fälschlich S01). Nur Titel/Topic, nicht Beschreibung.
    for chunk in (title, title_topic):
        if not chunk:
            continue
        m_paren = re.search(r"\([Ss](\d+)\s*/\s*[Ee](\d+)\)", chunk)
        if m_paren:
            season, episode = int(m_paren.group(1)), int(m_paren.group(2))
            logging.debug(
                f"Episoden-Info gefunden (Sxx/Eyy in Klammern): S{season:02d}E{episode:02d}"
            )
            return (season, episode)
        m_plain = re.search(r"[Ss](\d+)\s*/\s*[Ee](\d+)", chunk)
        if m_plain:
            season, episode = int(m_plain.group(1)), int(m_plain.group(2))
            logging.debug(
                f"Episoden-Info gefunden (Sxx/Eyy explizit Titel/Topic): S{season:02d}E{episode:02d}"
            )
            return (season, episode)

    # Früh prüfen: (X/Y) im Titel – typisch für Feeds (z. B. "Bad Banks (1/6) - ...")
    # So wird nicht versehentlich SxxExx aus der Beschreibung genommen
    title_xy = re.search(r'\((\d+)/\d+\)', title)
    if title_xy:
        episode = int(title_xy.group(1))
        season_in_title = re.search(r'(?:[Ss]taffel|[Ss]aison)\s+(\d+)', title, re.IGNORECASE)
        season = int(season_in_title.group(1)) if season_in_title else 1
        logging.debug(f"Episoden-Info gefunden (Titel X/Y): S{season:02d}E{episode:02d}")
        return (season, episode)
    
    # Pattern 1: S01E01, S1E1, S 01 E 01, S02/E01 (Schrägstrich wie bei Sendern in Klammern)
    pattern1 = re.search(r'[Ss](\d+)[\s/]*[Ee](\d+)', text)
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
    
    # Pattern 6: Nur Episode-Nummer in Klammern (X/Y) ohne Staffel-Info – nur Titel/Topic,
    # damit (1/6) o. Ä. aus der Beschreibung keine falsche Episodennummer erzeugt.
    pattern6 = re.search(r'\((\d+)/\d+\)', title_topic)
    if pattern6:
        episode = int(pattern6.group(1))
        season_match = re.search(r'(?:[Ss]taffel|[Ss]aison)\s+(\d+)', title_topic, re.IGNORECASE)
        if season_match:
            season = int(season_match.group(1))
            logging.debug(f"Episoden-Info gefunden (X/Y Format mit Kontext): S{season:02d}E{episode:02d}")
            return (season, episode)
        logging.debug(f"Episoden-Info gefunden (X/Y Format ohne Staffel, annehme S01): S01E{episode:02d}")
        return (1, episode)
    
    # Pattern 7: Episode X, Teil X, Folge X (ohne Staffel-Info)
    pattern7 = re.search(r'(?:[Ee]pisode|[Tt]eil|[Ff]olge)\s+(\d+)', text, re.IGNORECASE)
    if pattern7:
        episode = int(pattern7.group(1))
        # Versuche Staffel aus Kontext zu erkennen
        season_match = re.search(r'(?:[Ss]taffel|[Ss]aison)\s+(\d+)', text, re.IGNORECASE)
        if season_match:
            season = int(season_match.group(1))
            logging.debug(f"Episoden-Info gefunden (Episode/Teil/Folge mit Kontext): S{season:02d}E{episode:02d}")
            return (season, episode)
        # Fallback: Staffel 1 annehmen
        logging.debug(f"Episoden-Info gefunden (Episode/Teil/Folge ohne Staffel, annehme S01): S01E{episode:02d}")
        return (1, episode)
    
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


def _fetch_mvw_feed_results(query: str) -> list:
    """
    Ruft den MediathekViewWeb-Feed mit Suchbegriff ab und liefert Einträge im API-Ergebnis-Format.
    Fallback, wenn die API-Suche keine passenden Treffer liefert (Website nutzt gleichen Feed).
    """
    try:
        url = MVW_FEED_URL
        params = {"query": query, "everywhere": "true"}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        entries = getattr(feed, "entries", [])
        results = []
        for entry in entries:
            title = (entry.get("title") or "").strip()
            # Topic: Tags (Atom) oder Kategorie
            tags = entry.get("tags", [])
            topic = (tags[0].get("term", "") if tags and isinstance(tags[0], dict) else "") or (entry.get("topic", "") or "").strip()
            summary = (entry.get("summary") or entry.get("description") or "").strip()
            # Video-URL: Enclosure (RSS/Atom) oder media:content
            url_video = ""
            enclosures = entry.get("enclosures", [])
            if enclosures:
                enc = enclosures[0] if isinstance(enclosures[0], dict) else getattr(enclosures[0], "href", "")
                url_video = enc.get("href", "") if isinstance(enc, dict) else (enc or "")
            if not url_video and hasattr(entry, "links"):
                for link in entry.links:
                    if getattr(link, "rel", None) == "enclosure" or (getattr(link, "type", "") or "").startswith("video/"):
                        url_video = getattr(link, "href", "") or ""
                        break
            if not url_video:
                url_video = entry.get("link", "")
            results.append({
                "title": title,
                "topic": topic,
                "description": summary,
                "url_video": url_video,
            })
        return results
    except Exception as e:
        logging.debug(f"MediathekViewWeb-Feed fehlgeschlagen: {e}")
        return []


def _series_api_query_term(series_title: str) -> str:
    """
    Suchbegriff für Mediathek-API und Normalisierung in series_mediathek_result_matches:
    normalize_search_title, dann optionales (Jahr) am Ende entfernen („Serie (2024)“ → „Serie“).
    """
    n = normalize_search_title(series_title)
    s = re.sub(r"\s*\(\s*\d{4}\s*\)\s*$", "", n).strip()
    return s or n


def _merge_mvw_result_if_source(result: Dict) -> Dict:
    """API liefert teils _source — für score_movie/Download nach oben mergen."""
    if isinstance(result.get("_source"), dict):
        merged = {**result["_source"], **result}
        merged.pop("_source", None)
        return merged
    return result


def _fetch_mvw_api_series_raw_results(normalized_search_title: str) -> list:
    """
    Breite MediathekViewWeb-Suche (wie Website / #query), nicht nur Titelfeld.
    Zuerst Feldsuche mit großem size — reine {\"query\": ...} liefert oft irrelevante Top-Treffer
    und würde die breitere Liste verhindern (break nach erstem nicht-leeren Ergebnis).
    """
    payloads = [
        {
            "queries": [
                {"fields": ["title", "topic", "description"], "query": normalized_search_title}
            ],
            "future": False,
            "offset": 0,
            "size": 500,
        },
        {
            "queries": [
                {"fields": ["title", "topic"], "query": normalized_search_title}
            ],
            "future": False,
            "offset": 0,
            "size": 500,
        },
        {"query": normalized_search_title},
    ]
    results: List[Any] = []
    for payload in payloads:
        try:
            response = requests.post(
                MVW_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("result", {}).get("results", [])
            if results:
                logging.debug(
                    f"Serien-API: {len(results)} Roh-Einträge (Payload mit Feldsuche/query)"
                )
                break
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            logging.debug(f"Serien-API-Payload fehlgeschlagen: {e}")
            continue

    if not results:
        try:
            resp = requests.get(
                "https://mediathekviewweb.de/api/query",
                params={"query": normalized_search_title},
                headers={"Accept": "application/json"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("result", {}).get("results", [])
            if results:
                logging.debug(f"Serien-API (GET): {len(results)} Roh-Einträge")
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            logging.debug(f"Serien-API GET fehlgeschlagen: {e}")

    return results or []


def _mvw_raw_title_topic_desc(result: Dict) -> Tuple[str, str, str]:
    """Liest title/topic/description aus API-Dict inkl. _source."""
    t = result.get("title") or result.get("Title")
    if t is None and isinstance(result.get("_source"), dict):
        t = result["_source"].get("title") or result["_source"].get("Title")
    tp = result.get("topic") or result.get("Topic")
    if tp is None and isinstance(result.get("_source"), dict):
        tp = result["_source"].get("topic") or result["_source"].get("Topic")
    d = result.get("description") or result.get("Description")
    if d is None and isinstance(result.get("_source"), dict):
        d = result["_source"].get("description") or result["_source"].get("Description")
    return (t or "").strip(), (tp or "").strip(), (d or "").strip()


def _filter_series_mvw_results(
    series_title: str,
    normalized_search_title: str,
    results: list,
) -> List[Dict]:
    """Wie search_mediathek_series: nur passende Episoden, _source gemergt, ohne Promo."""
    filtered: List[Dict] = []
    for result in results:
        raw_title, raw_topic, raw_desc = _mvw_raw_title_topic_desc(result)
        if not series_mediathek_result_matches(
            series_title, normalized_search_title, raw_title, raw_topic, raw_desc
        ):
            continue
        to_append = _merge_mvw_result_if_source(result)
        if is_promotional_or_non_episode(to_append):
            continue
        filtered.append(to_append)
    return filtered


def search_mediathek_series(series_title: str, prefer_language: str = "deutsch", prefer_audio_desc: str = "egal", 
                            notify_url: Optional[str] = None, notify_source: Optional[str] = None, entry_link: Optional[str] = None, 
                            year: Optional[int] = None, metadata: Optional[Dict] = None, debug: bool = False) -> list:
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
    # Normalisiere Suchbegriff (inkl. (Jahr) für API/Matching)
    normalized_search_title = _series_api_query_term(series_title)
    if normalized_search_title != series_title.strip():
        logging.debug(f"Suchbegriff normalisiert: '{series_title}' → '{normalized_search_title}'")
    
    logging.info(f"Suche in MediathekViewWeb nach Serie: '{series_title}' (normalisiert: '{normalized_search_title}')")

    results = []
    try:
        results = _fetch_mvw_api_series_raw_results(normalized_search_title)

        if not results:
            logging.warning(f"Keine Ergebnisse gefunden für Serie '{series_title}'")
            if notify_source != "wishlist" and notify_url and APPRISE_AVAILABLE:
                body = f"Keine Ergebnisse in der Mediathek gefunden:\n\n"
                body += f"📺 {series_title}\n"
                if entry_link:
                    body += f"\n🔗 Blog-Post: {entry_link}"
                send_notification(notify_url, "Serie nicht gefunden", body, "warning")
            return []
        
        filtered_results = _filter_series_mvw_results(series_title, normalized_search_title, results)

        if not filtered_results:
            # Fallback: MediathekViewWeb-Feed (Website nutzt gleichen Feed für #query=...)
            feed_results = _fetch_mvw_feed_results(normalized_search_title)
            if feed_results:
                logging.info(f"Serien-API-Filter 0 Treffer, nutze MediathekViewWeb-Feed: {len(feed_results)} Einträge")
                filtered_results = _filter_series_mvw_results(series_title, normalized_search_title, feed_results)
            if not filtered_results:
                # Bei 0 Treffern: erste API-Ergebnisse ausgeben (INFO), damit Filter angepasst werden kann
                if results:
                    logging.info(f"Serien-Filter lieferte 0 Treffer bei {len(results)} API-Ergebnissen. Erste Titel:")
                    for i, r in enumerate(results[:5]):
                        rt, rp, _ = _mvw_raw_title_topic_desc(r)
                        logging.info(f"  [{i+1}] title={rt!r} topic={rp!r}")
                logging.warning(f"Keine Episoden für Serie '{series_title}' gefunden")
                if notify_source != "wishlist" and notify_url and APPRISE_AVAILABLE:
                    body = f"Keine Episoden für Serie gefunden:\n\n"
                    body += f"📺 {series_title}\n"
                    if entry_link:
                        body += f"\n🔗 Blog-Post: {entry_link}"
                    send_notification(notify_url, "Keine Episoden gefunden", body, "warning")
                return []
        
        # Bewerte alle Episoden
        scored_results = []
        for result in filtered_results:
            try:
                score = score_movie(
                    result,
                    prefer_language,
                    prefer_audio_desc,
                    search_title=series_title,
                    search_year=year,
                    metadata=metadata,
                    use_series_listing_similarity=True,
                )
                scored_results.append((score, result))
            except Exception as e:
                logging.debug(f"Fehler beim Bewerten einer Episode für '{series_title}': {e}")
                continue
        
        if not scored_results:
            logging.warning(f"Keine gültigen Episoden für '{series_title}' gefunden")
            return []
        
        # Sortiere nach Punktzahl (höchste zuerst)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        if debug:
            _log_scored_matches(scored_results, series_title, limit=10, label="Episoden-Matches")
        
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

def build_download_filepath(movie_data, download_dir, content_title: str, metadata: Dict, is_series: bool = False, 
                           series_base_dir: Optional[str] = None, season: Optional[int] = None, 
                           episode: Optional[int] = None, create_dirs: bool = True) -> str:
    """
    Baut den Ziel-Dateipfad für einen Download zusammen.
    """
    metadata = metadata or {}
    url = movie_data.get("url_video") or ""
    
    # Bestimme Ziel-Verzeichnis
    if is_series and series_base_dir:
        if create_dirs:
            target_dir = get_series_directory(series_base_dir, content_title, metadata.get("year"))
        else:
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', content_title)
            dir_parts = [safe_title]
            year = metadata.get("year")
            if year:
                dir_parts.append(f"({year})")
            target_dir = os.path.join(series_base_dir, " ".join(dir_parts))
        base_filename = format_episode_filename(content_title, season, episode, metadata)
    else:
        target_dir = download_dir
        base_title = content_title
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', base_title)
        filename_parts = [safe_title]
        year = metadata.get("year")
        if year:
            filename_parts.append(f"({year})")
        provider_id = metadata.get("provider_id")
        if provider_id:
            filename_parts.append(provider_id)
        base_filename = " ".join(filename_parts)
    
    # Try to guess extension
    ext = "mp4"
    if url.endswith(".mkv"):
        ext = "mkv"
    if url.endswith(".mp4"):
        ext = "mp4"
    
    filename = f"{base_filename}.{ext}"
    filepath = os.path.join(target_dir, filename)
    return filepath


def download_content(movie_data, download_dir, content_title: str, metadata: Dict, is_series: bool = False,
                     series_base_dir: Optional[str] = None, season: Optional[int] = None,
                     episode: Optional[int] = None,
                     notify_url: Optional[str] = None,
                     notify_source: Optional[str] = None):
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
        notify_url: Optional Apprise-URL; bei gesetztem ``notify_source`` werden Treffer gemeldet
            (Wishlist: Erfolg/Fehlschlag/„bereits vorhanden“; Feed/Suche: nur „bereits vorhanden“).
        notify_source: ``"wishlist"``, ``"feed"`` oder ``"search"`` — steuert Formulierung der Benachrichtigung.

    Returns:
        tuple: (success: bool, title: str, filepath: str, skipped_existing: bool)
    """
    url = movie_data.get("url_video")
    title = movie_data.get("title")
    filepath = build_download_filepath(
        movie_data,
        download_dir,
        content_title,
        metadata,
        is_series=is_series,
        series_base_dir=series_base_dir,
        season=season,
        episode=episode,
        create_dirs=True
    )

    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        file_size_mb = file_size / (1024 * 1024)
        logging.info(f"Datei bereits vorhanden, überspringe Download: '{title}' -> {filepath} ({file_size_mb:.1f} MB)")
        if notify_url and notify_source:
            icon = "📺" if is_series else "📽️"
            if notify_source == "wishlist":
                subj = "Wishlist: Übersprungen (bereits vorhanden)"
                body = (
                    "Wishlist: Die Datei existiert bereits — es wurde nichts erneut heruntergeladen.\n\n"
                    f"{icon} {title}\n"
                    f"💾 {filepath}\n"
                    f"📌 Gesucht: {content_title}"
                )
            elif notify_source == "feed":
                subj = "Download übersprungen (bereits vorhanden)"
                body = (
                    "Die Datei existiert bereits — Download wurde übersprungen.\n\n"
                    f"{icon} {title}\n"
                    f"💾 {filepath}\n"
                )
                if content_title:
                    body += f"📌 Feed-Titel: {content_title}\n"
            else:  # search
                subj = "Such-Download übersprungen (bereits vorhanden)"
                body = (
                    "Die Datei existiert bereits — es wurde nichts erneut heruntergeladen.\n\n"
                    f"{icon} {title}\n"
                    f"💾 {filepath}\n"
                    f"📌 Suchbegriff: {content_title}"
                )
            send_notification(notify_url, subj, body, "info")
        return (True, title, filepath, True)

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
        if notify_url and notify_source == "wishlist":
            icon = "📺" if is_series else "📽️"
            kind = "Episode" if is_series else "Film"
            body = (
                f"Wishlist: {kind} wurde heruntergeladen.\n\n"
                f"{icon} {title}\n"
                f"💾 {filepath}\n"
                f"📌 Wishlist-Titel: {content_title}"
            )
            if is_series and season is not None and episode is not None:
                body += f"\n📺 S{season:02d}E{episode:02d}"
            send_notification(notify_url, "Wishlist: Download erfolgreich", body, "success")
        return (True, title, filepath, False)

    except Exception as e:
        logging.error(f"Download fehlgeschlagen für '{title}': {e}")
        # Clean up partial file
        if os.path.exists(filepath):
            os.remove(filepath)
        if notify_url and notify_source == "wishlist":
            icon = "📺" if is_series else "📽️"
            body = (
                "Wishlist: Download ist fehlgeschlagen.\n\n"
                f"{icon} {title}\n"
                f"📌 Wishlist-Titel: {content_title}\n"
                f"⚠️ {e}"
            )
            send_notification(notify_url, "Wishlist: Download fehlgeschlagen", body, "error")
        return (False, title, filepath, False)


def download_by_search(
    search_term: str,
    download_dir: str,
    prefer_language: str = "deutsch",
    prefer_audio_desc: str = "egal",
    notify_url: Optional[str] = None,
    debug: bool = False,
    year: Optional[int] = None,
    tmdb_api_key: Optional[str] = None,
    omdb_api_key: Optional[str] = None,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Sucht einen Film in MediathekViewWeb per Suchbegriff (Titel) und lädt die beste
    Übereinstimmung herunter. Entspricht der Suche auf https://mediathekviewweb.de/#query=...

    Args:
        search_term: Filmtitel oder Suchbegriff (z.B. "The Quiet Girl")
        download_dir: Verzeichnis für den Download
        prefer_language: "deutsch", "englisch" oder "egal"
        prefer_audio_desc: "mit", "ohne" oder "egal"
        notify_url: Optional - Apprise-URL für Benachrichtigungen
        debug: Wenn True, wird nur gesucht, nicht heruntergeladen
        year: Optional - Erscheinungsjahr für besseres Matching
        tmdb_api_key / omdb_api_key: Optional für Metadaten

    Returns:
        Tuple (success, title, filepath). Bei "nicht gefunden" oder Fehler: (False, None, None).
    """
    if not (search_term and search_term.strip()):
        logging.warning("Download per Suchbegriff: leerer Suchbegriff.")
        return (False, None, None)

    search_term = search_term.strip()
    mvw_url = f"https://mediathekviewweb.de/#query={quote(search_term)}"
    yinfo = f", Jahr {year}" if year else ""
    logging.info(f"Download per Suchbegriff: '{search_term}'{yinfo} (entspricht Suche: {mvw_url})")

    metadata = None
    if year is not None or tmdb_api_key or omdb_api_key:
        metadata = get_metadata(search_term, year, tmdb_api_key, omdb_api_key)
        if year and not metadata.get("year"):
            metadata["year"] = year

    result = search_mediathek(
        search_term,
        prefer_language=prefer_language,
        prefer_audio_desc=prefer_audio_desc,
        notify_url=notify_url,
        entry_link=mvw_url,
        year=year,
        metadata=metadata,
        debug=debug,
    )

    if not result:
        return (False, None, None)

    meta_dl = metadata if metadata is not None else {}
    if debug:
        filepath = build_download_filepath(
            result,
            download_dir,
            search_term,
            meta_dl,
            is_series=False,
            create_dirs=False,
        )
        logging.info(f"DEBUG-MODUS: Download übersprungen: '{result.get('title')}' -> {filepath}")
        return (True, result.get("title"), filepath)

    nu = notify_url if notify_url else None
    ns = "search" if nu else None
    success, title, filepath, _skipped = download_content(
        result,
        download_dir,
        content_title=search_term,
        metadata=meta_dl,
        is_series=False,
        notify_url=nu,
        notify_source=ns,
    )
    return (success, title, filepath)


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
    parser.add_argument("--debug-no-download", action="store_true",
                      help="Debug-Modus: keine Downloads durchführen, aber Feed/Suche/Matches ausgeben")
    parser.add_argument("--search", default=None,
                       help="Film per Suchbegriff herunterladen (z.B. 'The Quiet Girl'). Kein RSS-Feed.")
    parser.add_argument("--year", type=int, default=None,
                       help="Erscheinungsjahr (optional, z.B. mit --search oder --wishlist-add)")
    parser.add_argument("--wishlist-file", default=None,
                       help="Pfad zur Wishlist-JSON (Standard: .perlentaucher_wishlist.json im Download-Ordner)")
    parser.add_argument("--wishlist-add", metavar="TITLE", default=None,
                       help="Eintrag zur Wishlist hinzufügen (beendet nach Aktion)")
    parser.add_argument("--wishlist-year", type=int, default=None,
                       help="Jahr für --wishlist-add (optional)")
    parser.add_argument("--wishlist-kind", choices=["movie", "series"], default="movie",
                       help="Typ für --wishlist-add: movie oder series")
    parser.add_argument("--wishlist-remove", metavar="ID", default=None,
                       help="Wishlist-Eintrag nach ID entfernen")
    parser.add_argument("--wishlist-list", action="store_true",
                       help="Wishlist auflisten und beenden")
    parser.add_argument("--wishlist-process", action="store_true",
                       help="Wishlist abarbeiten: bei Mediathek-Treffer herunterladen und Eintrag entfernen")
    parser.add_argument("--wishlist-web", action="store_true",
                       help="Wishlist-Web-UI (FastAPI) starten; blockiert bis Abbruch")
    parser.add_argument("--no-wishlist-web", action="store_true",
                       help="Wishlist-Web-UI nicht starten (überstimmt WISHLIST_WEB_ENABLED)")
    parser.add_argument("--wishlist-web-host", default=None,
                       help="Bind-Adresse für Wishlist-Web-UI (Default: 127.0.0.1 oder WISHLIST_WEB_HOST)")
    parser.add_argument("--wishlist-web-port", type=int, default=None,
                       help="Port für Wishlist-Web-UI (Default: 8765 oder WISHLIST_WEB_PORT)")
    
    args = parser.parse_args()
    args.activity_source = "cli"

    # Unterstützung für Umgebungsvariablen
    args.tmdb_api_key = args.tmdb_api_key or os.environ.get('TMDB_API_KEY')
    args.omdb_api_key = args.omdb_api_key or os.environ.get('OMDB_API_KEY')

    from src.wishlist_core import default_wishlist_path
    args.wishlist_path = args.wishlist_file or os.environ.get("WISHLIST_FILE") or default_wishlist_path(args.download_dir)
    
    setup_logging(args.loglevel)
    
    # Version beim Start ausgeben
    logging.info(f"Perlentaucher v{__version__}")
    
    # Prüfe auf Updates
    check_for_updates(__version__)
    
    if not os.path.exists(args.download_dir):
        try:
            os.makedirs(args.download_dir)
            logging.info(f"Download-Verzeichnis erstellt: {args.download_dir}")
        except OSError as e:
            logging.critical(f"Could not create download directory {args.download_dir}: {e}")
            sys.exit(1)

    logging.info(f"Präferenzen: Sprache={args.sprache}, Audiodeskription={args.audiodeskription}")
    if args.debug_no_download:
        logging.info("DEBUG-MODUS aktiv: Downloads werden übersprungen.")

    state_file = None if args.no_state else args.state_file
    if state_file:
        logging.info(f"Status-Datei: {state_file}")

    def _env_truthy(name: str) -> bool:
        v = (os.environ.get(name) or "").strip().lower()
        return v in ("1", "true", "yes", "on")

    wishlist_web_start = (
        (args.wishlist_web or _env_truthy("WISHLIST_WEB_ENABLED"))
        and not args.no_wishlist_web
    )
    if wishlist_web_start:
        host = args.wishlist_web_host or os.environ.get("WISHLIST_WEB_HOST") or "127.0.0.1"
        port = (
            args.wishlist_web_port
            if args.wishlist_web_port is not None
            else int(os.environ.get("WISHLIST_WEB_PORT", "8765"))
        )
        token = os.environ.get("WISHLIST_WEB_TOKEN")
        args.activity_source = "web"
        from src.wishlist_web import run_server
        run_server(
            host=host,
            port=port,
            wishlist_path=args.wishlist_path,
            download_dir=args.download_dir,
            token=token,
            cli_args=args,
        )
        sys.exit(0)

    if args.wishlist_list:
        from src.wishlist_core import list_items
        items = list_items(args.wishlist_path)
        for it in items:
            y = it.year if it.year is not None else ""
            print(f"{it.id}\t{it.title}\t{y}\t{it.kind}")
        sys.exit(0)

    if args.wishlist_add:
        from src.wishlist_core import add_item
        item = add_item(
            args.wishlist_path,
            args.wishlist_add.strip(),
            args.wishlist_year,
            args.wishlist_kind,
        )
        logging.info(f"Wishlist: hinzugefügt {item.id} — {item.title} ({item.kind})")
        log_activity_event(
            args.download_dir,
            "wishlist_add",
            item.title,
            f"Kind: {item.kind}, ID {item.id}",
            "info",
            "cli",
        )
        sys.exit(0)

    if args.wishlist_remove:
        from src.wishlist_core import remove_item
        if not remove_item(args.wishlist_path, args.wishlist_remove.strip()):
            logging.error("Wishlist: ID nicht gefunden.")
            sys.exit(1)
        logging.info("Wishlist: Eintrag entfernt.")
        log_activity_event(args.download_dir, "wishlist_remove", args.wishlist_remove.strip(), "", "info", "cli")
        sys.exit(0)

    if args.wishlist_process:
        from src.wishlist_core import process_wishlist_items
        processed, successes = process_wishlist_items(args.wishlist_path, args, remove_on_success=True)
        logging.info(f"Wishlist: verarbeitet {processed}, erfolgreiche Downloads {successes}")
        # Exit 0: leere Wishlist (0,0) oder jeder Eintrag erfolgreich entfernt (processed == successes).
        # Exit 1: mindestens ein Eintrag ohne erfolgreichen Abschluss (Monitoring/Docker).
        if processed != successes:
            logging.warning(
                "Wishlist: nicht alle Einträge erfolgreich abgeschlossen "
                f"({successes}/{processed} mit Download entfernt)."
            )
            sys.exit(1)
        sys.exit(0)

    # Download per Suchbegriff (ohne RSS-Feed)
    if args.search:
        success, title, filepath = download_by_search(
            args.search,
            args.download_dir,
            prefer_language=args.sprache,
            prefer_audio_desc=args.audiodeskription,
            notify_url=args.notify,
            debug=args.debug_no_download,
            year=args.year,
            tmdb_api_key=args.tmdb_api_key,
            omdb_api_key=args.omdb_api_key,
        )
        if success:
            logging.info(f"Download per Suchbegriff abgeschlossen: {title} -> {filepath}")
            log_activity_event(
                args.download_dir,
                "such_download",
                args.search,
                f"→ {filepath}" if filepath else "",
                "success",
                "search",
            )
        else:
            logging.warning("Download per Suchbegriff: Film nicht gefunden oder Fehler.")
            log_activity_event(
                args.download_dir,
                "such_download",
                args.search,
                "Kein Treffer oder Fehler",
                "warning",
                "search",
            )
        sys.exit(0 if success else 1)

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
                                         notify_url=args.notify, entry_link=entry_link, year=year, metadata=metadata, 
                                         debug=args.debug_no_download)
                if result:
                    # Extrahiere Episode-Info für Dateinamen
                    season, episode = extract_episode_info(result, movie_title)
                    # Bestimme series_base_dir
                    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
                    if args.debug_no_download:
                        filepath = build_download_filepath(
                            result,
                            args.download_dir,
                            movie_title,
                            metadata,
                            is_series=True,
                            series_base_dir=series_base_dir,
                            season=season,
                            episode=episode,
                            create_dirs=False
                        )
                        logging.info(f"DEBUG-MODUS: Download übersprungen: '{result.get('title')}' -> {filepath}")
                        continue
                    nu = args.notify if args.notify else None
                    ns = "feed" if nu else None
                    success, title, filepath, _skipped = download_content(
                        result, args.download_dir, movie_title, metadata,
                        is_series=True, series_base_dir=series_base_dir,
                        season=season, episode=episode,
                        notify_url=nu, notify_source=ns,
                    )
                    # Markiere Eintrag als verarbeitet nach Download-Versuch
                    if state_file:
                        status = 'download_success' if success else 'download_failed'
                        filename = os.path.basename(filepath) if filepath else None
                        save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, 
                                           filename=filename, is_series=True)
                        logging.debug(f"Eintrag als verarbeitet markiert: '{entry.title}' (Status: {status})")
                    # RSS-Feed: keine separaten Erfolgs-/Fehler-Pushes (notify_source=feed in download_content:
                    # nur Benachrichtigung bei „Datei bereits vorhanden“).
                    log_activity_event(
                        args.download_dir,
                        "feed_download",
                        movie_title,
                        f"Serie (erste Folge): {'OK' if success else 'Fehler'} — {title or ''}",
                        "success" if success else "error",
                        "feed",
                    )
                else:
                    logging.warning(f"Überspringe Serie '{movie_title}' - nicht in der Mediathek gefunden.")
                    if state_file:
                        save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title, is_series=True)
                    log_activity_event(
                        args.download_dir,
                        "feed_download",
                        movie_title,
                        "Serie: nicht in Mediathek",
                        "warning",
                        "feed",
                    )
                    continue
            elif args.serien_download == "staffel":
                # Lade alle Episoden der Staffel
                episodes = search_mediathek_series(movie_title, prefer_language=args.sprache, 
                                                  prefer_audio_desc=args.audiodeskription,
                                                  notify_url=args.notify, entry_link=entry_link, 
                                                  year=year, metadata=metadata, debug=args.debug_no_download)
                if episodes:
                    # Bestimme series_base_dir
                    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
                    
                    # Sortiere Episoden nach Staffel/Episode und dedupliziere
                    # Verwende Dictionary um nur die beste Version jeder Episode zu behalten
                    episodes_dict = {}  # Key: (season, episode), Value: (score, episode_data)
                    episodes_without_info = []  # Episoden ohne erkennbare S/E – Fallback-Nummer vergeben
                    
                    for episode_data in episodes:
                        season, episode_num = extract_episode_info(episode_data, movie_title)
                        if season is None or episode_num is None:
                            episodes_without_info.append(episode_data)
                            continue
                        
                        score = score_movie(
                            episode_data,
                            args.sprache,
                            args.audiodeskription,
                            search_title=movie_title,
                            search_year=year,
                            metadata=metadata,
                            use_series_listing_similarity=True,
                        )
                        episode_key = (season, episode_num)
                        if episode_key not in episodes_dict or score > episodes_dict[episode_key][0]:
                            episodes_dict[episode_key] = (score, episode_data)
                    
                    # Fallback: Episoden ohne S/E nicht verwerfen – als Staffel 1 fortlaufend nummerieren
                    if episodes_without_info:
                        max_ep_s1 = max((e for (s, e) in episodes_dict if s == 1), default=0)
                        for i, episode_data in enumerate(episodes_without_info):
                            fallback_ep = max_ep_s1 + 1 + i
                            score = score_movie(
                                episode_data,
                                args.sprache,
                                args.audiodeskription,
                                search_title=movie_title,
                                search_year=year,
                                metadata=metadata,
                                use_series_listing_similarity=True,
                            )
                            key = (1, fallback_ep)
                            if key not in episodes_dict or score > episodes_dict[key][0]:
                                episodes_dict[key] = (score, episode_data)
                        if episodes_without_info:
                            logging.info(f"{len(episodes_without_info)} Episoden ohne Staffel/Episode-Info als S01E{max_ep_s1 + 1}+ nummeriert")
                    
                    # Konvertiere Dictionary zu Liste und sortiere
                    episodes_with_info = [(s, e, data) for (s, e), (score, data) in episodes_dict.items()]
                    episodes_with_info.sort(key=lambda x: (x[0] or 0, x[1] or 0))
                    
                    total_episodes = len(episodes_with_info)
                    downloaded_count = 0
                    failed_count = 0
                    
                    # Analysiere gefundene Episoden nach Staffel
                    episodes_by_season = {}
                    for season, episode, _ in episodes_with_info:
                        if season:
                            if season not in episodes_by_season:
                                episodes_by_season[season] = []
                            episodes_by_season[season].append(episode)
                    
                    # Logge Episoden-Statistik
                    logging.info(f"Gefundene Episoden für '{movie_title}': {total_episodes} Episoden")
                    for season in sorted(episodes_by_season.keys()):
                        episodes = sorted(episodes_by_season[season])
                        missing = []
                        if len(episodes) > 0:
                            max_ep = max(episodes)
                            for ep in range(1, max_ep + 1):
                                if ep not in episodes:
                                    missing.append(ep)
                        if missing:
                            logging.warning(f"Staffel {season}: Episoden {missing} fehlen (gefunden: {episodes})")
                        else:
                            logging.info(f"Staffel {season}: {len(episodes)} Episoden gefunden (E{min(episodes) if episodes else 0}-E{max(episodes) if episodes else 0})")
                    
                    logging.info(f"Starte Download von {total_episodes} Episoden für '{movie_title}'")
                    
                    if args.debug_no_download:
                        logging.info(f"DEBUG-MODUS: Staffel-Download übersprungen ({total_episodes} Episoden)")
                        for season, episode_num, episode_data in episodes_with_info:
                            if season is None or episode_num is None:
                                continue
                            filepath = build_download_filepath(
                                episode_data,
                                args.download_dir,
                                movie_title,
                                metadata,
                                is_series=True,
                                series_base_dir=series_base_dir,
                                season=season,
                                episode=episode_num,
                                create_dirs=False
                            )
                            logging.info(
                                f"  - S{season:02d}E{episode_num:02d}: "
                                f"{episode_data.get('title', 'Unbekannt')} -> {filepath}"
                            )
                        continue
                    
                    # Zähle Episoden ohne Staffel/Episode-Info
                    skipped_episodes = []
                    for season, episode_num, episode_data in episodes_with_info:
                        if season is None or episode_num is None:
                            title = episode_data.get('title', 'Unbekannt')
                            skipped_episodes.append(title)
                            continue
                        
                        nu = args.notify if args.notify else None
                        ns = "feed" if nu else None
                        success, title, filepath, _sk = download_content(
                            episode_data, args.download_dir, movie_title, metadata,
                            is_series=True, series_base_dir=series_base_dir,
                            season=season, episode=episode_num,
                            notify_url=nu, notify_source=ns,
                        )
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
                    
                    # Logge übersprungene Episoden
                    if skipped_episodes:
                        logging.warning(f"{len(skipped_episodes)} Episoden konnten nicht verarbeitet werden (keine Staffel/Episode-Info):")
                        for title in skipped_episodes[:10]:  # Zeige nur erste 10
                            logging.warning(f"  - {title}")
                        if len(skipped_episodes) > 10:
                            logging.warning(f"  ... und {len(skipped_episodes) - 10} weitere")
                    
                    # Markiere Haupt-Eintrag als verarbeitet
                    if state_file:
                        status = 'download_success' if downloaded_count > 0 else 'download_failed'
                        episodes_list = [f"S{s:02d}E{e:02d}" for s, e, _ in episodes_with_info if s is not None and e is not None]
                        save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, 
                                            is_series=True, episodes=episodes_list)
                    # RSS-Feed: keine Staffel-Zusammenfassung per Push (nur „bereits vorhanden“ pro Episode in download_content).
                    st_lvl = "success" if downloaded_count > 0 else "error"
                    log_activity_event(
                        args.download_dir,
                        "feed_download",
                        movie_title,
                        f"Staffel: {downloaded_count}/{total_episodes} Episoden OK, {failed_count} fehlgeschlagen",
                        st_lvl,
                        "feed",
                    )
                    continue
                else:
                    # Keine Episoden gefunden
                    if state_file:
                        save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title, is_series=True)
                    log_activity_event(
                        args.download_dir,
                        "feed_download",
                        movie_title,
                        "Staffel: keine Episoden gefunden",
                        "warning",
                        "feed",
                    )
                    continue
        else:
            # Normale Film-Verarbeitung
            result = search_mediathek(movie_title, prefer_language=args.sprache, prefer_audio_desc=args.audiodeskription, 
                                     notify_url=args.notify, entry_link=entry_link, year=year, metadata=metadata, 
                                     debug=args.debug_no_download)
            if result:
                if args.debug_no_download:
                    filepath = build_download_filepath(
                        result,
                        args.download_dir,
                        movie_title,
                        metadata,
                        is_series=False,
                        create_dirs=False
                    )
                    logging.info(f"DEBUG-MODUS: Download übersprungen: '{result.get('title')}' -> {filepath}")
                    continue
                nu = args.notify if args.notify else None
                ns = "feed" if nu else None
                success, title, filepath, _skipped = download_content(
                    result, args.download_dir, movie_title, metadata, is_series=False,
                    notify_url=nu, notify_source=ns,
                )
                # Markiere Eintrag als verarbeitet nach Download-Versuch
                if state_file:
                    status = 'download_success' if success else 'download_failed'
                    filename = os.path.basename(filepath) if filepath else None
                    save_processed_entry(state_file, entry_id, status=status, movie_title=movie_title, filename=filename)
                    logging.debug(f"Eintrag als verarbeitet markiert: '{entry.title}' (Status: {status})")
                # RSS-Feed: keine separaten Erfolgs-/Fehler-Pushes (notify_source=feed in download_content:
                # nur Benachrichtigung bei „Datei bereits vorhanden“).
                log_activity_event(
                    args.download_dir,
                    "feed_download",
                    movie_title,
                    f"Film: {'OK' if success else 'Fehler'} — {title or ''}",
                    "success" if success else "error",
                    "feed",
                )
            else:
                logging.warning(f"Überspringe '{movie_title}' - nicht in der Mediathek gefunden.")
                # Auch nicht gefundene Filme als verarbeitet markieren, damit sie nicht immer wieder versucht werden
                if state_file:
                    save_processed_entry(state_file, entry_id, status='not_found', movie_title=movie_title)
                    logging.debug(f"Eintrag als verarbeitet markiert (Film nicht gefunden): '{entry.title}'")
                # Hinweis: Benachrichtigung wird bereits in search_mediathek() gesendet
                log_activity_event(
                    args.download_dir,
                    "feed_download",
                    movie_title,
                    "Film: nicht in Mediathek",
                    "warning",
                    "feed",
                )

if __name__ == "__main__":
    main()
