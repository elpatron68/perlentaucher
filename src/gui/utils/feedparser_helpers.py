"""
Hilfs-Funktionen für feedparser Entry-Objekte.
Macht feedparser Entry-Objekte kompatibel mit Dictionary-ähnlichem Zugriff.
"""
from typing import Any, Optional


def get_entry_attr(entry: Any, attr: str, default: Optional[Any] = None) -> Any:
    """
    Hilfs-Funktion um Attribute aus feedparser Entry-Objekten zu holen.
    Unterstützt sowohl Dictionary-ähnliche Objekte (.get()) als auch Attribut-Zugriff.
    
    Args:
        entry: feedparser Entry-Objekt
        attr: Attribut-Name
        default: Standardwert wenn nicht gefunden
        
    Returns:
        Attribut-Wert oder default
    """
    # Versuche zuerst .get() Methode (Dictionary-ähnlich)
    if hasattr(entry, 'get'):
        try:
            return entry.get(attr, default)
        except (TypeError, AttributeError):
            pass
    
    # Fallback: Attribut-Zugriff
    if hasattr(entry, attr):
        value = getattr(entry, attr, default)
        return value if value is not None else default
    
    # Fallback: Dictionary-Zugriff mit []
    try:
        return entry[attr]
    except (KeyError, TypeError):
        return default


class EntryDict(dict):
    """
    Wrapper-Klasse um feedparser Entry-Objekt Dictionary-ähnlich zu machen.
    Macht Entry-Objekte kompatibel mit Funktionen die .get() erwarten.
    """
    
    def __init__(self, entry: Any, title: str, tags: list):
        """
        Initialisiert den EntryDict Wrapper.
        
        Args:
            entry: Originales feedparser Entry-Objekt
            title: Titel des Eintrags
            tags: Liste von Tags/Kategorien
        """
        self.entry = entry
        self._title = title
        self._tags = tags
        # Initialisiere dict mit Werten
        super().__init__({
            'title': title,
            'tags': tags
        })
    
    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """
        Gibt einen Wert zurück (Dictionary-ähnlich).
        
        Args:
            key: Der Schlüssel
            default: Standardwert wenn nicht gefunden
            
        Returns:
            Der Wert oder default
        """
        # Prüfe zuerst unsere gespeicherten Werte
        if key == 'title':
            return self._title
        elif key == 'tags':
            return self._tags
        
        # Versuche auch original entry
        return get_entry_attr(self.entry, key, default)
    
    def __getitem__(self, key: str) -> Any:
        """
        Unterstützt auch [] Zugriff.
        
        Args:
            key: Der Schlüssel
            
        Returns:
            Der Wert
            
        Raises:
            KeyError: Wenn Key nicht gefunden
        """
        # Prüfe zuerst unsere gespeicherten Werte
        if key in self:
            return super().__getitem__(key)
        
        # Versuche original entry
        value = get_entry_attr(self.entry, key)
        if value is None and key not in ['title', 'tags']:
            raise KeyError(key)
        return value


def make_entry_compatible(entry: Any) -> EntryDict:
    """
    Erstellt ein kompatibles EntryDict-Objekt aus einem feedparser Entry.
    
    Args:
        entry: feedparser Entry-Objekt
        
    Returns:
        EntryDict-Objekt mit .get() Unterstützung
    """
    title = get_entry_attr(entry, 'title', '')
    tags = get_entry_attr(entry, 'tags', [])
    return EntryDict(entry, title, tags)
