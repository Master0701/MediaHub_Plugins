from __future__ import annotations

import re
from typing import Any


class FranchiseConnectionIntelligence:
    """Erkennt Spin-offs, Crossover, Backdoor-Piloten und gemeinsame Universen."""

    STRATEGY = "franchise_connection_intelligence_v460"

    RULES = (
        ("spin_off_of", (
            r"\bspin[- ]?off\s+von\s+(?P<title>[^.;,\n]+)",
            r"\bdirektes\s+spin[- ]?off\s+der\s+serie\s+(?P<title>[^.;,\n]+)",
            r"\bableger\s+von\s+(?P<title>[^.;,\n]+)",
        ), 0.96),
        ("crossover_with", (
            r"\bcrossover\s+mit\s+(?P<title>[^.;,\n]+)",
            r"\bcrossover[- ]folge\s+mit\s+(?P<title>[^.;,\n]+)",
        ), 0.94),
        ("backdoor_pilot_for", (
            r"\bbackdoor[- ]pilot\s+für\s+(?P<title>[^.;,\n]+)",
            r"\bdiente\s+als\s+backdoor[- ]pilot\s+für\s+(?P<title>[^.;,\n]+)",
        ), 0.97),
        ("shares_universe_with", (
            r"\bspielt\s+im\s+selben\s+universum\s+wie\s+(?P<title>[^.;,\n]+)",
            r"\bteil(?:\s+des)?\s+gleichen\s+universums\s+wie\s+(?P<title>[^.;,\n]+)",
            r"\bshares\s+(?:the\s+)?same\s+universe\s+with\s+(?P<title>[^.;,\n]+)",
        ), 0.93),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _node_key(cls, node_type: str, title: str) -> str:
        return f"{node_type}:{cls._norm(title).casefold()}"

    @classmethod
    def _clean_title(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(r"\s+(?:und|sowie)\s+(?:ist|war|wurde|spielt)\b.*$", "", text, flags=re.I)
        text = re.sub(r"\s+aus\s+dem\s+jahr\s+(?:19|20)\d{2}$", "", text, flags=re.I)
        return text.strip(" :–—-()[]{}")

    @classmethod
    def analyze(cls, *, main_node: dict[str, Any], text: str,
                source: dict[str, Any] | None = None,
                franchise_relations: dict[str, Any] | None = None,
                timeline_order_intelligence: dict[str, Any] | None = None) -> dict[str, Any]:
        source = dict(source or {})
        main_node = dict(main_node or {})
        main_type = cls._norm(main_node.get("node_type") or "media")
        main_title = cls._norm(main_node.get("title"))
        main_key = cls._norm(main_node.get("key")) or cls._node_key(main_type, main_title)
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str, str]] = set()

        for relation_type, patterns, confidence in cls.RULES:
            for pattern in patterns:
                for match in re.finditer(pattern, str(text or ""), flags=re.I):
                    title = cls._clean_title(match.group("title"))
                    if not title or title.casefold() == main_title.casefold():
                        continue
                    target_key = cls._node_key(main_type, title)
                    if target_key not in seen_nodes:
                        nodes.append({
                            "key": target_key, "node_type": main_type, "title": title,
                            "confidence": confidence,
                            "metadata": {"franchise_connection_intelligence": cls.STRATEGY},
                            "reason": f"Zielmedium aus erkannter `{relation_type}`-Aussage.",
                            "source_id": source.get("id"),
                            "automatic_import": False, "requires_confirmation": True,
                        })
                        seen_nodes.add(target_key)
                    edge_key = (relation_type, main_key, target_key)
                    if edge_key not in seen_edges:
                        evidence = cls._norm(match.group(0))
                        edges.append({
                            "edge_type": relation_type,
                            "source_node_key": main_key, "target_node_key": target_key,
                            "confidence": confidence,
                            "metadata": {"franchise_connection_intelligence": cls.STRATEGY, "evidence": evidence},
                            "reason": f"Franchise-Verbindung `{relation_type}` im Quelltext erkannt.",
                            "source_id": source.get("id"),
                            "automatic_import": False, "requires_confirmation": True,
                        })
                        observations.append({"relation_type": relation_type, "title": title,
                                             "confidence": confidence, "evidence": evidence})
                        seen_edges.add(edge_key)

        return {
            "strategy": cls.STRATEGY, "nodes": nodes, "edges": edges,
            "observations": observations,
            "summary": {"node_count": len(nodes), "edge_count": len(edges),
                        "relation_types": sorted({e[0] for e in seen_edges})},
            "automatic_import": False, "requires_confirmation": True,
        }
