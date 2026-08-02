from __future__ import annotations

import re
from typing import Any


class NarrativeExtractor:
    STRATEGY = "narrative_extractor_v560"

    CONFLICT_PATTERNS = (
        r"\bkämpft\b",
        r"\bgreift\b",
        r"\bbedroht\b",
        r"\bentführt\b",
        r"\bvernichten\b",
        r"\brache\b",
        r"\bkonflikt\b",
    )

    RESOLUTION_PATTERNS = (
        r"\bbesiegt\b",
        r"\bgerettet\b",
        r"\brettet\b",
        r"\bzerstört\b",
        r"\bbefreit\b",
        r"\bfliehen in sicherheit\b",
        r"\bversöhnt\b",
        r"\bentscheidet sich\b",
    )

    CHARACTER_GROWTH_PATTERNS = (
        r"\barbeitet .* zusammen\b",
        r"\bhilft\b",
        r"\brettet\b",
        r"\bverzichtet\b",
        r"\bübernimmt verantwortung\b",
        r"\bvereinigung\b",
        r"\bändert seine absicht\b",
    )

    MOTIF_PATTERNS = {
        "family": (
            r"\bfamilie\b",
            r"\bsohn\b",
            r"\bhalbbruder\b",
            r"\bmutter\b",
            r"\bvater\b",
        ),
        "revenge": (
            r"\brache\b",
            r"\bvergeltung\b",
        ),
        "power": (
            r"\bmacht\b",
            r"\bthron\b",
            r"\bkönig\b",
        ),
        "unity": (
            r"\bvereinigung\b",
            r"\bzusammen\b",
            r"\bmitgliedsstaat\b",
        ),
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _sentences(cls, text: str) -> list[str]:
        cleaned = cls._norm(text)
        if not cleaned:
            return []
        parts = re.split(r"(?<=[.!?])\s+", cleaned)
        return [
            part.strip()
            for part in parts
            if len(part.strip()) >= 20
        ]

    @classmethod
    def _matches(
        cls,
        sentence: str,
        patterns: tuple[str, ...],
    ) -> bool:
        lowered = sentence.casefold()
        return any(
            re.search(pattern, lowered, re.IGNORECASE)
            for pattern in patterns
        )

    @classmethod
    def _event_key(
        cls,
        index: int,
        sentence: str,
        prefix: str,
    ) -> str:
        slug = re.sub(
            r"[^a-z0-9]+",
            "-",
            sentence.casefold(),
        ).strip("-")[:48]
        return f"{prefix}:{index}:{slug or 'event'}"

    @classmethod
    def _extract_conflicts(
        cls,
        sentences: list[str],
        owner_key: str,
    ) -> list[dict[str, Any]]:
        relations = []
        for index, sentence in enumerate(sentences):
            if not cls._matches(sentence, cls.CONFLICT_PATTERNS):
                continue
            relations.append({
                "edge_type": "introduces_conflict",
                "source_node_key": owner_key,
                "target_node_key": cls._event_key(
                    index,
                    sentence,
                    "conflict",
                ),
                "confidence": 0.68,
                "reason": "Konflikthinweis im Handlungssatz erkannt.",
                "sentence": sentence,
                "requires_confirmation": True,
            })
        return relations

    @classmethod
    def _extract_resolutions(
        cls,
        sentences: list[str],
        owner_key: str,
    ) -> list[dict[str, Any]]:
        relations = []
        for index, sentence in enumerate(sentences):
            if not cls._matches(sentence, cls.RESOLUTION_PATTERNS):
                continue
            relations.append({
                "edge_type": "resolves_conflict",
                "source_node_key": owner_key,
                "target_node_key": cls._event_key(
                    index,
                    sentence,
                    "resolution",
                ),
                "confidence": 0.66,
                "reason": "Auflösungshinweis im Handlungssatz erkannt.",
                "sentence": sentence,
                "requires_confirmation": True,
            })
        return relations

    @classmethod
    def _extract_character_growth(
        cls,
        sentences: list[str],
    ) -> list[dict[str, Any]]:
        character_names = (
            "arthur",
            "orm",
            "mera",
            "david",
            "shin",
            "aquaman",
        )
        relations = []
        for index, sentence in enumerate(sentences):
            lowered = sentence.casefold()
            if not cls._matches(
                sentence,
                cls.CHARACTER_GROWTH_PATTERNS,
            ):
                continue
            for name in character_names:
                if re.search(rf"\b{re.escape(name)}\b", lowered):
                    relations.append({
                        "edge_type": "character_growth",
                        "source_node_key": f"character:{name}",
                        "target_node_key": cls._event_key(
                            index,
                            sentence,
                            "development",
                        ),
                        "confidence": 0.62,
                        "reason": (
                            "Hinweis auf Zusammenarbeit, Verantwortung "
                            "oder Verhaltensänderung erkannt."
                        ),
                        "sentence": sentence,
                        "requires_confirmation": True,
                    })
        return relations

    @classmethod
    def _extract_motifs(
        cls,
        sentences: list[str],
        owner_key: str,
    ) -> list[dict[str, Any]]:
        relations = []
        for motif, patterns in cls.MOTIF_PATTERNS.items():
            count = 0
            evidence = []
            for sentence in sentences:
                if cls._matches(sentence, patterns):
                    count += 1
                    evidence.append(sentence)
            if count < 2:
                continue
            relations.append({
                "edge_type": "repeats_motif",
                "source_node_key": owner_key,
                "target_node_key": f"motif:{motif}",
                "confidence": min(0.55 + count * 0.03, 0.78),
                "reason": (
                    f"Das Motiv {motif} wurde mehrfach im Handlungstext "
                    "erkannt."
                ),
                "evidence_sentences": evidence[:5],
                "requires_confirmation": True,
            })
        return relations

    @classmethod
    def extract(
        cls,
        *,
        text: str,
        source: dict[str, Any] | None = None,
        primary_title: str | None = None,
    ) -> dict[str, Any]:
        sentences = cls._sentences(text)
        owner_key = (
            "media:"
            + re.sub(
                r"[^a-z0-9]+",
                "-",
                cls._norm(primary_title).casefold(),
            ).strip("-")
        )
        if owner_key == "media:":
            owner_key = "media:unknown"

        relations = (
            cls._extract_conflicts(sentences, owner_key)
            + cls._extract_resolutions(sentences, owner_key)
            + cls._extract_character_growth(sentences)
            + cls._extract_motifs(sentences, owner_key)
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "owner_node_key": owner_key,
            "relations": relations,
            "summary": {
                "sentence_count": len(sentences),
                "relationship_count": len(relations),
                "conflict_count": sum(
                    item["edge_type"] == "introduces_conflict"
                    for item in relations
                ),
                "resolution_count": sum(
                    item["edge_type"] == "resolves_conflict"
                    for item in relations
                ),
                "character_growth_count": sum(
                    item["edge_type"] == "character_growth"
                    for item in relations
                ),
                "motif_count": sum(
                    item["edge_type"] == "repeats_motif"
                    for item in relations
                ),
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
