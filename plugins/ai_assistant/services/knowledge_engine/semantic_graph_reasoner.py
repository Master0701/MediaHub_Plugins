from __future__ import annotations

import re
from itertools import combinations
from typing import Any


class SemanticGraphReasoner:
    """Konservativer Reasoner für erklärbare Graph-Vorschläge."""

    RELATION_CONFIDENCE_MINIMUM = 0.72

    _NUMBER_WORDS = {
        "i": 1,
        "ii": 2,
        "iii": 3,
        "iv": 4,
        "v": 5,
        "vi": 6,
        "vii": 7,
        "viii": 8,
        "ix": 9,
        "x": 10,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }

    def __init__(self, engine: Any):
        self.engine = engine

    @staticmethod
    def _normalize(value: Any) -> str:
        text = str(value or "").casefold()
        text = re.sub(r"[^a-z0-9äöüß]+", " ", text)
        return " ".join(text.split())

    @classmethod
    def _title_number(
        cls,
        title: str,
    ) -> tuple[str, int | None]:
        normalized = cls._normalize(title)
        tokens = normalized.split()
        if not tokens:
            return "", None

        last = tokens[-1]
        number = None
        if last.isdigit():
            number = int(last)
        elif last in cls._NUMBER_WORDS:
            number = cls._NUMBER_WORDS[last]

        if number is not None:
            return " ".join(tokens[:-1]), number
        return normalized, None

    @staticmethod
    def _metadata(entity: dict[str, Any]) -> dict[str, Any]:
        return dict(entity.get("metadata") or {})

    @classmethod
    def _group_values(
        cls,
        entity: dict[str, Any],
    ) -> dict[str, str]:
        metadata = cls._metadata(entity)
        result = {}
        for relation_type, keys in (
            ("franchise", ("franchise", "franchise_name")),
            ("universe", ("universe", "universe_name")),
        ):
            value = next(
                (
                    str(metadata.get(key)).strip()
                    for key in keys
                    if metadata.get(key)
                ),
                "",
            )
            if value:
                result[relation_type] = value
        return result

    @staticmethod
    def _year(entity: dict[str, Any]) -> int | None:
        value = entity.get("year")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _known_relation_signatures(self) -> set[tuple[str, str, str]]:
        return {
            (
                str(item.get("source_id")),
                str(item.get("target_id")),
                str(item.get("relation_type")),
            )
            for item in self.engine.store.all_relations()
        }

    def _known_order_pairs(self) -> set[tuple[str, str]]:
        pairs = set()
        for order in self.engine.store.all_orders():
            entries = sorted(
                order.get("entries") or [],
                key=lambda item: int(item.get("position") or 0),
            )
            ids = [str(item.get("entity_id")) for item in entries]
            for left, right in zip(ids, ids[1:]):
                pairs.add((left, right))
        return pairs

    def _group_proposals(
        self,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        proposals = []
        for entity in entities:
            for relation_type, group_name in self._group_values(entity).items():
                proposals.append(
                    {
                        "kind": "group_membership",
                        "entity_id": str(entity.get("id")),
                        "entity_title": entity.get("title"),
                        "group_name": group_name,
                        "relation_type": relation_type,
                        "confidence": 0.96,
                        "evidence": [
                            {
                                "type": "confirmed_metadata",
                                "field": relation_type,
                                "value": group_name,
                                "weight": 1.0,
                            }
                        ],
                        "reason": (
                            f"Bestätigte {relation_type}-Metadaten "
                            f"nennen „{group_name}“."
                        ),
                        "requires_confirmation": True,
                    }
                )
        return proposals

    def _explicit_hint_proposals(
        self,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        by_title = {
            self._normalize(item.get("title")): item
            for item in entities
        }
        proposals = []

        for entity in entities:
            metadata = self._metadata(entity)
            for hint in metadata.get("relation_hints") or []:
                if not isinstance(hint, dict):
                    continue
                target = by_title.get(
                    self._normalize(hint.get("target_title"))
                )
                if not target:
                    continue
                confidence = float(hint.get("confidence") or 0.9)
                if confidence < self.RELATION_CONFIDENCE_MINIMUM:
                    continue
                proposals.append(
                    {
                        "kind": "direct_relation",
                        "source_id": str(entity.get("id")),
                        "source_title": entity.get("title"),
                        "target_id": str(target.get("id")),
                        "target_title": target.get("title"),
                        "relation_type": str(
                            hint.get("relation_type") or "related"
                        ),
                        "confidence": confidence,
                        "evidence": [
                            {
                                "type": "confirmed_relation_hint",
                                "value": hint,
                                "weight": 1.0,
                            }
                        ],
                        "reason": str(
                            hint.get("reason")
                            or "Bestätigter Beziehungshinweis in Metadaten."
                        ),
                        "requires_confirmation": True,
                    }
                )
        return proposals

    @classmethod
    def _contains_any(cls, value: Any, terms: set[str]) -> bool:
        normalized = cls._normalize(value)
        return any(term in normalized for term in terms)

    def _semantic_relation_proposals(
        self,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        proposals = []
        by_title = {
            self._normalize(item.get("title")): item
            for item in entities
        }

        for entity in entities:
            metadata = self._metadata(entity)
            title = str(entity.get("title") or "")
            parent_title = (
                metadata.get("parent_title")
                or metadata.get("origin_title")
                or metadata.get("source_title")
            )
            parent = by_title.get(self._normalize(parent_title))
            relation_type = None
            confidence = 0.0
            evidence = []

            if parent:
                if metadata.get("is_prequel") is True or self._contains_any(
                    title,
                    {" origins", " origin", " before", " beginnings"},
                ):
                    relation_type = "prequel"
                    confidence = 0.94
                    evidence.append({
                        "type": "prequel_metadata_or_title",
                        "value": parent_title,
                        "weight": 0.94,
                    })
                elif metadata.get("is_spin_off") is True or self._contains_any(
                    metadata.get("relation_kind"),
                    {"spin off", "spinoff"},
                ):
                    relation_type = "spin_off"
                    confidence = 0.96
                    evidence.append({
                        "type": "spin_off_metadata",
                        "value": parent_title,
                        "weight": 0.96,
                    })
                elif metadata.get("is_backdoor_pilot") is True:
                    relation_type = "backdoor_pilot"
                    confidence = 0.98
                    evidence.append({
                        "type": "backdoor_pilot_metadata",
                        "value": parent_title,
                        "weight": 0.98,
                    })
                elif metadata.get("is_reboot") is True or self._contains_any(
                    metadata.get("edition"),
                    {"reboot", "remake"},
                ):
                    relation_type = "reboot"
                    confidence = 0.95
                    evidence.append({
                        "type": "reboot_metadata",
                        "value": parent_title,
                        "weight": 0.95,
                    })

            if relation_type and parent:
                proposals.append({
                    "kind": "direct_relation",
                    "source_id": str(entity.get("id")),
                    "source_title": entity.get("title"),
                    "target_id": str(parent.get("id")),
                    "target_title": parent.get("title"),
                    "relation_type": relation_type,
                    "confidence": confidence,
                    "evidence": evidence,
                    "reason": (
                        f"Bestätigte Metadaten oder eindeutige "
                        f"Titelhinweise sprechen für {relation_type}."
                    ),
                    "requires_confirmation": True,
                })

            crossover_titles = metadata.get("crossover_with") or []
            if isinstance(crossover_titles, str):
                crossover_titles = [crossover_titles]
            for other_title in crossover_titles:
                other = by_title.get(self._normalize(other_title))
                if other:
                    proposals.append({
                        "kind": "direct_relation",
                        "source_id": str(entity.get("id")),
                        "source_title": entity.get("title"),
                        "target_id": str(other.get("id")),
                        "target_title": other.get("title"),
                        "relation_type": "crossover",
                        "confidence": 0.97,
                        "evidence": [{
                            "type": "confirmed_crossover_metadata",
                            "value": other_title,
                            "weight": 0.97,
                        }],
                        "reason": (
                            "Bestätigte Crossover-Metadaten verknüpfen "
                            "beide Medien."
                        ),
                        "requires_confirmation": True,
                    })

            shared_characters = metadata.get("shared_characters") or []
            if isinstance(shared_characters, str):
                shared_characters = [shared_characters]
            for other in entities:
                if other is entity or not shared_characters:
                    continue
                other_meta = self._metadata(other)
                other_chars = other_meta.get("shared_characters") or []
                if isinstance(other_chars, str):
                    other_chars = [other_chars]
                overlap = sorted(
                    {self._normalize(x) for x in shared_characters if self._normalize(x)}
                    & {self._normalize(x) for x in other_chars if self._normalize(x)}
                )
                same_universe = (
                    self._group_values(entity).get("universe")
                    and self._group_values(entity).get("universe")
                    == self._group_values(other).get("universe")
                )
                if overlap and same_universe:
                    proposals.append({
                        "kind": "direct_relation",
                        "source_id": str(entity.get("id")),
                        "source_title": entity.get("title"),
                        "target_id": str(other.get("id")),
                        "target_title": other.get("title"),
                        "relation_type": "related",
                        "confidence": 0.78,
                        "evidence": [
                            {"type": "shared_characters", "value": overlap, "weight": 0.42},
                            {"type": "shared_universe", "value": self._group_values(entity).get("universe"), "weight": 0.36},
                        ],
                        "reason": (
                            "Gemeinsames Universum und bestätigte gemeinsame "
                            "Figuren sprechen für eine inhaltliche Verbindung."
                        ),
                        "requires_confirmation": True,
                    })
        return proposals

    def _sequence_proposals(
        self,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        proposals = []
        known_order_pairs = self._known_order_pairs()

        for left, right in combinations(entities, 2):
            if left.get("media_type") != right.get("media_type"):
                continue
            if left.get("media_type") not in {"movie", "series", "audiobook"}:
                continue

            left_groups = self._group_values(left)
            right_groups = self._group_values(right)
            shared_groups = {
                key: value
                for key, value in left_groups.items()
                if right_groups.get(key) == value
            }

            left_base, left_number = self._title_number(
                str(left.get("title") or "")
            )
            right_base, right_number = self._title_number(
                str(right.get("title") or "")
            )

            left_year = self._year(left)
            right_year = self._year(right)

            earlier, later = (left, right)
            earlier_year, later_year = left_year, right_year
            earlier_base, later_base = left_base, right_base
            earlier_number, later_number = left_number, right_number

            if (
                left_year is not None
                and right_year is not None
                and left_year > right_year
            ):
                earlier, later = right, left
                earlier_year, later_year = right_year, left_year
                earlier_base, later_base = right_base, left_base
                earlier_number, later_number = right_number, left_number

            evidence = []
            confidence = 0.0

            if shared_groups:
                confidence += 0.48
                evidence.append(
                    {
                        "type": "shared_group",
                        "value": shared_groups,
                        "weight": 0.48,
                    }
                )

            if earlier_base and earlier_base == later_base:
                confidence += 0.34
                evidence.append(
                    {
                        "type": "matching_title_base",
                        "value": earlier_base,
                        "weight": 0.34,
                    }
                )

            if (
                earlier_number is not None
                and later_number is not None
                and later_number == earlier_number + 1
            ):
                confidence += 0.22
                evidence.append(
                    {
                        "type": "consecutive_title_number",
                        "value": [earlier_number, later_number],
                        "weight": 0.22,
                    }
                )

            if (
                earlier_year is not None
                and later_year is not None
                and 0 < later_year - earlier_year <= 12
            ):
                confidence += 0.12
                evidence.append(
                    {
                        "type": "release_year_progression",
                        "value": [earlier_year, later_year],
                        "weight": 0.12,
                    }
                )

            pair = (str(earlier.get("id")), str(later.get("id")))
            if pair in known_order_pairs:
                confidence += 0.18
                evidence.append(
                    {
                        "type": "confirmed_order_progression",
                        "value": pair,
                        "weight": 0.18,
                    }
                )

            confidence = min(confidence, 0.99)
            if confidence < self.RELATION_CONFIDENCE_MINIMUM:
                continue

            proposals.append(
                {
                    "kind": "direct_relation",
                    "source_id": str(earlier.get("id")),
                    "source_title": earlier.get("title"),
                    "target_id": str(later.get("id")),
                    "target_title": later.get("title"),
                    "relation_type": "sequel",
                    "confidence": round(confidence, 4),
                    "evidence": evidence,
                    "reason": (
                        "Gemeinsame bestätigte Gruppendaten, Titelmuster, "
                        "Jahresfolge oder Reihenfolge sprechen für eine "
                        "Fortsetzungsbeziehung."
                    ),
                    "requires_confirmation": True,
                }
            )

        return proposals

    def reason(self) -> dict[str, Any]:
        entities = list(self.engine.all_items())
        known = self._known_relation_signatures()

        proposals = [
            *self._group_proposals(entities),
            *self._explicit_hint_proposals(entities),
            *self._semantic_relation_proposals(entities),
            *self._sequence_proposals(entities),
        ]

        unique = {}
        skipped_existing = 0
        for proposal in proposals:
            if proposal.get("kind") == "direct_relation":
                signature = (
                    str(proposal.get("source_id")),
                    str(proposal.get("target_id")),
                    str(proposal.get("relation_type")),
                )
                if signature in known:
                    skipped_existing += 1
                    continue
            else:
                signature = (
                    str(proposal.get("entity_id")),
                    str(proposal.get("group_name")).casefold(),
                    str(proposal.get("relation_type")),
                )

            previous = unique.get(signature)
            if (
                previous is None
                or float(proposal.get("confidence") or 0.0)
                > float(previous.get("confidence") or 0.0)
            ):
                unique[signature] = proposal

        final_proposals = sorted(
            unique.values(),
            key=lambda item: (
                -float(item.get("confidence") or 0.0),
                str(item.get("source_title") or item.get("entity_title") or ""),
                str(item.get("target_title") or item.get("group_name") or ""),
            ),
        )

        return {
            "schema_version": 1,
            "strategy": "semantic_graph_reasoner_v250",
            "entity_count": len(entities),
            "proposal_count": len(final_proposals),
            "skipped_existing_relation_count": skipped_existing,
            "minimum_confidence": self.RELATION_CONFIDENCE_MINIMUM,
            "proposals": final_proposals,
            "automatic_changes": False,
            "requires_confirmation": True,
        }
