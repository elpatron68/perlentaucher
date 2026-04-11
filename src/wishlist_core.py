"""
Wishlist: persistente Merkliste für Filme/Serien; Verarbeitung über MediathekViewWeb.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

# Kernlogik aus perlentaucher (lazy würde Zyklen erzeugen — direkter Import)
from src import perlentaucher as core

WishlistKind = Literal["movie", "series"]


def _notify_download_kwargs(args: Any) -> Dict[str, Any]:
    """Apprise/Ntfy: Wishlist-Kontext für download_content."""
    nu = getattr(args, "notify", None)
    if nu:
        return {"notify_url": nu, "notify_source": "wishlist"}
    return {"notify_url": None, "notify_source": None}


@dataclass
class WishlistItem:
    id: str
    title: str
    year: Optional[int]
    kind: WishlistKind
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WishlistItem":
        return cls(
            id=data["id"],
            title=data["title"],
            year=data.get("year"),
            kind=data.get("kind", "movie"),
            created_at=data.get("created_at", datetime.now().isoformat(timespec="seconds")),
            note=data.get("note") or "",
        )


def default_wishlist_path(download_dir: Optional[str] = None) -> str:
    base = download_dir or os.getcwd()
    return os.path.join(base, ".perlentaucher_wishlist.json")


def load_wishlist(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"version": 1, "items": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "items" not in data:
            data = {"version": 1, "items": []}
        return data
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Wishlist konnte nicht geladen werden ({path}): {e}")
        return {"version": 1, "items": []}


def save_wishlist(path: str, data: Dict[str, Any]) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_items(path: str) -> List[WishlistItem]:
    data = load_wishlist(path)
    return [WishlistItem.from_dict(x) for x in data.get("items", [])]


def add_item(
    path: str,
    title: str,
    year: Optional[int],
    kind: WishlistKind,
    note: str = "",
) -> WishlistItem:
    data = load_wishlist(path)
    item = WishlistItem(
        id=str(uuid.uuid4()),
        title=title.strip(),
        year=year,
        kind=kind,
        note=note.strip(),
    )
    data.setdefault("items", []).append(item.to_dict())
    save_wishlist(path, data)
    return item


def remove_item(path: str, item_id: str) -> bool:
    data = load_wishlist(path)
    items = data.get("items", [])
    new_items = [x for x in items if x.get("id") != item_id]
    if len(new_items) == len(items):
        return False
    data["items"] = new_items
    save_wishlist(path, data)
    return True


def _synthetic_entry(movie_title: str, kind: WishlistKind) -> Dict[str, Any]:
    tags: List[Any] = []
    if kind == "series":
        tags = [{"term": "TV-Serien"}]
    return {"title": movie_title, "tags": tags}


def _metadata_for_item(
    movie_title: str,
    year: Optional[int],
    kind: WishlistKind,
    tmdb_key: Optional[str],
    omdb_key: Optional[str],
) -> Dict[str, Any]:
    metadata = core.get_metadata(movie_title, year, tmdb_key, omdb_key)
    if not metadata.get("year") and year:
        metadata["year"] = year
    if kind == "series":
        metadata["content_type"] = "tv"
    else:
        metadata["content_type"] = "movie"
    return metadata


def check_item_available(
    movie_title: str,
    year: Optional[int],
    kind: WishlistKind,
    metadata: Dict[str, Any],
    sprache: str,
    audiodeskription: str,
    serien_download: str,
) -> bool:
    """Prüft ob Mediathek mindestens einen Treffer liefert (ohne Download)."""
    is_series = kind == "series"
    if not is_series:
        r = core.search_mediathek(
            movie_title,
            prefer_language=sprache,
            prefer_audio_desc=audiodeskription,
            notify_url=None,
            entry_link="",
            year=year,
            metadata=metadata,
            debug=False,
        )
        return r is not None
    if serien_download == "staffel":
        eps = core.search_mediathek_series(
            movie_title,
            prefer_language=sprache,
            prefer_audio_desc=audiodeskription,
            year=year,
            metadata=metadata,
            debug=False,
        )
        return bool(eps)
    r = core.search_mediathek(
        movie_title,
        prefer_language=sprache,
        prefer_audio_desc=audiodeskription,
        notify_url=None,
        entry_link="",
        year=year,
        metadata=metadata,
        debug=False,
    )
    return r is not None


def check_wishlist_availability(
    path: str,
    sprache: str = "deutsch",
    audiodeskription: str = "egal",
    serien_download: str = "erste",
    tmdb_api_key: Optional[str] = None,
    omdb_api_key: Optional[str] = None,
) -> Tuple[List[WishlistItem], int]:
    """Gibt Wishlist-Einträge zurück, die aktuell in der Mediathek auffindbar sind, und die Gesamtanzahl."""
    available: List[WishlistItem] = []
    items = list_items(path)
    total = len(items)
    for item in items:
        meta = _metadata_for_item(item.title, item.year, item.kind, tmdb_api_key, omdb_api_key)
        if check_item_available(
            item.title,
            item.year,
            item.kind,
            meta,
            sprache,
            audiodeskription,
            serien_download,
        ):
            available.append(item)
    return available, total


def _classify_movie_probe(candidates: List[Dict[str, Any]]) -> str:
    """'clear' = ein dominanter Treffer, 'ambiguous' = Nutzer soll wählen."""
    if len(candidates) <= 1:
        return "clear"
    s0, s1 = candidates[0]["score"], candidates[1]["score"]
    sim0, sim1 = candidates[0]["title_similarity"], candidates[1]["title_similarity"]
    top = max(abs(s0), 1e-6)
    score_gap_ratio = (s0 - s1) / top
    sim_gap = sim0 - sim1
    if score_gap_ratio > 0.06 and sim_gap > 0.1:
        return "clear"
    return "ambiguous"


def probe_wishlist_item(
    item: WishlistItem,
    sprache: str = "deutsch",
    audiodeskription: str = "egal",
    serien_download: str = "erste",
    tmdb_api_key: Optional[str] = None,
    omdb_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Prüft einen Eintrag direkt nach dem Hinzufügen (MediathekViewWeb).
    Rückgabe ist JSON-tauglich (keine rohen API-Objekte).
    """
    meta = _metadata_for_item(item.title, item.year, item.kind, tmdb_api_key, omdb_api_key)

    if item.kind == "series" and serien_download == "keine":
        return {
            "status": "serien_skipped",
            "message": "Serien-Download ist auf „keine“ gestellt — Eintrag bleibt nur auf der Liste.",
        }

    if item.kind == "series" and serien_download == "staffel":
        eps = core.search_mediathek_series(
            item.title,
            prefer_language=sprache,
            prefer_audio_desc=audiodeskription,
            notify_url=None,
            entry_link="",
            year=item.year,
            metadata=meta,
            debug=False,
        )
        if not eps:
            return {"status": "not_found"}
        return {
            "status": "staffel_available",
            "episode_count": len(eps),
        }

    raw = core.list_mediathek_movie_candidates(
        item.title,
        prefer_language=sprache,
        prefer_audio_desc=audiodeskription,
        year=item.year,
        metadata=meta,
        limit=8,
    )
    if not raw:
        return {"status": "not_found"}

    pub = [
        {
            "index": i,
            "title": x["title"],
            "score": x["score"],
            "title_similarity": x["title_similarity"],
        }
        for i, x in enumerate(raw)
    ]
    sub = _classify_movie_probe(raw)
    return {
        "status": "ambiguous" if sub == "ambiguous" else "clear",
        "candidates": pub,
    }


