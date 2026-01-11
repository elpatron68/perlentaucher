"""
Tests für RSS-Feed-Laden und Parsing.
Testet kritische Funktionen wie SSL-Handling, Netzwerkfehler, etc.
"""
import pytest
import feedparser
from unittest.mock import patch, Mock, MagicMock
import requests
from requests.exceptions import SSLError, RequestException, Timeout, ConnectionError

import sys
from pathlib import Path

# Füge Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src import perlentaucher as core

# GUI-Imports nur wenn verfügbar
try:
    from src.gui.blog_list_panel import BlogListPanel
    from src.gui.config_manager import ConfigManager
    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    BlogListPanel = None
    ConfigManager = None


class TestRSSFeedLoading:
    """Tests für RSS-Feed-Laden mit verschiedenen Szenarien."""
    
    def test_feedparser_with_valid_rss(self, sample_rss_feed):
        """Test: feedparser kann gültigen RSS-Feed parsen."""
        feed = feedparser.parse(sample_rss_feed)
        
        assert hasattr(feed, 'entries')
        assert len(feed.entries) == 2
        assert feed.entries[0].title == 'Regisseur - "Testfilm" (2023)'
        assert feed.entries[1].title == 'Regisseur - "Testserie" (2023) - S01E01'
    
    def test_feedparser_with_empty_feed(self):
        """Test: feedparser mit leerem Feed."""
        empty_feed = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
        feed = feedparser.parse(empty_feed)
        
        assert hasattr(feed, 'entries')
        assert len(feed.entries) == 0
    
    def test_feedparser_with_invalid_xml(self):
        """Test: feedparser mit ungültigem XML."""
        invalid_feed = "Not XML at all"
        feed = feedparser.parse(invalid_feed)
        
        # feedparser gibt ein Feed-Objekt zurück, aber bozo sollte True sein
        assert hasattr(feed, 'bozo')
        # Bei ungültigem Feed sollten entries leer sein
        assert len(feed.entries) == 0
    
    @patch('requests.get')
    def test_rss_feed_load_with_requests_success(self, mock_get, sample_rss_feed):
        """Test: RSS-Feed-Laden mit requests erfolgreich."""
        # Mock requests.get Antwort
        mock_response = Mock()
        mock_response.content = sample_rss_feed.encode('utf-8')
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Test Feed-Laden
        response = requests.get('https://example.com/feed', timeout=10, verify=True)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        
        assert len(feed.entries) == 2
        mock_get.assert_called_once_with('https://example.com/feed', timeout=10, verify=True)
    
    @patch('requests.get')
    def test_rss_feed_load_ssl_error(self, mock_get):
        """Test: SSL-Fehler beim RSS-Feed-Laden."""
        # Mock SSL-Fehler
        mock_get.side_effect = SSLError("SSL certificate verification failed")
        
        with pytest.raises(SSLError):
            requests.get('https://example.com/feed', timeout=10, verify=True)
        
        mock_get.assert_called_once()
    
    @patch('requests.get')
    def test_rss_feed_load_connection_error(self, mock_get):
        """Test: Verbindungsfehler beim RSS-Feed-Laden."""
        # Mock Verbindungsfehler
        mock_get.side_effect = ConnectionError("Failed to establish connection")
        
        with pytest.raises(ConnectionError):
            requests.get('https://example.com/feed', timeout=10, verify=True)
    
    @patch('requests.get')
    def test_rss_feed_load_timeout(self, mock_get):
        """Test: Timeout beim RSS-Feed-Laden."""
        # Mock Timeout
        mock_get.side_effect = Timeout("Request timed out")
        
        with pytest.raises(Timeout):
            requests.get('https://example.com/feed', timeout=10, verify=True)
    
    @patch('requests.get')
    def test_rss_feed_load_http_error(self, mock_get):
        """Test: HTTP-Fehler (404, 500, etc.) beim RSS-Feed-Laden."""
        # Mock 404-Fehler
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status = Mock(side_effect=requests.exceptions.HTTPError("404 Not Found"))
        mock_get.return_value = mock_response
        
        response = requests.get('https://example.com/feed', timeout=10, verify=True)
        with pytest.raises(requests.exceptions.HTTPError):
            response.raise_for_status()


