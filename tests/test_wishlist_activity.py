"""
Tests für wishlist_activity (Aktivitätslog ohne GUI).
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.wishlist_activity import (  # noqa: E402
    ACTIVITY_FILENAME,
    LEGACY_WISHLIST_ACTIVITY,
    append_activity,
    clear_activity,
    default_activity_path,
    list_activity,
    log_activity_event,
    log_wishlist_item_result,
    resolve_activity_path,
    summarize_probe_for_log,
)


class TestResolveActivityPath:
    def test_migrates_legacy_file(self, tmp_path):
        old = tmp_path / LEGACY_WISHLIST_ACTIVITY
        payload = {
            "version": 2,
            "entries": [
                {
                    "ts": "2021-01-01T00:00:00+00:00",
                    "action": "t",
                    "label": "L",
                    "detail": "",
                    "level": "info",
                    "source": "cli",
                }
            ],
        }
        old.write_text(json.dumps(payload), encoding="utf-8")
        new = tmp_path / ACTIVITY_FILENAME
        assert not new.exists()
        p = resolve_activity_path(str(tmp_path))
        assert p == str(new)
        assert new.exists()

    def test_no_migration_when_new_already_exists(self, tmp_path):
        new = tmp_path / ACTIVITY_FILENAME
        new.write_text('{"version":2,"entries":[]}', encoding="utf-8")
        old = tmp_path / LEGACY_WISHLIST_ACTIVITY
        old.write_text('{"version":2,"entries":[]}', encoding="utf-8")
        p = resolve_activity_path(str(tmp_path))
        assert p == str(new)


class TestListAndClear:
    def test_list_missing_file(self, tmp_path):
        assert list_activity(str(tmp_path / "nope.json")) == []

    def test_list_invalid_json(self, tmp_path):
        p = tmp_path / ACTIVITY_FILENAME
        p.write_text("{not json", encoding="utf-8")
        assert list_activity(str(p)) == []

    def test_clear_activity(self, tmp_path):
        p = tmp_path / ACTIVITY_FILENAME
        append_activity(str(p), "a", "lbl")
        clear_activity(str(p))
        assert list_activity(str(p)) == []

    def test_list_limit_clamped(self, tmp_path):
        p = tmp_path / ACTIVITY_FILENAME
        for i in range(3):
            append_activity(str(p), "a", f"x{i}")
        assert len(list_activity(str(p), limit=2)) == 2
        assert len(list_activity(str(p), limit=0)) == 1


def test_default_activity_path(tmp_path):
    assert default_activity_path(str(tmp_path)) == str(tmp_path / ACTIVITY_FILENAME)


class TestSummarizeProbe:
    def test_not_found(self):
        s, lvl = summarize_probe_for_log({"status": "not_found"})
        assert "Kein Treffer" in s
        assert lvl == "warning"

    def test_staffel_available(self):
        s, _ = summarize_probe_for_log({"status": "staffel_available", "episode_count": 5})
        assert "Staffel" in s
        assert "5" in s

    def test_serien_skipped_uses_message(self):
        s, lvl = summarize_probe_for_log({"status": "serien_skipped", "message": "Eigene Meldung"})
        assert s == "Eigene Meldung"
        assert lvl == "warning"

    def test_ambiguous_clear_other(self):
        assert summarize_probe_for_log({"status": "ambiguous"})[1] == "info"
        assert summarize_probe_for_log({"status": "clear"})[1] == "success"
        s, _ = summarize_probe_for_log({"status": "unknown"})
        assert "Status" in s


class TestLogWishlistItemResult:
    def test_success(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "Titel", True, "success", "cli")
        e = list_activity(resolve_activity_path(dd))
        assert e[0]["level"] == "success"

    def test_debug(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", True, "debug", "web")
        assert "Debug" in list_activity(resolve_activity_path(dd))[0]["detail"]

    def test_not_found(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", False, "not_found", "cli")
        assert list_activity(resolve_activity_path(dd))[0]["level"] == "warning"

    def test_not_found_item(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", False, "not_found_item", "cli")
        d = list_activity(resolve_activity_path(dd))[0]["detail"].lower()
        assert "wishlist" in d or "eintrag" in d

    def test_serien_skipped(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", False, "serien_skipped", "cli")
        assert "Serien" in list_activity(resolve_activity_path(dd))[0]["detail"] or "deaktiviert" in list_activity(
            resolve_activity_path(dd)
        )[0]["detail"].lower()

    def test_ok_other_code(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", True, "partial", "cli")
        e = list_activity(resolve_activity_path(dd))[0]
        assert e["level"] == "success"
        assert "partial" in e["detail"]

    def test_fail_other_code(self, tmp_path):
        dd = str(tmp_path)
        log_wishlist_item_result(dd, "T", False, "failed", "cli")
        assert list_activity(resolve_activity_path(dd))[0]["level"] == "error"

    def test_no_download_dir(self):
        log_wishlist_item_result(None, "T", True, "success", "cli")


class TestLogActivityEvent:
    def test_skips_without_download_dir(self):
        log_activity_event(None, "a", "b")

    def test_writes(self, tmp_path):
        dd = str(tmp_path)
        log_activity_event(dd, "act", "lab", "det", "warning", "gui")
        e = list_activity(resolve_activity_path(dd))
        assert e[0]["action"] == "act"
        assert e[0]["source"] == "gui"
