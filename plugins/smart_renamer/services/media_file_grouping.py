from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from models.media_item import MediaItem


VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv",
    ".ts", ".m2ts", ".webm", ".mpg", ".mpeg",
}

SUBTITLE_EXTENSIONS = {
    ".srt", ".ass", ".ssa", ".sub", ".idx", ".sup", ".vtt",
}

METADATA_EXTENSIONS = {
    ".nfo", ".xml", ".json",
}

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
}

CHECKSUM_EXTENSIONS = {
    ".sfv", ".md5", ".sha1", ".sha256",
}

TEXT_EXTENSIONS = {
    ".txt", ".md", ".log",
}

PLAYLIST_EXTENSIONS = {
    ".m3u", ".m3u8", ".pls", ".cue",
}

EPISODE_PATTERN = re.compile(
    r"(?i)\bS(?P<season>\d{1,3})[ ._-]*E(?P<episode>\d{1,4})\b"
)

LANGUAGE_TOKENS = {
    "de": "de",
    "ger": "de",
    "german": "de",
    "deu": "de",
    "en": "en",
    "eng": "en",
    "english": "en",
    "fr": "fr",
    "fre": "fr",
    "fra": "fr",
    "french": "fr",
    "es": "es",
    "spa": "es",
    "it": "it",
    "ita": "it",
}


