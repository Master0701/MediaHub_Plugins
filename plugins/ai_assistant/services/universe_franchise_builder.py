from __future__ import annotations
import re
import uuid
from typing import Any


class UniverseFranchiseBuilder:
    """Erzeugt Universums-, Franchise-, Team- und Ortsbeziehungen."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str, year=None) -> str:
        suffix = f":{year}" if year not in (None, "") else ""
        return (
            f"{kind}:"
            f"{' '.join(str(title or '').casefold().split())}"
            f"{suffix}"
        )

    @classmethod
    def _normalize_universe_name(cls, value: Any) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"^(?:es ist\s+)?(?:der\s+)?(?:\d+\.\s*)?"
            r"(?:und\s+)?letzte(?:r|n)?\s+film\s+des\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"^(?:teil des|gehört zum|das|der|die)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"[,.;:]+$", "", text).strip()
        return text

    def build(self, *, main_node, text, source):
        nodes, edges, evidence, warnings, index = [], [], [], [], {}

        def add_node(
            kind,
            title,
            confidence,
            reason,
            metadata=None,
            year=None,
        ):
            title = self._norm(title)
            if not title:
                return None
            key = self._key(kind, title, year)
            if key in index:
                index[key]["metadata"].update(dict(metadata or {}))
                return index[key]
            item = {
                "id": uuid.uuid4().hex,
                "key": key,
                "node_type": kind,
                "title": title,
                "year": year,
                "metadata": dict(metadata or {}),
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            }
            index[key] = item
            nodes.append(item)
            return item

        def add_edge(kind, src, dst, confidence, reason, sentence):
            if src is None or dst is None:
                return
            if any(
                item["edge_type"] == kind
                and item["source_node_key"] == src["key"]
                and item["target_node_key"] == dst["key"]
                for item in edges
            ):
                return
            evidence_id = uuid.uuid4().hex
            evidence.append({
                "id": evidence_id,
                "text": sentence,
                "edge_type": kind,
                "source_id": source.get("id"),
            })
            edges.append({
                "id": uuid.uuid4().hex,
                "edge_type": kind,
                "source_node_key": src["key"],
                "target_node_key": dst["key"],
                "confidence": round(float(confidence), 4),
                "reason": reason,
                "evidence_id": evidence_id,
                "source_id": source.get("id"),
                "status": "proposed",
                "requires_confirmation": True,
            })

        main = add_node(
            str(main_node.get("node_type") or "media"),
            str(main_node.get("title") or ""),
            float(main_node.get("confidence") or 0.8),
            "Hauptknoten aus bestehendem Graph-Vorschlag.",
            dict(main_node.get("metadata") or {}),
            year=main_node.get("year"),
        )

        relation_rules = (
            (
                "belongs_to",
                "universe",
                r"\b(?:Teil des|letzte Film des|gehört zum)\s+"
                r"((?:DC|Marvel|Star Trek|Star Wars|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*)"
                r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*){0,5}\s+Universe)\b",
                0.91,
            ),
            (
                "part_of",
                "franchise",
                r"\b(?:Teil der|gehört zur)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]+?(?:Reihe|Franchise))\b",
                0.88,
            ),
            (
                "member_of",
                "team",
                r"\b(?:Mitglied der|Mitglied von|gehört zur)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]+?(?:League|Team|Guardians|Avengers))\b",
                0.86,
            ),
            (
                "located_in",
                "location",
                r"\b(?:König von|Herrscher von|lebt in|stammt aus)\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{2,80})\b",
                0.78,
            ),
            (
                "enemy_of",
                "character",
                r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{2,80})\s+ist (?:der|die|das)?\s*(?:Erzfeind|Feind) von\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{2,80})\b",
                0.84,
            ),
            (
                "ally_of",
                "character",
                r"\b([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{2,80})\s+ist (?:ein|eine)?\s*(?:Verbündeter|Verbündete) von\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9 .'-]{2,80})\b",
                0.82,
            ),
        )

        for edge_type, target_type, pattern, confidence in relation_rules:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                if edge_type in {"enemy_of", "ally_of"}:
                    left = add_node(
                        "character",
                        self._normalize_universe_name(match.group(1)),
                        confidence,
                        f"Figur aus {edge_type}-Aussage.",
                    )
                    right = add_node(
                        "character",
                        self._norm(match.group(2)),
                        confidence,
                        f"Ziel aus {edge_type}-Aussage.",
                    )
                    add_edge(
                        edge_type,
                        left,
                        right,
                        confidence,
                        f"Explizite Aussage: {edge_type}.",
                        match.group(0),
                    )
                    continue

                if (
                    edge_type == "located_in"
                    and str(main.get("node_type") or "") in {
                        "movie", "series", "episode", "season"
                    }
                ):
                    continue

                target_title = (
                    self._normalize_universe_name(match.group(1))
                    if target_type == "universe"
                    else self._norm(match.group(1))
                )
                if edge_type == "located_in":
                    target_title = re.sub(
                        r"\s+(?:geworden|war|ist|wurde).*$",
                        "",
                        target_title,
                        flags=re.IGNORECASE,
                    ).strip()

                target = add_node(
                    target_type,
                    target_title,
                    confidence,
                    f"Ziel aus {edge_type}-Aussage.",
                )
                add_edge(
                    edge_type,
                    main,
                    target,
                    confidence,
                    f"Explizite Aussage: {edge_type}.",
                    match.group(0),
                )

        replacement_pattern = re.compile(
            r"\b((?:DC|Marvel|Star Trek|Star Wars|"
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*)"
            r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*){0,5}\s+Universe)"
            r"\s*,?\s*das\s+(19\d{2}|20\d{2})\s+durch\s+"
            r"((?:DC|Marvel|Star Trek|Star Wars|"
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*)"
            r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9'-]*){0,5}\s+Universe)"
            r"\s+ersetzt wurde",
            flags=re.IGNORECASE,
        )
        for match in replacement_pattern.finditer(text):
            old_universe = add_node(
                "universe",
                self._normalize_universe_name(match.group(1)),
                0.92,
                "Aus Universumswechsel erkannt.",
                {"transition_year": int(match.group(2))},
            )
            new_universe = add_node(
                "universe",
                self._normalize_universe_name(match.group(3)),
                0.92,
                "Nachfolgeuniversum aus Universumswechsel.",
                {"transition_year": int(match.group(2))},
            )
            add_edge(
                "replaced_by",
                old_universe,
                new_universe,
                0.92,
                "Expliziter Universumswechsel.",
                match.group(0),
            )

        if len(nodes) <= 1:
            warnings.append("Keine zusätzlichen Universe-/Franchise-Knoten erkannt.")

        return {
            "schema_version": 1,
            "strategy": "universe_franchise_builder_v330",
            "main_node_key": main["key"] if main else None,
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
