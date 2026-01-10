#!/bin/bash
# Hilfs-Script zum Generieren von Release Notes aus Git Commits
# Kann optional OpenRouter API für AI-basierte Zusammenfassung verwenden

LAST_TAG="$1"
NEW_TAG="$2"
OPENROUTER_API_KEY="${3:-}"
OPENROUTER_MODEL="${4:-anthropic/claude-3.5-sonnet}"

if [ -z "$LAST_TAG" ] || [ -z "$NEW_TAG" ]; then
    echo "Usage: $0 <last_tag> <new_tag> [openrouter_api_key] [model]"
    exit 1
fi

# Hole Commits zwischen den Tags (oder seit letztem Tag)
if [ -n "$LAST_TAG" ]; then
    commit_range="${LAST_TAG}..HEAD"
else
    # Falls kein letzter Tag, verwende letzten 100 Commits
    commit_range="HEAD~100..HEAD"
    echo "Kein letzter Tag gefunden, verwende letzte 100 Commits" >&2
fi

commits=$(git log "$commit_range" --pretty=format:"%h|%s|%b" --no-merges 2>&1)

# Prüfe auf Git-Fehler
if echo "$commits" | grep -q "fatal:"; then
    echo "Fehler beim Abrufen der Commits: $commits" >&2
    commits=""
fi

if [ -z "$commits" ] || [ -z "$(echo "$commits" | grep -v '^$')" ]; then
    echo "Keine Commits gefunden zwischen $LAST_TAG und HEAD" >&2
    cat <<EOF
# Release $NEW_TAG

## Änderungen

Keine Änderungen seit dem letzten Release.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/$NEW_TAG)
EOF
    exit 0
fi

# Zähle Commits (filtere leere Zeilen)
commit_count=$(echo "$commits" | grep -v "^$" | wc -l | tr -d ' ')
if [ -z "$commit_count" ] || [ "$commit_count" = "0" ]; then
    echo "Keine Commits gefunden zwischen $LAST_TAG und HEAD" >&2
    cat <<EOF
# Release $NEW_TAG

## Änderungen

Keine Commits gefunden seit dem letzten Release.

---

**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/elpatron/perlentaucher/commits/$NEW_TAG)
EOF
    exit 0
fi

echo "Gefundene Commits: $commit_count" >&2

# Generiere Release Notes
release_notes=""

if [ -n "$OPENROUTER_API_KEY" ]; then
    # Verwende OpenRouter API für AI-basierte Zusammenfassung
    echo "Generiere Release Notes mit AI (OpenRouter)..." >&2
    
    # Erstelle Commits-Text für Prompt (verwende temporäre Datei wegen Subshell-Problem)
    commits_text_file=$(mktemp)
    echo "$commits" | while IFS='|' read -r hash subject body; do
        if [ -n "$hash" ] && [ -n "$subject" ]; then
            echo "- ${subject}" >> "$commits_text_file"
            if [ -n "$body" ]; then
                echo "  ${body}" >> "$commits_text_file"
            fi
        fi
    done
    commits_text=$(cat "$commits_text_file")
    rm -f "$commits_text_file"
    
    prompt=$(cat <<PROMPT
Erstelle strukturierte Release Notes für ein Python-Projekt basierend auf folgenden Git Commits seit dem letzten Release:

${commits_text}

Kategorisiere die Commits in:
- Neue Features
- Verbesserungen
- Bugfixes
- Technische Änderungen

Format: Markdown, strukturiert, prägnant, auf Deutsch.
Beginne mit: "# Release $NEW_TAG"
PROMPT
)
    
    # API Request an OpenRouter
    api_url="https://openrouter.ai/api/v1/chat/completions"
    
    # Verwende jq falls verfügbar für JSON, sonst manuell
    if command -v jq &> /dev/null; then
        json_data=$(jq -n \
            --arg model "$OPENROUTER_MODEL" \
            --arg prompt "$prompt" \
            '{
                model: $model,
                messages: [{role: "user", content: $prompt}],
                temperature: 0.7,
                max_tokens: 2000
            }')
    else
        # Manuelles JSON (mit Escape)
        prompt_escaped=$(printf '%s' "$prompt" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed ':a;N;$!ba;s/\n/\\n/g')
        json_data="{\"model\":\"$OPENROUTER_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"$prompt_escaped\"}],\"temperature\":0.7,\"max_tokens\":2000}"
    fi
    
    response=$(printf '%s' "$json_data" | curl -s -w "\n%{http_code}" -X POST \
        -H "Authorization: Bearer $OPENROUTER_API_KEY" \
        -H "Content-Type: application/json" \
        -H "HTTP-Referer: https://codeberg.org/elpatron/perlentaucher" \
        --data-binary @- \
        "$api_url" 2>/dev/null)
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ] && [ -n "$response_body" ]; then
        # Extrahiere Content aus JSON Response
        if command -v jq &> /dev/null; then
            release_notes=$(echo "$response_body" | jq -r '.choices[0].message.content' 2>/dev/null)
        else
            # Fallback: manuelles Parsing (vereinfacht)
            release_notes=$(echo "$response_body" | grep -o '"content":"[^"]*"' | head -1 | sed 's/"content":"//' | sed 's/"$//' | sed 's/\\n/\n/g')
        fi
        
        if [ -n "$release_notes" ]; then
            # Extrahiere Codeberg Repository-Informationen
            codeberg_url=$(git remote get-url origin 2>&1 || echo "")
            codeberg_repo="elpatron/perlentaucher"
            if [[ $codeberg_url =~ codeberg\.org[/:]([^/]+)/([^/]+?)(\.git)?$ ]]; then
                codeberg_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
            fi
            
            release_notes="${release_notes}"$'\n\n'"---"$'\n\n'"**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/$codeberg_repo/commits/$NEW_TAG)"
            echo "✓ Release Notes erfolgreich mit AI generiert" >&2
        else
            echo "⚠ Fehler: Konnte Content aus AI-Response nicht extrahieren" >&2
            OPENROUTER_API_KEY=""  # Fallback
        fi
    else
        echo "⚠ Fehler bei AI-Generierung (HTTP $http_code)" >&2
        echo "Response: $response_body" >&2
        echo "Verwende Fallback-Methode..." >&2
        OPENROUTER_API_KEY=""  # Fallback
    fi
