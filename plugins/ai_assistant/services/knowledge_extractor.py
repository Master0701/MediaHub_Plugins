from __future__ import annotations

import re
import uuid
from typing import Any


class KnowledgeExtractor:
    """Wandelt Parser-Ergebnisse in bestätigbare Wissensvorschläge um."""

    MEDIA_TYPES = {
        "movie",
        "series",
        "episode",
        "audiobook",
        "book",
        "character",
        "franchise",
        "universe",
    }

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _candidate(
        *,
        field: str,
        value: Any,
        confidence: float,
        reason: str,
        source: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "id": uuid.uuid4().hex,
            "field": field,
            "value": value,
            "confidence": round(float(confidence), 4),
            "reason": reason,
            "source_id": source.get("id"),
            "source_name": source.get("name"),
            "source_url": source.get("url"),
            "requires_confirmation": True,
        }

    def _select_year(
        self,
        *,
        title: str,
        years: list[int],
        text: str,
    ) -> tuple[int | None, float, str]:
        if not years:
            return None, 0.0, "Keine Jahreszahl gefunden."

        title_pattern = re.escape(title)
        patterns = [
            rf"(?i){title_pattern}.{{0,100}}(?:film|kinofilm).{{0,60}}(19\d{{2}}|20\d{{2}})",
            rf"(?i)(?:film|kinofilm).{{0,100}}{title_pattern}.{{0,60}}(19\d{{2}}|20\d{{2}})",
            rf"(?i)(19\d{{2}}|20\d{{2}}).{{0,80}}(?:erschien|veröffentlicht).{{0,40}}(?:der|die|das)?\s*(?:film|kinofilm).{{0,80}}{title_pattern}",
            rf"(?i)(19\d{{2}}|20\d{{2}}).{{0,80}}(?:film|kinofilm).{{0,80}}{title_pattern}",
            rf"(?i)(?:erschien|veröffentlicht|veröffentlicht wurde).{{0,80}}(19\d{{2}}|20\d{{2}})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                year = int(match.group(1))
                if year in years:
                    return (
                        year,
                        0.88,
                        "Jahreszahl steht in direktem Kontext zum Titel "
                        "oder zur Veröffentlichung.",
                    )

        recent = [year for year in years if year >= 1900]
        if len(recent) == 1:
            return (
                recent[0],
                0.70,
                "Einzige plausible Jahreszahl im Parser-Ergebnis.",
            )

        return (
            None,
            0.0,
            "Mehrere Jahreszahlen gefunden; keine davon ist eindeutig genug.",
        )

    def extract(
        self,
        *,
        source: dict[str, Any],
        parser_result: dict[str, Any],
        scan_result: dict[str, Any] | None = None,
        semantic_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scan_result = dict(scan_result or {})
        semantic_result = dict(semantic_result or {})
        parsed = dict(parser_result.get("result") or parser_result)
        fields = dict(parsed.get("fields") or {})
        text = str(scan_result.get("text_preview") or "")

        title = self._normalize(fields.get("title"))
        media_type = self._normalize(fields.get("media_type")).casefold()
        years = [
            int(item)
            for item in fields.get("year_candidates") or []
            if str(item).isdigit()
        ]
        metadata = dict(fields.get("metadata") or {})
        relation_terms = list(fields.get("relation_terms") or [])

        field_candidates = []
        entity_proposals = []
        relation_proposals = []
        group_proposals = []
        warnings = []

        if title:
            field_candidates.append(
                self._candidate(
                    field="title",
                    value=title,
                    confidence=float(parsed.get("confidence") or 0.65),
                    reason="Vom ausgewählten Quellenparser erkannter Titel.",
                    source=source,
                )
            )
        else:
            warnings.append("Kein eindeutiger Titel erkannt.")

        if media_type in self.MEDIA_TYPES:
            field_candidates.append(
                self._candidate(
                    field="media_type",
                    value=media_type,
                    confidence=0.72,
                    reason="Medientyp wurde aus Seitentext und Parserregeln abgeleitet.",
                    source=source,
                )
            )

        semantic_entities = list(
            semantic_result.get("entity_proposals") or []
        )
        has_semantic_result = bool(semantic_result)

        primary_type = self._normalize(
            semantic_result.get("primary_entity_type")
        ).casefold()
        if primary_type:
            media_type = primary_type

        primary_entity_year = None
        for semantic_entity in semantic_entities:
            if (
                self._normalize(semantic_entity.get("title")).casefold()
                == title.casefold()
                and self._normalize(
                    semantic_entity.get("entity_type")
                ).casefold()
                == media_type
            ):
                primary_entity_year = semantic_entity.get("year")
                break

        if has_semantic_result:
            if primary_entity_year is not None:
                field_candidates.append(
                    self._candidate(
                        field="year",
                        value=primary_entity_year,
                        confidence=0.90,
                        reason=(
                            "Jahr wurde von der Semantic Knowledge Engine "
                            "für genau diese Entität bestimmt."
                        ),
                        source=source,
                    )
                )
            elif years:
                field_candidates.append(
                    self._candidate(
                        field="year_candidates",
                        value=years,
                        confidence=0.25,
                        reason=(
                            "Kein eindeutiges Jahr für die Primärentität; "
                            "Jahresliste bleibt nur als manueller Kandidat."
                        ),
                        source=source,
                    )
                )
                warnings.append(
                    "Kein Primärjahr übernommen; manuelle Bestätigung nötig."
                )
        else:
            (
                primary_entity_year,
                fallback_confidence,
                fallback_reason,
            ) = self._select_year(
                title=title,
                years=years,
                text=text,
            )
            if primary_entity_year is not None:
                field_candidates.append(
                    self._candidate(
                        field="year",
                        value=primary_entity_year,
                        confidence=fallback_confidence,
                        reason=(
                            "Kompatibilitäts-Fallback ohne Semantic-Ergebnis: "
                            + fallback_reason
                        ),
                        source=source,
                    )
                )
            elif years:
                field_candidates.append(
                    self._candidate(
                        field="year_candidates",
                        value=years,
                        confidence=0.35,
                        reason=fallback_reason,
                        source=source,
                    )
                )
                warnings.append(
                    "Mehrere Jahreszahlen vorhanden; Jahr muss manuell "
                    "bestätigt werden."
                )

        universe = self._normalize(metadata.get("universe"))
        if universe:
            field_candidates.append(
                self._candidate(
                    field="universe",
                    value=universe,
                    confidence=0.86,
                    reason="Universumsname wurde vom Quellenparser erkannt.",
                    source=source,
                )
            )
            group_proposals.append(
                {
                    "id": uuid.uuid4().hex,
                    "kind": "group_membership",
                    "group_type": "universe",
                    "group_name": universe,
                    "entity_title": title,
                    "confidence": 0.86,
                    "source_id": source.get("id"),
                    "reason": "Quelle ordnet das Medium diesem Universum zu.",
                    "requires_confirmation": True,
                }
            )

        franchise = self._normalize(metadata.get("franchise"))
        if franchise:
            field_candidates.append(
                self._candidate(
                    field="franchise",
                    value=franchise,
                    confidence=0.86,
                    reason="Franchise wurde vom Quellenparser erkannt.",
                    source=source,
                )
            )
            group_proposals.append(
                {
                    "id": uuid.uuid4().hex,
                    "kind": "group_membership",
                    "group_type": "franchise",
                    "group_name": franchise,
                    "entity_title": title,
                    "confidence": 0.86,
                    "source_id": source.get("id"),
                    "reason": "Quelle ordnet das Medium diesem Franchise zu.",
                    "requires_confirmation": True,
                }
            )

        possible_sequel = self._normalize(
            metadata.get("possible_sequel_title")
        )
        if possible_sequel:
            relation_proposals.append(
                {
                    "id": uuid.uuid4().hex,
                    "kind": "direct_relation",
                    "source_title": title,
                    "target_title": possible_sequel,
                    "relation_type": "sequel",
                    "confidence": 0.68,
                    "source_id": source.get("id"),
                    "reason": "Quellentext nennt einen möglichen Nachfolger.",
                    "requires_confirmation": True,
                }
            )

        for term in relation_terms:
            normalized = str(term).casefold()
            if normalized in {"crossover", "prequel", "sequel", "reboot", "remake"}:
                warnings.append(
                    f"Beziehungsbegriff „{term}“ gefunden, aber ohne "
                    "eindeutiges Zielmedium."
                )

        semantic_keys = set()
        for semantic_entity in semantic_entities:
            semantic_title = self._normalize(
                semantic_entity.get("title")
            )
            semantic_type = self._normalize(
                semantic_entity.get("entity_type")
            ).casefold()
            semantic_year = semantic_entity.get("year")
            if not semantic_title or not semantic_type:
                continue

            key = (
                semantic_title.casefold(),
                semantic_type,
                semantic_year,
            )
            if key in semantic_keys:
                continue
            semantic_keys.add(key)

            entity_proposals.append(
                {
                    "id": uuid.uuid4().hex,
                    "kind": "entity",
                    "title": semantic_title,
                    "media_type": semantic_type,
                    "year": semantic_year,
                    "metadata": {
                        "semantic_sentence": semantic_entity.get(
                            "sentence"
                        ),
                        "semantic_reason": semantic_entity.get(
                            "reason"
                        ),
                    },
                    "confidence": float(
                        semantic_entity.get("confidence") or 0.0
                    ),
                    "source_id": source.get("id"),
                    "source_name": source.get("name"),
                    "source_url": source.get("url"),
                    "requires_confirmation": True,
                }
            )

        primary_key = (
            title.casefold(),
            media_type,
            primary_entity_year,
        )
        if title and (
            not has_semantic_result
            or primary_key not in semantic_keys
        ):
            entity_proposals.insert(
                0,
                {
                    "id": uuid.uuid4().hex,
                    "kind": "entity",
                    "title": title,
                    "media_type": media_type or None,
                    "year": primary_entity_year,
                    "metadata": {
                        key: value
                        for key, value in metadata.items()
                        if value not in (None, "", [], {})
                    },
                    "confidence": round(
                        max(
                            [
                                float(item["confidence"])
                                for item in field_candidates
                            ]
                            or [0.0]
                        ),
                        4,
                    ),
                    "source_id": source.get("id"),
                    "source_name": source.get("name"),
                    "source_url": source.get("url"),
                    "requires_confirmation": True,
                },
            )

        return {
            "schema_version": 1,
            "strategy": "semantic_knowledge_extractor_v272",
            "source": {
                "id": source.get("id"),
                "name": source.get("name"),
                "url": source.get("url"),
                "trust": source.get("trust"),
            },
            "parser_id": parsed.get("parser_id"),
            "field_candidates": field_candidates,
            "entity_proposals": entity_proposals,
            "relation_proposals": relation_proposals,
            "group_proposals": group_proposals,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
