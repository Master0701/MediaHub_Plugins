from __future__ import annotations

import re
from typing import Any


class EntityIntelligence:
    """Erkennt explizit benannte Medienentitäten und ihre Beziehungen."""

    STRATEGY = "entity_intelligence_v500"

    TYPE_PATTERNS = (
        ("organization", (
            r"organisation", r"organization", r"behörde", r"agency",
            r"unternehmen", r"company", r"team", r"fraktion", r"faction",
        )),
        ("spacecraft", (
            r"raumschiff", r"starship", r"spacecraft", r"spaceship",
        )),
        ("vehicle", (
            r"fahrzeug", r"vehicle", r"auto", r"car", r"flugzeug",
            r"aircraft", r"schiff", r"ship",
        )),
        ("planet", (
            r"planet", r"mond", r"moon", r"welt", r"world",
        )),
        ("location", (
            r"stadt", r"city", r"ort", r"location", r"land", r"country",
            r"region", r"galaxie", r"galaxy", r"gebäude", r"building",
            r"basis", r"base", r"station",
        )),
        ("species", (
            r"spezies", r"species", r"volk", r"race", r"alien race",
        )),
        ("technology", (
            r"technologie", r"technology", r"gerät", r"device",
            r"zeitmaschine", r"time machine", r"computer",
        )),
        ("weapon", (
            r"waffe", r"weapon", r"schwert", r"sword", r"gewehr", r"gun",
        )),
        ("artifact", (
            r"artefakt", r"artifact", r"reliquie", r"relic",
            r"magischer gegenstand", r"magical object",
        )),
    )

    RELATION_PATTERNS = (
        ("member_of", (
            r"ist mitglied von", r"is a member of", r"gehört zu",
            r"belongs to",
        )),
        ("operated_by", (
            r"wird betrieben von", r"is operated by",
        )),
        ("commanded_by", (
            r"wird kommandiert von", r"is commanded by",
            r"steht unter dem kommando von", r"is under the command of",
        )),
        ("owned_by", (
            r"gehört", r"is owned by",
        )),
        ("located_in", (
            r"liegt in", r"befindet sich in", r"is located in",
            r"is situated in",
        )),
        ("homeworld_of", (
            r"ist die heimatwelt von", r"is the homeworld of",
        )),
        ("created_by", (
            r"wurde erschaffen von", r"wurde entwickelt von",
            r"was created by", r"was developed by",
        )),
        ("used_by", (
            r"wird benutzt von", r"wird verwendet von",
            r"is used by", r"is wielded by",
        )),
        ("allied_with", (
            r"ist verbündet mit", r"is allied with",
        )),
        ("enemy_of", (
            r"ist ein feind von", r"is an enemy of",
        )),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _clean(cls, value: Any) -> str:
        return cls._norm(value).strip(" :–—-()[]{}.,;\"'")

    @classmethod
    def _key(cls, node_type: str, title: str) -> str:
        return f"{node_type}:{cls._clean(title).casefold()}"

    @classmethod
    def analyze(
        cls,
        *,
        main_node: dict[str, Any],
        text: str,
        source: dict[str, Any] | None = None,
        character_roles: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        main_node = dict(main_node or {})
        source = dict(source or {})
        source_id = source.get("id")
        main_type = cls._norm(main_node.get("node_type") or "media")
        main_title = cls._clean(main_node.get("title"))
        main_key = cls._norm(main_node.get("key")) or cls._key(main_type, main_title)

        raw = str(text or "")
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+|[\r\n]+", raw)
            if item.strip()
        ]
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str, str]] = set()
        node_types: dict[str, str] = {}

        known_characters = {
            cls._clean(item.get("title")).casefold()
            for item in (character_roles or {}).get("nodes") or []
            if item.get("node_type") == "character" and cls._clean(item.get("title"))
        }

        def add_node(node_type: str, title: str, confidence: float, reason: str, evidence: str) -> str:
            title = cls._clean(title)
            if not title:
                return ""
            folded = title.casefold()
            if folded in known_characters:
                node_type = "character"
            key = cls._key(node_type, title)
            node_types[folded] = node_type
            if key not in seen_nodes:
                nodes.append({
                    "key": key,
                    "node_type": node_type,
                    "title": title,
                    "confidence": confidence,
                    "metadata": {
                        "entity_intelligence": cls.STRATEGY,
                        "evidence": cls._norm(evidence),
                    },
                    "reason": reason,
                    "source_id": source_id,
                    "automatic_import": False,
                    "requires_confirmation": True,
                })
                seen_nodes.add(key)
            return key

        def inferred_type(title: str) -> str:
            folded = cls._clean(title).casefold()
            if folded in known_characters:
                return "character"
            return node_types.get(folded, "entity")

        def add_edge(edge_type: str, source_key: str, target_key: str, confidence: float, evidence: str) -> None:
            if not source_key or not target_key or source_key == target_key:
                return
            marker = (edge_type, source_key, target_key)
            if marker in seen_edges:
                return
            edges.append({
                "edge_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "metadata": {
                    "entity_intelligence": cls.STRATEGY,
                    "evidence": cls._norm(evidence),
                },
                "reason": f"Explizite Entitätsbeziehung `{edge_type}` erkannt.",
                "source_id": source_id,
                "automatic_import": False,
                "requires_confirmation": True,
            })
            observations.append({
                "relation_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "evidence": cls._norm(evidence),
            })
            seen_edges.add(marker)

        name = r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .:'’\-]{1,80}?"

        for node_type, labels in cls.TYPE_PATTERNS:
            label_union = "|".join(labels)
            patterns = (
                re.compile(
                    rf"\b(?:die|der|das|the)?\s*(?P<title>{name})\s+"
                    rf"(?:ist|sind|is|are)\s+(?:ein|eine|einer|an?|the)?\s*"
                    rf"(?P<label>{label_union})\b",
                    re.IGNORECASE,
                ),
                re.compile(
                    rf"\b(?P<title>{name})\s*,\s+(?:ein|eine|an?)\s+"
                    rf"(?P<label>{label_union})\b",
                    re.IGNORECASE,
                ),
            )
            for pattern in patterns:
                for sentence in sentences:
                    for match in pattern.finditer(sentence):
                        title = cls._clean(match.group("title"))
                        if not title or len(title.split()) > 10:
                            continue
                        key = add_node(
                            node_type,
                            title,
                            0.91,
                            f"Entität wurde ausdrücklich als `{node_type}` bezeichnet.",
                            match.group(0),
                        )
                        add_edge("appears_in", key, main_key, 0.86, match.group(0))

        for relation, phrases in cls.RELATION_PATTERNS:
            phrase_union = "|".join(phrases)
            if relation == "used_by":
                pattern = re.compile(
                    rf"\b(?P<left>{name})\s+"
                    rf"(?P<phrase>wird\s+(?:benutzt|verwendet)\s+von|"
                    rf"is\s+(?:used|wielded)\s+by)\s+"
                    rf"(?P<right>{name})(?=[.!?;\n]|$)",
                    re.IGNORECASE,
                )
            else:
                pattern = re.compile(
                    rf"\b(?P<left>{name})\s+(?P<phrase>{phrase_union})\s+"
                    rf"(?:die|der|das|den|dem|the|a|an)?\s*(?P<right>{name})"
                    rf"(?=[.!?;\n]|$)",
                    re.IGNORECASE,
                )
            for sentence in sentences:
                for match in pattern.finditer(sentence):
                    left = cls._clean(match.group("left"))
                    right = cls._clean(match.group("right"))
                    if (
                        not left
                        or not right
                        or left.casefold() == right.casefold()
                        or len(left.split()) > 10
                        or len(right.split()) > 10
                    ):
                        continue
                    left_key = add_node(
                        inferred_type(left),
                        left,
                        0.86,
                        "Entität aus expliziter Beziehung erkannt.",
                        match.group(0),
                    )
                    right_key = add_node(
                        inferred_type(right),
                        right,
                        0.86,
                        "Entität aus expliziter Beziehung erkannt.",
                        match.group(0),
                    )
                    add_edge(relation, left_key, right_key, 0.89, match.group(0))
                    add_edge("appears_in", left_key, main_key, 0.82, match.group(0))
                    add_edge("appears_in", right_key, main_key, 0.82, match.group(0))

        return {
            "strategy": cls.STRATEGY,
            "nodes": nodes,
            "edges": edges,
            "observations": observations,
            "summary": {
                "node_count": len(nodes),
                "edge_count": len(edges),
                "node_types": sorted({item["node_type"] for item in nodes}),
                "relation_types": sorted({item["edge_type"] for item in edges}),
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