class MediaFileGrouper:
    """
    Fasst Begleitdateien unter dem eigentlichen Medienobjekt zusammen.

    Primäre Medien bleiben MediaItems. Untertitel, NFOs, Bilder,
    Prüfsummen und ähnliche Begleitdateien werden als `companion_files`
    gespeichert und erscheinen nicht mehr als eigenständige Medienobjekte.
    """

    def group(
        self,
        items: list[MediaItem],
    ) -> tuple[list[MediaItem], list[dict[str, Any]]]:
        primaries = [
            item
            for item in items
            if item.extension.casefold() in VIDEO_EXTENSIONS
            or not self.is_companion(item.path)
        ]
        companions = [
            item
            for item in items
            if self.is_companion(item.path)
        ]

        video_primaries = [
            item
            for item in primaries
            if item.extension.casefold() in VIDEO_EXTENSIONS
        ]

        by_episode: dict[tuple[str, str], list[MediaItem]] = defaultdict(list)
        by_directory: dict[str, list[MediaItem]] = defaultdict(list)

        for item in video_primaries:
            key = self.episode_key(item.path, item.season, item.episode)
            if key:
                by_episode[key].append(item)
            by_directory[str(item.parent.resolve()).casefold()].append(item)

        grouped: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []

        for companion in companions:
            owner = self._find_owner(
                companion,
                video_primaries,
                by_episode,
                by_directory,
            )
            payload = self.describe(companion.path)

            if owner is None:
                payload["group_status"] = "unmatched"
                unmatched.append(payload)
                # Unmatched companions remain visible for safety.
                primaries.append(companion)
                companion.detection_data["companion_file"] = payload
                companion.detection_data["companion_unmatched"] = True
                continue

            payload["group_status"] = "grouped"
            payload["owner_path"] = str(owner.path)
            owner.companion_files.append(payload)
            owner.detection_data["companion_files"] = list(owner.companion_files)
            owner.detection_data["companion_count"] = len(owner.companion_files)
            grouped.append(payload)

        primaries.sort(key=lambda item: str(item.path).casefold())
        return primaries, grouped + unmatched

    @classmethod
    def is_companion(cls, path: Path) -> bool:
        suffix = Path(path).suffix.casefold()
        return suffix in (
            SUBTITLE_EXTENSIONS
            | METADATA_EXTENSIONS
            | IMAGE_EXTENSIONS
            | CHECKSUM_EXTENSIONS
            | TEXT_EXTENSIONS
            | PLAYLIST_EXTENSIONS
        )

    @classmethod
    def describe(cls, path: Path) -> dict[str, Any]:
        path = Path(path)
        suffix = path.suffix.casefold()
        name = path.stem.casefold()

        if suffix in SUBTITLE_EXTENSIONS:
            role = "subtitle"
        elif suffix in METADATA_EXTENSIONS:
            role = "metadata"
        elif suffix in IMAGE_EXTENSIONS:
            role = cls._image_role(name)
        elif suffix in CHECKSUM_EXTENSIONS:
            role = "checksum"
        elif suffix in PLAYLIST_EXTENSIONS:
            role = "playlist"
        else:
            role = "text"

        tokens = {
            value
            for value in re.split(r"[^a-z0-9]+", name)
            if value
        }
        language = ""
        for token in tokens:
            if token in LANGUAGE_TOKENS:
                language = LANGUAGE_TOKENS[token]
                break

        return {
            "path": str(path),
            "name": path.name,
            "extension": suffix,
            "role": role,
            "language": language,
            "forced": "forced" in tokens,
            "sdh": "sdh" in tokens or "hi" in tokens,
        }

    @staticmethod
    def _image_role(name: str) -> str:
        for role in ("poster", "fanart", "thumb", "logo", "banner", "clearart"):
            if role in name:
                return role
        return "image"

    @classmethod
    def episode_key(
        cls,
        path: Path,
        season: str = "",
        episode: str = "",
    ) -> tuple[str, str] | None:
        if season and episode:
            return (
                str(int(season)),
                str(int(episode)),
            )

        match = EPISODE_PATTERN.search(Path(path).stem)
        if match:
            return (
                str(int(match.group("season"))),
                str(int(match.group("episode"))),
            )
        return None

    def _find_owner(
        self,
        companion: MediaItem,
        videos: list[MediaItem],
        by_episode: dict[tuple[str, str], list[MediaItem]],
        by_directory: dict[str, list[MediaItem]],
    ) -> MediaItem | None:
        episode_key = self.episode_key(
            companion.path,
            companion.season,
            companion.episode,
        )

        if episode_key:
            candidates = by_episode.get(episode_key, [])
            if candidates:
                return min(
                    candidates,
                    key=lambda item: self._path_distance(
                        companion.path.parent,
                        item.path.parent,
                    ),
                )

        # Gleiches Verzeichnis: bevorzugt exakter gemeinsamer Namensstamm.
        directory = str(companion.parent.resolve()).casefold()
        local = by_directory.get(directory, [])
        if len(local) == 1:
            return local[0]

        if local:
            companion_base = self._normalized_base(companion.path.stem)
            ranked = sorted(
                local,
                key=lambda item: self._prefix_score(
                    companion_base,
                    self._normalized_base(item.path.stem),
                ),
                reverse=True,
            )
            if ranked and self._prefix_score(
                companion_base,
                self._normalized_base(ranked[0].path.stem),
            ) > 0:
                return ranked[0]

        # Subs-Unterordner: in Eltern/Grandparent nach genau einem Video suchen.
        parent = companion.parent
        for _ in range(3):
            directory = str(parent.resolve()).casefold()
            local = by_directory.get(directory, [])
            if len(local) == 1:
                return local[0]
            parent = parent.parent

        return None

    @staticmethod
    def _normalized_base(value: str) -> str:
        text = value.casefold()
        text = re.sub(
            r"(?i)(?:[-._ ](?:forced|eng|ger|german|english|subs?|sdh|hi))+$",
            "",
            text,
        )
        return re.sub(r"[^a-z0-9]+", "", text)

    @staticmethod
    def _prefix_score(a: str, b: str) -> int:
        count = 0
        for left, right in zip(a, b):
            if left != right:
                break
            count += 1
        return count

    @staticmethod
    def _path_distance(left: Path, right: Path) -> int:
        left_parts = left.resolve().parts
        right_parts = right.resolve().parts
        common = 0
        for a, b in zip(left_parts, right_parts):
            if a.casefold() != b.casefold():
                break
            common += 1
        return (len(left_parts) - common) + (len(right_parts) - common)
