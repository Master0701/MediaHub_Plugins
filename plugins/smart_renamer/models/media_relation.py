from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


RELATION_TYPES = {
    "single",
    "missing_episode",
    "multi_episode",
    "split_episode",
    "split_movie",
    "multi_part",
    "duplicate_candidate",
    "sample",
    "unknown_relation",
}

RECOMMENDED_ACTIONS = {
    "none",
    "keep",
    "rename_only",
    "review",
    "mark_missing",
    "plex_multi_episode_name",
    "plex_split_name",
    "merge_candidate",
    "split_candidate",
}


@dataclass(slots=True)
class MediaRelation:
    relation_type: str = "single"
    episode_start: str = ""
    episode_end: str = ""
    part_number: int | None = None
    part_count: int | None = None
    official_episode_count: int | None = None
    detected_episode_count: int | None = None
    missing_episode_candidates: list[str] = field(default_factory=list)
    recommended_action: str = "none"
    confidence: float = 0.0
    review_required: bool = False
    evidence: list[str] = field(default_factory=list)
    profile_hint: str = ""

    def __post_init__(self) -> None:
        if self.relation_type not in RELATION_TYPES:
            raise ValueError(f"Unbekannter relation_type: {self.relation_type}")
        if self.recommended_action not in RECOMMENDED_ACTIONS:
            raise ValueError(
                f"Unbekannte recommended_action: {self.recommended_action}"
            )
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence muss zwischen 0.0 und 1.0 liegen.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "relation_type": self.relation_type,
            "episode_start": self.episode_start,
            "episode_end": self.episode_end,
            "part_number": self.part_number,
            "part_count": self.part_count,
            "official_episode_count": self.official_episode_count,
            "detected_episode_count": self.detected_episode_count,
            "missing_episode_candidates": list(self.missing_episode_candidates),
            "recommended_action": self.recommended_action,
            "confidence": float(self.confidence),
            "review_required": bool(self.review_required),
            "evidence": list(self.evidence),
            "profile_hint": self.profile_hint,
        }