def _process_movie_with_result(
    result: Dict[str, Any],
    movie_title: str,
    year: Optional[int],
    metadata: Dict[str, Any],
    entry_link: str,
    args: Any,
    entry_id: str,
    state_file: Optional[str],
) -> Tuple[bool, str]:
    if not result:
        if state_file:
            core.save_processed_entry(state_file, entry_id, status="not_found", movie_title=movie_title)
        return False, "not_found"
    if args.debug_no_download:
        fp = core.build_download_filepath(
            result, args.download_dir, movie_title, metadata, is_series=False, create_dirs=False
        )
        logging.info(f"DEBUG-MODUS: Wishlist-Film übersprungen: '{result.get('title')}' -> {fp}")
        return True, "debug"
    success, title, filepath, _sk = core.download_content(
        result, args.download_dir, movie_title, metadata, is_series=False, **_notify_download_kwargs(args)
    )
    if state_file:
        st = "download_success" if success else "download_failed"
        fn = os.path.basename(filepath) if filepath else None
        core.save_processed_entry(state_file, entry_id, status=st, movie_title=movie_title, filename=fn)
    return success, "success" if success else "failed"


def _process_series_erste_with_result(
    result: Dict[str, Any],
    movie_title: str,
    year: Optional[int],
    metadata: Dict[str, Any],
    entry_link: str,
    args: Any,
    entry_id: str,
    state_file: Optional[str],
) -> Tuple[bool, str]:
    if not result:
        return False, "not_found"
    season, episode = core.extract_episode_info(result, movie_title)
    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
    if args.debug_no_download:
        fp = core.build_download_filepath(
            result,
            args.download_dir,
            movie_title,
            metadata,
            is_series=True,
            series_base_dir=series_base_dir,
            season=season,
            episode=episode,
            create_dirs=False,
        )
        logging.info(f"DEBUG-MODUS: Wishlist-Serie übersprungen: '{result.get('title')}' -> {fp}")
        return True, "debug"
    success, title, filepath, _sk = core.download_content(
        result,
        args.download_dir,
        movie_title,
        metadata,
        is_series=True,
        series_base_dir=series_base_dir,
        season=season,
        episode=episode,
        **_notify_download_kwargs(args),
    )
    if state_file:
        st = "download_success" if success else "download_failed"
        fn = os.path.basename(filepath) if filepath else None
        core.save_processed_entry(
            state_file, entry_id, status=st, movie_title=movie_title, filename=fn, is_series=True
        )
    return success, "success" if success else "failed"


