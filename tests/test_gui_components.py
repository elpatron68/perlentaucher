"""
Tests für GUI-Komponenten.
Verwendet pytest-qt für Qt-spezifische Tests.
Nur ausführen wenn PyQt6 und pytest-qt verfügbar sind.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Füge Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Prüfe ob PyQt6 und pytest-qt verfügbar sind
try:
    import PyQt6
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

try:
    import pytest_qt
    HAS_PYTEST_QT = True
except ImportError:
    HAS_PYTEST_QT = False

# Überspringe alle GUI-Tests wenn PyQt6 oder pytest-qt nicht verfügbar sind
if not HAS_PYQT6 or not HAS_PYTEST_QT:
    pytest.skip("PyQt6 oder pytest-qt nicht verfügbar - GUI-Tests werden übersprungen", allow_module_level=True)


@pytest.fixture
def qtbot(qtbot):
    """QtBot Fixture für GUI-Tests."""
    return qtbot


@pytest.mark.gui
class TestConfigManager:
    """Tests für ConfigManager."""
    
    def test_config_manager_init(self, temp_config_file):
        """Test: ConfigManager Initialisierung."""
        from gui.config_manager import ConfigManager
        
        config_manager = ConfigManager(temp_config_file)
        assert config_manager is not None
        assert config_manager.config is not None
    
    def test_config_manager_get_default(self, temp_config_file):
        """Test: ConfigManager gibt Standard-Werte zurück."""
        from gui.config_manager import ConfigManager
        
        config_manager = ConfigManager(temp_config_file)
        assert config_manager.get('download_dir') == './downloads'
        assert config_manager.get('loglevel') == 'INFO'
    
    def test_config_manager_update(self, temp_config_file):
        """Test: ConfigManager kann Werte aktualisieren."""
        from gui.config_manager import ConfigManager
        
        config_manager = ConfigManager(temp_config_file)
        config_manager.update({'download_dir': '/custom/path'})
        
        assert config_manager.get('download_dir') == '/custom/path'
    
    def test_config_manager_save(self, temp_config_file):
        """Test: ConfigManager kann speichern."""
        from gui.config_manager import ConfigManager
        
        config_manager = ConfigManager(temp_config_file)
        config_manager.update({'download_dir': '/test/path'})
        result = config_manager.save()
        
        assert result is True
        # Prüfe ob Datei existiert
        from pathlib import Path
        assert Path(temp_config_file).exists()


@pytest.mark.gui
@pytest.mark.slow
class TestBlogListPanel:
    """Tests für BlogListPanel - erfordert Qt-Application."""
    
    @pytest.fixture(autouse=True)
    def setup_qt_app(self, qapp):
        """Setup Qt-Application für Tests."""
        self.app = qapp
    
    @patch('feedparser.parse')
    @patch('requests.get')
    def test_load_rss_feed_success(self, mock_requests_get, mock_feedparse, temp_config_file):
        """Test: RSS-Feed erfolgreich laden."""
        from gui.blog_list_panel import BlogListPanel
        from gui.config_manager import ConfigManager
        
        # Mock Feed
        mock_feed = Mock()
        mock_feed.entries = [Mock(title='Test Entry', link='http://test.com')]
        mock_feedparse.return_value = mock_feed
        
        # Mock requests
        mock_response = Mock()
        mock_response.content = b'<rss></rss>'
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_requests_get.return_value = mock_response
        
        config_manager = ConfigManager(temp_config_file)
        panel = BlogListPanel(config_manager)
        
        # Test sollte ohne Fehler durchlaufen
        assert panel is not None
    
    @patch('requests.get')
    def test_load_rss_feed_ssl_error(self, mock_requests_get, temp_config_file, qapp):
        """Test: SSL-Fehler beim RSS-Feed-Laden."""
        from gui.blog_list_panel import BlogListPanel
        from gui.config_manager import ConfigManager
        from requests.exceptions import SSLError
        
        # Mock SSL-Fehler
        mock_requests_get.side_effect = SSLError("SSL certificate verification failed")
        
        config_manager = ConfigManager(temp_config_file)
        panel = BlogListPanel(config_manager)
        
        # Panel sollte trotzdem initialisiert werden
        assert panel is not None
        
        # Feed-Laden sollte fehlschlagen, aber GUI sollte nicht abstürzen
        # (wird in _load_rss_feed behandelt)
    
    @patch('requests.get')
    def test_load_rss_feed_network_error(self, mock_requests_get, temp_config_file, qapp):
        """Test: Netzwerkfehler beim RSS-Feed-Laden."""
        from gui.blog_list_panel import BlogListPanel
        from gui.config_manager import ConfigManager
        from requests.exceptions import ConnectionError
        
        # Mock Netzwerkfehler
        mock_requests_get.side_effect = ConnectionError("Failed to establish connection")
        
        config_manager = ConfigManager(temp_config_file)
        panel = BlogListPanel(config_manager)
        
        assert panel is not None


@pytest.mark.gui
class TestFeedParserHelpers:
    """Tests für FeedParser-Helper-Funktionen."""
    
    def test_get_entry_attr_exists(self):
        """Test: Extraktion von existierendem Attribut."""
        from gui.utils.feedparser_helpers import get_entry_attr
        
        entry = Mock()
        entry.title = 'Test Title'
        
        result = get_entry_attr(entry, 'title')
        assert result == 'Test Title'
    
    def test_get_entry_attr_missing(self):
        """Test: Extraktion von fehlendem Attribut."""
        from gui.utils.feedparser_helpers import get_entry_attr
        
        entry = Mock()
        del entry.title
        
        result = get_entry_attr(entry, 'title', 'Default')
        assert result == 'Default'
    
    def test_get_entry_attr_none(self):
        """Test: Extraktion von None-Wert."""
        from gui.utils.feedparser_helpers import get_entry_attr
        
        entry = Mock()
        entry.title = None
        
        result = get_entry_attr(entry, 'title', 'Default')
        assert result == 'Default'
