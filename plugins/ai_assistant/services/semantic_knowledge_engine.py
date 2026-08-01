from __future__ import annotations
import re
import uuid
from typing import Any


class SemanticKnowledgeEngine:
    ENTITY_PATTERNS = (
        ("character", (r"\bist ein(?:e|er)?\s+(?:fiktive[rn]?\s+|comic[- ]?)?figur\b", r"\bist ein superheld\b", r"\bcomicfigur\b")),
        (
            "movie",
            (
                r"\bist ein(?:e|er)?\s+.*?\bfilm\b",
                r"\bkinofilm\b",
                r"\bspielfilm\b",
                r"\berschien(?:e|en)?\s+(?:der|die|das)?\s*film\b",
                r"\bfilm\s+[A-ZÄÖÜ]",
                r"\bveröffentlicht(?:e|en)?\s+.*?\bfilm\b",
            ),
        ),
        ("series", (r"\bfernsehserie\b", r"\bzeichentrickserie\b")),
        ("audiobook", (r"\bhörbuch\b", r"\baudiobook\b")),
        ("publisher", (r"\bcomicverlag\b", r"\bverlag\b")),
        ("universe", (r"\buniversum\b", r"\bextended universe\b")),
    )
    RELATION_PATTERNS = (
        ("sequel", r"\b(?:fortsetzung|nachfolger)\b"),
        ("prequel", r"\bprequel\b"),
        ("spin_off", r"\bspin[- ]?off\b"),
        ("crossover", r"\bcrossover\b"),
        ("reboot", r"\breboot\b"),
        ("remake", r"\bremake\b"),
    )

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _sentences(text: str) -> list[str]:
        text = re.sub(r"\s+", " ", str(text or "")).strip()
        return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]

    @classmethod
    def _type_from_sentence(cls, sentence: str):
        for entity_type, patterns in cls.ENTITY_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, sentence, flags=re.IGNORECASE):
                    confidence = 0.90 if entity_type == "character" else 0.84
                    return entity_type, confidence, f"Eindeutiger Typ-Hinweis: {pattern}"
        return None, 0.0, None

    @staticmethod
    def _year(sentence: str):
        match = re.search(r"\b(19\d{2}|20\d{2})\b", sentence)
        return int(match.group(1)) if match else None

    def analyze(self, *, title: str, text: str, source: dict[str, Any]):
        title = self._normalize(title)
        primary_type = None
        primary_confidence = 0.0
        primary_reason = None
        entities = []
        relations = []
        observations = []

        for sentence in self._sentences(text):
            lowered = sentence.casefold()
            entity_type, confidence, reason = self._type_from_sentence(sentence)
            year = self._year(sentence)

            if title and title.casefold() in lowered and confidence > primary_confidence:
                primary_type = entity_type
                primary_confidence = confidence
                primary_reason = reason

            if title and title.casefold() in lowered and year and entity_type:
                entities.append({
                    "id": uuid.uuid4().hex,
                    "title": title,
                    "entity_type": entity_type,
                    "year": year,
                    "confidence": round(min(0.97, confidence + 0.05), 4),
                    "sentence": sentence,
                    "reason": "Titel, Typ und Jahr stehen im selben Satz.",
                    "source_id": source.get("id"),
                    "requires_confirmation": True,
                })

            for relation_type, pattern in self.RELATION_PATTERNS:
                if re.search(pattern, sentence, flags=re.IGNORECASE):
                    relations.append({
                        "id": uuid.uuid4().hex,
                        "relation_type": relation_type,
                        "sentence": sentence,
                        "confidence": 0.66,
                        "reason": "Beziehungsbegriff im Satz erkannt.",
                        "source_id": source.get("id"),
                        "requires_confirmation": True,
                    })

            observations.append({"sentence": sentence, "year": year, "type_hint": entity_type})

        unique = {}
        for item in entities:
            key = (item["title"], item["entity_type"], item["year"])
            if key not in unique or item["confidence"] > unique[key]["confidence"]:
                unique[key] = item

        return {
            "schema_version": 1,
            "strategy": "semantic_knowledge_engine_v271",
            "primary_title": title,
            "primary_entity_type": primary_type,
            "primary_entity_confidence": round(primary_confidence, 4),
            "primary_entity_reason": primary_reason,
            "entity_proposals": list(unique.values()),
            "relation_proposals": relations,
            "observations": observations[:200],
            "automatic_import": False,
            "requires_confirmation": True,
        }
