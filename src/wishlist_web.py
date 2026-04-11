"""
Wishlist-Web-UI (FastAPI): CRUD + Verarbeitung für Headless/Konsolen-Nutzung.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Optional

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    import uvicorn
except ImportError:
    FastAPI = None  # type: ignore

from src.wishlist_core import (
    WishlistItem,
    WishlistKind,
    add_item,
    check_wishlist_availability,
    default_wishlist_path,
    list_items,
    process_wishlist_items,
    remove_item,
)

logger = logging.getLogger(__name__)

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
    return a


INDEX_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Perlentaucher Wishlist</title>
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
  </style>
</head>
<body>
  <h1>Wunschliste</h1>
  <p>Filme und Serien, die noch nicht in der Mediathek sind — bei Verfügbarkeit herunterladen (<code>Verarbeiten</code>).</p>

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
      });
    }
    function escapeHtml(s) {
      const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
    }
    document.getElementById('addf').onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const body = { title: fd.get('title'), year: fd.get('year') ? parseInt(fd.get('year'),10) : null, kind: fd.get('kind') };
      await api('/api/items', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
      show('Eintrag hinzugefügt.');
      e.target.reset();
      loadRows();
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
      }
    };
    document.getElementById('process').onclick = async () => {
      try {
        const r = await api('/api/process', { method: 'POST' });
        show('Verarbeitet: ' + r.processed + ', erfolgreich: ' + r.successes);
        loadRows();
      } catch (e) { show(String(e), true); }
    };
    loadRows();
  </script>
</body>
</html>
"""


def create_app(
    wishlist_path: str,
    process_args_factory,
    token: Optional[str] = None,
) -> "FastAPI":
    if FastAPI is None:
        raise RuntimeError("FastAPI und Uvicorn müssen installiert sein: pip install fastapi uvicorn[standard]")

    app = FastAPI(title="Perlentaucher Wishlist", version="1.0")

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
        return HTMLResponse(INDEX_HTML)

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
        return item.to_dict()

    @app.delete("/api/items/{item_id}")
    async def del_item(request: Request, item_id: str):
        _auth(request)
        if not remove_item(wishlist_path, item_id):
            raise HTTPException(404, "not found")
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
        return {
            "total": total,
            "available_count": len(avail),
            "available": [a.to_dict() for a in avail],
        }

    @app.post("/api/process")
    async def process(request: Request):
        _auth(request)
        args = process_args_factory()
        processed, successes = process_wishlist_items(wishlist_path, args, remove_on_success=True)
        return {"processed": processed, "successes": successes}

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8765,
    wishlist_path: Optional[str] = None,
    download_dir: Optional[str] = None,
    token: Optional[str] = None,
    cli_args: Optional[Any] = None,
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

    app = create_app(wl, factory, token=token)
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
