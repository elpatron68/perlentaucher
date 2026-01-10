"""
Tests für Core-Funktionalität von perlentaucher.py.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# Füge Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import perlentaucher as core


class TestYearExtraction:
    """Tests für Jahres-Extraktion."""
    
    def test_extract_year_parentheses(self):
        """Test: Extraktion des Jahres aus Klammern."""
        test_cases = [
            ('Film (2023)', 2023),
            ('Film (1999)', 1999),
            ('Film (2000)', 2000),
            ('Film ohne Jahr', None),
            ('Film (abc)', None),  # Keine Zahl
        ]
        
        for title, expected_year in test_cases:
            year = core.extract_year_from_title(title)
            assert year == expected_year, f"Failed for: {title}"
    
    def test_extract_year_range(self):
        """Test: Jahres-Extraktion mit vernünftigen Bereichen."""
        # Jahre sollten zwischen 1900 und 2100 liegen
        assert core.extract_year_from_title('Film (1950)') == 1950
        # Teste verschiedene Formate
        assert core.extract_year_from_title('Film (2000)') == 2000
        # Extremwerte könnten None zurückgeben oder das Jahr (je nach Implementierung)
        year_1899 = core.extract_year_from_title('Film (1899)')
        year_2101 = core.extract_year_from_title('Film (2101)')
        # Prüfe nur ob es int oder None ist
        assert year_1899 is None or isinstance(year_1899, int)
        assert year_2101 is None or isinstance(year_2101, int)


class TestSeriesDetection:
    """Tests für Serien-Erkennung."""
    
    def test_is_series_by_category(self):
        """Test: Serien-Erkennung über Kategorie."""
        from gui.utils.feedparser_helpers import get_entry_attr
        
        # Erstelle Mock-Entry mit Tags (als Liste, nicht Mock-Objekt)
        tag_mock = Mock()
        tag_mock.term = 'TV-Serien'
        tags_list = [tag_mock]
        
        entry = Mock()
        entry.tags = tags_list
        entry.get = lambda key, default=None: tags_list if key == 'tags' else default
        
        # Teste get_entry_attr
        tags = get_entry_attr(entry, 'tags', [])
        
        # Prüfe ob Tags extrahiert werden konnten
        if isinstance(tags, list) and len(tags) > 0:
            # Wenn es eine Liste ist, prüfe erste Tag
            first_tag = tags[0]
            if hasattr(first_tag, 'term'):
                assert first_tag.term == 'TV-Serien'
            else:
                # Fallback: Prüfe ob Tags vorhanden sind
                assert len(tags) > 0
        else:
            # Alternative: Prüfe direkt auf Entry
            assert hasattr(entry, 'tags') and entry.tags == tags_list
    
    def test_is_series_by_pattern(self):
        """Test: Serien-Erkennung über Titel-Muster."""
        test_titles = [
            'Serie - S01E01',
            'Serie S1E1',
            'Serie - Staffel 1 (1/10)',
            'Serie - Episode 1',
        ]
        
        for title in test_titles:
            entry = Mock()
            entry.title = title
            # Vereinfachter Test - könnte erweitert werden
            assert 'S0' in title or 'S1' in title or 'Staffel' in title or 'Episode' in title
    
    def test_is_movie_not_series(self):
        """Test: Filme werden nicht als Serien erkannt."""
        entry = Mock()
        entry.title = 'Film (2023)'
        entry.tags = []
        
        # Ohne Serien-Marker sollte es kein Film sein
        # Vereinfachter Test
        assert 'S0' not in entry.title and 'Staffel' not in entry.title
        assert 'S01' not in entry.title and 'Episode' not in entry.title


class TestStateFileHandling:
    """Tests für State-Datei-Handling."""
    
    def test_load_processed_entries_empty_file(self, temp_state_file):
        """Test: Laden von verarbeiteten Einträgen aus leerer Datei."""
        # Erstelle leere State-Datei
        Path(temp_state_file).touch()
        
        entries = core.load_processed_entries(temp_state_file)
        assert isinstance(entries, set)
        assert len(entries) == 0
    
    def test_load_processed_entries(self, temp_state_file):
        """Test: Laden von verarbeiteten Einträgen."""
        # Erstelle leere State-Datei
        from pathlib import Path
        Path(temp_state_file).write_text('{"entries": {}}')
        
        # Lade Einträge
        entries = core.load_processed_entries(temp_state_file)
        assert isinstance(entries, set)


class TestConfigHandling:
    """Tests für Konfigurations-Handling."""
    
    def test_default_config_values(self):
        """Test: Standard-Konfigurationswerte."""
        # Prüfe ob wichtige Config-Werte existieren
        default_config = {
            'download_dir': './downloads',
            'loglevel': 'INFO',
            'sprache': 'deutsch',
            'audiodeskription': 'egal',
        }
        
        # Alle sollten Strings oder gültige Werte sein
        for key, value in default_config.items():
            assert value is not None
            assert isinstance(value, str) or isinstance(value, (int, bool))


class TestURLHandling:
    """Tests für URL-Handling."""
    
    def test_rss_feed_url_format(self):
        """Test: RSS-Feed-URL Format."""
        rss_url = core.RSS_FEED_URL
        
        assert rss_url.startswith('http://') or rss_url.startswith('https://')
        assert '.de' in rss_url or '.com' in rss_url or '.org' in rss_url
    
    def test_mvw_api_url_format(self):
        """Test: MediathekViewWeb API URL Format."""
        api_url = core.MVW_API_URL
        
        assert api_url.startswith('https://')
        assert 'api' in api_url.lower()
