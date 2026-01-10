# Test-Suite für Perlentaucher

Diese Test-Suite verwendet `pytest` für Unit-Tests und Integrationstests.

## Setup

Installiere die Test-Dependencies:

```bash
pip install -r requirements.txt
```

Die Test-Dependencies sind bereits in `requirements.txt` enthalten:
- `pytest>=7.0.0` - Test-Framework
- `pytest-cov>=4.0.0` - Coverage-Analyse
- `pytest-mock>=3.10.0` - Mock-Support
- `pytest-qt>=4.2.0` - Qt/GUI-Tests
- `responses>=0.23.0` - HTTP-Response-Mocking

## Tests ausführen

### Alle Tests
```bash
pytest
```

### Nur Unit-Tests (ohne GUI/Netzwerk)
```bash
pytest -m "not gui and not slow and not network"
```

### Mit Coverage-Report
```bash
pytest --cov=. --cov=perlentaucher --cov=gui --cov-report=html --cov-report=term-missing
```

### Spezifische Test-Datei
```bash
pytest tests/test_rss_feed.py
```

### Verbose Output
```bash
pytest -v
```

## Test-Struktur

- `tests/test_rss_feed.py` - Tests für RSS-Feed-Laden (SSL, Netzwerkfehler, etc.)
- `tests/test_core_functions.py` - Tests für Core-Funktionalität
- `tests/test_gui_components.py` - Tests für GUI-Komponenten (mit pytest-qt)
- `tests/conftest.py` - Pytest-Konfiguration und gemeinsame Fixtures

## Test-Marker

Tests können mit Markierungen versehen werden:
- `@pytest.mark.slow` - Tests die länger dauern
- `@pytest.mark.integration` - Integrationstests
- `@pytest.mark.unit` - Unit-Tests
- `@pytest.mark.gui` - GUI-Tests
- `@pytest.mark.network` - Tests die Netzwerkzugriff benötigen

## CI/CD Integration

Die Tests werden automatisch in GitHub Actions ausgeführt:
- Bei jedem Push auf `master`
- Vor jedem Build bei Git Tags
- Auf allen unterstützten Python-Versionen (3.9-3.12)

## Coverage-Ziele

Aktuelles Coverage-Ziel: **30%** (kann schrittweise erhöht werden)

Kritische Bereiche die getestet werden sollten:
- ✅ RSS-Feed-Laden (SSL, Netzwerkfehler)
- ✅ Config-Management
- ✅ Core-Parsing-Funktionen
- ⏳ GUI-Komponenten (teilweise)
- ⏳ Download-Funktionalität
- ⏳ MediathekViewWeb-Integration

## Bekannte Einschränkungen

- GUI-Tests benötigen eine Qt-Application (werden in CI möglicherweise übersprungen)
- Netzwerk-Tests werden gemockt (keine echten HTTP-Requests)
- Plattformspezifische Tests (macOS, Windows) werden nur in CI ausgeführt
