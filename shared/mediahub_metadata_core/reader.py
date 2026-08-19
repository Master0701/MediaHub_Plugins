from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .formats import capability_for_extension

TAG_ALIASES = {
    "title": ("title",),
    "description": ("description", "comment", "synopsis"),
    "year": ("year", "date", "creation_time"),
    "published_at": ("date", "creation_time"),
    "series": ("show", "showtitle", "series"),
    "season": ("season_number", "season"),
    "episode": ("episode_sort", "episode_id", "episode"),
    "episode_title": ("episode_title",),
    "artist": ("artist",),
    "album": ("album",),
    "album_artist": ("album_artist", "albumartist"),
    "track": ("track",),
    "disc": ("disc",),
    "genre": ("genre",),
    "composer": ("composer",),
    "comment": ("comment",),
    "author": ("author", "artist"),
    "narrator": ("narrator", "performer"),
    "book_series": ("series",),
    "book_series_index": ("series-part", "series_part"),
    "publisher": ("publisher",),
}


def _first(tags: dict[str, Any], names: tuple[str, ...]):
    for name in names:
        value = tags.get(name)
        if value not in (None, ""):
            return value
    return None


def _integer(value):
    if value in (None, ""):
        return None

    text = str(value).strip()

    # Track/Disc können z.B. "3/12" enthalten.
    if "/" in text:
        text = text.split("/", 1)[0].strip()

    # Datumswerte wie 2026-08-16 -> Jahr.
    if (
        len(text) >= 4
        and text[:4].isdigit()
        and ("-" in text or ":" in text)
    ):
        return int(text[:4])

    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def normalize_tags(
    extension: str,
    raw_tags: dict[str, Any],
) -> dict[str, Any]:
    capability = capability_for_extension(extension)

    if not capability.get("supported"):
        return {}

    tags = {
        str(key).strip().lower(): value
        for key, value in dict(raw_tags or {}).items()
    }

    allowed = set(capability.get("read_fields") or ())
    result: dict[str, Any] = {}

    for field, aliases in TAG_ALIASES.items():
        if field not in allowed:
            continue

        value = _first(tags, aliases)

        if value in (None, ""):
            continue

        if field in {
            "year",
            "season",
            "episode",
            "track",
            "disc",
            "book_series_index",
        }:
            value = _integer(value)
            if value is None:
                continue

        result[field] = value

    return result


def read_embedded_metadata(
    path: str | Path,
    ffprobe_path: str | Path,
) -> dict[str, Any]:
    media_path = Path(path)
    capability = capability_for_extension(media_path.suffix)

    if not capability.get("supported"):
        return {
            "ok": False,
            "supported": False,
            "path": str(media_path),
            "tags": {},
            "raw_tags": {},
            "message": "Dateiformat wird vom Metadata-Core nicht unterstützt.",
        }

    if not media_path.is_file():
        return {
            "ok": False,
            "supported": True,
            "path": str(media_path),
            "tags": {},
            "raw_tags": {},
            "message": "Mediendatei wurde nicht gefunden.",
        }

    probe = Path(ffprobe_path)

    if not probe.is_file():
        return {
            "ok": False,
            "supported": True,
            "path": str(media_path),
            "tags": {},
            "raw_tags": {},
            "message": "FFprobe ist nicht verfügbar.",
        }

    process = subprocess.run(
        [
            str(probe),
            "-v",
            "error",
            "-show_entries",
            "format_tags",
            "-of",
            "json",
            str(media_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    if process.returncode != 0:
        return {
            "ok": False,
            "supported": True,
            "path": str(media_path),
            "tags": {},
            "raw_tags": {},
            "message": (
                process.stderr.strip()
                or "FFprobe konnte die Metadaten nicht lesen."
            ),
        }

    try:
        payload = json.loads(process.stdout or "{}")
    except json.JSONDecodeError:
        return {
            "ok": False,
            "supported": True,
            "path": str(media_path),
            "tags": {},
            "raw_tags": {},
            "message": "FFprobe lieferte ungültige JSON-Daten.",
        }

    raw_tags = dict(
        (payload.get("format") or {}).get("tags") or {}
    )

    tags = normalize_tags(
        media_path.suffix,
        raw_tags,
    )

    return {
        "ok": True,
        "supported": True,
        "path": str(media_path),
        "kind": capability.get("kind"),
        "container": capability.get("container"),
        "tags": tags,
        "raw_tags": raw_tags,
        "message": "Eingebettete Metadaten wurden gelesen.",
    }
