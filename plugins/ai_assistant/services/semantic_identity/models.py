from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class IdentityEvidence:
    source: str
    value: str
    confidence: float
    detail: str = ""
    independent_group: str = "other"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["confidence"] = round(max(0.0, min(1.0, self.confidence)), 4)
        return data


@dataclass(slots=True)
class IdentityCandidate:
    media_type: str
    title: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    edition: str | None = None
    original_title: str | None = None
    external_ids: dict[str, Any] = field(default_factory=dict)
    aliases: set[str] = field(default_factory=set)
    evidence: list[IdentityEvidence] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        groups = sorted({item.independent_group for item in self.evidence})
        return {
            "media_type": self.media_type,
            "title": self.title,
            "year": self.year,
            "season": self.season,
            "episode": self.episode,
            "edition": self.edition,
            "original_title": self.original_title,
            "external_ids": dict(self.external_ids),
            "aliases": sorted(self.aliases),
            "evidence": [item.to_dict() for item in self.evidence],
            "source_count": len(groups),
            "independent_groups": groups,
        }
