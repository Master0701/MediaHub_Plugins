from __future__ import annotations

import re
import uuid
from typing import Any


class CharacterIntelligence:
    """Erkennt einfache Beziehungen zwischen Figuren und Orten."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str) -> str:
        normalized = " ".join(str(title or "").casefold().split())
        return f"{kind}:{normalized}"

    def analyze(self, *, text: str, source: dict[str, Any]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        index: dict[str, dict[str, Any]] = {}
        warnings: list[str] = []

        def add_node(
            kind: str,
            title: str,
            confidence: float,
            reason: str,
            metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any] | None:
            title = self._norm(title)
            if not title:
                return None

            key = self._key(kind, title)
            existing = index.get(key)
            if existing is not None:
                existing["metadata"].update(dict(metadata or {}))
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(confidence),
                )
                return existing

            item = {
                "id": uuid.uuid4().hex,
                "key": key,
                "node_type": kind,
                "title": title,
                "metadata": dict(metadata or {}),
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            }
            index[key] = item
            nodes.append(item)
            return item

        def add_edge(
            edge_type: str,
            source_node: dict[str, Any] | None,
            target_node: dict[str, Any] | None,
            confidence: float,
            reason: str,
            sentence: str,
            metadata: dict[str, Any] | None = None,
        ) -> None:
            if source_node is None or target_node is None:
                return

            duplicate = any(
                edge["edge_type"] == edge_type
                and edge["source_node_key"] == source_node["key"]
                and edge["target_node_key"] == target_node["key"]
                for edge in edges
            )
            if duplicate:
                return

            evidence_id = uuid.uuid4().hex
            evidence.append(
                {
                    "id": evidence_id,
                    "text": sentence,
                    "edge_type": edge_type,
                    "source_id": source.get("id"),
                }
            )
            edges.append(
                {
                    "id": uuid.uuid4().hex,
                    "edge_type": edge_type,
                    "source_node_key": source_node["key"],
                    "target_node_key": target_node["key"],
                    "confidence": round(float(confidence), 4),
                    "reason": reason,
                    "metadata": dict(metadata or {}),
                    "evidence_id": evidence_id,
                    "source_id": source.get("id"),
                    "status": "proposed",
                    "requires_confirmation": True,
                }
            )

        rules = (
            (
                "married_to",
                re.compile(
                    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
                    r"(?:heiratete|ist verheiratet mit)\s+"
                    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
                    flags=re.IGNORECASE,
                ),
                0.88,
            ),
            (
                "parent_of",
                re.compile(
                    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
                    r"(?:bekam|hat)\s+(?:einen Sohn|eine Tochter|ein Kind),?\s+"
                    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
                    flags=re.IGNORECASE,
                ),
                0.82,
            ),
            (
                "sibling_of",
                re.compile(
                    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
                    r"(?:ist|war)\s+(?:der|die)\s+"
                    r"(?:Bruder|Schwester|Halbbruder|Halbschwester)\s+von\s+"
                    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
                    flags=re.IGNORECASE,
                ),
                0.86,
            ),
            (
                "enemy_of",
                re.compile(
                    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
                    r"(?:ist|war)\s+(?:der|die|ein|eine)?\s*"
                    r"(?:Erzfeind|Feind|Gegner)\s+von\s+"
                    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
                    flags=re.IGNORECASE,
                ),
                0.84,
            ),
            (
                "ally_of",
                re.compile(
                    r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
                    r"(?:ist|war)\s+(?:der|die|ein|eine)?\s*"
                    r"(?:Verbündete|Verbündeter|Verbündeterin)\s+von\s+"
                    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
                    flags=re.IGNORECASE,
                ),
                0.82,
            ),
        )

        for edge_type, pattern, confidence in rules:
            for match in pattern.finditer(text):
                left = add_node(
                    "character",
                    match.group(1),
                    confidence,
                    f"Figur aus {edge_type}-Aussage.",
                )
                right = add_node(
                    "character",
                    match.group(2),
                    confidence,
                    f"Ziel aus {edge_type}-Aussage.",
                )
                add_edge(
                    edge_type,
                    left,
                    right,
                    confidence,
                    f"Explizite Figurenbeziehung: {edge_type}.",
                    match.group(0),
                )

                if edge_type == "married_to":
                    add_edge(
                        edge_type,
                        right,
                        left,
                        confidence,
                        "Symmetrische Ehebeziehung.",
                        match.group(0),
                    )
                elif edge_type == "sibling_of":
                    add_edge(
                        edge_type,
                        right,
                        left,
                        confidence,
                        "Symmetrische Geschwisterbeziehung.",
                        match.group(0),
                    )
                elif edge_type == "parent_of":
                    add_edge(
                        "child_of",
                        right,
                        left,
                        confidence,
                        "Umkehrbeziehung zu parent_of.",
                        match.group(0),
                    )

        ruler_pattern = re.compile(
            r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
            r"(?:ist|war|wurde)\s+(?:König|Königin|Herrscher|Herrscherin)\s+"
            r"von\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
            flags=re.IGNORECASE,
        )
        for match in ruler_pattern.finditer(text):
            character = add_node(
                "character",
                match.group(1),
                0.87,
                "Herrscherfigur aus Handlungstext.",
            )
            location = add_node(
                "location",
                re.sub(
                    r"\s+(?:geworden|war|ist|wurde).*$",
                    "",
                    match.group(2),
                    flags=re.IGNORECASE,
                ),
                0.84,
                "Ort oder Reich aus Herrscherbeziehung.",
            )
            add_edge(
                "ruler_of",
                character,
                location,
                0.87,
                "Explizite Herrscherbeziehung.",
                match.group(0),
            )
            add_edge(
                "lives_in",
                character,
                location,
                0.74,
                "Aus Herrscherbeziehung abgeleitete Wohn-/Ortsbeziehung.",
                match.group(0),
                {"inferred": True},
            )

        lives_pattern = re.compile(
            r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s+"
            r"(?:lebt|wohnt)\s+in\s+"
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\b",
            flags=re.IGNORECASE,
        )
        for match in lives_pattern.finditer(text):
            character = add_node(
                "character",
                match.group(1),
                0.80,
                "Figur aus Ortsaussage.",
            )
            location = add_node(
                "location",
                match.group(2),
                0.80,
                "Ort aus Ortsaussage.",
            )
            add_edge(
                "lives_in",
                character,
                location,
                0.80,
                "Explizite Wohnortbeziehung.",
                match.group(0),
            )

        if not edges:
            warnings.append("Keine sicheren Figurenbeziehungen erkannt.")

        return {
            "schema_version": 1,
            "strategy": "character_intelligence_v350",
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
