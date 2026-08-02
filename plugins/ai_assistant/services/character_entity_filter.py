from __future__ import annotations

import re
from typing import Any


class CharacterEntityFilter:
    STRATEGY = "character_entity_filter_v601"

    INVALID_PREFIXES = {
        "befreit",
        "kämpft",
        "hilft",
        "trifft",
        "rettet",
        "greift",
        "findet",
        "erfährt",
        "beschließt",
        "flieht",
        "wirft",
        "entführt",
        "verletzt",
        "tötet",
        "sucht",
        "arbeitet",
    }

    SENTENCE_MARKERS = (
        ".",
        "!",
        "?",
        ";",
        ":",
        ",",
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def is_valid_character_name(cls, value: Any) -> bool:
        name = cls._norm(value)
        if not name:
            return False

        lowered = name.casefold()

        if len(name) < 2 or len(name) > 80:
            return False

        if any(marker in name for marker in cls.SENTENCE_MARKERS):
            return False

        words = name.split()
        if len(words) > 5:
            return False

        if words and words[0].casefold() in cls.INVALID_PREFIXES:
            return False

        if lowered.startswith(("der ", "die ", "das ", "ein ", "eine ")):
            return False

        if re.search(r"\b(und|oder|während|nachdem|bevor|dass)\b", lowered):
            return False

        if re.fullmatch(r"\d+", name):
            return False

        return True

    @classmethod
    def filter_graph_payload(
        cls,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(payload or {})
        nodes = []
        valid_ids = set()
        rejected = []

        for node in result.get("nodes") or []:
            if not isinstance(node, dict):
                continue

            node_type = cls._norm(node.get("node_type")).casefold()
            node_id = cls._norm(node.get("id"))
            title = cls._norm(
                node.get("title")
                or node_id.split(":", 1)[-1]
            )

            if node_type == "character":
                if not cls.is_valid_character_name(title):
                    rejected.append({
                        "id": node_id,
                        "title": title,
                        "reason": "invalid_character_name",
                    })
                    continue

            nodes.append(dict(node))
            if node_id:
                valid_ids.add(node_id)

        edges = []
        for edge in result.get("edges") or []:
            if not isinstance(edge, dict):
                continue

            source = cls._norm(edge.get("source_node_key"))
            target = cls._norm(edge.get("target_node_key"))

            if source and source not in valid_ids:
                continue
            if target and target not in valid_ids:
                continue

            edges.append(dict(edge))

        result["nodes"] = nodes
        result["edges"] = edges
        result["filter_report"] = {
            "strategy": cls.STRATEGY,
            "rejected_character_count": len(rejected),
            "rejected_characters": rejected,
            "kept_node_count": len(nodes),
            "kept_edge_count": len(edges),
            "automatic_resolution": False,
            "requires_confirmation": True,
        }

        summary = dict(result.get("summary") or {})
        summary["node_count"] = len(nodes)
        summary["edge_count"] = len(edges)
        summary["rejected_character_count"] = len(rejected)
        result["summary"] = summary

        result["automatic_import"] = False
        result["requires_confirmation"] = True
        return result
