from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Any


class EntityResolutionGraph:
    STRATEGY = "entity_resolution_graph_v610"

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _canonical_text(cls, value: Any) -> str:
        text = unicodedata.normalize("NFKD", cls._norm(value))
        text = "".join(
            char for char in text
            if not unicodedata.combining(char)
        )
        text = text.casefold()
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return " ".join(text.split())

    @classmethod
    def _confidence(cls, value: Any, default: float = 0.5) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        if number > 1.0:
            number /= 100.0
        return max(0.0, min(1.0, number))

    @classmethod
    def _collect_nodes(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        nodes: dict[str, dict[str, Any]] = {}

        for payload in payloads:
            for item in (
                payload.get("nodes")
                or payload.get("entities")
                or payload.get("entity_proposals")
                or []
            ):
                if not isinstance(item, dict):
                    continue

                node_id = cls._norm(
                    item.get("id")
                    or item.get("node_key")
                    or item.get("entity_id")
                )
                title = cls._norm(
                    item.get("title")
                    or item.get("name")
                    or item.get("label")
                )
                node_type = cls._norm(
                    item.get("node_type")
                    or item.get("entity_type")
                    or item.get("type")
                ).casefold()

                if not node_id:
                    if not title:
                        continue
                    node_id = (
                        f"{node_type or 'entity'}:"
                        + cls._canonical_text(title).replace(" ", "-")
                    )

                if not title:
                    title = node_id.split(":", 1)[-1]

                existing = nodes.get(node_id)
                candidate = {
                    "id": node_id,
                    "title": title,
                    "node_type": node_type or "entity",
                    "canonical_title": cls._canonical_text(title),
                    "year": item.get("year"),
                    "source_strategy": payload.get("strategy"),
                    "confidence": cls._confidence(
                        item.get("confidence"), 0.6
                    ),
                }

                if existing is None or candidate["confidence"] > existing["confidence"]:
                    nodes[node_id] = candidate

        return list(nodes.values())

    @classmethod
    def _collect_alias_evidence(
        cls,
        *payloads: dict[str, Any],
    ) -> list[dict[str, Any]]:
        evidence = []

        for payload in payloads:
            items = (
                payload.get("edges")
                or payload.get("relations")
                or payload.get("conclusions")
                or []
            )
            for item in items:
                if not isinstance(item, dict):
                    continue

                edge_type = cls._norm(
                    item.get("edge_type")
                    or item.get("relation_type")
                ).casefold()

                if edge_type not in {
                    "alias_of",
                    "same_identity_as",
                    "secret_identity_of",
                    "portrays",
                    "portrayed_by",
                }:
                    continue

                source = cls._norm(item.get("source_node_key"))
                target = cls._norm(item.get("target_node_key"))
                if not source or not target:
                    continue

                evidence.append({
                    "edge_type": edge_type,
                    "source_node_key": source,
                    "target_node_key": target,
                    "confidence": cls._confidence(
                        item.get("confidence"), 0.7
                    ),
                    "origin": payload.get("strategy"),
                })

        return evidence

    @classmethod
    def _same_type(cls, left: dict[str, Any], right: dict[str, Any]) -> bool:
        left_type = cls._norm(left.get("node_type")).casefold()
        right_type = cls._norm(right.get("node_type")).casefold()
        return (
            not left_type
            or not right_type
            or left_type == right_type
            or {left_type, right_type}
            <= {"character", "identity", "person"}
        )

    @classmethod
    def _year_compatible(
        cls,
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> bool:
        left_year = left.get("year")
        right_year = right.get("year")
        if left_year in (None, "") or right_year in (None, ""):
            return True
        try:
            return abs(int(left_year) - int(right_year)) <= 1
        except (TypeError, ValueError):
            return True

    @classmethod
    def build(
        cls,
        *,
        semantic_result: dict[str, Any],
        franchise_knowledge_graph: dict[str, Any],
        character_relationship_graph: dict[str, Any],
        character_identity_fusion: dict[str, Any],
        relationship_identity_map: dict[str, Any],
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        nodes = cls._collect_nodes(
            semantic_result,
            franchise_knowledge_graph,
            character_relationship_graph,
            character_identity_fusion,
            relationship_identity_map,
        )

        alias_evidence = cls._collect_alias_evidence(
            character_relationship_graph,
            character_identity_fusion,
            relationship_identity_map,
        )

        proposals: list[dict[str, Any]] = []
        seen = set()

        for index, left in enumerate(nodes):
            for right in nodes[index + 1:]:
                if not cls._same_type(left, right):
                    continue
                if not cls._year_compatible(left, right):
                    continue

                left_title = left["canonical_title"]
                right_title = right["canonical_title"]
                if not left_title or not right_title:
                    continue

                similarity = SequenceMatcher(
                    None, left_title, right_title
                ).ratio()

                exact = left_title == right_title
                containment = (
                    left_title in right_title
                    or right_title in left_title
                )

                if exact:
                    reason = "canonical_title_match"
                    score = 0.97
                elif containment and min(
                    len(left_title), len(right_title)
                ) >= 5:
                    reason = "title_containment"
                    score = max(0.78, similarity)
                elif similarity >= 0.88:
                    reason = "high_title_similarity"
                    score = similarity
                else:
                    continue

                key = tuple(sorted((left["id"], right["id"])))
                if key in seen:
                    continue
                seen.add(key)

                proposals.append({
                    "proposal_type": "merge_candidate",
                    "left_node_key": left["id"],
                    "right_node_key": right["id"],
                    "reason": reason,
                    "similarity": round(similarity, 4),
                    "confidence": round(score, 4),
                    "automatic_resolution": False,
                    "requires_confirmation": True,
                })

        alias_groups = defaultdict(set)
        for evidence in alias_evidence:
            group_key = tuple(sorted((
                evidence["source_node_key"],
                evidence["target_node_key"],
            )))
            alias_groups[group_key].add(evidence["edge_type"])

        alias_proposals = []
        for (left, right), relation_types in alias_groups.items():
            alias_proposals.append({
                "proposal_type": "identity_link_candidate",
                "left_node_key": left,
                "right_node_key": right,
                "relation_types": sorted(relation_types),
                "confidence": 0.9,
                "automatic_resolution": False,
                "requires_confirmation": True,
            })

        conflicts = []
        by_title = defaultdict(list)
        for node in nodes:
            by_title[node["canonical_title"]].append(node)

        for canonical_title, group in by_title.items():
            types = {
                cls._norm(node.get("node_type")).casefold()
                for node in group
                if cls._norm(node.get("node_type"))
            }
            if len(group) > 1 and len(types) > 1:
                conflicts.append({
                    "conflict_type": "same_name_different_entity_types",
                    "canonical_title": canonical_title,
                    "node_keys": [node["id"] for node in group],
                    "node_types": sorted(types),
                    "requires_confirmation": True,
                })

        confidence_values = [
            item["confidence"]
            for item in proposals + alias_proposals
        ]
        overall_confidence = (
            round(
                sum(confidence_values) / len(confidence_values),
                4,
            )
            if confidence_values
            else 0.0
        )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "source": {
                "id": (source or {}).get("id"),
                "url": (source or {}).get("url"),
                "name": (source or {}).get("name"),
            },
            "nodes": nodes,
            "merge_proposals": proposals,
            "identity_link_proposals": alias_proposals,
            "conflicts": conflicts,
            "summary": {
                "node_count": len(nodes),
                "merge_candidate_count": len(proposals),
                "identity_link_candidate_count": len(alias_proposals),
                "conflict_count": len(conflicts),
                "overall_confidence": overall_confidence,
            },
            "decision": {
                "status": (
                    "needs_review"
                    if proposals or alias_proposals or conflicts
                    else "no_resolution_candidates"
                ),
                "confidence": overall_confidence,
                "automatic_resolution": False,
            },
            "automatic_import": False,
            "requires_confirmation": True,
        }
