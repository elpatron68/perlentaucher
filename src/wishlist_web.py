"""
Wishlist-Web-UI (FastAPI): CRUD + Verarbeitung für Headless/Konsolen-Nutzung.
"""
from __future__ import annotations

import argparse
import html
import logging
import os
import subprocess
import sys
from typing import Any, Optional

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import FileResponse, HTMLResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn
except ImportError:
    FastAPI = None  # type: ignore
    FileResponse = None  # type: ignore
    StaticFiles = None  # type: ignore

from src.wishlist_activity import (
    append_activity,
    clear_activity,
    query_activity,
    resolve_activity_path,
    summarize_probe_for_log,
)
from src.wishlist_core import (
    WishlistItem,
    WishlistKind,
    add_item,
    check_wishlist_availability,
    default_wishlist_path,
    list_items,
    process_one_wishlist_item,
    process_wishlist_items,
    probe_wishlist_item,
    remove_item,
)

logger = logging.getLogger(__name__)

# Projektroot/…/src/wishlist_web.py → Projektroot/assets (Icons, Logo)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_PROJECT_ROOT, "assets")

if BaseModel is not None:

    class WishlistItemIn(BaseModel):
        title: str
        year: Optional[int] = None
        kind: str = "movie"
        note: str = ""

else:

    class WishlistItemIn:  # type: ignore
        pass


def build_process_args_from_env(download_dir: Optional[str] = None) -> Any:
    """Minimal args für process_wishlist_items (Docker/Umgebung)."""
    a = type("_Args", (), {})()
    a.sprache = os.environ.get("SPRACHE", "deutsch")
    a.audiodeskription = os.environ.get("AUDIODESKRIPTION", "egal")
    a.serien_download = os.environ.get("SERIEN_DOWNLOAD", "erste")
    a.tmdb_api_key = os.environ.get("TMDB_API_KEY")
    a.omdb_api_key = os.environ.get("OMDB_API_KEY")
    a.notify = os.environ.get("NOTIFY")
    a.debug_no_download = os.environ.get("DEBUG_NO_DOWNLOAD", "").lower() in ("1", "true", "yes")
    a.download_dir = download_dir or os.environ.get("DOWNLOAD_DIR") or os.getcwd()
    a.serien_dir = os.environ.get("SERIEN_DIR")
    a.no_state = os.environ.get("NO_STATE", "").lower() in ("1", "true", "yes")
    a.state_file = os.environ.get("STATE_FILE", ".perlentaucher_state.json")
    a.activity_source = "web"
    ff = os.environ.get("FFMPEG_PATH")
    a.ffmpeg_path = ff.strip() if ff and ff.strip() else None
    return a


def _git_describe_footer_string() -> Optional[str]:
    """
    Git-Referenz für den Footer: ``git describe --tags --always`` (enthält Tag bzw. Abstand zum Tag).
    Unreines Arbeitsverzeichnis: angehängt ``+<kurze HEAD-Commit-ID>`` (nicht ``-dirty``).
    """
    root = _PROJECT_ROOT
    try:
        if not (os.path.isdir(os.path.join(root, ".git")) or os.path.isfile(os.path.join(root, ".git"))):
            return None
        d = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if d.returncode != 0 or not (d.stdout or "").strip():
            return None
        line = d.stdout.strip()
        st = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if st.returncode == 0 and (st.stdout or "").strip():
            r = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and (r.stdout or "").strip():
                return f"{line}+{r.stdout.strip()}"
        return line
    except Exception as ex:
        logger.debug("Wishlist-Web: Git-Version nicht ermittelbar: %s", ex)
        return None


def build_wishlist_web_version_footer() -> str:
    """
    Kurzstring für Tests und Anzeige: Git-``describe`` (Tag/Version) ggf. ``+Commit`` bei dirty,
    sonst Paketversion aus ``src._version``.
    """
    g = _git_describe_footer_string()
    if g is not None:
        return g
    try:
        from src._version import __version__

        return str(__version__)
    except Exception:
        return ""


def _wishlist_version_footer_html() -> str:
    g = _git_describe_footer_string()
    if g is not None:
        esc = html.escape(g)
        return (
            f'<footer id="wl-footer" style="margin-top:2.5rem;padding-top:1rem;border-top:1px solid #3b4261;'
            f'font-size:0.8rem;color:#565f89;">Perlentaucher · Git: <span translate="no">{esc}</span></footer>'
        )
    v = build_wishlist_web_version_footer()
    if not v:
        return ""
    esc = html.escape(v)
    return (
        f'<footer id="wl-footer" style="margin-top:2.5rem;padding-top:1rem;border-top:1px solid #3b4261;'
        f'font-size:0.8rem;color:#565f89;">Perlentaucher · Version (Paket): <span translate="no">{esc}</span></footer>'
    )


