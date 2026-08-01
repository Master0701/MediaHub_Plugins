from __future__ import annotations

import re
from collections import Counter
from typing import Any


class EventCharacterIdentityResolver:
    """Führt kurze Ereignisnamen mit vollständigen Figurennamen zusammen."""

    SUFFIXES = {
        "jr",
        "jr.",
        "sr",
        "sr.",
        "ii",
        "iii",
        "iv",
    }

    BLOCKED_SECOND_WORDS = {
        "kämpft",
        "kämpfte",
        "befreit",
        "befreite",
        "rettet",
        "rettete",
        "entführt",
        "entführte",
        "findet",
        "fand",
        "arbeitet",
        "arbeitete",
        "ist",
        "war",
        "hat",
        "wurde",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _canonical_candidates(cls, text: str) -> list[str]:
        source = cls._norm(text)
        if not source:
            return []

        candidates: list[str] = []

        def add(value: str) -> None:
            name = cls._norm(value).strip(" ,.;:/|-")
            words = name.split()

            if len(words) != 2:
                return

            # Beide Bestandteile müssen im Original wirklich mit einem
            # Großbuchstaben beginnen. So werden Kandidaten wie
            # "Orm aus", "David hat" oder "Arthur kämpft" verworfen,
            # auch wenn der umgebende Suchausdruck IGNORECASE verwendet.
            if not all(
                re.match(r"^[A-ZÄÖÜ]", word)
                for word in words
            ):
                return

            if words[-1].casefold() in cls.SUFFIXES:
                return
            if words[1].casefold() in cls.BLOCKED_SECOND_WORDS:
                return
            if any(
                token.casefold() in {
                    "lost",
                    "kingdom",
                    "extended",
                    "universe",
                    "comic",
                    "film",
                    "wikipedia",
                    "bearbeiten",
                    "quelltext",
                    "handlung",
                    "produktion",
                    "besetzung",
                    "chronologie",
                }
                for token in words
            ):
                return

            candidates.append(name)

        full_name = (
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'-]+"
            r"\s+"
            r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'-]+"
        )

        # Typische Rollen-/Aliasformen:
        # Arthur Curry / Aquaman
        # David Kane / Black Manta
        for match in re.finditer(
            rf"\b(?P<name>{full_name})\s*/\s*"
            rf"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'-]+"
            rf"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'-]+)?",
            source,
        ):
            add(match.group("name"))

        # Wikipedia-/Besetzungsformen:
        # Jason Momoa : Arthur Curry
        # Besetzung Arthur Curry, Orm Marius, David Kane
        for match in re.finditer(
            rf"(?:^|[:,;]\s+|\bBesetzung\s+)"
            rf"(?P<name>{full_name})"
            rf"(?=\s*(?:/|,|;|:|\bHandlung\b|\bProduktion\b|$))",
            source,
            flags=re.IGNORECASE,
        ):
            add(match.group("name"))

        # Explizite bekannte Vollnamen im Fließtext, aber nur wenn danach
        # ein Satzzeichen, ein Verb oder ein Abschnittsmarker folgt.
        boundary_words = (
            r"heiratete|bekam|sucht|arbeitet|findet|fand|greift|"
            r"erfährt|befreit|kämpft|entführt|ist|war|hat|wurde|"
            r"Handlung|Produktion"
        )
        for match in re.finditer(
            rf"\b(?P<name>{full_name})"
            rf"(?=\s+(?:{boundary_words})\b|[,.;:/]|$)",
            source,
            flags=re.IGNORECASE,
        ):
            add(match.group("name"))

        # Reihen aus genau zweiwortigen Namen ohne Satzzeichen werden nur
        # verwendet, wenn sie direkt vor einer echten Abschnittsüberschrift
        # stehen. Dann wird paarweise von links gelesen:
        # "Arthur Curry Orm Marius David Kane Handlung"
        for match in re.finditer(
            rf"(?P<block>(?:{full_name}\s+){{1,8}})"
            rf"(?=Handlung\b|Produktion\b)",
            source,
            flags=re.IGNORECASE,
        ):
            tokens = match.group("block").split()
            if len(tokens) % 2 != 0:
                continue
            for index in range(0, len(tokens), 2):
                add(" ".join(tokens[index:index + 2]))

        unique: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            folded = item.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            unique.append(item)

        return unique

    @classmethod
    def build_alias_map(cls, text: str) -> dict[str, str]:
        candidates = cls._canonical_candidates(text)
        counts = Counter(item.casefold() for item in candidates)
        original_by_folded = {
            item.casefold(): item
            for item in candidates
        }

        grouped: dict[str, list[str]] = {}
        for folded in counts:
            first = folded.split()[0]
            grouped.setdefault(first, []).append(folded)

        alias_map: dict[str, str] = {}

        for first, values in grouped.items():
            scored: list[tuple[float, str]] = []
            for folded in values:
                words = folded.split()
                if len(words) != 2:
                    continue

                score = float(counts[folded]) * 10.0

                if words[-1] in cls.SUFFIXES:
                    score -= 100.0

                score += 3.0
                scored.append((score, folded))

            if not scored:
                continue

            scored.sort(reverse=True)
            best_score, best = scored[0]

            if best_score <= 0:
                continue

            alias_map[first] = original_by_folded[best]

        return alias_map

    @classmethod
    def resolve_name(
        cls,
        name: str,
        alias_map: dict[str, str],
    ) -> str:
        value = cls._norm(name)
        words = value.split()

        # Vollständige Namen und Namen mit Suffix nie verändern.
        if len(words) != 1:
            return value
        if value.casefold() in cls.SUFFIXES:
            return value

        return alias_map.get(value.casefold(), value)

    @classmethod
    def resolve_result(
        cls,
        *,
        text: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        alias_map = cls.build_alias_map(text)
        nodes = list(result.get("nodes") or [])
        edges = list(result.get("edges") or [])

        key_replacements: dict[str, str] = {}
        merged_nodes: dict[str, dict[str, Any]] = {}

        for node in nodes:
            item = dict(node)
            if item.get("node_type") == "character":
                old_key = str(item.get("key") or "")
                old_title = str(item.get("title") or "")
                new_title = cls.resolve_name(old_title, alias_map)

                if new_title != old_title:
                    item["title"] = new_title
                    item["key"] = (
                        "character:"
                        + " ".join(new_title.casefold().split())
                    )
                    metadata = dict(item.get("metadata") or {})
                    metadata["identity_resolved_from"] = old_title
                    metadata["identity_resolver"] = (
                        "event_character_identity_resolver_v385"
                    )
                    item["metadata"] = metadata
                    item["reason"] = (
                        str(item.get("reason") or "")
                        + " Kurzname mit vollständigem Artikelnamen zusammengeführt."
                    ).strip()
                    key_replacements[old_key] = item["key"]

            key = str(item.get("key") or "")
            existing = merged_nodes.get(key)
            if existing is None:
                merged_nodes[key] = item
            else:
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0.0),
                    float(item.get("confidence") or 0.0),
                )
                metadata = dict(existing.get("metadata") or {})
                metadata.update(dict(item.get("metadata") or {}))
                existing["metadata"] = metadata

        resolved_edges: list[dict[str, Any]] = []
        seen_edges: set[tuple[str, str, str]] = set()

        for edge in edges:
            item = dict(edge)
            source_key = str(item.get("source_node_key") or "")
            target_key = str(item.get("target_node_key") or "")

            item["source_node_key"] = key_replacements.get(
                source_key,
                source_key,
            )
            item["target_node_key"] = key_replacements.get(
                target_key,
                target_key,
            )

            edge_key = (
                str(item.get("edge_type") or ""),
                item["source_node_key"],
                item["target_node_key"],
            )
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            resolved_edges.append(item)

        resolved = dict(result)
        resolved["nodes"] = list(merged_nodes.values())
        resolved["edges"] = resolved_edges
        resolved["identity_resolution"] = {
            "strategy": "event_character_identity_resolver_v385",
            "alias_map": alias_map,
            "resolved_key_count": len(key_replacements),
            "automatic_import": False,
            "requires_confirmation": True,
        }
        return resolved
