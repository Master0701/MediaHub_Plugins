from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from models.media_item import MediaItem
from models.media_relation import MediaRelation


PART_PATTERNS = (
    re.compile(
        r"(?i)(?:^|[ ._\-])(?:cd|disc|disk|dvd|part|pt)[ ._\-]?(?P<num>\d{1,2})(?:$|[ ._\-])"
    ),
    re.compile(
        r"(?i)(?:^|[ ._\-])teil[ ._\-]?(?P<num>\d{1,2})(?:$|[ ._\-])"
    ),
)

MULTI_EPISODE_PATTERN = re.compile(
    r"(?i)\bS(?P<season>\d{1,3})[ ._\-]*E(?P<start>\d{1,4})"
    r"(?:[ ._\-]*(?:E|TO|THRU|THROUGH|\-)[ ._\-]*(?P<end>\d{1,4}))\b"
)

SINGLE_EPISODE_PATTERN = re.compile(
    r"(?i)\bS(?P<season>\d{1,3})[ ._\-]*E(?P<episode>\d{1,4})(?!\d)"
)


class MediaRelationEngine:
    """
    Lokale, konservative Basisanalyse für Medienbeziehungen.

    Diese Engine entscheidet NICHT, ob eine fehlende Episodennummer wirklich
    in einer benachbarten Datei enthalten ist. Ohne externe/inhaltliche
    Bestätigung bleibt dieser Fall review_required=True.

    Sie liefert gemeinsame Felder, die Smart Renamer, Metadata Editor,
    KI-Assistent und Cut & Merge später identisch verwenden können.
    """

    def analyze_items(
        self,
        items: Iterable[MediaItem],
    ) -> list[MediaItem]:
        items = list(items)
        self._analyze_direct_patterns(items)
        self._infer_parts(items)
        self._infer_missing_candidates(items)
        return items

    def analyze_item(self, item: MediaItem) -> MediaRelation:
        path = Path(item.path)
        stem = path.stem

        if self._is_sample(item):
            return MediaRelation(
                relation_type="sample",
                recommended_action="keep",
                confidence=1.0,
                review_required=False,
                evidence=["sample_marker"],
            )

        multi = MULTI_EPISODE_PATTERN.search(stem)
        if multi:
            start = self._norm(multi.group("start"))
            end = self._norm(multi.group("end"))
            if int(end) > int(start):
                return MediaRelation(
                    relation_type="multi_episode",
                    episode_start=start,
                    episode_end=end,
                    official_episode_count=None,
                    detected_episode_count=int(end) - int(start) + 1,
                    recommended_action="review",
                    confidence=0.90,
                    review_required=True,
                    evidence=["filename_multi_episode_pattern"],
                )

        part = self._part_number(stem)
        if part is not None:
            if item.media_type == "movie":
                return MediaRelation(
                    relation_type="split_movie",
                    part_number=part,
                    recommended_action="review",
                    confidence=0.80,
                    review_required=True,
                    evidence=["filename_part_marker"],
                )
            if item.media_type == "series" and item.episode:
                return MediaRelation(
                    relation_type="split_episode",
                    episode_start=self._norm(item.episode),
                    part_number=part,
                    recommended_action="review",
                    confidence=0.80,
                    review_required=True,
                    evidence=["filename_part_marker"],
                )
            return MediaRelation(
                relation_type="multi_part",
                part_number=part,
                recommended_action="review",
                confidence=0.70,
                review_required=True,
                evidence=["filename_part_marker"],
            )

        if item.media_type == "series" and item.episode:
            return MediaRelation(
                relation_type="single",
                episode_start=self._norm(item.episode),
                recommended_action="none",
                confidence=0.95,
                review_required=False,
                evidence=["single_episode"],
            )

        return MediaRelation(
            relation_type="single",
            recommended_action="none",
            confidence=0.90,
            review_required=False,
            evidence=["no_relation_marker"],
        )

    def _analyze_direct_patterns(self, items: list[MediaItem]) -> None:
        for item in items:
            relation = self.analyze_item(item)
            item.detection_data["media_relation"] = relation.to_dict()

    def _infer_parts(self, items: list[MediaItem]) -> None:
        groups: dict[tuple, list[MediaItem]] = defaultdict(list)

        for item in items:
            relation = dict(item.detection_data.get("media_relation") or {})
            if relation.get("relation_type") not in {
                "split_episode", "split_movie", "multi_part"
            }:
                continue

            key = self._part_group_key(item)
            groups[key].append(item)

        for group in groups.values():
            numbered = []
            for item in group:
                relation = dict(item.detection_data["media_relation"])
                number = relation.get("part_number")
                if number is not None:
                    numbered.append((int(number), item))

            if not numbered:
                continue

            numbered.sort(key=lambda value: value[0])
            part_count = max(number for number, _ in numbered)

            for _, item in numbered:
                relation = dict(item.detection_data["media_relation"])
                relation["part_count"] = part_count
                relation["evidence"] = list(relation.get("evidence") or []) + [
                    "matching_part_group"
                ]

                # Mehrere Teile desselben Medienobjekts sind ein Merge-Kandidat,
                # aber niemals automatisch freigegeben.
                if len(numbered) >= 2:
                    relation["recommended_action"] = "merge_candidate"
                    relation["confidence"] = max(
                        float(relation.get("confidence") or 0),
                        0.90,
                    )
                    relation["review_required"] = True

                item.detection_data["media_relation"] = relation

    def _infer_missing_candidates(self, items: list[MediaItem]) -> None:
        by_season: dict[str, set[int]] = defaultdict(set)

        for item in items:
            if item.media_type != "series" or not item.season or not item.episode:
                continue

            relation = dict(item.detection_data.get("media_relation") or {})
            # Multi-Episode-Dateien decken eine Range ab.
            if relation.get("relation_type") == "multi_episode":
                try:
                    start = int(relation["episode_start"])
                    end = int(relation["episode_end"])
                except (TypeError, ValueError):
                    continue
                for number in range(start, end + 1):
                    by_season[self._norm(item.season)].add(number)
                continue

            try:
                by_season[self._norm(item.season)].add(int(item.episode))
            except (TypeError, ValueError):
                continue

        missing_by_season: dict[str, list[str]] = {}
        for season, episodes in by_season.items():
            if len(episodes) < 2:
                continue
            low = min(episodes)
            high = max(episodes)
            missing = [
                self._norm(number)
                for number in range(low, high + 1)
                if number not in episodes
            ]
            if missing:
                missing_by_season[season] = missing

        if not missing_by_season:
            return

        # Wir markieren Kandidaten nur als Hinweis. Ob eine "fehlende" Folge
        # tatsächlich in einer Multi-Episode-Datei steckt, muss später durch
        # offizielle Metadaten/KI/In-Video-Analyse bestätigt werden.
        for item in items:
            season = self._norm(item.season) if item.season else ""
            missing = missing_by_season.get(season)
            if not missing:
                continue

            relation = dict(item.detection_data.get("media_relation") or {})
            relation["missing_episode_candidates"] = list(missing)

            if relation.get("relation_type") == "single":
                relation["recommended_action"] = "review"
                relation["review_required"] = True
                relation["confidence"] = min(
                    float(relation.get("confidence") or 0.95),
                    0.75,
                )
                relation["evidence"] = list(relation.get("evidence") or []) + [
                    "season_gap_detected"
                ]

            item.detection_data["media_relation"] = relation

    @staticmethod
    def _part_group_key(item: MediaItem) -> tuple:
        relation = dict(item.detection_data.get("media_relation") or {})
        if item.media_type == "series":
            return (
                "series",
                str(item.parent).casefold(),
                MediaRelationEngine._norm(item.season),
                relation.get("episode_start") or MediaRelationEngine._norm(item.episode),
            )

        # Für Filme: Part-Marker aus dem Stamm entfernen.
        stem = Path(item.path).stem.casefold()
        for pattern in PART_PATTERNS:
            stem = pattern.sub(" ", stem)
        stem = re.sub(r"[^a-z0-9]+", " ", stem).strip()
        return ("movie", str(item.parent).casefold(), stem)

    @staticmethod
    def _is_sample(item: MediaItem) -> bool:
        path = Path(item.path)
        if any(part.casefold() == "sample" for part in path.parts[:-1]):
            return True
        tokens = {
            token
            for token in re.split(r"[^a-z0-9]+", path.stem.casefold())
            if token
        }
        return "sample" in tokens

    @staticmethod
    def _part_number(stem: str) -> int | None:
        for pattern in PART_PATTERNS:
            match = pattern.search(stem)
            if match:
                return int(match.group("num"))
        return None

    @staticmethod
    def _norm(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            return str(int(text)).zfill(2)
        except ValueError:
            return text.zfill(2)
