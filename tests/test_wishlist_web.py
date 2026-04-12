"""
Tests für Wishlist-Web-UI (FastAPI), ohne laufenden Server.
"""
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from src.wishlist_core import add_item, save_wishlist  # noqa: E402
from src.wishlist_web import build_process_args_from_env, build_wishlist_web_version_footer, create_app  # noqa: E402


def _factory(tmp_path):
    """Args für Downloads: isoliertes Verzeichnis."""

    def factory():
        a = type("_A", (), {})()
        a.sprache = "deutsch"
        a.audiodeskription = "egal"
        a.serien_download = "erste"
        a.tmdb_api_key = None
        a.omdb_api_key = None
        a.notify = None
        a.debug_no_download = False
        a.download_dir = str(tmp_path / "dl")
        a.serien_dir = None
        a.no_state = True
        a.state_file = None
        return a

    return factory


def test_build_process_args_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SPRACHE", "englisch")
    monkeypatch.setenv("AUDIODESKRIPTION", "mit")
    monkeypatch.setenv("SERIEN_DOWNLOAD", "staffel")
    monkeypatch.setenv("TMDB_API_KEY", "t1")
    monkeypatch.setenv("NOTIFY", "mailto://a@b")
    monkeypatch.setenv("DEBUG_NO_DOWNLOAD", "1")
    dd = str(tmp_path / "down")
    monkeypatch.setenv("DOWNLOAD_DIR", dd)
    monkeypatch.setenv("SERIEN_DIR", dd)
    monkeypatch.setenv("NO_STATE", "true")
    monkeypatch.setenv("STATE_FILE", str(tmp_path / "st.json"))

    a = build_process_args_from_env(dd)
    assert a.sprache == "englisch"
    assert a.audiodeskription == "mit"
    assert a.serien_download == "staffel"
    assert a.tmdb_api_key == "t1"
    assert a.notify == "mailto://a@b"
    assert a.debug_no_download is True
    assert a.download_dir == dd
    assert a.serien_dir == dd
    assert a.no_state is True
    assert a.state_file == str(tmp_path / "st.json")
    assert a.activity_source == "web"


def test_api_get_items_empty(tmp_path):
    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    r = client.get("/api/items")
    assert r.status_code == 200
    assert r.json() == {"items": []}


def test_api_requires_token(tmp_path):
    wl = str(tmp_path / "wl.json")
    app = create_app(wl, _factory(tmp_path), token="geheim")
    client = TestClient(app)
    assert client.get("/api/items").status_code == 401
    assert client.get("/api/items", headers={"Authorization": "Bearer geheim"}).status_code == 200
    assert client.get("/api/items?token=geheim").status_code == 200


def test_api_delete_404(tmp_path):
    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    assert client.delete("/api/items/nope").status_code == 404


def test_api_delete_ok(tmp_path):
    wl = str(tmp_path / "wl.json")
    it = add_item(wl, "ZumLoeschen", None, "movie")
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    r = client.delete(f"/api/items/{it.id}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert client.get("/api/items").json()["items"] == []


def test_api_post_item_probe_mocked(tmp_path, monkeypatch):
    from src import wishlist_web as ww

    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    monkeypatch.setattr(
        ww,
        "probe_wishlist_item",
        lambda *a, **k: {"status": "not_found"},
    )
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    r = client.post(
        "/api/items",
        json={"title": "  Neu  ", "year": 2021, "kind": "movie", "note": ""},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["probe"]["status"] == "not_found"
    assert body["item"]["title"] == "Neu"
    assert body["item"]["year"] == 2021


def test_api_check_and_process_mocked(tmp_path, monkeypatch):
    from src import wishlist_web as ww

    wl = str(tmp_path / "wl.json")
    add_item(wl, "X", None, "movie")
    monkeypatch.setattr(ww, "check_wishlist_availability", lambda *a, **k: ([], 1))
    monkeypatch.setattr(ww, "process_wishlist_items", lambda *a, **k: (1, 0))

    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    chk = client.post("/api/check")
    assert chk.status_code == 200
    assert chk.json()["total"] == 1
    assert chk.json()["available_count"] == 0

    proc = client.post("/api/process")
    assert proc.status_code == 200
    assert proc.json() == {"processed": 1, "successes": 0}


def test_api_download_one_mocked(tmp_path, monkeypatch):
    from src import wishlist_web as ww

    wl = str(tmp_path / "wl.json")
    it = add_item(wl, "D", None, "movie")
    monkeypatch.setattr(
        ww,
        "process_one_wishlist_item",
        lambda *a, **k: (True, "success"),
    )
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    r = client.post(
        f"/api/items/{it.id}/download",
        json={"candidate_index": 0},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True, "code": "success"}


def test_index_returns_html(tmp_path):
    wl = str(tmp_path / "wl.json")
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Wunschliste" in r.text
    assert "Verlauf" in r.text
    assert "/favicon.ico" in r.text
    assert "/assets/icon_32.png" in r.text
    assert 'id="wl-footer"' in r.text
    assert "__WISHLIST_VERSION_FOOTER__" not in r.text
    assert build_wishlist_web_version_footer() in r.text


def test_build_wishlist_web_version_footer_nonempty():
    s = build_wishlist_web_version_footer()
    assert isinstance(s, str)
    assert len(s) > 0


def test_favicon_and_assets_served(tmp_path):
    wl = str(tmp_path / "wl.json")
    app = create_app(wl, _factory(tmp_path), token=None)
    client = TestClient(app)
    assert client.get("/favicon.ico").status_code == 200
    assert client.get("/assets/icon_32.png").status_code == 200


def test_api_history_empty(tmp_path):
    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    hist = str(tmp_path / "act.json")
    app = create_app(wl, _factory(tmp_path), token=None, activity_path=hist)
    client = TestClient(app)
    r = client.get("/api/history")
    assert r.status_code == 200
    assert r.json() == {"entries": []}


def test_api_history_clear(tmp_path):
    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    hist = str(tmp_path / "act.json")
    app = create_app(wl, _factory(tmp_path), token=None, activity_path=hist)
    client = TestClient(app)
    from src.wishlist_activity import append_activity

    append_activity(hist, "pruefen", "x", "y", "info")
    assert len(client.get("/api/history").json()["entries"]) == 1
    assert client.delete("/api/history").status_code == 200
    assert client.get("/api/history").json()["entries"] == []


def test_post_item_writes_activity_log(tmp_path, monkeypatch):
    from src import wishlist_web as ww

    wl = str(tmp_path / "wl.json")
    save_wishlist(wl, {"version": 1, "items": []})
    hist = str(tmp_path / "act.json")
    monkeypatch.setattr(ww, "probe_wishlist_item", lambda *a, **k: {"status": "not_found"})
    app = create_app(wl, _factory(tmp_path), token=None, activity_path=hist)
    client = TestClient(app)
    r = client.post("/api/items", json={"title": "LogTest", "year": None, "kind": "movie", "note": ""})
    assert r.status_code == 200
    entries = client.get("/api/history").json()["entries"]
    assert len(entries) == 1
    assert entries[0]["action"] == "hinzufuegen"
    assert entries[0]["label"] == "LogTest"
    assert entries[0]["level"] == "warning"
    assert entries[0]["source"] == "web"
