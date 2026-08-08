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
    episode_end: str = ""
    episode_title: str = ""
    edition: str = ""
    part: str = ""
    extra_type: str = ""
    is_special: bool = False
    is_extra: bool = False
    is_bonus: bool = False
    detection_confidence: float = 0.0
    source: str = "filesystem"
    metadata: dict[str, Any] = field(default_factory=dict)
    detection_data: dict[str, Any] = field(default_factory=dict)
    ai_data: dict[str, Any] = field(default_factory=dict)
    quality_data: dict[str, Any] = field(default_factory=dict)
    companion_files: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        metadata: dict[str, Any] | None = None,
        source: str = "filesystem",
        detection: dict[str, Any] | None = None,
    ) -> "MediaItem":
        path = Path(path)
        stat = path.stat() if path.exists() else None
        data = dict(metadata or {})
        detected = dict(detection or {})

        def value(*keys: str, default: str = "") -> str:
            for key in keys:
                if data.get(key) not in (None, ""):
                    return str(data[key])
            for key in keys:
                if detected.get(key) not in (None, ""):
                    return str(detected[key])
            return default

        media_type = value("media_type", default="unknown")
        title = value("titel", "title", default=path.stem)

        return cls(
            path=path,
            name=path.name,
            stem=path.stem,
            extension=path.suffix,
            parent=path.parent,
            item_type="folder" if path.is_dir() else "file",
            size=(stat.st_size if stat and path.is_file() else None),
            modified_time=(stat.st_mtime if stat else None),
            media_type=media_type,
            title=title,
            year=value("jahr", "year"),
            season=value("staffel", "season"),
            episode=value("episode"),
            episode_end=value("episode_end", "episode_bis"),
            episode_title=value("episodentitel", "episode_title"),
            edition=value("edition", "fassung"),
            part=value("part", "teil"),
            extra_type=value("extra_type"),
            is_special=bool(detected.get("is_special", False)),
            is_extra=bool(detected.get("is_extra", False)),
            is_bonus=bool(detected.get("is_bonus", False)),
            detection_confidence=float(detected.get("confidence") or 0.0),
            source=source,
            metadata=data,
            detection_data=detected,
        )

    def rule_metadata(self) -> dict[str, Any]:
        return {
            **self.metadata,
            "titel": self.title,
            "jahr": self.year,
            "staffel": self.season,
            "episode": self.episode,
            "episode_bis": self.episode_end,
            "episodentitel": self.episode_title,
            "edition": self.edition,
            "fassung": self.edition,
            "teil": self.part,
            "part": self.part,
            "extra_type": self.extra_type,
            "is_special": self.is_special,
            "is_extra": self.is_extra,
            "is_bonus": self.is_bonus,
            "medientyp": self.media_type,
            "media_type": self.media_type,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["path"] = str(self.path)
        payload["parent"] = str(self.parent)
        return payload
