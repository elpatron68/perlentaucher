"""
Tests für Wishlist-Kernlogik (ohne Netzwerk).
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src import wishlist_core as wc  # noqa: E402
from src.wishlist_core import (  # noqa: E402
    WishlistItem,
    add_item,
    check_item_available,
    check_wishlist_availability,
    default_wishlist_path,
    list_items,
    load_wishlist,
    process_one_wishlist_item,
    process_wishlist_items,
    probe_wishlist_item,
    remove_item,
    save_wishlist,
)


def _args_base(tmp_path, **kwargs):
    """Minimal args-Objekt wie CLI/Docker."""

    class Args:
        sprache = "deutsch"
        audiodeskription = "egal"
        serien_download = "erste"
        tmdb_api_key = None
        omdb_api_key = None
        notify = None
        debug_no_download = False
        download_dir = str(tmp_path / "dl")
        serien_dir = None
        no_state = True
        state_file = None

    a = Args()
    for k, v in kwargs.items():
        setattr(a, k, v)
    return a


def test_default_wishlist_path(tmp_path):
    p = default_wishlist_path(str(tmp_path))
    assert p.endswith(".perlentaucher_wishlist.json")
    assert os.path.dirname(p) == str(tmp_path.resolve())


def test_list_items(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "A", 2020, "movie")
    items = list_items(p)
    assert len(items) == 1
    assert items[0].title == "A"
    assert items[0].year == 2020


def test_load_wishlist_corrupt_json_returns_empty(tmp_path):
    p = tmp_path / "wl.json"
    p.write_text("{ keine json", encoding="utf-8")
    data = load_wishlist(str(p))
    assert data["items"] == []


def test_load_wishlist_without_items_key_normalized(tmp_path):
    p = tmp_path / "wl.json"
    p.write_text('{"version": 1}', encoding="utf-8")
    data = load_wishlist(str(p))
    assert data.get("items") == []


def test_process_wishlist_empty(tmp_path):
    p = str(tmp_path / "empty.json")
    save_wishlist(p, {"version": 1, "items": []})
    proc, succ = process_wishlist_items(p, _args_base(tmp_path))
    assert proc == 0
    assert succ == 0


def test_process_wishlist_series_serien_keine_keeps_item(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "SerieX", None, "series")
    os.makedirs(tmp_path / "dl", exist_ok=True)
    args = _args_base(tmp_path, serien_download="keine")
    proc, succ = process_wishlist_items(p, args, remove_on_success=True)
    assert proc == 1
    assert succ == 0
    assert len(load_wishlist(p)["items"]) == 1


def test_notify_download_kwargs(monkeypatch):
    monkeypatch.delenv("FFMPEG_PATH", raising=False)

    class Mit:
        notify = "ntfy://x"

    class Ohne:
        notify = None

    assert wc._notify_download_kwargs(Mit()) == {
        "notify_url": "ntfy://x",
        "notify_source": "wishlist",
        "ffmpeg_path": None,
    }
    assert wc._notify_download_kwargs(Ohne()) == {
        "notify_url": None,
        "notify_source": None,
        "ffmpeg_path": None,
    }


def test_classify_movie_probe():
    assert wc._classify_movie_probe([]) == "clear"
    assert wc._classify_movie_probe([{"score": 10.0, "title_similarity": 0.9}]) == "clear"
    # klarer Abstand zwischen Platz 1 und 2
    c_clear = [
        {"score": 10.0, "title_similarity": 0.95},
        {"score": 5.0, "title_similarity": 0.5},
    ]
    assert wc._classify_movie_probe(c_clear) == "clear"
    # ähnliche Scores -> mehrdeutig
    c_amb = [
        {"score": 10.0, "title_similarity": 0.91},
        {"score": 9.5, "title_similarity": 0.90},
    ]
    assert wc._classify_movie_probe(c_amb) == "ambiguous"


@pytest.mark.parametrize(
    "serien_download,fn_name,return_val,expected",
    [
        ("erste", "search_mediathek", {"x": 1}, True),
        ("staffel", "search_mediathek_series", [{"e": 1}], True),
        ("staffel", "search_mediathek_series", [], False),
    ],
)
def test_check_item_available_series_modes(serien_download, fn_name, return_val, expected):
    meta = {"year": None, "content_type": "tv"}
    with patch.object(wc.core, fn_name, return_value=return_val):
        ok = check_item_available(
            "T", None, "series", meta, "deutsch", "egal", serien_download
        )
        assert ok is expected


def test_check_item_available_movie():
    meta = {"year": 2020, "content_type": "movie"}
    with patch.object(wc.core, "search_mediathek", return_value={"url": 1}):
        assert check_item_available("F", 2020, "movie", meta, "deutsch", "egal", "erste") is True
    with patch.object(wc.core, "search_mediathek", return_value=None):
        assert check_item_available("F", 2020, "movie", meta, "deutsch", "egal", "erste") is False


def test_check_wishlist_availability(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "Only", None, "movie")
    meta = {"year": None, "content_type": "movie", "provider_id": None}
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "search_mediathek", return_value={"ok": True}
    ):
        avail, total = check_wishlist_availability(p)
        assert total == 1
        assert len(avail) == 1
        assert avail[0].title == "Only"


def test_probe_serien_skipped():
    item = WishlistItem(
        id="i1", title="S", year=None, kind="series", created_at="", note=""
    )
    r = probe_wishlist_item(item, serien_download="keine")
    assert r["status"] == "serien_skipped"


def test_probe_not_found_movie():
    item = WishlistItem(
        id="i1", title="M", year=None, kind="movie", created_at="", note=""
    )
    meta = {"year": None, "content_type": "movie"}
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "list_mediathek_movie_candidates", return_value=[]
    ):
        r = probe_wishlist_item(item)
        assert r["status"] == "not_found"


def test_probe_staffel_available():
    item = WishlistItem(
        id="i1", title="S", year=None, kind="series", created_at="", note=""
    )
    meta = {"year": None, "content_type": "tv"}
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "search_mediathek_series", return_value=[{"a": 1}, {"b": 2}]
    ):
        r = probe_wishlist_item(item, serien_download="staffel")
        assert r["status"] == "staffel_available"
        assert r["episode_count"] == 2


def test_probe_clear_and_ambiguous():
    item = WishlistItem(
        id="i1", title="M", year=None, kind="movie", created_at="", note=""
    )
    meta = {"year": None, "content_type": "movie"}
    cands_raw = [
        {"result": {"t": 1}, "title": "A", "score": 10.0, "title_similarity": 0.95},
        {"result": {"t": 2}, "title": "B", "score": 9.9, "title_similarity": 0.94},
    ]
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "list_mediathek_movie_candidates", return_value=cands_raw
    ):
        r = probe_wishlist_item(item)
        assert r["status"] == "ambiguous"
        assert len(r["candidates"]) == 2

    cands_clear = [
        {"result": {"t": 1}, "title": "A", "score": 20.0, "title_similarity": 0.99},
        {"result": {"t": 2}, "title": "B", "score": 2.0, "title_similarity": 0.3},
    ]
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "list_mediathek_movie_candidates", return_value=cands_clear
    ):
        r = probe_wishlist_item(item)
        assert r["status"] == "clear"


def test_process_wishlist_removes_on_success(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "X", None, "movie")

    args = _args_base(tmp_path)
    os.makedirs(args.download_dir, exist_ok=True)

    fake_result = {"title": "X", "url_video": "http://example.com/x.mp4"}
    meta = {"year": None, "content_type": "movie", "provider_id": None}

    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "search_mediathek", return_value=fake_result
    ), patch.object(
        wc.core,
        "download_content",
        return_value=(True, "X", str(tmp_path / "dl" / "f.mp4"), False),
    ):
        proc, succ = process_wishlist_items(str(p), args, remove_on_success=True)
        assert proc == 1
        assert succ == 1
        assert load_wishlist(str(p))["items"] == []


def test_process_wishlist_series_erste_success(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "SerieY", None, "series")
    args = _args_base(tmp_path)
    os.makedirs(args.download_dir, exist_ok=True)
    fake = {"title": "E1", "url_video": "http://example.com/e.mp4"}
    meta = {"year": None, "content_type": "tv", "provider_id": None}
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "search_mediathek", return_value=fake
    ), patch.object(wc.core, "extract_episode_info", return_value=(1, 1)), patch.object(
        wc.core,
        "download_content",
        return_value=(True, "E1", str(tmp_path / "dl" / "f.mp4"), False),
    ):
        proc, succ = process_wishlist_items(p, args, remove_on_success=True)
        assert proc == 1
        assert succ == 1
        assert load_wishlist(p)["items"] == []


def test_process_wishlist_series_staffel_one_episode(tmp_path):
    p = str(tmp_path / "wl.json")
    add_item(p, "StaffelZ", None, "series")
    args = _args_base(tmp_path, serien_download="staffel")
    os.makedirs(args.download_dir, exist_ok=True)
    ep = {"title": "S01E01", "url_video": "http://example.com/1.mp4"}
    meta = {"year": None, "content_type": "tv", "provider_id": None}
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "search_mediathek_series", return_value=[ep]
    ), patch.object(wc.core, "extract_episode_info", return_value=(1, 1)), patch.object(
        wc.core, "score_movie", return_value=100.0
    ), patch.object(
        wc.core,
        "download_content",
        return_value=(True, "S01E01", str(tmp_path / "dl" / "out.mp4"), False),
    ):
        proc, succ = process_wishlist_items(p, args, remove_on_success=True)
        assert proc == 1
        assert succ == 1
        assert load_wishlist(p)["items"] == []


def test_process_one_wishlist_item_not_found_item(tmp_path):
    p = str(tmp_path / "wl.json")
    save_wishlist(p, {"version": 1, "items": []})
    args = _args_base(tmp_path)
    ok, code = process_one_wishlist_item(p, "missing-id", args)
    assert ok is False
    assert code == "not_found_item"


def test_process_one_wishlist_item_movie_with_candidates(tmp_path):
    p = str(tmp_path / "wl.json")
    it = add_item(p, "FilmQ", None, "movie")
    args = _args_base(tmp_path)
    os.makedirs(args.download_dir, exist_ok=True)
    meta = {"year": None, "content_type": "movie", "provider_id": None}
    cand = {
        "result": {"title": "FilmQ", "url_video": "http://example.com/q.mp4"},
        "title": "FilmQ",
        "score": 10.0,
        "title_similarity": 1.0,
    }
    with patch.object(wc.core, "get_metadata", return_value=meta), patch.object(
        wc.core, "list_mediathek_movie_candidates", return_value=[cand]
    ), patch.object(
        wc.core,
        "download_content",
        return_value=(True, "FilmQ", str(tmp_path / "dl" / "q.mp4"), False),
    ):
        ok, code = process_one_wishlist_item(p, it.id, args, candidate_index=0)
        assert ok is True
        assert code == "success"
        assert load_wishlist(p)["items"] == []


def test_load_save_roundtrip(tmp_path):
    p = tmp_path / "wl.json"
    save_wishlist(str(p), {"version": 1, "items": []})
    data = load_wishlist(str(p))
    assert data["version"] == 1
    assert data["items"] == []


def test_add_remove_item(tmp_path):
    p = tmp_path / "wl.json"
    it = add_item(str(p), "Testfilm", 2024, "movie")
    assert it.title == "Testfilm"
    assert it.year == 2024
    loaded = load_wishlist(str(p))
    assert len(loaded["items"]) == 1
    assert remove_item(str(p), it.id)
    assert len(load_wishlist(str(p))["items"]) == 0
    assert not remove_item(str(p), "bogus")
