"""
Tests für Wishlist-Kernlogik (ohne Netzwerk).
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.wishlist_core import (  # noqa: E402
    add_item,
    load_wishlist,
    process_wishlist_items,
    remove_item,
    save_wishlist,
)


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


def test_process_wishlist_removes_on_success(tmp_path):
    p = tmp_path / "wl.json"
    add_item(str(p), "X", None, "movie")

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

    args = Args()
    os.makedirs(args.download_dir, exist_ok=True)

    fake_result = {"title": "X", "url_video": "http://example.com/x.mp4"}
    meta = {"year": None, "content_type": "movie", "provider_id": None}

    with patch("src.wishlist_core.core.get_metadata", return_value=meta), patch(
        "src.wishlist_core.core.search_mediathek", return_value=fake_result
    ), patch(
        "src.wishlist_core.core.download_content",
        return_value=(True, "X", str(tmp_path / "dl" / "f.mp4"), False),
    ):
        proc, succ = process_wishlist_items(str(p), args, remove_on_success=True)
        assert proc == 1
        assert succ == 1
        assert load_wishlist(str(p))["items"] == []
