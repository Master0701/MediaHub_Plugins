from __future__ import annotations

import re
from typing import Any


class UniverseIntelligence:
    """Erkennt Universen, Kontinuitäten, Timelines und Kanonstatus aus expliziten Aussagen."""

    STRATEGY = "universe_intelligence_v470"

    MEMBERSHIP_RULES = (
        ("belongs_to_universe", "universe", (
            r"\b(?:teil|bestandteil)\s+des\s+(?P<title>[^.;,\n]+?)\s+universums\b",
            r"\bgehört\s+zum\s+(?P<title>[^.;,\n]+?)\s+universum\b",
            r"\bfilm\s+des\s+(?P<title>[^.;,\n]+?)\s+universums\b",
            r"\b(?:ist|war)\s+(?:der\s+\d+\.?\s+)?(?:und\s+letzte\s+)?film\s+des\s+(?P<title>[^.;,\n]+?)(?:,|\s+das\b|\s+welches\b|\.|$)",
            r"\bpart\s+of\s+the\s+(?P<title>[^.;,\n]+?)\s+universe\b",
        ), 0.95),
        ("belongs_to_timeline", "timeline", (
            r"\bgehört\s+zur\s+(?P<title>[^.;,\n]+?)\s+timeline\b",
            r"\bspielt\s+in\s+der\s+(?P<title>[^.;,\n]+?)\s+timeline\b",
            r"\bpart\s+of\s+the\s+(?P<title>[^.;,\n]+?)\s+timeline\b",
        ), 0.94),
        ("belongs_to_continuity", "continuity", (
            r"\bgehört\s+zur\s+(?P<title>[^.;,\n]+?)\s+kontinuität\b",
            r"\bspielt\s+in\s+der\s+(?P<title>[^.;,\n]+?)\s+kontinuität\b",
            r"\bpart\s+of\s+the\s+(?P<title>[^.;,\n]+?)\s+continuity\b",
        ), 0.94),
    )

    STATUS_RULES = (
        ("part_of_canon", "canon", (
            r"\b(?:ist|gilt\s+als)\s+kanon(?:isch)?\b",
            r"\bgehört\s+zum\s+kanon\b",
            r"\bis\s+canon\b",
        ), 0.92),
        ("non_canon", "non_canon", (
            r"\b(?:ist|gilt\s+als)\s+nicht\s+kanon(?:isch)?\b",
            r"\bgehört\s+nicht\s+zum\s+kanon\b",
            r"\bnon[- ]canon(?:ical)?\b",
        ), 0.96),
        ("legends", "legends", (
            r"\bgehört\s+(?:zu|zum)\s+legends\b",
            r"\b(?:ist|wurde)\s+als\s+legends\s+eingestuft\b",
        ), 0.95),
        ("expanded_universe", "expanded_universe", (
            r"\bgehört\s+zum\s+(?:erweiterten\s+universum|expanded\s+universe)\b",
            r"\bpart\s+of\s+the\s+expanded\s+universe\b",
        ), 0.93),
    )

    RELATION_RULES = (
        ("reboot_of", (
            r"\breboot\s+von\s+(?P<title>[^.;,\n]+)",
            r"\bneuauflage\s+von\s+(?P<title>[^.;,\n]+)",
            r"\breboot\s+of\s+(?P<title>[^.;,\n]+)",
        ), 0.96),
        ("soft_reboot_of", (
            r"\bsoft[- ]reboot\s+von\s+(?P<title>[^.;,\n]+)",
            r"\bsanfter\s+reboot\s+von\s+(?P<title>[^.;,\n]+)",
            r"\bsoft[- ]reboot\s+of\s+(?P<title>[^.;,\n]+)",
        ), 0.96),
        ("alternate_version_of", (
            r"\balternative\s+version\s+von\s+(?P<title>[^.;,\n]+)",
            r"\bparallelwelt[- ]version\s+von\s+(?P<title>[^.;,\n]+)",
            r"\balternate\s+version\s+of\s+(?P<title>[^.;,\n]+)",
        ), 0.93),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _clean_title(cls, value: Any) -> str:
        text = cls._norm(value)
        text = re.sub(r"\s+(?:aus\s+dem\s+jahr\s+)?(?:19|20)\d{2}$", "", text, flags=re.I)
        text = re.sub(r"\s+(?:ersetzt|fortgeführt|beendet)\s+wurde$", "", text, flags=re.I)
        return text.strip(" :–—-()[]{}.,")

    @classmethod
    def _key(cls, node_type: str, title: str) -> str:
        return f"{node_type}:{cls._norm(title).casefold()}"

    @classmethod
    def analyze(cls, *, main_node: dict[str, Any], text: str,
                source: dict[str, Any] | None = None,
                universe_proposal: dict[str, Any] | None = None,
                franchise_connections: dict[str, Any] | None = None) -> dict[str, Any]:
        source = dict(source or {})
        main_node = dict(main_node or {})
        main_type = cls._norm(main_node.get("node_type") or "media")
        main_title = cls._norm(main_node.get("title"))
        main_key = cls._norm(main_node.get("key")) or cls._key(main_type, main_title)
        source_id = source.get("id")
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()
        seen_edges: set[tuple[str, str, str]] = set()

        def add_node(node_type: str, title: str, confidence: float, reason: str) -> str:
            key = cls._key(node_type, title)
            if key not in seen_nodes:
                nodes.append({
                    "key": key, "node_type": node_type, "title": title,
                    "confidence": confidence,
                    "metadata": {"universe_intelligence": cls.STRATEGY},
                    "reason": reason, "source_id": source_id,
                    "automatic_import": False, "requires_confirmation": True,
                })
                seen_nodes.add(key)
            return key

        def add_edge(edge_type: str, target_key: str, confidence: float, evidence: str) -> None:
            edge_key = (edge_type, main_key, target_key)
            if edge_key in seen_edges:
                return
            edges.append({
                "edge_type": edge_type,
                "source_node_key": main_key,
                "target_node_key": target_key,
                "confidence": confidence,
                "metadata": {"universe_intelligence": cls.STRATEGY, "evidence": cls._norm(evidence)},
                "reason": f"Explizite Universumsbeziehung `{edge_type}` erkannt.",
                "source_id": source_id,
                "automatic_import": False, "requires_confirmation": True,
            })
            observations.append({"relation_type": edge_type, "target_node_key": target_key,
                                 "confidence": confidence, "evidence": cls._norm(evidence)})
            seen_edges.add(edge_key)

        raw_text = str(text or "")
        for edge_type, node_type, patterns, confidence in cls.MEMBERSHIP_RULES:
            for pattern in patterns:
                for match in re.finditer(pattern, raw_text, flags=re.I):
                    title = cls._clean_title(match.group("title"))
                    if title:
                        target = add_node(node_type, title, confidence, f"{node_type.title()} aus expliziter Aussage erkannt.")
                        add_edge(edge_type, target, confidence, match.group(0))

        for edge_type, status_title, patterns, confidence in cls.STATUS_RULES:
            for pattern in patterns:
                match = re.search(pattern, raw_text, flags=re.I)
                if match:
                    target = add_node("canon_status", status_title, confidence, "Kanonstatus aus expliziter Aussage erkannt.")
                    add_edge(edge_type, target, confidence, match.group(0))
                    break

        for edge_type, patterns, confidence in cls.RELATION_RULES:
            for pattern in patterns:
                for match in re.finditer(pattern, raw_text, flags=re.I):
                    title = cls._clean_title(match.group("title"))
                    if not title or title.casefold() == main_title.casefold():
                        continue
                    target = add_node(main_type, title, confidence, f"Bezugsmedium für `{edge_type}` erkannt.")
                    add_edge(edge_type, target, confidence, match.group(0))

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
