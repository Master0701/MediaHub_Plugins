from __future__ import annotations

import re
from typing import Any


class TimelineOrderIntelligence:
    """Erkennt explizite Medienreihenfolgen und zeitliche Beziehungen."""

    STRATEGY = "timeline_order_intelligence_v452"

    RELATION_RULES = (
        (
            "precedes_chronologically",
            (
                r"\bchronologisch\s+vor\s+(?P<title>[^.;,\n]+)",
                r"\bspielt\s+vor\s+(?P<title>[^.;,\n]+)",
            ),
            0.91,
        ),
        (
            "follows_chronologically",
            (
                r"\bchronologisch\s+nach\s+(?P<title>[^.;,\n]+)",
                r"\bspielt\s+nach\s+(?P<title>[^.;,\n]+)",
            ),
            0.91,
        ),
        (
            "precedes_in_release",
            (
                r"\berschien\s+vor\s+(?P<title>[^.;,\n]+)",
                r"\bwurde\s+vor\s+(?P<title>[^.;,\n]+)\s+veröffentlicht",
            ),
            0.90,
        ),
        (
            "follows_in_release",
            (
                r"\berschien\s+nach\s+(?P<title>[^.;,\n]+)",
                r"\bwurde\s+nach\s+(?P<title>[^.;,\n]+)\s+veröffentlicht",
            ),
            0.90,
        ),
    )

    ORDER_HEADINGS = (
        (
            "chronological",
            (
                "chronologische reihenfolge",
                "chronologie",
                "in-universe-reihenfolge",
            ),
            0.95,
        ),
        (
            "release",
            (
                "veröffentlichungsreihenfolge",
                "erscheinungsreihenfolge",
                "release-reihenfolge",
                "produktionsreihenfolge",
            ),
            0.94,
        ),
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _slug(cls, value: Any) -> str:
        text = cls._norm(value).casefold().replace("_", " ")
        text = re.sub(
            r"[^\wäöüß]+",
            " ",
            text,
            flags=re.UNICODE,
        )
        return "-".join(text.split())

    @classmethod
    def _clean_title(cls, value: Any) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"\s+(?:aus\s+dem\s+jahr\s+)?(?:19|20)\d{2}$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\s+\((?:19|20)\d{2}\)$",
            "",
            text,
        )
        text = re.sub(
            r"\s+(?:angesiedelt|veröffentlicht|erschienen)$",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip(" :–—-,.")

    @classmethod
    def _extract_year(cls, value: Any) -> int | None:
        match = re.search(
            r"\b((?:19|20)\d{2})\b",
            str(value or ""),
        )
        return int(match.group(1)) if match else None

    @classmethod
    def _media_key(
        cls,
        node_type: str,
        title: str,
        year: int | None = None,
    ) -> str:
        key = f"{node_type}:{cls._norm(title).casefold()}"
        if year is not None:
            key += f":{year}"
        return key

    @classmethod
    def _make_media_node(
        cls,
        *,
        node_type: str,
        title: str,
        year: int | None,
        confidence: float,
        source_id: Any,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "key": cls._media_key(
                node_type,
                title,
                year,
            ),
            "node_type": node_type,
            "title": title,
            "year": year,
            "confidence": confidence,
            "metadata": {
                "timeline_order_intelligence": cls.STRATEGY,
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
        source_id: Any,
        evidence: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "edge_type": edge_type,
            "source_node_key": source_key,
            "target_node_key": target_key,
            "confidence": confidence,
            "metadata": {
                "timeline_order_intelligence": cls.STRATEGY,
                "evidence": cls._norm(evidence),
                **dict(metadata or {}),
            },
            "reason": (
                f"Explizite Reihenfolgebeziehung `{edge_type}` erkannt."
            ),
            "source_id": source_id,
            "automatic_import": False,
            "requires_confirmation": True,
        }

    @classmethod
    def _split_order_items(cls, value: str) -> list[str]:
        text = cls._norm(value)
        text = re.sub(
            r"\s*(?:→|->|>|»)\s*",
            " | ",
            text,
        )
        text = re.sub(
            r"\s*;\s*",
            " | ",
            text,
        )

        if " | " not in text:
            text = re.sub(
                r"\s*,\s*",
                " | ",
                text,
            )

        items = []
        for raw in text.split(" | "):
            title = cls._clean_title(raw)
            title = re.sub(
                r"^\d+\.\s*",
                "",
                title,
            ).strip()
            if title:
                items.append(title)

        result = []
        seen = set()
        for item in items:
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @classmethod
    def _extract_order_blocks(
        cls,
        text: str,
    ) -> list[dict[str, Any]]:
        results = []
        for order_type, headings, confidence in cls.ORDER_HEADINGS:
            heading_pattern = "|".join(
                re.escape(item)
                for item in headings
            )
            pattern = re.compile(
                rf"\b(?:{heading_pattern})\s*:\s*"
                rf"(?P<items>[^\n]+)",
                flags=re.IGNORECASE,
            )
            for match in pattern.finditer(text):
                raw_items = match.group("items")
                raw_items = re.split(
                    r"\s{2,}|[.!?]\s+(?=[A-ZÄÖÜ])",
                    raw_items,
                    maxsplit=1,
                )[0]
                items = cls._split_order_items(raw_items)
                if len(items) < 2:
                    continue
                results.append({
                    "order_type": order_type,
                    "items": items,
                    "confidence": confidence,
                    "evidence": cls._norm(match.group(0)),
                })
        return results

    @classmethod
    def analyze(
        cls,
        *,
        main_node: dict[str, Any],
        text: str,
        source: dict[str, Any] | None = None,
        franchise_collection: dict[str, Any] | None = None,
        franchise_relations: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        main_node = dict(main_node or {})
        text = str(text or "")

        main_type = cls._norm(
            main_node.get("node_type") or "media"
        )
        main_title = cls._norm(
            main_node.get("title")
        )
        main_year = main_node.get("year")
        main_key = cls._norm(
            main_node.get("key")
        )
        if not main_key:
            main_key = cls._media_key(
                main_type,
                main_title,
                main_year,
            )

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        orders: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        warnings: list[str] = []

        for edge_type, patterns, confidence in cls.RELATION_RULES:
            for pattern in patterns:
                for match in re.finditer(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                ):
                    raw_title = cls._norm(
                        match.group("title")
                    )
                    year = cls._extract_year(raw_title)
                    title = cls._clean_title(raw_title)
                    if not title:
                        continue
                    if title.casefold() == main_title.casefold():
                        continue

                    target = cls._make_media_node(
                        node_type=main_type,
                        title=title,
                        year=year,
                        confidence=confidence,
                        source_id=source_id,
                        reason=(
                            "Zielmedium aus expliziter "
                            "Reihenfolgebeziehung."
                        ),
                    )
                    nodes.append(target)
                    evidence = cls._norm(match.group(0))
                    edges.append(
                        cls._make_edge(
                            edge_type=edge_type,
                            source_key=main_key,
                            target_key=target["key"],
                            confidence=confidence,
                            source_id=source_id,
                            evidence=evidence,
                        )
                    )
                    observations.append({
                        "kind": "direct_order_relation",
                        "edge_type": edge_type,
                        "target_title": title,
                        "target_year": year,
                        "confidence": confidence,
                        "evidence": evidence,
                    })

        wikipedia_chronology_patterns = (
            (
                "predecessor_of",
                r"\bchronologie\s*(?:←|<-)\s*"
                r"(?P<title>[^.;,\n]+)",
            ),
            (
                "successor_of",
                r"\bchronologie\s*(?:→|->)\s*"
                r"(?P<title>[^.;,\n]+)",
            ),
        )

        for edge_type, pattern in wikipedia_chronology_patterns:
            for match in re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                raw_title = cls._norm(
                    match.group("title")
                )
                if main_title:
                    main_title_match = re.search(
                        rf"\s+{re.escape(main_title)}"
                        rf"\s+(?:ist|war)\b",
                        raw_title,
                        flags=re.IGNORECASE,
                    )
                    if main_title_match:
                        raw_title = raw_title[
                            :main_title_match.start()
                        ]
                year = cls._extract_year(raw_title)
                title = cls._clean_title(raw_title)
                if not title:
                    continue
                if title.casefold() == main_title.casefold():
                    continue

                target = cls._make_media_node(
                    node_type=main_type,
                    title=title,
                    year=year,
                    confidence=0.96,
                    source_id=source_id,
                    reason=(
                        "Medium aus Wikipedia-Chronologiepfeil."
                    ),
                )
                nodes.append(target)

                if edge_type == "predecessor_of":
                    source_key = target["key"]
                    target_key = main_key
                else:
                    source_key = main_key
                    target_key = target["key"]

                edges.append(
                    cls._make_edge(
                        edge_type=edge_type,
                        source_key=source_key,
                        target_key=target_key,
                        confidence=0.96,
                        source_id=source_id,
                        evidence=match.group(0),
                        metadata={
                            "source_format":
                            "wikipedia_chronology_arrow",
                        },
                    )
                )
                observations.append({
                    "kind": "wikipedia_chronology",
                    "edge_type": edge_type,
                    "target_title": title,
                    "target_year": year,
                    "confidence": 0.96,
                    "evidence": cls._norm(
                        match.group(0)
                    ),
                })

        predecessor_patterns = (
            (
                "predecessor_of",
                r"\b(?:der\s+)?vorgänger\s+(?:ist|war)\s+"
                r"(?P<title>[^.;,\n]+)",
                True,
            ),
            (
                "successor_of",
                r"\b(?:der\s+)?nachfolger\s+(?:ist|war)\s+"
                r"(?P<title>[^.;,\n]+)",
                False,
            ),
        )

        for edge_type, pattern, reverse in predecessor_patterns:
            for match in re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                raw_title = cls._norm(
                    match.group("title")
                )
                year = cls._extract_year(raw_title)
                title = cls._clean_title(raw_title)
                if not title:
                    continue

                target = cls._make_media_node(
                    node_type=main_type,
                    title=title,
                    year=year,
                    confidence=0.94,
                    source_id=source_id,
                    reason=(
                        "Medium aus expliziter Vorgänger- "
                        "oder Nachfolgerangabe."
                    ),
                )
                nodes.append(target)

                source_key = (
                    target["key"]
                    if reverse
                    else main_key
                )
                target_key = (
                    main_key
                    if reverse
                    else target["key"]
                )

                edges.append(
                    cls._make_edge(
                        edge_type=edge_type,
                        source_key=source_key,
                        target_key=target_key,
                        confidence=0.94,
                        source_id=source_id,
                        evidence=match.group(0),
                    )
                )

        installment_match = re.search(
            r"\b(?:der|die|das)\s+"
            r"(?P<number>\d+)\.\s+"
            r"(?:und\s+(?:letzte|letzter|letztes)\s+)?"
            r"(?:film|teil|band|staffel)\s+"
            r"(?:der|des)\s+"
            r"(?P<group>[^.;,\n]+)",
            text,
            flags=re.IGNORECASE,
        )
        installment_number = None
        if installment_match:
            installment_number = int(
                installment_match.group("number")
            )
            observations.append({
                "kind": "installment_position",
                "position": installment_number,
                "group": cls._clean_title(
                    installment_match.group("group")
                ),
                "confidence": 0.90,
                "evidence": cls._norm(
                    installment_match.group(0)
                ),
            })

        franchise_name = cls._norm(
            dict(franchise_collection or {}).get(
                "franchise_name"
            )
            or dict(franchise_collection or {}).get(
                "franchise"
            )
        )

        for block in cls._extract_order_blocks(text):
            order_type = block["order_type"]
            order_items = block["items"]
            confidence = float(block["confidence"])
            order_name = (
                franchise_name
                or main_title
                or "Medienreihe"
            )
            order_key = (
                f"order:{cls._slug(order_name)}:"
                f"{order_type}"
            )
            order_node = {
                "key": order_key,
                "node_type": "order",
                "title": (
                    f"{order_name} – "
                    f"{'Chronologische Reihenfolge' if order_type == 'chronological' else 'Veröffentlichungsreihenfolge'}"
                ),
                "confidence": confidence,
                "metadata": {
                    "order_type": order_type,
                    "timeline_order_intelligence": cls.STRATEGY,
                },
                "reason": (
                    "Explizite Reihenfolgeliste im Quelltext erkannt."
                ),
                "source_id": source_id,
                "automatic_import": False,
                "requires_confirmation": True,
            }
            nodes.append(order_node)

            order_entry = {
                "key": order_key,
                "order_type": order_type,
                "name": order_node["title"],
                "items": [],
                "confidence": confidence,
                "evidence": block["evidence"],
                "automatic_import": False,
                "requires_confirmation": True,
            }

            for position, title in enumerate(
                order_items,
                start=1,
            ):
                media_node = cls._make_media_node(
                    node_type=main_type,
                    title=title,
                    year=None,
                    confidence=confidence,
                    source_id=source_id,
                    reason=(
                        "Medium aus expliziter Reihenfolgeliste."
                    ),
                )
                nodes.append(media_node)
                edges.append(
                    cls._make_edge(
                        edge_type="has_order_item",
                        source_key=order_key,
                        target_key=media_node["key"],
                        confidence=confidence,
                        source_id=source_id,
                        evidence=block["evidence"],
                        metadata={
                            "order_type": order_type,
                            "position": position,
                        },
                    )
                )
                order_entry["items"].append({
                    "position": position,
                    "title": title,
                    "node_key": media_node["key"],
                })

            orders.append(order_entry)

        node_map: dict[str, dict[str, Any]] = {}
        for node in nodes:
            key = cls._norm(node.get("key"))
            if not key:
                continue
            existing = node_map.get(key.casefold())
            if existing is None:
                node_map[key.casefold()] = node
            else:
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(node.get("confidence") or 0.0),
                )
                existing.setdefault(
                    "metadata",
                    {},
                ).update(
                    dict(node.get("metadata") or {})
                )

        edge_map: dict[
            tuple[str, str, str, int | None],
            dict[str, Any],
        ] = {}
        for edge in edges:
            metadata = dict(edge.get("metadata") or {})
            signature = (
                cls._norm(
                    edge.get("edge_type")
                ).casefold(),
                cls._norm(
                    edge.get("source_node_key")
                ).casefold(),
                cls._norm(
                    edge.get("target_node_key")
                ).casefold(),
                metadata.get("position"),
            )
            if all(signature[:3]):
                edge_map[signature] = edge

        relation_counts: dict[str, int] = {}
        for edge in edge_map.values():
            edge_type = str(
                edge.get("edge_type") or ""
            )
            relation_counts[edge_type] = (
                relation_counts.get(edge_type, 0)
                + 1
            )

        if not node_map and not edge_map:
            warnings.append(
                "Keine expliziten Reihenfolgeinformationen erkannt."
            )

        return {
            "schema_version": 1,
            "strategy": cls.STRATEGY,
            "main_node_key": main_key,
            "installment_number": installment_number,
            "node_count": len(node_map),
            "edge_count": len(edge_map),
            "order_count": len(orders),
            "relation_counts": relation_counts,
            "nodes": list(node_map.values()),
            "edges": list(edge_map.values()),
            "orders": orders,
            "observations": observations,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