INDEX_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Perlentaucher Wishlist</title>
  <link rel="icon" href="/favicon.ico" sizes="any"/>
  <link rel="icon" type="image/png" sizes="16x16" href="/assets/icon_16.png"/>
  <link rel="icon" type="image/png" sizes="32x32" href="/assets/icon_32.png"/>
  <link rel="icon" type="image/png" sizes="48x48" href="/assets/icon_48.png"/>
  <link rel="icon" type="image/png" sizes="256x256" href="/assets/icon_256.png"/>
  <link rel="icon" type="image/png" sizes="512x512" href="/assets/icon_512.png"/>
  <link rel="apple-touch-icon" href="/assets/icon_256.png"/>
  <style>
    :root { font-family: system-ui, sans-serif; background: #1a1b26; color: #c0caf5; }
    body { max-width: 720px; margin: 2rem auto; padding: 0 1rem; }
    h1 { font-weight: 600; }
    label { display: block; margin-top: 1rem; font-size: 0.9rem; color: #a9b1d6; }
    input, select, button { margin-top: 0.35rem; padding: 0.5rem 0.75rem; border-radius: 6px;
      border: 1px solid #3b4261; background: #24283b; color: #c0caf5; width: 100%; box-sizing: border-box; }
    button { cursor: pointer; background: #7aa2f7; color: #1a1b26; border: none; font-weight: 600; width: auto; margin-right: 0.5rem; margin-top: 1rem; }
    button.secondary { background: #414868; color: #c0caf5; }
    table { width: 100%; border-collapse: collapse; margin-top: 1.5rem; font-size: 0.9rem; }
    th, td { text-align: left; padding: 0.5rem 0.4rem; border-bottom: 1px solid #3b4261; vertical-align: middle; }
    table tbody td button { margin-top: 0; margin-bottom: 0; }
    td.col-actions { text-align: center; width: 3.25rem; padding: 0.35rem 0.3rem; }
    button.btn-icon-del {
      padding: 0.35rem 0.45rem; font-size: 1.15rem; line-height: 1; min-height: 2rem; min-width: 2rem;
      display: inline-flex; align-items: center; justify-content: center;
    }
    .msg { margin-top: 1rem; padding: 0.75rem; border-radius: 6px; background: #24283b; white-space: pre-wrap; }
    a { color: #7dcfff; }
    .badge { display: inline-block; padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .lvl-info { background: #414868; color: #c0caf5; }
    .lvl-success { background: #1f3d2f; color: #9ece6a; }
    .lvl-warning { background: #4a3f2a; color: #e0af68; }
    .lvl-error { background: #4a2a2a; color: #f7768e; }
    #history-wrap { margin-top: 2.5rem; }
    #history-wrap table { font-size: 0.85rem; }
    #history-wrap td.detail { color: #a9b1d6; max-width: 22rem; word-break: break-word; }
    details.hist-details > summary {
      cursor: pointer;
      list-style: none;
      font-size: 1.15rem;
      font-weight: 600;
      padding: 0.35rem 0;
      color: #c0caf5;
    }
    details.hist-details > summary::-webkit-details-marker { display: none; }
    details.hist-details .hist-hint { font-weight: 400; font-size: 0.85rem; color: #a9b1d6; margin-left: 0.35rem; }
    .hist-inner { margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid #3b4261; }
    .hist-filters { display: flex; flex-wrap: wrap; gap: 0.75rem 1rem; align-items: flex-end; margin: 0.75rem 0 1rem; }
    .hist-filters label { margin-top: 0; font-size: 0.85rem; }
    .hist-filters input[type="search"], .hist-filters select { max-width: 14rem; }
    .hist-filters input.hist-q { max-width: min(100%, 18rem); }
    .hist-pager { margin-top: 1rem; display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; font-size: 0.9rem; color: #a9b1d6; }
    .hist-pager button:disabled { opacity: 0.45; cursor: not-allowed; }
  </style>
</head>
<body>
  <h1>Wunschliste</h1>
  <p>Beliebige Titel merken und in den öffentlichen Mediatheken suchen — nach dem Hinzufügen folgt eine Verfügbarkeitsprüfung; bei mehreren Treffern kannst du die passende Fassung wählen.</p>

  <form id="addf">
    <label>Titel <input name="title" required placeholder="Filmtitel"/></label>
    <label>Jahr (optional) <input name="year" type="number" min="1900" max="2100" placeholder="z.B. 2024"/></label>
    <label>Typ
      <select name="kind">
        <option value="movie">Film</option>
        <option value="series">Serie</option>
      </select>
    </label>
    <button type="submit">Hinzufügen</button>
  </form>
  <div id="msg" class="msg" style="display:none;" role="status" aria-live="polite"></div>

  <h2>Einträge</h2>
  <button type="button" class="secondary" id="reload">Aktualisieren</button>
  <button type="button" id="check">Prüfen (Verfügbarkeit)</button>
  <button type="button" id="process">Verarbeiten (Download)</button>
  <table><thead><tr><th>Titel</th><th>Jahr</th><th>Typ</th><th class="col-actions" aria-label="Aktionen"></th></tr></thead><tbody id="rows"></tbody></table>

  <div id="history-wrap">
    <details id="hist-details" class="hist-details">
      <summary><span class="hist-sum-title">Verlauf</span> <span id="hist-total-hint" class="hist-hint">(aufklappen, Filter &amp; Seiten)</span></summary>
      <div class="hist-inner">
        <p style="font-size:0.9rem;color:#a9b1d6;margin-top:0;">Gemeinsame Aktivitätsdatei mit CLI und GUI (RSS-Feed, Suche, Wishlist, Downloads). Web-Aktionen sind als Quelle „Web“ erkennbar.</p>
        <div class="hist-filters">
          <label>Stufe
            <select id="histFilterLevel" aria-label="Nach Stufe filtern">
              <option value="">alle</option>
              <option value="info">info</option>
              <option value="success">success</option>
              <option value="warning">warning</option>
              <option value="error">error</option>
            </select>
          </label>
          <label>Art
            <select id="histFilterAction" aria-label="Nach Art filtern">
              <option value="">alle</option>
              <option value="hinzufuegen">Eintrag &amp; Probe</option>
              <option value="download">Download</option>
              <option value="pruefen">Prüfen</option>
              <option value="verarbeiten">Verarbeiten</option>
              <option value="entfernen">Entfernt</option>
              <option value="wishlist_download">Wishlist-Download</option>
              <option value="wishlist_stapel">Wishlist Stapel</option>
              <option value="wishlist_add">Wishlist +</option>
              <option value="wishlist_remove">Wishlist −</option>
              <option value="feed_download">RSS-Feed</option>
              <option value="such_download">Suche</option>
            </select>
          </label>
          <label style="flex:1;min-width:12rem;">Text
            <input class="hist-q" type="search" id="histFilterQ" placeholder="Betreff, Details, Art …" autocomplete="off" aria-label="Textsuche im Verlauf"/>
          </label>
          <button type="button" id="histFilterApply">Filtern</button>
        </div>
        <div>
          <button type="button" class="secondary" id="reloadHist">Aktualisieren</button>
          <button type="button" class="secondary" id="clearHist">Verlauf leeren</button>
        </div>
        <table><thead><tr><th>Zeit (UTC)</th><th>Quelle</th><th>Art</th><th>Betreff</th><th>Details</th><th>Stufe</th></tr></thead><tbody id="histRows"></tbody></table>
        <div id="histPager" class="hist-pager">
          <button type="button" class="secondary" id="histPrev" disabled>Zurück</button>
          <span id="histPageInfo"></span>
          <button type="button" class="secondary" id="histNext" disabled>Weiter</button>
        </div>
      </div>
    </details>
  </div>

  <script>
    const api = (path, opt) => fetch(path, opt).then(r => { if (!r.ok) throw new Error(r.statusText); return r.json(); });
    function show(m, err) {
      const el = document.getElementById('msg');
      el.style.display = 'block';
      if (err === true) el.style.background = '#3f2d2d';
      else if (err === 'loading') el.style.background = '#414868';
      else el.style.background = '#24283b';
      el.textContent = m;
    }
    async function loadRows() {
      const data = await api('/api/items');
      const tb = document.getElementById('rows');
      tb.innerHTML = '';
      for (const it of data.items) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td>'+escapeHtml(it.title)+'</td><td>'+(it.year||'')+'</td><td>'+(it.kind==='series'?'Serie':'Film')+'</td><td class="col-actions"><button type="button" data-id="'+escapeHtml(it.id)+'" class="del secondary btn-icon-del" aria-label="Eintrag entfernen" title="Entfernen">🗑️</button></td>';
        tb.appendChild(tr);
      }
      tb.querySelectorAll('.del').forEach(b => b.onclick = async () => {
        await api('/api/items/'+b.dataset.id, { method: 'DELETE' });
        show('Eintrag entfernt.');
        loadRows();
        refreshHistoryIfOpen();
      });
    }
    function escapeHtml(s) {
      const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
    }
    const actionLabel = { hinzufuegen: 'Eintrag & Probe', download: 'Download', pruefen: 'Prüfen', verarbeiten: 'Verarbeiten', entfernen: 'Entfernt',
      wishlist_download: 'Wishlist-Download', wishlist_stapel: 'Wishlist Stapel', wishlist_add: 'Wishlist +', wishlist_remove: 'Wishlist −',
      feed_download: 'RSS-Feed', such_download: 'Suche' };
    const sourceLabel = { cli: 'CLI', web: 'Web', gui: 'GUI', feed: 'RSS', search: 'Suche' };
    function badgeClass(lvl) {
      const m = { info: 'lvl-info', success: 'lvl-success', warning: 'lvl-warning', error: 'lvl-error' };
      return m[lvl] || 'lvl-info';
    }
    const histState = { limit: 20, offset: 0, level: '', action: '', q: '' };
    let histEverOpened = false;
    function syncHistFiltersFromDom() {
      const lv = document.getElementById('histFilterLevel');
      const ac = document.getElementById('histFilterAction');
      const tq = document.getElementById('histFilterQ');
      histState.level = (lv && lv.value) ? lv.value : '';
      histState.action = (ac && ac.value) ? ac.value : '';
      histState.q = (tq && tq.value) ? tq.value.trim() : '';
    }
    function renderHistoryRows(entries) {
      const tb = document.getElementById('histRows');
      tb.innerHTML = '';
      for (const e of entries || []) {
        const tr = document.createElement('tr');
        const ts = (e.ts || '').replace('T', ' ').replace('+00:00', ' UTC');
        const al = actionLabel[e.action] || e.action;
        const src = sourceLabel[e.source] || (e.source || '—');
        tr.innerHTML = '<td>'+escapeHtml(ts)+'</td><td>'+escapeHtml(src)+'</td><td>'+escapeHtml(al)+'</td><td>'+escapeHtml(e.label||'')+'</td><td class="detail">'+escapeHtml(e.detail||'')+'</td><td><span class="badge '+badgeClass(e.level)+'">'+(e.level||'info')+'</span></td>';
        tb.appendChild(tr);
      }
    }
    function renderHistoryPager(total) {
      const lim = histState.limit;
      const off = histState.offset;
      const tot = typeof total === 'number' ? total : 0;
      const pages = Math.max(1, Math.ceil(tot / lim) || 1);
      const cur = tot === 0 ? 1 : Math.min(pages, Math.floor(off / lim) + 1);
      const prev = document.getElementById('histPrev');
      const next = document.getElementById('histNext');
      const info = document.getElementById('histPageInfo');
      if (prev) prev.disabled = off <= 0;
      if (next) next.disabled = tot === 0 || off + lim >= tot;
      if (info) {
        if (tot === 0) info.textContent = 'Keine Einträge (mit aktuellem Filter).';
        else info.textContent = 'Seite ' + cur + ' von ' + pages + ' · Zeilen ' + (off + 1) + '–' + Math.min(off + lim, tot) + ' von ' + tot;
      }
    }
    async function loadHistoryPage(resetOffset) {
      if (resetOffset) histState.offset = 0;
      const params = new URLSearchParams();
      params.set('limit', String(histState.limit));
      params.set('offset', String(histState.offset));
      if (histState.level) params.set('level', histState.level);
      if (histState.action) params.set('action', histState.action);
      if (histState.q) params.set('q', histState.q);
      const data = await api('/api/history?' + params.toString());
      const total = typeof data.total === 'number' ? data.total : 0;
      renderHistoryRows(data.entries || []);
      const hint = document.getElementById('hist-total-hint');
      if (hint) {
        var filt = histState.level || histState.action || histState.q;
        hint.textContent = total === 0
          ? (filt ? '(keine Treffer — Filter lockern)' : '(keine Einträge)')
          : '(' + total + ' Eintrag' + (total === 1 ? '' : 'e') + (filt ? ', gefiltert' : '') + ')';
      }
      renderHistoryPager(total);
    }
    function refreshHistoryIfOpen() {
      const d = document.getElementById('hist-details');
      if (d && d.open) {
        syncHistFiltersFromDom();
        loadHistoryPage(true).catch(function(e) { show('Verlauf: ' + e, true); });
      }
    }
    async function offerDownloadAfterProbe(item, probe) {
      const msg = document.getElementById('msg');
      msg.style.display = 'block';
      msg.style.background = '#24283b';
      msg.innerHTML = '';
      const titleHint = item && item.title ? '„' + item.title + '“ ist gespeichert. ' : 'Eintrag gespeichert. ';
      if (probe.status === 'probe_error') {
        show(titleHint + 'Die Mediathek konnte nicht geprüft werden'
          + (probe.message ? ': ' + probe.message : '') + ' Später erneut versuchen oder „Verarbeiten“ nutzen.', true);
        return;
      }
      if (probe.status === 'not_found') {
        show(titleHint + 'Aktuell kein passender Treffer in der Mediathek — der Wunschtitel bleibt auf der Liste und kann später mit „Verarbeiten“ geladen werden, sobald er erscheint.', false);
        return;
      }
      if (probe.status === 'serien_skipped') {
        show(probe.message || 'Serien-Download ist deaktiviert.', false);
        return;
      }
      if (probe.status === 'staffel_available') {
        const n = probe.episode_count || 0;
        if (!confirm('Es wurden etwa ' + n + ' Episoden gefunden. Gesamte Staffel jetzt herunterladen?')) {
          show('Eintrag gespeichert. Du kannst später „Verarbeiten“ nutzen.', false);
          return;
        }
        try {
          const r = await api('/api/items/' + encodeURIComponent(item.id) + '/download', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ candidate_index: 0 })
          });
          show('Download: ' + (r.ok ? 'OK (' + r.code + ')' : 'Fehler (' + r.code + ')'), r.ok ? false : true);
          refreshHistoryIfOpen();
        } catch (e) { show(String(e), true); }
        return;
      }
      const cands = probe.candidates || [];
      if (cands.length === 0) {
        show(titleHint + 'Unerwartete Antwort der Mediathek-Prüfung — der Eintrag bleibt gespeichert.', false);
        return;
      }
      const savedNote = document.createElement('p');
      savedNote.style.fontSize = '0.9rem';
      savedNote.style.color = '#a9b1d6';
      savedNote.textContent = titleHint + 'Wenn keiner der Vorschläge passt, ohne Download fortfahren — der Wunschtitel bleibt auf der Liste und kann später über „Verarbeiten“ geladen werden, sobald er in der Mediathek verfügbar ist.';
      msg.appendChild(savedNote);
      const intro = document.createElement('p');
      intro.textContent = probe.status === 'ambiguous'
        ? 'Mehrere Treffer — passende Fassung wählen und Download starten, oder nur merken:'
        : 'Treffer in der Mediathek — jetzt herunterladen oder nur merken:';
      msg.appendChild(intro);
      const sel = document.createElement('select');
      sel.style.width = '100%';
      sel.style.marginTop = '0.5rem';
      cands.forEach(function(c, i) {
        const o = document.createElement('option');
        o.value = String(c.index !== undefined ? c.index : i);
        o.textContent = c.title + ' (Ähnlichkeit ' + (c.title_similarity || 0).toFixed(2) + ')';
        sel.appendChild(o);
      });
      msg.appendChild(sel);
      const row = document.createElement('div');
      row.style.marginTop = '0.75rem';
      const btnDl = document.createElement('button');
      btnDl.type = 'button';
      btnDl.textContent = 'Jetzt herunterladen';
      btnDl.onclick = async function() {
        const idx = parseInt(sel.value, 10) || 0;
        try {
          const r = await api('/api/items/' + encodeURIComponent(item.id) + '/download', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({ candidate_index: idx })
          });
          show('Ergebnis: ' + r.code + (r.ok ? ' — bei Erfolg wurde der Eintrag entfernt.' : ''), r.ok ? false : true);
          loadRows();
          refreshHistoryIfOpen();
        } catch (e) { show(String(e), true); }
      };
      const btnSkip = document.createElement('button');
      btnSkip.type = 'button';
      btnSkip.className = 'secondary';
      btnSkip.textContent = 'Kein Vorschlag passt — nur merken';
      btnSkip.title = 'Wishlist-Eintrag behalten, keinen der Vorschläge herunterladen';
      btnSkip.onclick = function() {
        show((item && item.title ? '„' + item.title + '“ bleibt auf der Wishlist. ' : '') + 'Später „Verarbeiten“, sobald der Titel in der Mediathek passt.', false);
      };
      row.appendChild(btnDl);
      row.appendChild(btnSkip);
      msg.appendChild(row);
    }
    document.getElementById('addf').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = { title: fd.get('title'), year: fd.get('year') ? parseInt(fd.get('year'),10) : null, kind: fd.get('kind') };
      show('Mediathek wird geprüft …', 'loading');
      try {
        const r = await api('/api/items', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
        e.target.reset();
        await offerDownloadAfterProbe(r.item, r.probe);
      } catch (err) {
        show(String(err), true);
      }
      loadRows();
      refreshHistoryIfOpen();
    };
    document.getElementById('reload').onclick = () => loadRows();
    document.getElementById('check').onclick = async () => {
      const btn = document.getElementById('check');
      btn.disabled = true;
      show('Mediathek wird geprüft … Bitte warten.', 'loading');
      try {
        const r = await api('/api/check', { method: 'POST' });
        const total = typeof r.total === 'number' ? r.total : (r.available || []).length;
        const list = r.available || [];
        const n = list.length;
        if (total === 0) {
          show('Prüfung abgeschlossen.\\n\\nDie Wishlist ist leer — es gibt keine Einträge zu prüfen.', false);
        } else if (n === 0) {
          show('Prüfung abgeschlossen.\\n\\nKeiner der ' + total + ' Einträge ist in der Mediathek (MediathekViewWeb) auffindbar. Die Titel sind vermutlich noch nicht verfügbar oder die Suche findet keine passende Fassung.', false);
        } else {
          const lines = list.map(function(x) {
            const y = x.year ? ' (' + x.year + ')' : '';
            const kind = x.kind === 'series' ? 'Serie' : 'Film';
            return '• ' + x.title + y + ' — ' + kind;
          }).join('\\n');
          const summary = n === total
            ? 'Alle ' + n + ' Einträge sind in der Mediathek auffindbar.'
            : n + ' von ' + total + ' Einträgen sind in der Mediathek auffindbar.';
          show('Prüfung abgeschlossen.\\n\\n' + summary + '\\n\\nGefundene Titel:\\n' + lines, false);
        }
      } catch (e) {
        show('Prüfung fehlgeschlagen: ' + e, true);
      } finally {
        btn.disabled = false;
        refreshHistoryIfOpen();
      }
    };
    document.getElementById('process').onclick = async () => {
      try {
        const r = await api('/api/process', { method: 'POST' });
        show('Verarbeitet: ' + r.processed + ', erfolgreich: ' + r.successes);
        loadRows();
        refreshHistoryIfOpen();
      } catch (e) { show(String(e), true); }
    };
    document.getElementById('reloadHist').onclick = function() {
      syncHistFiltersFromDom();
      loadHistoryPage(true).catch(function(e) { show('Verlauf: ' + e, true); });
    };
    document.getElementById('histFilterApply').onclick = function() {
      syncHistFiltersFromDom();
      loadHistoryPage(true).catch(function(e) { show('Verlauf: ' + e, true); });
    };
    document.getElementById('histFilterQ').addEventListener('keydown', function(ev) {
      if (ev.key === 'Enter') { ev.preventDefault(); document.getElementById('histFilterApply').click(); }
    });
    document.getElementById('histPrev').onclick = function() {
      histState.offset = Math.max(0, histState.offset - histState.limit);
      loadHistoryPage(false).catch(function(e) { show('Verlauf: ' + e, true); });
    };
    document.getElementById('histNext').onclick = function() {
      histState.offset += histState.limit;
      loadHistoryPage(false).catch(function(e) { show('Verlauf: ' + e, true); });
    };
    document.getElementById('hist-details').addEventListener('toggle', function() {
      if (!this.open) return;
      if (!histEverOpened) {
        histEverOpened = true;
        syncHistFiltersFromDom();
        loadHistoryPage(true).catch(function(e) { show('Verlauf: ' + e, true); });
      }
    });
    document.getElementById('clearHist').onclick = async () => {
      if (!confirm('Gesamten Verlauf unwiderruflich leeren?')) return;
      await api('/api/history', { method: 'DELETE' });
      if (document.getElementById('hist-details').open) {
        syncHistFiltersFromDom();
        loadHistoryPage(true).catch(function(e) { show('Verlauf: ' + e, true); });
      } else {
        var hint = document.getElementById('hist-total-hint');
        if (hint) hint.textContent = '(aufklappen, Filter & Seiten)';
      }
    };
    loadRows();
  </script>
__WISHLIST_VERSION_FOOTER__
</body>
</html>
"""


def create_app(
    wishlist_path: str,
    process_args_factory,
    token: Optional[str] = None,
    activity_path: Optional[str] = None,
) -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI und Uvicorn müssen installiert sein: pip install fastapi uvicorn[standard]")

    app = FastAPI(title="Perlentaucher Wishlist", version="1.0")

    _index_html = INDEX_HTML.replace("__WISHLIST_VERSION_FOOTER__", _wishlist_version_footer_html())

    if StaticFiles is not None and os.path.isdir(ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    if activity_path:
        _hist = activity_path
    else:
        try:
            _a = process_args_factory()
            _dd = getattr(_a, "download_dir", None) or os.getcwd()
        except Exception:
            _dd = os.getcwd()
        _hist = resolve_activity_path(_dd)

    def _auth(request: Request) -> None:
        if not token:
            return
        auth = request.headers.get("authorization") or ""
        if auth == f"Bearer {token}":
            return
        q = request.query_params.get("token")
        if q == token:
            return
        raise HTTPException(status_code=401, detail="Unauthorized")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(_index_html)

    @app.get("/favicon.ico")
    async def favicon_ico():
        ico = os.path.join(ASSETS_DIR, "icon.ico")
        if os.path.isfile(ico) and FileResponse is not None:
            return FileResponse(ico, media_type="image/x-icon")
        raise HTTPException(status_code=404, detail="favicon not found")

    @app.get("/api/items")
    async def get_items(request: Request):
        _auth(request)
        items = [i.to_dict() for i in list_items(wishlist_path)]
        return {"items": items}

    @app.post("/api/items")
    async def post_item(request: Request, body: WishlistItemIn):
        _auth(request)
        title = body.title.strip()
        if not title:
            raise HTTPException(400, "title required")
        kind: WishlistKind = "series" if body.kind == "series" else "movie"
        item = add_item(wishlist_path, title, body.year, kind, note=body.note.strip())
        args = process_args_factory()
        try:
            probe = probe_wishlist_item(
                item,
                sprache=getattr(args, "sprache", "deutsch"),
                audiodeskription=getattr(args, "audiodeskription", "egal"),
                serien_download=getattr(args, "serien_download", "erste"),
                tmdb_api_key=getattr(args, "tmdb_api_key", None),
                omdb_api_key=getattr(args, "omdb_api_key", None),
            )
        except Exception as ex:
            logger.warning("probe_wishlist_item nach add_item fehlgeschlagen: %s", ex, exc_info=True)
            msg = str(ex).strip() or type(ex).__name__
            if len(msg) > 300:
                msg = msg[:297] + "…"
            probe = {"status": "probe_error", "message": msg}
        summ, lvl = summarize_probe_for_log(probe)
        append_activity(_hist, "hinzufuegen", item.title, summ, lvl, "web")
        return {"item": item.to_dict(), "probe": probe}

    @app.post("/api/items/{item_id}/download")
    async def download_one(request: Request, item_id: str):
        _auth(request)
        try:
            data = await request.json()
        except Exception:
            data = {}
        ci = int(data.get("candidate_index", 0))
        args = process_args_factory()
        wl_items = list_items(wishlist_path)
        title_dl = next((i.title for i in wl_items if i.id == item_id), item_id)
        ok, code = process_one_wishlist_item(
            wishlist_path,
            item_id,
            args,
            candidate_index=ci,
            remove_on_success=True,
        )
        return {"ok": ok, "code": code}

    @app.delete("/api/items/{item_id}")
    async def del_item(request: Request, item_id: str):
        _auth(request)
        wl_items = list_items(wishlist_path)
        title_rm = next((i.title for i in wl_items if i.id == item_id), None)
        if title_rm is None:
            raise HTTPException(404, "not found")
        if not remove_item(wishlist_path, item_id):
            raise HTTPException(404, "not found")
        append_activity(_hist, "entfernen", title_rm, "Manuell aus der Liste entfernt", "info", "web")
        return {"ok": True}

    @app.post("/api/check")
    async def check(request: Request):
        _auth(request)
        args = process_args_factory()
        avail, total = check_wishlist_availability(
            wishlist_path,
            sprache=getattr(args, "sprache", "deutsch"),
            audiodeskription=getattr(args, "audiodeskription", "egal"),
            serien_download=getattr(args, "serien_download", "erste"),
            tmdb_api_key=getattr(args, "tmdb_api_key", None),
            omdb_api_key=getattr(args, "omdb_api_key", None),
        )
        n = len(avail)
        detail = f"{n} von {total} Titel(n) auffindbar"
        if n and n <= 5:
            detail += ": " + ", ".join(x.title for x in avail)
        elif n > 5:
            detail += ": " + ", ".join(x.title for x in avail[:3]) + ", …"
        append_activity(_hist, "pruefen", f"Wishlist ({total} Einträge)", detail, "info", "web")
        return {
            "total": total,
            "available_count": n,
            "available": [a.to_dict() for a in avail],
        }

    @app.post("/api/process")
    async def process(request: Request):
        _auth(request)
        args = process_args_factory()
        processed, successes = process_wishlist_items(wishlist_path, args, remove_on_success=True)
        if processed == 0:
            append_activity(_hist, "verarbeiten", "Wishlist leer oder keine Aktion", "", "info", "web")
        return {"processed": processed, "successes": successes}

    @app.get("/api/history")
    async def get_history(
        request: Request,
        limit: int = 20,
        offset: int = 0,
        level: Optional[str] = None,
        action: Optional[str] = None,
        q: Optional[str] = None,
    ):
        _auth(request)
        entries, total = query_activity(
            _hist,
            limit=limit,
            offset=offset,
            level=level,
            action=action,
            q=q,
        )
        return {"entries": entries, "total": total, "limit": limit, "offset": offset}

    @app.delete("/api/history")
    async def delete_history(request: Request):
        _auth(request)
        clear_activity(_hist)
        return {"ok": True}

    return app


def _preflight_port(host: str, port: int) -> None:
    """
    Prüft, ob der Port lokal gebunden werden kann — vermeidet stilles Scheitern
    (z. B. WinError 10048), wenn 8765 schon von einem anderen Prozess genutzt wird.
    """
    import socket

    test_host = host
    if host in ("0.0.0.0", "::"):
        test_host = "127.0.0.1"
    if ":" in test_host and test_host != "127.0.0.1":
        return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((test_host, port))
    except OSError as e:
        print(
            f"Wishlist-Web-UI: Port {port} ist bereits belegt ({e}).\n"
            "Anderen Prozess beenden (z. B. alte Wishlist-Instanz) oder anderen Port wählen, "
            "z. B. --wishlist-web-port 8766 bzw. WISHLIST_WEB_PORT=8766.",
            file=sys.stderr,
        )
        sys.exit(1)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    wishlist_path: Optional[str] = None,
    download_dir: Optional[str] = None,
    token: Optional[str] = None,
    cli_args: Optional[Any] = None,
    activity_path: Optional[str] = None,
) -> None:
    if FastAPI is None:
        print("Bitte installieren: pip install fastapi uvicorn[standard]", file=sys.stderr)
        sys.exit(1)

    dd = download_dir or os.getcwd()
    wl = wishlist_path or default_wishlist_path(dd)

    def factory():
        if cli_args is not None:
            return cli_args
        return build_process_args_from_env(dd)

    app = create_app(wl, factory, token=token, activity_path=activity_path)
    _preflight_port(host, port)
    logging.info(f"Wishlist-Web-UI: http://{host}:{port}/  (Wishlist: {wl})")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    p = argparse.ArgumentParser(description="Perlentaucher Wishlist Web-UI")
    p.add_argument("--host", default=os.environ.get("WISHLIST_WEB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("WISHLIST_WEB_PORT", "8765")))
    p.add_argument("--wishlist-file", default=os.environ.get("WISHLIST_FILE"))
    p.add_argument("--download-dir", default=os.environ.get("DOWNLOAD_DIR", os.getcwd()))
    p.add_argument("--token", default=os.environ.get("WISHLIST_WEB_TOKEN"))
    args = p.parse_args()
    wl = args.wishlist_file or default_wishlist_path(args.download_dir)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run_server(host=args.host, port=args.port, wishlist_path=wl, download_dir=args.download_dir, token=args.token)


if __name__ == "__main__":
    main()
