# Automatische Release Notes Generierung

Die Release-Scripts können automatisch Release Notes aus Git Commits generieren. Dies kann optional mit AI-Unterstützung (OpenRouter) erfolgen.

## Funktionsweise

### Ohne AI (Standard)

Die Release-Scripts (`release.ps1` / `release.sh`) sammeln automatisch alle Commits seit dem letzten Release-Tag und kategorisieren sie basierend auf Commit-Message-Patterns:

- **Neue Features**: `feat:`, `feature:`, `add:`, `Neue:`, etc.
- **Bugfixes**: `fix:`, `bugfix:`, `bug:`, `Fix:`, `Behebe:`, etc.
- **Verbesserungen**: `improve:`, `enhance:`, `perf:`, `update:`, `Verbessere:`, etc.
- **Technische Änderungen**: `refactor:`, `tech:`, `chore:`, `build:`, `ci:`, etc.
- **Weitere Änderungen**: Alle anderen Commits

### Mit AI (Optional)

Mit einem OpenRouter API Key können die Release Notes automatisch von einer AI (z.B. Claude 3.5 Sonnet) zusammengefasst werden. Die AI kategorisiert die Commits intelligent und erstellt strukturierte Release Notes auf Deutsch.

## Setup

### OpenRouter API Key (Optional)

1. Erstelle einen Account bei [OpenRouter](https://openrouter.ai/)
2. Erstelle einen API Key in den Einstellungen
3. Speichere den API Key in einer der folgenden Varianten:

#### Option 1: Umgebungsvariable (Empfohlen)

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY = "sk-or-v1-..."
```

**Linux/macOS (Bash):**
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

#### Option 2: .env Datei

Erstelle eine `.env` Datei im `scripts/` Verzeichnis:

```env
OPENROUTER_API_KEY=sk-or-v1-...
```

Die Scripts lesen automatisch aus dieser Datei.

## Verwendung

### Automatisch beim Release

Wenn du `scripts/release.ps1` oder `scripts/release.sh` ausführst, werden automatisch Release Notes generiert:

1. **Prüfung**: Existiert bereits eine Release Notes Datei (`docs/release-notes/RELEASE_NOTES_<version>.md`)?
   - **Ja**: Verwende die vorhandene Datei
   - **Nein**: Generiere neue Release Notes

2. **Generierung**:
   - Falls `OPENROUTER_API_KEY` gesetzt ist: Verwende AI für Zusammenfassung
   - Sonst: Verwende manuelle Kategorisierung basierend auf Commit-Patterns

3. **Speichern**: Die generierten Release Notes werden in `docs/release-notes/RELEASE_NOTES_<version>.md` gespeichert

4. **Bearbeitung**: Du kannst die generierte Datei vor dem Release noch bearbeiten

5. **Verwendung**: Die Release Notes werden automatisch für GitHub und Codeberg Releases verwendet

### Manuell testen

**PowerShell:**
```powershell
# Ohne AI
.\scripts\get_release_notes.ps1 -LastTag "v0.1.18" -NewTag "v0.1.19"

# Mit AI
.\scripts\get_release_notes.ps1 -LastTag "v0.1.18" -NewTag "v0.1.19" -OpenRouterApiKey "sk-or-v1-..."

# Mit anderem Model
.\scripts\get_release_notes.ps1 -LastTag "v0.1.18" -NewTag "v0.1.19" -OpenRouterApiKey "sk-or-v1-..." -OpenRouterModel "openai/gpt-4"
```

**Bash:**
```bash
# Ohne AI
./scripts/get_release_notes.sh "v0.1.18" "v0.1.19"

# Mit AI
./scripts/get_release_notes.sh "v0.1.18" "v0.1.19" "sk-or-v1-..."

# Mit anderem Model
./scripts/get_release_notes.sh "v0.1.18" "v0.1.19" "sk-or-v1-..." "openai/gpt-4"
```

## Unterstützte AI Models

Standard-Model: `anthropic/claude-3.5-sonnet`

Weitere verfügbare Models:
- `openai/gpt-4`
- `openai/gpt-4-turbo`
- `anthropic/claude-3-opus`
- `anthropic/claude-3-haiku`
- `meta-llama/llama-3-70b-instruct`
- ... und viele mehr auf [OpenRouter Models](https://openrouter.ai/models)

## Commit-Message Konventionen

Für beste Ergebnisse bei manueller Kategorisierung, verwende konventionelle Commit-Messages:

```
feat: Neue Funktion hinzufügen
fix: Bug beheben
improve: Performance verbessern
refactor: Code umstrukturieren
chore: Wartungsarbeiten
build: Build-System ändern
ci: CI/CD ändern
```

## Beispiel Output

**Ohne AI:**
```markdown
# Release v0.1.19

## Neue Features

- feat: Add comprehensive test suite

## Bugfixes

- fix: SSL certificate handling in Linux GUI

## Technische Änderungen

- refactor: Improve error handling in RSS feed loading
- ci: Add tests to GitHub Actions workflow
```

**Mit AI:**
```markdown
# Release v0.1.19

## Neue Features

- Umfassende Test-Suite implementiert: Automatisierte Tests für RSS-Feed-Laden, Core-Funktionalität und GUI-Komponenten mit pytest und Coverage-Analyse

## Verbesserungen

- Verbesserte SSL/Netzwerk-Fehlerbehandlung mit benutzerfreundlichen Fehlermeldungen und Lösungshinweisen

## Bugfixes

- SSL-Zertifikatsproblem im Linux GUI behoben: certifi wird jetzt korrekt gebündelt

## Technische Änderungen

- GitHub Actions Workflow erweitert: Tests laufen automatisch vor jedem Build
- Code-Coverage erhöht: 11.94% (Ziel: 10% erreicht)
```

## Troubleshooting

### "get_release_notes.ps1 nicht gefunden"

Stelle sicher, dass das Script im `scripts/` Verzeichnis liegt und ausführbar ist.

**Windows:** Scripts sollten automatisch ausführbar sein.

**Linux/macOS:**
```bash
chmod +x scripts/get_release_notes.sh
```

### AI-Generierung schlägt fehl

1. Prüfe ob der API Key korrekt gesetzt ist:
   ```bash
   echo $OPENROUTER_API_KEY
   ```

2. Prüfe ob du Credits auf OpenRouter hast

3. Prüfe ob das gewählte Model verfügbar ist

4. Bei Fehlern: Fallback zu manueller Generierung erfolgt automatisch

### Keine Commits gefunden

- Stelle sicher, dass zwischen dem letzten Tag und HEAD Commits existieren
- Prüfe mit: `git log <last_tag>..HEAD --oneline`

### Encoding-Probleme

Die Scripts verwenden UTF-8 Encoding. Bei Problemen:
- Stelle sicher, dass deine Terminal-Encoding UTF-8 ist
- Für PowerShell: `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
- Für Bash: `export LANG=en_US.UTF-8`