def process_one_wishlist_item(
    path: str,
    item_id: str,
    args: Any,
    candidate_index: int = 0,
    remove_on_success: bool = True,
) -> Tuple[bool, str]:
    """
    Verarbeitet genau einen Wishlist-Eintrag. Bei Film/Serie (erste Folge) kann ``candidate_index``
    die Auswahl aus list_mediathek_movie_candidates steuern. Bei Staffel-Modus wird die komplette Staffel geladen.
    """
    data = load_wishlist(path)
    raw_item = next((x for x in data.get("items", []) if x.get("id") == item_id), None)
    if not raw_item:
        return False, "not_found_item"
    item = WishlistItem.from_dict(raw_item)
    metadata = _metadata_for_item(
        item.title, item.year, item.kind, getattr(args, "tmdb_api_key", None), getattr(args, "omdb_api_key", None)
    )
    entry_id = f"wishlist:{item.id}"
    entry_link = f"wishlist:{item.id}"
    state_file = None if getattr(args, "no_state", False) else getattr(args, "state_file", None)
    serien_mode = getattr(args, "serien_download", "erste")

    if item.kind == "series" and serien_mode == "keine":
        return False, "serien_skipped"

    if item.kind == "series" and serien_mode == "staffel":
        ok, code = _process_series_staffel(
            item.title, item.year, metadata, entry_link, args, entry_id, state_file
        )
    elif item.kind == "series":
        cands = core.list_mediathek_movie_candidates(
            item.title,
            prefer_language=args.sprache,
            prefer_audio_desc=args.audiodeskription,
            year=item.year,
            metadata=metadata,
            limit=8,
        )
        if not cands:
            return False, "not_found"
        ci = max(0, min(int(candidate_index), len(cands) - 1))
        ok, code = _process_series_erste_with_result(
            cands[ci]["result"], item.title, item.year, metadata, entry_link, args, entry_id, state_file
        )
    else:
        cands = core.list_mediathek_movie_candidates(
            item.title,
            prefer_language=args.sprache,
            prefer_audio_desc=args.audiodeskription,
            year=item.year,
            metadata=metadata,
            limit=8,
        )
        if not cands:
            return False, "not_found"
        ci = max(0, min(int(candidate_index), len(cands) - 1))
        ok, code = _process_movie_with_result(
            cands[ci]["result"], item.title, item.year, metadata, entry_link, args, entry_id, state_file
        )

    if ok and code == "success" and remove_on_success:
        remove_item(path, item_id)
    return ok, code