fi

if [ -z "$OPENROUTER_API_KEY" ] || [ -z "$release_notes" ]; then
    # Manuelle Generierung ohne AI
    echo "Generiere Release Notes manuell..." >&2
    
    features=()
    improvements=()
    bugfixes=()
    technical=()
    other=()
    
    # Parse und kategorisiere Commits
    while IFS='|' read -r hash subject body; do
        if [ -z "$hash" ] || [ -z "$subject" ]; then
            continue
        fi
        
        # Kategorisiere basierend auf Commit-Message-Patterns
        if echo "$subject" | grep -qE '^(feat|feature|add|Neue|neue|Add|add):'; then
            features+=("- $subject")
        elif echo "$subject" | grep -qE '^(fix|bugfix|bug|Fix|fix|Behebe|behebe):'; then
            bugfixes+=("- $subject")
        elif echo "$subject" | grep -qE '^(refactor|tech|chore|build|ci|Refactor|refactor|Technical|technical):'; then
            technical+=("- $subject")
        elif echo "$subject" | grep -qE '^(improve|enhance|perf|update|Improve|improve|Verbessere|verbessere):'; then
            improvements+=("- $subject")
        else
            other+=("- $subject")
        fi
    done <<< "$commits"
    
    # Erstelle Release Notes
    release_notes="# Release $NEW_TAG"$'\n\n'
    
    if [ ${#features[@]} -gt 0 ]; then
        release_notes+="## Neue Features"$'\n\n'
        release_notes+=$(printf '%s\n' "${features[@]}")$'\n\n'
    fi
    
    if [ ${#improvements[@]} -gt 0 ]; then
        release_notes+="## Verbesserungen"$'\n\n'
        release_notes+=$(printf '%s\n' "${improvements[@]}")$'\n\n'
    fi
    
    if [ ${#bugfixes[@]} -gt 0 ]; then
        release_notes+="## Bugfixes"$'\n\n'
        release_notes+=$(printf '%s\n' "${bugfixes[@]}")$'\n\n'
    fi
    
    if [ ${#technical[@]} -gt 0 ]; then
        release_notes+="## Technische Änderungen"$'\n\n'
        release_notes+=$(printf '%s\n' "${technical[@]}")$'\n\n'
    fi
    
    if [ ${#other[@]} -gt 0 ]; then
        release_notes+="## Weitere Änderungen"$'\n\n'
        release_notes+=$(printf '%s\n' "${other[@]}")$'\n\n'
    fi
    
    # Fallback: Wenn keine Kategorisierung, liste alle Commits
    if [ ${#features[@]} -eq 0 ] && [ ${#improvements[@]} -eq 0 ] && [ ${#bugfixes[@]} -eq 0 ] && [ ${#technical[@]} -eq 0 ] && [ ${#other[@]} -eq 0 ]; then
        release_notes+="## Änderungen"$'\n\n'
        while IFS='|' read -r hash subject body; do
            if [ -n "$hash" ] && [ -n "$subject" ]; then
                release_notes+="- $subject"$'\n'
            fi
        done <<< "$commits"
        release_notes+=$'\n'
    fi
    
    # Extrahiere Codeberg Repository-Informationen
    codeberg_url=$(git remote get-url origin 2>&1 || echo "")
    codeberg_repo="elpatron/perlentaucher"
    if [[ $codeberg_url =~ codeberg\.org[/:]([^/]+)/([^/]+?)(\.git)?$ ]]; then
        codeberg_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
    fi
    
    release_notes+="---"$'\n\n'"**Vollständige Änderungsliste:** Siehe [Git Commits](https://codeberg.org/$codeberg_repo/commits/$NEW_TAG)"
fi

echo "$release_notes"
