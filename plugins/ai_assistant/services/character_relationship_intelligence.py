from __future__ import annotations

import re
from typing import Any


class CharacterRelationshipIntelligence:
    """Erkennt explizit formulierte Beziehungen zwischen Figuren."""

    STRATEGY = "character_relationship_intelligence_v490"

    RELATIONS = (
        ("father_of", (r"ist der vater von", r"is the father of")),
        ("mother_of", (r"ist die mutter von", r"is the mother of")),
        ("parent_of", (r"ist ein elternteil von", r"is a parent of")),
        ("brother_of", (r"ist der bruder von", r"is the brother of")),
        ("sister_of", (r"ist die schwester von", r"is the sister of")),
        ("sibling_of", (r"ist geschwister von", r"is a sibling of")),
        ("spouse_of", (r"ist (?:der ehepartner|die ehepartnerin) von", r"is married to", r"is the spouse of")),
        ("mentor_of", (r"ist der mentor von", r"ist die mentorin von", r"is the mentor of", r"mentors")),
        ("student_of", (r"ist der schüler von", r"ist die schülerin von", r"is the student of")),
        ("friend_of", (r"ist ein freund von", r"ist eine freundin von", r"is a friend of")),
        ("ally_of", (r"ist ein verbündeter von", r"ist eine verbündete von", r"is an ally of", r"allied with")),
        ("rival_of", (r"ist ein rivale von", r"ist eine rivalin von", r"is a rival of")),
        ("enemy_of", (r"ist ein feind von", r"ist eine feindin von", r"is an enemy of")),
        ("partner_of", (r"ist der partner von", r"ist die partnerin von", r"is the partner of")),
        ("teammate_of", (r"ist ein teammitglied von", r"is a teammate of")),
        ("protects", (r"beschützt", r"protects")),
        ("betrayed_by", (r"wurde von .* verraten", r"was betrayed by")),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _clean(cls, value: Any) -> str:
        return cls._norm(value).strip(" :–—-()[]{}.,;\"")

    @classmethod
    def _key(cls, title: str) -> str:
        return f"character:{cls._clean(title).casefold()}"

    @classmethod
    def analyze(cls, *, main_node: dict[str, Any], text: str,
                source: dict[str, Any] | None = None,
                character_roles: dict[str, Any] | None = None) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        raw = str(text or "")
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str, str]] = set()

        known_titles = {
            cls._clean(item.get("title"))
            for item in (character_roles or {}).get("nodes") or []
            if item.get("node_type") == "character" and cls._clean(item.get("title"))
        }

        name = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{1,70}?"

        def add_node(title: str) -> str:
            title = cls._clean(title)
            key = cls._key(title)
            if title and key not in seen_nodes:
                nodes.append({
                    "key": key,
                    "node_type": "character",
                    "title": title,
                    "confidence": 0.9,
                    "metadata": {"character_relationship_intelligence": cls.STRATEGY},
                    "reason": "Figur aus expliziter Beziehungsangabe erkannt.",
                    "source_id": source_id,
                    "automatic_import": False,
                    "requires_confirmation": True,
                })
                seen_nodes.add(key)
            return key

        def add_edge(relation: str, left: str, right: str, evidence: str, confidence: float = 0.9) -> None:
            source_key = add_node(left)
            target_key = add_node(right)
            edge_key = (relation, source_key, target_key)
            if edge_key in seen_edges:
                return
            edges.append({
                "edge_type": relation,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "metadata": {
                    "character_relationship_intelligence": cls.STRATEGY,
                    "evidence": cls._norm(evidence),
                },
                "reason": f"Explizite Figurenbeziehung `{relation}` erkannt.",
                "source_id": source_id,
                "automatic_import": False,
                "requires_confirmation": True,
            })
            observations.append({
                "relation_type": relation,
                "source": cls._clean(left),
                "target": cls._clean(right),
                "confidence": confidence,
                "evidence": cls._norm(evidence),
            })
            seen_edges.add(edge_key)

        for relation, phrases in cls.RELATIONS:
            for phrase in phrases:
                if relation == "betrayed_by":
                    pattern = re.compile(rf"\b(?P<left>{name})\s+(?P<phrase>{phrase.replace('.*', rf'(?P<right>{name})')})", re.I)
                elif relation in {"protects"}:
                    pattern = re.compile(rf"\b(?P<left>{name})\s+(?P<phrase>{phrase})\s+(?P<right>{name})\b", re.I)
                else:
                    pattern = re.compile(rf"\b(?P<left>{name})\s+(?P<phrase>{phrase})\s+(?P<right>{name})\b", re.I)
                for match in pattern.finditer(raw):
                    left = cls._clean(match.group("left"))
                    right = cls._clean(match.group("right"))
                    if not left or not right or left.casefold() == right.casefold():
                        continue
                    confidence = 0.93 if left in known_titles or right in known_titles else 0.88
                    add_edge(relation, left, right, match.group(0), confidence)

        return {
            "strategy": cls.STRATEGY,
            "nodes": nodes,
            "edges": edges,
            "observations": observations,
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "relation_types": sorted({item[0] for item in seen_edges}),
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
