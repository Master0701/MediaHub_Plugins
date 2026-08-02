from __future__ import annotations

from collections import defaultdict
from typing import Any


class MissingEntityResolver:
    STRATEGY = "missing_entity_resolver_v703"

    TYPE_HINTS = {
        "belongs_to_franchise": "franchise",
        "belongs_to_universe": "universe",
        "belongs_to_timeline": "timeline",
        "portrayed_by": "person",
        "voices": "person",
        "appears_in": "media",
        "lives_in": "location",
        "ruler_of": "location",
        "parent_of": "character",
        "child_of": "character",
        "sibling_of": "character",
        "married_to": "character",
        "partner_of": "character",
        "ally_of": "character",
        "enemy_of": "character",
        "sequel_of": "media",
        "prequel_of": "media",
        "spin_off_of": "media",
        "backdoor_pilot_for": "series",
        "legacy_sequel_of": "media",
        "soft_reboot_of": "media",
        "hard_reboot_of": "media",
        "parallel_universe_of": "universe",
        "alternate_timeline_of": "timeline",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _guess_type(
        cls,
        node_key: str,
        edge_type: str,
    ) -> str:
        if ":" in node_key:
            prefix = cls._norm(node_key.split(":", 1)[0]).casefold()
            if prefix:
                return prefix
        return cls.TYPE_HINTS.get(edge_type, "entity")

    @classmethod
    def _guess_title(cls, node_key: str) -> str:
        raw = node_key.split(":", 1)[-1]
        raw = raw.replace("-", " ").replace("_", " ")
        return " ".join(part.capitalize() for part in raw.split())

    @classmethod
    def build(
        cls,
        *,
        knowledge_graph_validation: dict[str, Any],
        global_knowledge: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        checks = knowledge_graph_validation.get("checks") or {}
        edge_check = checks.get("edges") or {}
        orphaned_edges = list(edge_check.get("orphaned_edges") or [])

        existing_nodes = {
            cls._norm(node.get("node_key") or node.get("id"))
            for node in (
                (global_knowledge.get("graph") or {}).get("nodes") or []
            )
            if isinstance(node, dict)
            and cls._norm(node.get("node_key") or node.get("id"))
        }

        proposals = {}
        references = defaultdict(list)

        for orphan in orphaned_edges:
            if not isinstance(orphan, dict):
                continue

            edge_key = cls._norm(orphan.get("edge_key"))
            parts = edge_key.split("|", 2)
            edge_type = parts[0].casefold() if len(parts) == 3 else ""

            for missing_node in orphan.get("missing_nodes") or []:
                node_key = cls._norm(missing_node)
                if not node_key or node_key in existing_nodes:
                    continue

                node_type = cls._guess_type(node_key, edge_type)
                proposal = proposals.setdefault(node_key, {
                    "node_key": node_key,
                    "node_type": node_type,
                    "title": cls._guess_title(node_key),
                    "confidence": 0.68,
                    "reason": "referenced_by_orphaned_edge",
                    "referenced_by_edges": [],
                    "automatic_creation": False,
                    "requires_confirmation": True,
                })

                references[node_key].append(edge_key)
                proposal["referenced_by_edges"] = sorted(set(
                    proposal["referenced_by_edges"] + [edge_key]
                ))

                if ":" in node_key:
                    proposal["confidence"] = max(
                        proposal["confidence"],
                        0.78,
                    )

                if edge_type in cls.TYPE_HINTS:
                    proposal["confidence"] = max(
                        proposal["confidence"],
                        0.82,
                    )

        grouped = defaultdict(list)
        for proposal in proposals.values():
            grouped[proposal["node_type"]].append(proposal["node_key"])

        type_counts = {
            node_type: len(node_keys)
            for node_type, node_keys in sorted(grouped.items())
        }

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "missing_node_proposals": sorted(
                proposals.values(),
                key=lambda item: (
                    item["node_type"],
                    item["node_key"],
                ),
            ),
            "summary": {
                "orphaned_edge_count": len(orphaned_edges),
                "missing_node_proposal_count": len(proposals),
                "proposal_type_counts": type_counts,
                "existing_node_count": len(existing_nodes),
            },
            "decision": {
                "status": (
                    "needs_confirmation"
                    if proposals
                    else "no_missing_entities"
                ),
                "automatic_creation": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
