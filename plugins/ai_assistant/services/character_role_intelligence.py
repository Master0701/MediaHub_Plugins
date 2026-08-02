from __future__ import annotations

import re
from typing import Any


class CharacterRoleIntelligence:
    """Erkennt Figuren, Darsteller, Rollen und Auftritte aus expliziten Besetzungsangaben."""

    STRATEGY = "character_role_intelligence_v480"

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _key(cls, node_type: str, title: str) -> str:
        return f"{node_type}:{cls._norm(title).casefold()}"

    @classmethod
    def _clean(cls, value: Any) -> str:
        text = cls._norm(value)
        text = re.sub(r"\s*\([^)]*(?:stimme|voice|uncredited|archiv)[^)]*\)\s*$", "", text, flags=re.I)
        return text.strip(" :–—-()[]{}.,;\"")

    @classmethod
    def analyze(cls, *, main_node: dict[str, Any], text: str,
                source: dict[str, Any] | None = None,
                cast_resolution: dict[str, Any] | None = None) -> dict[str, Any]:
        main_node = dict(main_node or {})
        source = dict(source or {})
        main_type = cls._norm(main_node.get("node_type") or "media")
        main_title = cls._norm(main_node.get("title"))
        main_key = cls._norm(main_node.get("key")) or cls._key(main_type, main_title)
        source_id = source.get("id")
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str, str]] = set()

        def add_node(node_type: str, title: str, confidence: float, reason: str,
                     metadata: dict[str, Any] | None = None) -> str:
            title = cls._clean(title)
            key = cls._key(node_type, title)
            if title and key not in seen_nodes:
                nodes.append({
                    "key": key, "node_type": node_type, "title": title,
                    "confidence": confidence,
                    "metadata": {"character_role_intelligence": cls.STRATEGY, **dict(metadata or {})},
                    "reason": reason, "source_id": source_id,
                    "automatic_import": False, "requires_confirmation": True,
                })
                seen_nodes.add(key)
            return key

        def add_edge(edge_type: str, source_key: str, target_key: str,
                     confidence: float, evidence: str) -> None:
            key = (edge_type, source_key, target_key)
            if not source_key or not target_key or key in seen_edges:
                return
            edges.append({
                "edge_type": edge_type,
                "source_node_key": source_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "metadata": {"character_role_intelligence": cls.STRATEGY, "evidence": cls._norm(evidence)},
                "reason": f"Explizite Rollenbeziehung `{edge_type}` erkannt.",
                "source_id": source_id,
                "automatic_import": False, "requires_confirmation": True,
            })
            observations.append({"relation_type": edge_type, "source_node_key": source_key,
                                 "target_node_key": target_key, "confidence": confidence,
                                 "evidence": cls._norm(evidence)})
            seen_edges.add(key)

        patterns = (
            re.compile(r"(?m)^\s*[*-]?\s*(?P<actor>[A-ZÄÖÜ][^:\n]{2,70}?)\s*:\s*(?P<role>[^\n]{2,90})\s*$"),
            re.compile(r"\b(?P<actor>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,70}?)\s+(?:spielt|verkörpert)\s+(?:die\s+Rolle\s+von\s+)?(?P<role>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 /.'-]{2,80})"),
            re.compile(r"\b(?P<role>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 /.'-]{2,80}?)\s+wird\s+von\s+(?P<actor>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß .'-]{2,70})\s+(?:gespielt|verkörpert)"),
            re.compile(r"\b(?P<actor>[A-Z][A-Za-z .'-]{2,70}?)\s+as\s+(?P<role>[A-Z][A-Za-z0-9 /.'-]{2,80})"),
        )

        raw = str(text or "")
        for pattern in patterns:
            for match in pattern.finditer(raw):
                actor = cls._clean(match.group("actor"))
                role_text = cls._clean(match.group("role"))
                if not actor or not role_text or len(actor.split()) > 7:
                    continue
                roles = [cls._clean(part) for part in re.split(r"\s*/\s*|\s+alias\s+", role_text, flags=re.I)]
                roles = [item for item in roles if item and len(item.split()) <= 8]
                if not roles:
                    continue
                actor_key = add_node("person", actor, 0.94, "Darsteller aus expliziter Besetzungsangabe erkannt.")
                for index, role in enumerate(roles):
                    character_key = add_node("character", role, 0.93 if index == 0 else 0.88,
                                             "Figur oder Rollenalias aus Besetzungsangabe erkannt.",
                                             {"alias_index": index})
                    add_edge("portrays", actor_key, character_key, 0.94, match.group(0))
                    add_edge("appears_in", character_key, main_key, 0.92, match.group(0))
                    if index > 0:
                        primary_key = cls._key("character", roles[0])
                        add_edge("alias_of", character_key, primary_key, 0.88, match.group(0))

        return {
            "strategy": cls.STRATEGY,
            "nodes": nodes,
            "edges": edges,
            "observations": observations,
            "summary": {"node_count": len(nodes), "edge_count": len(edges),
                        "relation_types": sorted({item[0] for item in seen_edges})},
            "automatic_import": False,
            "requires_confirmation": True,
        }