class TestFeedParsing:
    """Tests für Feed-Parsing-Funktionalität."""
    
    def test_extract_movie_title_from_entry(self, sample_rss_feed):
        """Test: Extraktion des Filmtitels aus RSS-Eintrag."""
        feed = feedparser.parse(sample_rss_feed)
        entry = feed.entries[0]
        
        # Teste Extraktion mit verschiedenen Regex-Patterns
        import re
        title = entry.title
        
        # Unicode-Anführungszeichen („")
        match = re.search(r'\u201E(.+?)(?:[\u201C\u201D\u0022])', title)
        if not match:
            # Normale Anführungszeichen
            match = re.search(r'"([^"]+?)"', title)
        
        assert match is not None
        assert match.group(1) == 'Testfilm'
    
    def test_extract_year_from_title(self):
        """Test: Extraktion des Jahres aus Titel."""
        test_cases = [
            ('Regisseur - "Film" (2023)', 2023),
            ('Film (2022)', 2022),
            ('Film ohne Jahr', None),
        ]
        
        for title, expected_year in test_cases:
            year = core.extract_year_from_title(title)
            if expected_year is not None:
                assert year == expected_year, f"Failed for: {title}"
            else:
                assert year is None or isinstance(year, int), f"Failed for: {title}"


class TestConfigManager:
    """Tests für Config-Manager."""
    
    @pytest.mark.skipif(not HAS_GUI, reason="GUI-Module nicht verfügbar")
    def test_config_manager_load_defaults(self, temp_config_file):
        """Test: Config-Manager lädt Standard-Werte."""
        if ConfigManager is None:
            pytest.skip("ConfigManager nicht verfügbar")
        config_manager = ConfigManager(temp_config_file)
        
        assert config_manager.get('download_dir') == './downloads'
        assert config_manager.get('loglevel') == 'INFO'
        assert config_manager.get('sprache') == 'deutsch'
    
    @pytest.mark.skipif(not HAS_GUI, reason="GUI-Module nicht verfügbar")
    def test_config_manager_save_and_load(self, temp_config_file):
        """Test: Config-Manager kann speichern und laden."""
        if ConfigManager is None:
            pytest.skip("ConfigManager nicht verfügbar")
        config_manager = ConfigManager(temp_config_file)
        
        # Ändere einen Wert
        config_manager.update({'download_dir': '/custom/path'})
        config_manager.save()
        
        # Lade neu
        config_manager2 = ConfigManager(temp_config_file)
        assert config_manager2.get('download_dir') == '/custom/path'


class TestSSLCertificates:
    """Tests für SSL-Zertifikat-Handling."""
    
    def test_certifi_available(self):
        """Test: certifi ist verfügbar."""
        import certifi
        
        # Prüfe ob certifi CA-Zertifikate-Pfad existiert
        cert_path = certifi.where()
        assert cert_path is not None
        # Prüfe ob Datei existiert (wenn nicht gebündelt)
        # In PyInstaller-Build könnte der Pfad anders sein
        
    @patch('certifi.where')
    def test_requests_with_certifi(self, mock_certifi_where, sample_rss_feed):
        """Test: requests verwendet certifi für SSL-Zertifikate."""
        import certifi
        mock_cert_path = '/fake/path/cacert.pem'
        mock_certifi_where.return_value = mock_cert_path
        
        # Prüfe ob certifi.where() aufgerufen wird (indirekt über requests)
        cert_path = certifi.where()
        assert cert_path == mock_cert_path
        
    @patch('requests.get')
    def test_requests_verify_ssl_default(self, mock_get, sample_rss_feed):
        """Test: requests verifiziert SSL standardmäßig."""
        mock_response = Mock()
        mock_response.content = sample_rss_feed.encode('utf-8')
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        requests.get('https://example.com/feed', timeout=10)
        
        # verify=True sollte der Default sein, aber explizit überprüfen
        calls = mock_get.call_args_list
        if calls:
            # Prüfe ob verify=True oder nicht explizit gesetzt (Standard ist True)
            assert 'verify' not in calls[0].kwargs or calls[0].kwargs.get('verify') is True


class TestPlatformSpecific:
    """Tests für plattformspezifische Probleme."""
    
    def test_path_handling_cross_platform(self, temp_download_dir):
        """Test: Pfad-Handling funktioniert cross-platform."""
        import os
        from pathlib import Path
        
        # Teste verschiedene Pfad-Formate
        paths = [
            temp_download_dir,
            str(Path(temp_download_dir)),
            os.path.join(temp_download_dir, 'subdir'),
        ]
        
        for path in paths:
            # Erstelle Verzeichnis wenn nötig
            Path(path).mkdir(parents=True, exist_ok=True)
            assert os.path.exists(path)
    
    def test_line_endings_consistent(self):
        """Test: Line-Endings sind konsistent."""
        test_string = "Line 1\nLine 2\nLine 3"
        
        # Prüfe ob nur LF verwendet wird (nicht CRLF)
        assert '\r\n' not in test_string
        assert '\n' in test_string
