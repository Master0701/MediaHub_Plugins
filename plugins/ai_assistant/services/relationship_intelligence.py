from __future__ import annotations

import re
import uuid
from typing import Any

from services.alias_parser import AliasParser


class RelationshipIntelligence:
    """Erkennt handlungsbezogene Beziehungen zwischen Figuren und Objekten."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str) -> str:
        normalized = " ".join(str(title or "").casefold().split())
        return f"{kind}:{normalized}"

    @classmethod
    def _clean_name(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"^(?:der|die|das|ein|eine|seinen|seine|seiner|ihren|ihre)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip(" ,.;:")

    @classmethod
    def _clean_character_reference(cls, value: str) -> str:
        text = cls._clean_name(value)
        text = re.split(
            r"\s+(?:alias|auch bekannt als)\s+",
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        return text

    def analyze(self, *, text: str, source: dict[str, Any]) -> dict[str, Any]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        warnings: list[str] = []
        index: dict[str, dict[str, Any]] = {}

        def add_node(
            node_type: str,
            title: str,
            confidence: float,
            reason: str,
            metadata: dict[str, Any] | None = None,
        ) -> dict[str, Any] | None:
            if node_type == "character":
                title = self._clean_character_reference(title)
            else:
                title = self._clean_name(title)

            if not title:
                return None

            key = self._key(node_type, title)
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
                "node_type": node_type,
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

        char_name = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{1,80}"
        object_name = r"[A-ZÄÖÜa-zäöüß][A-Za-zÄÖÜäöüß0-9 .'-]{1,100}"

        rules = (
            (
                "works_with",
                re.compile(
                    rf"\b({char_name})\s+arbeitet(?:e)?\s+"
                    rf"(?:mit|zusammen mit)\s+({char_name})\s+zusammen\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.84,
            ),
            (
                "works_with",
                re.compile(
                    rf"\b({char_name})\s+arbeitet(?:e)?\s+mit\s+"
                    rf"({char_name})\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.80,
            ),
            (
                "rescues",
                re.compile(
                    rf"\b({char_name})\s+(?:rettet|rettete|befreit|befreite)\s+"
                    rf"({char_name})\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.84,
            ),
            (
                "fights_with",
                re.compile(
                    rf"\b({char_name})\s+(?:kämpft|kämpfte)\s+"
                    rf"(?:gegen|mit)\s+({char_name})\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.80,
            ),
            (
                "kidnaps",
                re.compile(
                    rf"\b({char_name})\s+(?:entführt|entführte)\s+"
                    rf"({char_name})\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.88,
            ),
            (
                "protects",
                re.compile(
                    rf"\b({char_name})\s+(?:beschützt|beschützte|verteidigt|"
                    rf"verteidigte)\s+({char_name})\b",
                    flags=re.IGNORECASE,
                ),
                "character",
                "character",
                0.82,
            ),
            (
                "created_by",
                re.compile(
                    rf"\b(?:der|die|das)\s+({object_name})\s+"
                    rf"(?:wurde|war)\s+von\s+({char_name})\s+"
                    rf"(?:erschaffen|geschaffen|gebaut)\b",
                    flags=re.IGNORECASE,
                ),
                "artifact",
                "character",
                0.86,
            ),
        )

        symmetric_edges = {"works_with", "fights_with"}

        for edge_type, pattern, left_type, right_type, confidence in rules:
            for match in pattern.finditer(text):
                left = add_node(
                    left_type,
                    match.group(1),
                    confidence,
                    f"Quelle aus {edge_type}-Aussage.",
                )
                right = add_node(
                    right_type,
                    match.group(2),
                    confidence,
                    f"Ziel aus {edge_type}-Aussage.",
                )
                add_edge(
                    edge_type,
                    left,
                    right,
                    confidence,
                    f"Explizite Handlungsbeziehung: {edge_type}.",
                    match.group(0),
                )

                if edge_type in symmetric_edges:
                    add_edge(
                        edge_type,
                        right,
                        left,
                        confidence,
                        f"Symmetrische Handlungsbeziehung: {edge_type}.",
                        match.group(0),
                    )

                if edge_type == "kidnaps":
                    add_edge(
                        "kidnapped_by",
                        right,
                        left,
                        confidence,
                        "Umkehrbeziehung zu kidnaps.",
                        match.group(0),
                    )

                if edge_type == "rescues":
                    add_edge(
                        "rescued_by",
                        right,
                        left,
                        confidence,
                        "Umkehrbeziehung zu rescues.",
                        match.group(0),
                    )

                if edge_type == "created_by":
                    add_edge(
                        "creates",
                        right,
                        left,
                        confidence,
                        "Umkehrbeziehung zu created_by.",
                        match.group(0),
                    )

        for alias_result in AliasParser.parse(text):
            primary = add_node(
                "character",
                alias_result["primary"],
                0.88,
                "Hauptfigur aus Alias-Aussage.",
            )
            alias = add_node(
                "character_alias",
                alias_result["alias"],
                0.88,
                "Alias aus Alias-Aussage.",
            )
            add_edge(
                "alias_of",
                alias,
                primary,
                0.90,
                "Explizite Alias-Aussage.",
                alias_result["evidence"],
                {
                    "separator": alias_result["separator"],
                    "parser": "dedicated_alias_parser_v363",
                },
            )

        half_brother_pattern = re.compile(
            rf"\b({char_name})\s+(?:seinen|ihren)\s+"
            rf"(?:Halbbruder|Halbschwester)\s+({char_name})\b",
            flags=re.IGNORECASE,
        )
        for match in half_brother_pattern.finditer(text):
            first = add_node(
                "character",
                match.group(1),
                0.78,
                "Figur aus Geschwisteraussage.",
            )
            second = add_node(
                "character",
                match.group(2),
                0.78,
                "Geschwisterfigur aus Handlungstext.",
            )
            add_edge(
                "sibling_of",
                first,
                second,
                0.82,
                "Halbgeschwisterbeziehung aus Handlungstext.",
                match.group(0),
            )
            add_edge(
                "sibling_of",
                second,
                first,
                0.82,
                "Symmetrische Halbgeschwisterbeziehung.",
                match.group(0),
            )

        possession_pattern = re.compile(
            rf"\b({char_name})\s+findet\s+(?:einen|eine|ein)\s+"
            rf"({object_name})\b",
            flags=re.IGNORECASE,
        )
        for match in possession_pattern.finditer(text):
            character = add_node(
                "character",
                match.group(1),
                0.76,
                "Figur aus Fund-Aussage.",
            )
            artifact = add_node(
                "artifact",
                match.group(2),
                0.76,
                "Artefakt aus Fund-Aussage.",
            )
            add_edge(
                "finds",
                character,
                artifact,
                0.78,
                "Explizite Fundbeziehung.",
                match.group(0),
            )

        if not edges:
            warnings.append("Keine zusätzlichen Handlungsbeziehungen erkannt.")

        return {
            "schema_version": 1,
            "strategy": "relationship_intelligence_v360",
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
