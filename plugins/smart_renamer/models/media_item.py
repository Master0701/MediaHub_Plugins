from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MediaItem:
    """Plattformneutrales Eingabemodell für Renamer und spätere Plugins."""

    path: Path
    name: str
    stem: str
    extension: str
    parent: Path
    item_type: str
    size: int | None = None
    modified_time: float | None = None
    media_type: str = "unknown"
    title: str = ""
    year: str = ""
    season: str = ""
    episode: str = ""
    episode_title: str = ""
    source: str = "filesystem"
    metadata: dict[str, Any] = field(default_factory=dict)
    ai_data: dict[str, Any] = field(default_factory=dict)
    quality_data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        metadata: dict[str, Any] | None = None,
        source: str = "filesystem",
    ) -> "MediaItem":
        path = Path(path)
        stat = path.stat() if path.exists() else None
        data = dict(metadata or {})
        return cls(
            path=path,
            name=path.name,
            stem=path.stem,
            extension=path.suffix,
            parent=path.parent,
            item_type="folder" if path.is_dir() else "file",
            size=(stat.st_size if stat and path.is_file() else None),
            modified_time=(stat.st_mtime if stat else None),
            media_type=str(data.get("media_type") or "unknown"),
            title=str(data.get("titel") or data.get("title") or path.stem),
            year=str(data.get("jahr") or data.get("year") or ""),
            season=str(data.get("staffel") or data.get("season") or ""),
            episode=str(data.get("episode") or ""),
            episode_title=str(
                data.get("episodentitel")
                or data.get("episode_title")
                or ""
            ),
            source=source,
            metadata=data,
        )

    def rule_metadata(self) -> dict[str, Any]:
        return {
            **self.metadata,
            "titel": self.title,
            "jahr": self.year,
            "staffel": self.season,
            "episode": self.episode,
            "episodentitel": self.episode_title,
            "media_type": self.media_type,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["parent"] = str(self.parent)
        return payload
