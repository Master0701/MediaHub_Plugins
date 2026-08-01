from __future__ import annotations
import re
import uuid
from typing import Any


class RelationshipBuilder:
    RELATION_PATTERNS = (
        ("sequel_of", r"\bist die Fortsetzung von\s+(.+?)(?:\s+aus dem Jahr\s+(19\d{2}|20\d{2}))?[.!]", "movie", 0.94),
        ("prequel_of", r"\bist ein Prequel zu\s+(.+?)(?:\s+aus dem Jahr\s+(19\d{2}|20\d{2}))?[.!]", "movie", 0.90),
        ("spin_off_of", r"\bist ein Spin[- ]?off von\s+(.+?)(?:\s+aus dem Jahr\s+(19\d{2}|20\d{2}))?[.!]", "series", 0.88),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str, year=None) -> str:
        suffix = f":{year}" if year not in (None, "") else ""
        return f"{kind}:{' '.join(title.casefold().split())}{suffix}"

    def build(self, *, main_node, text, source):
        nodes, edges, evidence, index = [], [], [], {}

        def add_node(kind, title, year=None, confidence=0.8, reason="", metadata=None):
            title = self._norm(title)
            key = self._key(kind, title, year)
            if key in index:
                return index[key]
            item = {
                "id": uuid.uuid4().hex,
                "key": key,
                "node_type": kind,
                "title": title,
                "year": year,
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

        def add_edge(kind, src, dst, confidence, reason, sentence):
            if any(
                e["edge_type"] == kind
                and e["source_node_key"] == src["key"]
                and e["target_node_key"] == dst["key"]
                for e in edges
            ):
                return
            evidence_id = uuid.uuid4().hex
            evidence.append({
                "id": evidence_id,
                "sentence": sentence,
                "edge_type": kind,
                "source_id": source.get("id"),
            })
            edges.append({
                "id": uuid.uuid4().hex,
                "edge_type": kind,
                "source_node_key": src["key"],
                "target_node_key": dst["key"],
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "evidence_id": evidence_id,
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            })

        main = add_node(
            str(main_node.get("node_type") or "media"),
            str(main_node.get("title") or ""),
            main_node.get("year"),
            float(main_node.get("confidence") or 0.8),
            "Hauptknoten aus Graph Builder.",
            dict(main_node.get("metadata") or {}),
        )

        for edge_type, pattern, target_type, confidence in self.RELATION_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                target_title = self._norm(match.group(1))
                target_year = int(match.group(2)) if match.group(2) else None
                target = add_node(
                    target_type, target_title, target_year,
                    confidence, f"Ziel aus {edge_type}.",
                )
                add_edge(
                    edge_type, main, target, confidence,
                    f"Explizite Beziehung {edge_type}.",
                    match.group(0),
                )

        cast_match = re.search(
            r"\bBesetzung\b(.+?)(?:\bChronologie\b|\bHandlung\b)",
            text, flags=re.IGNORECASE | re.DOTALL
        )
        cast_text = cast_match.group(1) if cast_match else ""
        cast_pattern = re.compile(
            r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,80})\s*:\s*"
            r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß /.'’-]{2,100})"
        )
        for match in cast_pattern.finditer(cast_text):
            actor_name = self._norm(match.group(1))
            role_name = self._norm(match.group(2))
            actor = add_node("person", actor_name, confidence=0.84, reason="Schauspieler aus Besetzung.")
            character = add_node("character", role_name, confidence=0.82, reason="Figur aus Besetzung.")
            add_edge("appears_in", character, main, 0.82, "Figur erscheint im Werk.", match.group(0))
            add_edge("portrayed_by", character, actor, 0.84, "Besetzungszuordnung.", match.group(0))

        return {
            "schema_version": 1,
            "strategy": "relationship_builder_v310",
            "main_node_key": main["key"],
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "automatic_import": False,
            "requires_confirmation": True,
        }
