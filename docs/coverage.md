# Test-Coverage (Kern vs. vollständig)

Perlentaucher nutzt **zwei Coverage-Konfigurationen**, damit die Mindestabdeckung (`--cov-fail-under`) für den **Kern-Code ohne Qt-GUI** sinnvoll bleibt. Die GUI wird in den Standardläufen aus der Messung ausgeschlossen; für Analysen inklusive GUI gibt es eine separate Konfiguration.

## Konfigurationsdateien


| Datei                                           | Zweck                                                                                                                                                                                                      |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `[.coveragerc](../.coveragerc)`                 | Standard für `pytest`: `source = src`, aber **ohne** `src/gui/*` und ohne `src/perlentaucher_gui.py`. Enthält `exclude_lines` für typische Nicht-Mess-Zeilen (`pragma: no cover`, `if TYPE_CHECKING:`, …). |
| `[coveragerc-full.ini](../coveragerc-full.ini)` | Misst **alles** unter `src`, **inklusive** GUI. Keine `omit`-Regeln.                                                                                                                                       |
| `[pytest.ini](../pytest.ini)`                   | Verwendet standardmäßig `--cov=src` mit `--cov-config=.coveragerc` und `--cov-fail-under=30`.                                                                                                              |


## Standard: Tests mit Kern-Coverage

Im Projektroot:

```bash
python -m pytest
```

Damit gelten die Einträge aus `pytest.ini` (u. a. Terminal-Report, HTML unter `htmlcov/`, XML als `coverage.xml`). Die Schwelle **30 %** bezieht sich auf die **ohne GUI** gemessene Abdeckung.

## Vollständiger Report inklusive GUI

Um alle Pakete unter `src` zu messen (inkl. GUI), die Coverage-Konfiguration explizit überschreiben:

```bash
python -m pytest --cov=src --cov-config=coveragerc-full.ini
```

Optional nur HTML (zusätzlich zu den in `pytest.ini` gesetzten Reports):

```bash
python -m pytest --cov=src --cov-config=coveragerc-full.ini --cov-report=html
```

Hinweis: `--cov-fail-under` aus `pytest.ini` gilt weiter; bei einem vollen Lauf kann die gemessene Quote niedriger sein, weil die GUI mitzählt. Zum lokalen Vergleich kannst du die Schwelle einmalig aussetzen:

```bash
python -m pytest --cov=src --cov-config=coveragerc-full.ini --cov-fail-under=0
```

## Ausgaben

- **HTML:** Verzeichnis `htmlcov/` (übersichtliche Zeilenabdeckung im Browser).
- **XML:** `coverage.xml` (u. a. für CI-Tools oder IDEs).

Pfade beziehen sich auf das Projektroot nach einem Lauf mit den Reports aus `pytest.ini`.