def _process_series_erste(
    movie_title: str,
    year: Optional[int],
    metadata: Dict[str, Any],
    entry_link: str,
    args: Any,
    entry_id: str,
    state_file: Optional[str],
) -> Tuple[bool, str]:
    result = core.search_mediathek(
        movie_title,
        prefer_language=args.sprache,
        prefer_audio_desc=args.audiodeskription,
        notify_url=args.notify,
        entry_link=entry_link,
        year=year,
        metadata=metadata,
        debug=args.debug_no_download,
    )
    if not result:
        return False, "not_found"
    season, episode = core.extract_episode_info(result, movie_title)
    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
    if args.debug_no_download:
        fp = core.build_download_filepath(
            result,
            args.download_dir,
            movie_title,
            metadata,
            is_series=True,
            series_base_dir=series_base_dir,
            season=season,
            episode=episode,
            create_dirs=False,
        )
        logging.info(f"DEBUG-MODUS: Wishlist-Serie übersprungen: '{result.get('title')}' -> {fp}")
        return True, "debug"
    success, title, filepath, _sk = core.download_content(
        result,
        args.download_dir,
        movie_title,
        metadata,
        is_series=True,
        series_base_dir=series_base_dir,
        season=season,
        episode=episode,
        **_notify_download_kwargs(args),
    )
    if state_file:
        st = "download_success" if success else "download_failed"
        fn = os.path.basename(filepath) if filepath else None
        core.save_processed_entry(
            state_file, entry_id, status=st, movie_title=movie_title, filename=fn, is_series=True
        )
    return success, "success" if success else "failed"


def _process_series_staffel(
    movie_title: str,
    year: Optional[int],
    metadata: Dict[str, Any],
    entry_link: str,
    args: Any,
    entry_id: str,
    state_file: Optional[str],
) -> Tuple[bool, str]:
    episodes = core.search_mediathek_series(
        movie_title,
        prefer_language=args.sprache,
        prefer_audio_desc=args.audiodeskription,
        notify_url=args.notify,
        entry_link=entry_link,
        year=year,
        metadata=metadata,
        debug=args.debug_no_download,
    )
    if not episodes:
        if state_file:
            core.save_processed_entry(
                state_file, entry_id, status="not_found", movie_title=movie_title, is_series=True
            )
        return False, "not_found"
    series_base_dir = args.serien_dir if args.serien_dir else args.download_dir
    episodes_dict: Dict[Tuple[int, int], Tuple[float, Any]] = {}
    episodes_without_info: List[Any] = []
    for episode_data in episodes:
        season, episode_num = core.extract_episode_info(episode_data, movie_title)
        if season is None or episode_num is None:
            episodes_without_info.append(episode_data)
            continue
        score = core.score_movie(
            episode_data,
            args.sprache,
            args.audiodeskription,
            search_title=movie_title,
            search_year=year,
            metadata=metadata,
        )
        episode_key = (season, episode_num)
        if episode_key not in episodes_dict or score > episodes_dict[episode_key][0]:
            episodes_dict[episode_key] = (score, episode_data)
    if episodes_without_info:
        max_ep_s1 = max((e for (s, e) in episodes_dict if s == 1), default=0)
        for i, episode_data in enumerate(episodes_without_info):
            fallback_ep = max_ep_s1 + 1 + i
            score = core.score_movie(
                episode_data,
                args.sprache,
                args.audiodeskription,
                search_title=movie_title,
                search_year=year,
                metadata=metadata,
            )
            key = (1, fallback_ep)
            if key not in episodes_dict or score > episodes_dict[key][0]:
                episodes_dict[key] = (score, episode_data)
    episodes_with_info = [(s, e, data) for (s, e), (score, data) in episodes_dict.items()]
    episodes_with_info.sort(key=lambda x: (x[0] or 0, x[1] or 0))
    total_episodes = len(episodes_with_info)
    if args.debug_no_download:
        logging.info(f"DEBUG-MODUS: Wishlist-Staffel übersprungen ({total_episodes} Episoden)")
        return True, "debug"
    downloaded_count = 0
    for season, episode_num, episode_data in episodes_with_info:
        if season is None or episode_num is None:
            continue
        success, title, filepath, _sk = core.download_content(
            episode_data,
            args.download_dir,
            movie_title,
            metadata,
            is_series=True,
            series_base_dir=series_base_dir,
            season=season,
            episode=episode_num,
            **_notify_download_kwargs(args),
        )
        if success:
            downloaded_count += 1
        if state_file:
            eid = f"{entry_id}_S{season:02d}E{episode_num:02d}"
            st = "download_success" if success else "download_failed"
            fn = os.path.basename(filepath) if filepath else None
            core.save_processed_entry(
                state_file,
                eid,
                status=st,
                movie_title=f"{movie_title} S{season:02d}E{episode_num:02d}",
                filename=fn,
            )
    if state_file:
        status = "download_success" if downloaded_count > 0 else "download_failed"
        ep_list = [f"S{s:02d}E{e:02d}" for s, e, _ in episodes_with_info if s is not None and e is not None]
        core.save_processed_entry(
            state_file,
            entry_id,
            status=status,
            movie_title=movie_title,
            is_series=True,
            episodes=ep_list,
        )
    ok = downloaded_count > 0
    return ok, "success" if ok else "failed"


