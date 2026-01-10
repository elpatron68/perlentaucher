"""
Update-Checker für die GUI-Anwendung.
Prüft, ob eine neuere Version auf Codeberg verfügbar ist.
"""
from typing import Optional, Tuple
import sys
import os
import requests
import semver

# Füge Root-Verzeichnis zum Python-Pfad hinzu
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

try:
    import _version
    CURRENT_VERSION = _version.__version__
except ImportError:
    CURRENT_VERSION = "unknown"


def check_for_updates(current_version: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Prüft, ob eine neuere Version auf Codeberg verfügbar ist.
    
    Args:
        current_version: Die aktuelle Version (optional, verwendet _version.__version__ wenn None)
    
    Returns:
        Tuple (is_update_available: bool, latest_version: Optional[str], download_url: Optional[str])
        - is_update_available: True wenn eine neuere Version verfügbar ist
        - latest_version: Die neueste verfügbare Version (z.B. "v0.1.26")
        - download_url: URL zum Download der neuesten Version
    """
    if current_version is None:
        current_version = CURRENT_VERSION
    
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
            return (False, None, None)
        
        # Entferne "v" Präfix für semver-Vergleich
        latest_tag_clean = latest_tag_raw.lstrip('v')
        current_clean = current_version.lstrip('v')
        
        # Überspringe Prüfung wenn aktuelle Version "unknown" ist
        if current_clean == "unknown" or not latest_tag_clean:
            return (False, None, None)
        
        # Versionsvergleich mit semver
        try:
            comparison = semver.compare(current_clean, latest_tag_clean)
            if comparison < 0:
                # Neuere Version verfügbar
                download_url = f"https://codeberg.org/elpatron/Perlentaucher/releases/tag/{latest_tag_raw}"
                return (True, latest_tag_raw, download_url)
            elif comparison == 0:
                # Aktuelle Version ist die neueste
                return (False, latest_tag_raw, None)
            else:
                # Aktuelle Version ist neuer (z.B. Entwicklung), keine Meldung nötig
                return (False, latest_tag_raw, None)
        except ValueError:
            # Semver-Vergleich fehlgeschlagen (ungültige Version)
            return (False, None, None)
            
    except requests.exceptions.RequestException:
        # Netzwerk-Fehler (keine Internetverbindung, API-Fehler, etc.)
        return (False, None, None)
    except Exception:
        # Andere Fehler (JSON-Parsing, etc.)
        return (False, None, None)
