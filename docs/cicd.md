# CI/CD

Das Projekt verwendet Codeberg Actions (Forgejo Actions) für automatische Tests. Die Pipeline wird bei jedem Push und Pull Request ausgeführt.

## Aktivierung auf Codeberg

**Wichtig:** Actions müssen für dein Repository aktiviert sein:

1. Gehe zu deinem Repository auf Codeberg
2. Öffne die **Einstellungen** (Settings)
3. Navigiere zu **Units** > **Overview**
4. Aktiviere **Actions** (falls noch nicht aktiviert)

## Runner einrichten

Codeberg bietet keine gehosteten Runner. Du musst einen selbstgehosteten Runner einrichten:

1. Lade den [Forgejo Runner](https://codeberg.org/forgejo/runner/releases) herunter
2. Registriere den Runner mit dem Label `self-hosted`:
   ```bash
   ./forgejo-runner register --name myrunner --labels self-hosted
   ```
3. Starte den Runner:
   ```bash
   ./forgejo-runner daemon
   ```

Die Workflow-Datei befindet sich in `.github/workflows/test.yml` und testet das Script mit Python 3.9-3.12.

## Empfohlen: Woodpecker CI

Da die Einrichtung eines selbstgehosteten Runners aufwendig ist, wird **Woodpecker CI** empfohlen. Eine `.woodpecker.yml` Konfiguration ist bereits vorhanden:

1. Stelle einen Antrag bei [Codeberg Community](https://codeberg.org/Codeberg/Community/issues)
2. Aktiviere dein Repository auf [ci.codeberg.org](https://ci.codeberg.org)

Woodpecker CI ist einfacher zu nutzen und erfordert keine eigene Runner-Einrichtung.