def _process_movie(
    movie_title: str,
    year: Optional[int],
    metadata: Dict[str, Any],
    entry_link: str,
    args: Any,
    entry_id: str,
    state_file: Optional[str],
) -> Tuple[bool, str]:
    result = core.search_mediathek(
        movie_title,
        prefer_language=args.sprache,
        prefer_audio_desc=args.audiodeskription,
        notify_url=args.notify,
        entry_link=entry_link,
        year=year,
        metadata=metadata,
        debug=args.debug_no_download,
    )
    if not result:
        if state_file:
            core.save_processed_entry(state_file, entry_id, status="not_found", movie_title=movie_title)
        return False, "not_found"
    if args.debug_no_download:
        fp = core.build_download_filepath(
            result, args.download_dir, movie_title, metadata, is_series=False, create_dirs=False
        )
        logging.info(f"DEBUG-MODUS: Wishlist-Film übersprungen: '{result.get('title')}' -> {fp}")
        return True, "debug"
    success, title, filepath, _sk = core.download_content(
        result, args.download_dir, movie_title, metadata, is_series=False, **_notify_download_kwargs(args)
    )
    if state_file:
        st = "download_success" if success else "download_failed"
        fn = os.path.basename(filepath) if filepath else None
        core.save_processed_entry(state_file, entry_id, status=st, movie_title=movie_title, filename=fn)
    return success, "success" if success else "failed"


def process_wishlist_items(
    path: str,
    args: Any,
    remove_on_success: bool = True,
) -> Tuple[int, int]:
    """
    Verarbeitet alle Wishlist-Einträge. Entfernt erfolgreich verarbeitete Einträge (Download geklappt).

    Returns:
        (processed_count, success_count)
    """
    data = load_wishlist(path)
    items_raw = data.get("items", [])
    if not items_raw:
        logging.info("Wishlist ist leer.")
        return 0, 0

    state_file = None if getattr(args, "no_state", False) else getattr(args, "state_file", None)
    tmdb_key = getattr(args, "tmdb_api_key", None)
    omdb_key = getattr(args, "omdb_api_key", None)
    serien_mode = getattr(args, "serien_download", "erste")

    processed = 0
    successes = 0
    remaining: List[Dict[str, Any]] = []

    for raw in items_raw:
        item = WishlistItem.from_dict(raw)
        movie_title = item.title
        year = item.year
        kind = item.kind
        entry_id = f"wishlist:{item.id}"
        entry_link = f"wishlist:{item.id}"
        metadata = _metadata_for_item(movie_title, year, kind, tmdb_key, omdb_key)
        is_series = kind == "series"

        logging.info(f"Wishlist: '{movie_title}' ({kind}, Jahr={year})")

        if is_series:
            if serien_mode == "keine":
                logging.info(f"Wishlist: Serie übersprungen (serien-download=keine): {movie_title}")
                remaining.append(raw)
                processed += 1
                continue
            if serien_mode == "erste":
                ok, code = _process_series_erste(
                    movie_title, year, metadata, entry_link, args, entry_id, state_file
                )
            else:
                ok, code = _process_series_staffel(
                    movie_title, year, metadata, entry_link, args, entry_id, state_file
                )
        else:
            ok, code = _process_movie(
                movie_title, year, metadata, entry_link, args, entry_id, state_file
            )

        processed += 1
        if ok and code == "success" and remove_on_success:
            successes += 1
            logging.info(f"Wishlist: Eintrag erledigt und entfernt: {movie_title}")
            continue
        remaining.append(raw)

    data["items"] = remaining
    save_wishlist(path, data)
    return processed, successes
