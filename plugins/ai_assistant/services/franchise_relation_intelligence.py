from __future__ import annotations

import re
from typing import Any


class FranchiseRelationIntelligence:
    """Erkennt Franchise-, Editions- und Kontinuitätsbeziehungen."""

    STRATEGY = "franchise_relation_intelligence_v442"

    RELATION_PATTERNS = (
        (
            "sequel_of",
            (
                r"\bfortsetzung\s+von\s+(?P<title>[^.;,\n]+)",
                r"\bsequel\s+to\s+(?P<title>[^.;,\n]+)",
            ),
            0.94,
        ),
        (
            "prequel_of",
            (
                r"\bprequel\s+zu\s+(?P<title>[^.;,\n]+)",
                r"\bvorgeschichte\s+zu\s+(?P<title>[^.;,\n]+)",
            ),
            0.92,
        ),
        (
            "midquel_of",
            (
                r"\bmidquel\s+zu\s+(?P<title>[^.;,\n]+)",
                r"\bzwischen\s+.+?\s+und\s+(?P<title>[^.;,\n]+)\s+angesiedelt",
            ),
            0.86,
        ),
        (
            "spin_off_of",
            (
                r"\bspin[- ]?off\s+(?:von|zu)\s+(?P<title>[^.;,\n]+)",
                r"\bableger\s+(?:von|zu)\s+(?P<title>[^.;,\n]+)",
            ),
            0.93,
        ),
        (
            "crossover_with",
            (
                r"\bcrossover\s+mit\s+(?P<title>[^.;,\n]+)",
                r"\btrifft\s+auf\s+(?P<title>[^.;,\n]+)",
            ),
            0.88,
        ),
        (
            "reboot_of",
            (
                r"\breboot\s+(?:von|zu)\s+(?P<title>[^.;,\n]+)",
                r"\bneustart\s+(?:von|der)\s+(?P<title>[^.;,\n]+)",
            ),
            0.91,
        ),
        (
            "soft_reboot_of",
            (
                r"\bsoft[- ]reboot\s+(?:von|zu)\s+(?P<title>[^.;,\n]+)",
                r"\bweicher\s+neustart\s+(?:von|der)\s+(?P<title>[^.;,\n]+)",
            ),
            0.89,
        ),
        (
            "remake_of",
            (
                r"\bremake\s+(?:von|zu)\s+(?P<title>[^.;,\n]+)",
                r"\bneuverfilmung\s+(?:von|des|der)\s+(?P<title>[^.;,\n]+)",
            ),
            0.92,
        ),
    )

    EDITION_PATTERNS = (
        ("directors_cut_of", r"\bdirector'?s\s+cut\b", 0.98),
        ("extended_cut_of", r"\bextended\s+cut\b", 0.98),
        ("uncut_version_of", r"\buncut\b", 0.96),
        ("remaster_of", r"\bremaster(?:ed)?\b", 0.94),
        ("theatrical_cut_of", r"\btheatrical\s+cut\b", 0.96),
    )

    CONTINUITY_PATTERNS = (
        ("canon_status", r"\bkanon(?:isch)?\b", "canon", 0.90),
        ("canon_status", r"\bnon[- ]?canon\b|\bnicht[- ]kanonisch\b", "non_canon", 0.92),
        ("timeline", r"\balternative\s+zeitlinie\b", "alternate_timeline", 0.90),
        ("timeline", r"\bparallel(?:e|en|er|es)?\s+(?:zeitlinie|universum)\b", "parallel_universe", 0.90),
        ("timeline", r"\bprime\s+timeline\b", "prime_timeline", 0.94),
        ("timeline", r"\bkelvin\s+timeline\b", "kelvin_timeline", 0.94),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _slug(cls, value: str) -> str:
        value = cls._norm(value).casefold()
        value = value.replace("_", " ")
        value = re.sub(r"[^\wäöüß]+", " ", value, flags=re.UNICODE)
        return "-".join(value.split())

    @classmethod
    def _node_key(
        cls,
        node_type: str,
        title: str,
        year: int | None = None,
    ) -> str:
        key = f"{node_type}:{cls._norm(title).casefold()}"
        return f"{key}:{year}" if year is not None else key

    @classmethod
    def _clean_related_title(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"\s+aus\s+dem\s+jahr\s+(?P<year>\d{4})$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\s+\((?:19|20)\d{2}\)$", "", text)
        return text.strip(" :–—-")

    @classmethod
    def _extract_year(cls, value: str) -> int | None:
        match = re.search(r"\b((?:19|20)\d{2})\b", value)
        return int(match.group(1)) if match else None

    @classmethod
    def _make_related_node(
        cls,
        *,
        title: str,
        year: int | None,
        node_type: str,
        source_id: Any,
        reason: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "key": cls._node_key(node_type, title, year),
            "node_type": node_type,
            "title": title,
            "year": year,
            "confidence": confidence,
            "metadata": {
                "franchise_relation_intelligence": cls.STRATEGY,
            },
            "reason": reason,
            "source_id": source_id,
            "automatic_import": False,
            "requires_confirmation": True,
        }

    @classmethod
    def _make_edge(
        cls,
        *,
        edge_type: str,
        source_key: str,
        target_key: str,
        confidence: float,
        evidence: str,
        source_id: Any,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "edge_type": edge_type,
            "source_node_key": source_key,
            "target_node_key": target_key,
            "confidence": confidence,
            "metadata": {
                "franchise_relation_intelligence": cls.STRATEGY,
                "evidence": evidence,
                **dict(metadata or {}),
            },
            "reason": f"Beziehung `{edge_type}` im Quelltext erkannt.",
            "source_id": source_id,
            "automatic_import": False,
            "requires_confirmation": True,
        }

    @classmethod
    def analyze(
        cls,
        *,
        main_node: dict[str, Any],
        text: str,
        source: dict[str, Any] | None = None,
        relationship_proposal: dict[str, Any] | None = None,
        franchise_collection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        main_node = dict(main_node or {})
        text = str(text or "")
        main_key = cls._norm(main_node.get("key"))
        main_title = cls._norm(main_node.get("title"))
        main_year = main_node.get("year")
        main_type = cls._norm(main_node.get("node_type") or "media")

        if not main_key:
            main_key = cls._node_key(main_type, main_title, main_year)

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        warnings: list[str] = []

        # Preserve already-known core franchise relations.
        for edge in dict(relationship_proposal or {}).get("edges") or []:
            if edge.get("edge_type") not in {
                "sequel_of",
                "prequel_of",
                "spin_off_of",
                "crossover_with",
            }:
                continue
            edges.append({
                **dict(edge),
                "automatic_import": False,
                "requires_confirmation": True,
            })

        for edge_type, patterns, confidence in cls.RELATION_PATTERNS:
            for pattern in patterns:
                for match in re.finditer(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                ):
                    raw_title = cls._norm(match.group("title"))
                    related_year = cls._extract_year(raw_title)
                    related_title = cls._clean_related_title(raw_title)
                    if not related_title:
                        continue
                    if related_title.casefold() == main_title.casefold():
                        continue

                    related_node = cls._make_related_node(
                        title=related_title,
                        year=related_year,
                        node_type=main_type,
                        source_id=source_id,
                        reason=(
                            f"Zielmedium aus erkannter "
                            f"`{edge_type}`-Aussage."
                        ),
                        confidence=confidence,
                    )
                    nodes.append(related_node)
                    evidence = cls._norm(match.group(0))
                    edges.append(
                        cls._make_edge(
                            edge_type=edge_type,
                            source_key=main_key,
                            target_key=related_node["key"],
                            confidence=confidence,
                            evidence=evidence,
                            source_id=source_id,
                        )
                    )
                    observations.append({
                        "kind": "franchise_relation",
                        "edge_type": edge_type,
                        "target_title": related_title,
                        "target_year": related_year,
                        "evidence": evidence,
                        "confidence": confidence,
                    })

        # Editions refer to the underlying base medium.
        edition_base_title = re.sub(
            r"\s*[:\-–—]\s*"
            r"(?:director'?s\s+cut|extended\s+cut|uncut|"
            r"remaster(?:ed)?|theatrical\s+cut)\s*$",
            "",
            main_title,
            flags=re.IGNORECASE,
        ).strip()

        for edge_type, pattern, confidence in cls.EDITION_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            title_match = re.search(pattern, main_title, flags=re.IGNORECASE)
            if not match and not title_match:
                continue
            if not edition_base_title or edition_base_title == main_title:
                edition_base_title = cls._norm(
                    dict(main_node.get("metadata") or {}).get("base_title")
                )
            if not edition_base_title:
                warnings.append(
                    f"Edition `{edge_type}` erkannt, aber Basistitel fehlt."
                )
                continue

            base_node = cls._make_related_node(
                title=edition_base_title,
                year=main_year,
                node_type=main_type,
                source_id=source_id,
                reason="Basismedium der erkannten Schnittfassung.",
                confidence=confidence,
            )
            nodes.append(base_node)
            evidence = cls._norm(
                (match or title_match).group(0)
            )
            edges.append(
                cls._make_edge(
                    edge_type=edge_type,
                    source_key=main_key,
                    target_key=base_node["key"],
                    confidence=confidence,
                    evidence=evidence,
                    source_id=source_id,
                    metadata={"edition": True},
                )
            )
            observations.append({
                "kind": "edition_relation",
                "edge_type": edge_type,
                "base_title": edition_base_title,
                "evidence": evidence,
                "confidence": confidence,
            })

        # Canon and timeline are represented as dedicated nodes.
        for edge_type, pattern, label, confidence in cls.CONTINUITY_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue

            node_type = "canon" if edge_type == "canon_status" else "timeline"
            title = label.replace("_", " ").title()
            continuity_node = {
                "key": f"{node_type}:{cls._slug(label)}",
                "node_type": node_type,
                "title": title,
                "confidence": confidence,
                "metadata": {
                    "value": label,
                    "franchise_relation_intelligence": cls.STRATEGY,
                },
                "reason": "Kontinuitätsstatus im Quelltext erkannt.",
                "source_id": source_id,
                "automatic_import": False,
                "requires_confirmation": True,
            }
            nodes.append(continuity_node)
            evidence = cls._norm(match.group(0))
            edges.append(
                cls._make_edge(
                    edge_type=(
                        "has_canon_status"
                        if edge_type == "canon_status"
                        else "belongs_to_timeline"
                    ),
                    source_key=main_key,
                    target_key=continuity_node["key"],
                    confidence=confidence,
                    evidence=evidence,
                    source_id=source_id,
                )
            )
            observations.append({
                "kind": "continuity",
                "value": label,
                "evidence": evidence,
                "confidence": confidence,
            })

        # Franchise collection can contribute the shared franchise key.
        franchise_key = dict(franchise_collection or {}).get(
            "franchise_key"
        )
        if franchise_key:
            edges.append(
                cls._make_edge(
                    edge_type="installment_of",
                    source_key=main_key,
                    target_key=str(franchise_key),
                    confidence=0.95,
                    evidence="franchise_collection",
                    source_id=source_id,
                    metadata={"inherited": True},
                )
            )

        node_map: dict[str, dict[str, Any]] = {}
        for node in nodes:
            key = cls._norm(node.get("key"))
            if key:
                node_map[key.casefold()] = node

        edge_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        for edge in edges:
            signature = (
                cls._norm(edge.get("edge_type")).casefold(),
                cls._norm(edge.get("source_node_key")).casefold(),
                cls._norm(edge.get("target_node_key")).casefold(),
            )
            if all(signature):
                edge_map[signature] = edge

        relation_counts: dict[str, int] = {}
        for edge in edge_map.values():
            edge_type = str(edge.get("edge_type") or "")
            relation_counts[edge_type] = (
                relation_counts.get(edge_type, 0) + 1
            )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "node_count": len(node_map),
            "edge_count": len(edge_map),
            "relation_counts": relation_counts,
            "nodes": list(node_map.values()),
            "edges": list(edge_map.values()),
            "observations": observations,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }

