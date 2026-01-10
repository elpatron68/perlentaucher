"""
Pytest-Konfiguration und gemeinsame Fixtures.
"""
import pytest
import sys
import os
from pathlib import Path

# Füge Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Prüfe ob PyQt6 verfügbar ist
try:
    import PyQt6
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

# Prüfe ob pytest-qt verfügbar ist (benötigt PyQt6)
try:
    import pytest_qt
    HAS_PYTEST_QT = True
except (ImportError, Exception):
    HAS_PYTEST_QT = False

# Registriere Marker für PyQt6-Verfügbarkeit
def pytest_configure(config):
    """Registriert Marker für PyQt6-Verfügbarkeit."""
    config.addinivalue_line("markers", "gui: GUI-Tests (benötigen PyQt6)")
    config.addinivalue_line("markers", "has_pyqt6: Marker für PyQt6-Verfügbarkeit")
    
    # Wenn PyQt6 nicht verfügbar ist, überspringe GUI-Tests standardmäßig
    if not HAS_PYQT6:
        # Setze default marker expression um GUI-Tests zu überspringen
        if not hasattr(config.option, 'markexpr') or not config.option.markexpr:
            config.option.markexpr = 'not gui'


@pytest.fixture
def temp_config_file(tmp_path):
    """Erstellt eine temporäre Konfigurationsdatei."""
    config_file = tmp_path / ".perlentaucher_config.json"
    return str(config_file)


@pytest.fixture
def temp_state_file(tmp_path):
    """Erstellt eine temporäre State-Datei."""
    state_file = tmp_path / ".perlentaucher_state.json"
    return str(state_file)


@pytest.fixture
def temp_download_dir(tmp_path):
    """Erstellt ein temporäres Download-Verzeichnis."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return str(download_dir)


@pytest.fixture
def sample_rss_feed():
    """Beispiel-RSS-Feed XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
    <channel>
        <title>Test Feed</title>
        <link>https://example.com</link>
        <description>Test RSS Feed</description>
        <item>
            <title>Regisseur - "Testfilm" (2023)</title>
            <link>https://example.com/testfilm</link>
            <pubDate>Mon, 01 Jan 2023 12:00:00 +0000</pubDate>
            <guid>https://example.com/testfilm</guid>
            <category>Film</category>
        </item>
        <item>
            <title>Regisseur - "Testserie" (2023) - S01E01</title>
            <link>https://example.com/testserie-s01e01</link>
            <pubDate>Mon, 01 Jan 2023 13:00:00 +0000</pubDate>
            <guid>https://example.com/testserie-s01e01</guid>
            <category>TV-Serien</category>
        </item>
    </channel>
</rss>"""
