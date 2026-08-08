from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SEASON_FOLDER_PATTERNS = (
    re.compile(r"(?i)^staffel[ ._-]*(?P<season>\d{1,3})$"),
    re.compile(r"(?i)^season[ ._-]*(?P<season>\d{1,3})$"),
    re.compile(r"(?i)^s(?P<season>\d{1,3})$"),
)

EXTRA_FOLDER_NAMES = {
    "extras",
    "extra",
    "bonus",
    "bonusmaterial",
    "specials",
    "special",
    "trailers",
    "trailer",
}

DISC_FOLDER_PATTERNS = (
    re.compile(r"(?i)^(?:cd|disc|disk)[ ._-]*(?P<part>\d{1,3})$"),
    re.compile(r"(?i)^teil[ ._-]*(?P<part>\d{1,3})$"),
    re.compile(r"(?i)^part[ ._-]*(?P<part>\d{1,3})$"),
)


@dataclass(frozen=True, slots=True)
class FolderContext:
    root_path: str
    collection_type: str
    collection_title: str = ""
    season_map: dict[str, str] = field(default_factory=dict)
    item_relations: dict[str, dict[str, Any]] = field(default_factory=dict)
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_path": self.root_path,
            "collection_type": self.collection_type,
            "collection_title": self.collection_title,
            "season_map": dict(self.season_map),
            "item_relations": {
                key: dict(value)
                for key, value in self.item_relations.items()
            },
            "confidence": self.confidence,
            "evidence": list(self.evidence),
        }


class FolderStructureAnalyzer:
    """
    Analysiert einen kompletten Scan als Sammlung.

    Die Einzeldateierkennung bleibt führend. Ordnerkontext ergänzt nur
    zusätzliche Beziehungen wie Serienname, Staffel, Extras oder Mehrteiler.
    """

    def analyze(
        self,
        root: Path,
        media_items: list[Any],
    ) -> FolderContext:
        root = Path(root)
        type_counts = Counter(
            str(getattr(item, "media_type", "") or "unknown")
            for item in media_items
        )
        evidence: list[str] = []
        relations: dict[str, dict[str, Any]] = {}
        season_map: dict[str, str] = {}

        collection_type = self._collection_type(type_counts)
        if collection_type != "unknown":
            evidence.append(f"dominant_type:{collection_type}")

        collection_title = self._collection_title(root, media_items, collection_type)
        if collection_title:
            evidence.append("collection_title_from_root")

        for item in media_items:
            path = Path(getattr(item, "path"))
            relation = self._relation_for(root, path, item)
            relations[str(path)] = relation

            season = str(relation.get("season") or "")
            if season:
                season_map[season] = str(path.parent)

        if season_map:
            evidence.append(f"season_folders:{len(season_map)}")

        if any(value.get("is_extra_folder") for value in relations.values()):
            evidence.append("extra_folders")

        confidence = self._confidence(
            collection_type,
            media_items,
            season_map,
            relations,
        )

        return FolderContext(
            root_path=str(root),
            collection_type=collection_type,
            collection_title=collection_title,
            season_map=season_map,
            item_relations=relations,
            confidence=confidence,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _collection_type(type_counts: Counter[str]) -> str:
        filtered = Counter({
            key: value
            for key, value in type_counts.items()
            if key not in {"", "unknown", "extra"}
        })
        if not filtered:
            return "unknown"
        if len(filtered) == 1:
            return next(iter(filtered))
        top = filtered.most_common()
        if len(top) >= 2 and top[0][1] == top[1][1]:
            return "mixed"
        return top[0][0]

    @staticmethod
    def _collection_title(
        root: Path,
        media_items: list[Any],
        collection_type: str,
    ) -> str:
        if root.name:
            name = root.name.replace("_", " ").replace(".", " ").strip()
            if name.casefold() not in EXTRA_FOLDER_NAMES:
                return re.sub(r"\s+", " ", name)

        titles = [
            str(getattr(item, "title", "") or "").strip()
            for item in media_items
            if str(getattr(item, "title", "") or "").strip()
        ]
        return Counter(titles).most_common(1)[0][0] if titles else ""

    def _relation_for(
        self,
        root: Path,
        path: Path,
        item: Any,
    ) -> dict[str, Any]:
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path

        parts = list(relative.parts[:-1])
        season = str(getattr(item, "season", "") or "")
        part = str(getattr(item, "part", "") or "")
        is_extra_folder = False
        folder_role = ""
        parent_title = ""

        for folder in parts:
            cleaned = folder.strip()

            for pattern in SEASON_FOLDER_PATTERNS:
                match = pattern.match(cleaned)
                if match:
                    season = season or match.group("season").zfill(2)
                    folder_role = "season"
                    break

            if cleaned.casefold() in EXTRA_FOLDER_NAMES:
                is_extra_folder = True
                folder_role = "extra"

            for pattern in DISC_FOLDER_PATTERNS:
                match = pattern.match(cleaned)
                if match:
                    part = part or match.group("part")
                    if not folder_role:
                        folder_role = "part"
                    break

        if len(parts) >= 2:
            parent_title = parts[-2]
        elif parts:
            candidate = parts[0]
            if not any(p.match(candidate) for p in SEASON_FOLDER_PATTERNS):
                if candidate.casefold() not in EXTRA_FOLDER_NAMES:
                    parent_title = candidate

        return {
            "relative_path": str(relative),
            "folder_depth": len(parts),
            "season": season,
            "part": part,
            "is_extra_folder": is_extra_folder,
            "folder_role": folder_role,
            "parent_title": parent_title,
        }

    @staticmethod
    def _confidence(
        collection_type: str,
        media_items: list[Any],
        season_map: dict[str, str],
        relations: dict[str, dict[str, Any]],
    ) -> float:
        score = 0.45
        if collection_type not in {"unknown", "mixed"}:
            score += 0.20
        if season_map:
            score += 0.20
        if len(media_items) >= 2:
            score += 0.05
        if any(value.get("is_extra_folder") for value in relations.values()):
            score += 0.05
        return min(score, 0.95)
