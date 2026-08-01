from __future__ import annotations

import re
import uuid
from typing import Any


class CharacterCastResolver:
    """Strukturierte Besetzungs-, Figuren- und Aliasauflösung."""

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _key(kind: str, title: str, year=None) -> str:
        suffix = f":{year}" if year not in (None, "") else ""
        normalized = " ".join(str(title or "").casefold().split())
        return f"{kind}:{normalized}{suffix}"

    @classmethod
    def _split_role(cls, role: str) -> tuple[str, list[str]]:
        cleaned = cls._norm(role)
        cleaned = re.sub(
            r"\s*\((?:stimme|voice|sprecher(?:in)?)\)\s*$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        parts = [
            cls._norm(item)
            for item in re.split(
                r"\s*/\s*|\s+alias\s+",
                cleaned,
                flags=re.IGNORECASE,
            )
            if cls._norm(item)
        ]
        return (parts[0], parts[1:]) if parts else ("", [])

    @staticmethod
    def _performance_type(role: str) -> str:
        if re.search(
            r"\((?:stimme|voice|sprecher(?:in)?)\)",
            str(role or ""),
            flags=re.IGNORECASE,
        ):
            return "voice"
        return "on_screen"

    @staticmethod
    def _clean_wikilinks(value: str) -> str:
        return re.sub(
            r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]",
            r"\1",
            value,
        )

    @classmethod
    def _clean_actor_candidate(cls, value: str) -> str:
        actor = cls._norm(value)
        actor = actor.replace("\\n", " ").replace("\n", " ")
        actor = re.sub(
            r"^(?:Besetzung|Rolle|Schauspieler|Darsteller)\s+",
            "",
            actor,
            flags=re.IGNORECASE,
        )
        actor = re.sub(
            r"^.*?\bBesetzung\s+",
            "",
            actor,
            flags=re.IGNORECASE,
        )
        return actor.strip(" ,.;:*")

    @classmethod
    def _clean_role_candidate(cls, value: str) -> str:
        role = str(value or "")
        role = role.replace("\\n", " ").replace("\n", " ")
        role = cls._clean_wikilinks(role)
        role = re.sub(r"\\+", "", role)
        role = re.sub(
            r'["}\]]+\s*,?\s*$',
            "",
            role,
        )
        return cls._norm(role).strip(" ,.;:*")

    @classmethod
    def _valid_actor_name(cls, value: str) -> bool:
        actor = cls._norm(value)
        words = actor.split()

        if not 2 <= len(words) <= 5:
            return False

        blocked = {
            "film",
            "titel",
            "originaltitel",
            "produktionsland",
            "originalsprache",
            "erscheinungsjahr",
            "länge",
            "altersfreigabe",
            "stab",
            "regie",
            "drehbuch",
            "produktion",
            "musik",
            "kamera",
            "schnitt",
            "besetzung",
            "chronologie",
        }
        if any(word.casefold() in blocked for word in words):
            return False

        return all(
            re.match(
                r"^(?:[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.'’\-]+|II|III|IV|V)$",
                word,
            )
            is not None
            for word in words
        )

    @classmethod
    def _valid_role_name(cls, value: str) -> bool:
        role = cls._norm(value)
        if not role or len(role) > 100:
            return False

        blocked_starts = (
            "Chronologie",
            "Handlung",
            "Produktion",
            "Synchronisation",
        )
        return not role.startswith(blocked_starts)

    def _extract_wikipedia_markup_pairs(
        self,
        text: str,
    ) -> list[dict[str, str]]:
        # Eingebettete Wikipedia-Infoboxen können mehrfach escaped sein:
        # \"Besetzung\":{\"wt\":\"...\\n...\"}
        # Deshalb zuerst escaped Anführungszeichen und anschließend beide
        # gebräuchlichen Backslash-n-Varianten normalisieren.
        normalized = str(text or "")
        normalized = normalized.replace("\\\\n", "\n")
        normalized = normalized.replace("\\n", "\n")
        normalized = normalized.replace("\\\"", "\"")

        # Wenn möglich nur das Besetzungsfeld betrachten. Dadurch können
        # nachfolgende Infoboxfelder nicht Teil der letzten Rolle werden.
        field_match = re.search(
            r'["\']?Besetzung["\']?\s*:\s*\{\s*'
            r'["\']?wt["\']?\s*:\s*["\']'
            r'(?P<cast>.*?)'
            r'["\']\s*\}\s*,\s*'
            r'["\']?Synchronisation["\']?\s*:',
            normalized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        cast_text = (
            field_match.group("cast")
            if field_match
            else normalized
        )

        line_pattern = re.compile(
            r"^\s*\*\s*"
            r"\[\[(?P<actor>[^\]|]+)"
            r"(?:\|[^\]]+)?\]\]"
            r"\s*:\s*"
            r"(?P<role>.+?)\s*$",
            flags=re.MULTILINE,
        )

        pairs: list[dict[str, str]] = []
        for match in line_pattern.finditer(cast_text):
            actor = self._clean_actor_candidate(
                match.group("actor")
            )
            role = self._clean_role_candidate(
                match.group("role")
            )

            if not self._valid_actor_name(actor):
                continue
            if not self._valid_role_name(role):
                continue

            pairs.append(
                {
                    "actor": actor,
                    "role": role,
                    "evidence": self._norm(match.group(0)),
                    "source_format": "wikipedia_infobox_markup",
                }
            )

        return pairs

    @classmethod
    def _split_trailing_actor(
        cls,
        value: str,
    ) -> tuple[str, str] | None:
        """Trennt `vorherige Rolle + nächster Schauspieler`.

        Wikipedia liefert flache Folgen wie:
        `Orm Marius Amber Heard : Mera`.
        Vor dem Doppelpunkt steht dabei zuerst die vorherige Rolle und
        direkt am Ende der nächste Schauspieler.
        """
        text = cls._norm(value).strip(" ,.;:")
        if not text:
            return None

        words = text.split()
        if len(words) < 3:
            return None

        actor_length = 2

        suffixes = {
            "ii",
            "iii",
            "iv",
            "v",
            "jr.",
            "jr",
            "sr.",
            "sr",
        }
        if words[-1].casefold() in suffixes and len(words) >= 4:
            actor_length = 3
        elif (
            len(words) >= 4
            and len(words[-2].rstrip(".")) == 1
        ):
            actor_length = 3

        actor = " ".join(words[-actor_length:])
        role = " ".join(words[:-actor_length])

        if not role:
            return None
        if not cls._valid_actor_name(actor):
            return None

        return role, actor

    def _extract_flat_cast_pairs(
        self,
        text: str,
    ) -> list[dict[str, str]]:
        match = re.search(
            r"\bBesetzung\b(?P<cast>.+?)"
            r"(?=\bChronologie\b|\bHandlung\b|\Z)",
            str(text or ""),
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return []

        cast_text = self._norm(match.group("cast"))
        chunks = [
            self._norm(item)
            for item in cast_text.split(":")
        ]

        if len(chunks) < 2:
            return []

        first_actor = self._clean_actor_candidate(chunks[0])
        if not self._valid_actor_name(first_actor):
            return []

        actors: list[str] = [first_actor]
        roles: list[str] = []

        # Jeder mittlere Block enthält:
        # Rolle des vorigen Schauspielers + Namen des nächsten Schauspielers.
        for chunk in chunks[1:-1]:
            split = self._split_trailing_actor(chunk)
            if split is None:
                return []

            previous_role, next_actor = split
            roles.append(
                self._clean_role_candidate(previous_role)
            )
            actors.append(
                self._clean_actor_candidate(next_actor)
            )

        roles.append(
            self._clean_role_candidate(chunks[-1])
        )

        if len(actors) != len(roles):
            return []

        pairs: list[dict[str, str]] = []
        for actor, role in zip(actors, roles):
            if not self._valid_actor_name(actor):
                continue
            if not self._valid_role_name(role):
                continue

            pairs.append(
                {
                    "actor": actor,
                    "role": role,
                    "evidence": f"{actor} : {role}",
                    "source_format": "wikipedia_flat_cast_list",
                }
            )

        return pairs

    def _extract_cast_pairs(self, text: str) -> list[dict[str, str]]:
        pairs = self._extract_wikipedia_markup_pairs(text)
        if not pairs:
            pairs = self._extract_flat_cast_pairs(text)

        unique: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for pair in pairs:
            key = (
                pair["actor"].casefold(),
                pair["role"].casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(pair)

        return unique

    def resolve(self, *, main_node, text, source):
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        warnings: list[str] = []
        index: dict[str, dict[str, Any]] = {}

        def add_node(
            kind,
            title,
            confidence,
            reason,
            metadata=None,
            year=None,
        ):
            title = self._norm(title)
            key = self._key(kind, title, year)
            existing = index.get(key)
            if existing is not None:
                existing["metadata"].update(dict(metadata or {}))
                existing["confidence"] = max(
                    float(existing.get("confidence") or 0),
                    float(confidence),
                )
                return existing

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

        def add_edge(
            kind,
            src,
            dst,
            confidence,
            reason,
            text_value,
            metadata=None,
        ):
            duplicate = any(
                item["edge_type"] == kind
                and item["source_node_key"] == src["key"]
                and item["target_node_key"] == dst["key"]
                for item in edges
            )
            if duplicate:
                return

            evidence_id = uuid.uuid4().hex
            evidence.append(
                {
                    "id": evidence_id,
                    "text": text_value,
                    "edge_type": kind,
                    "source_id": source.get("id"),
                }
            )
            edges.append(
                {
                    "id": uuid.uuid4().hex,
                    "edge_type": kind,
                    "source_node_key": src["key"],
                    "target_node_key": dst["key"],
                    "confidence": round(float(confidence), 4),
                    "reason": reason,
                    "metadata": dict(metadata or {}),
                    "evidence_id": evidence_id,
                    "source_id": source.get("id"),
                    "status": "proposed",
                    "requires_confirmation": True,
                }
            )

        media = add_node(
            str(main_node.get("node_type") or "media"),
            str(main_node.get("title") or ""),
            float(main_node.get("confidence") or 0.8),
            "Hauptmedium aus Graph Builder.",
            dict(main_node.get("metadata") or {}),
            year=main_node.get("year"),
        )

        cast_pairs = self._extract_cast_pairs(str(text or ""))
        if not cast_pairs:
            warnings.append("Keine sicheren Besetzungspaare gefunden.")

        for position, pair in enumerate(cast_pairs, start=1):
            actor_name = pair["actor"]
            raw_role_name = pair["role"]
            performance_type = self._performance_type(raw_role_name)
            primary, aliases = self._split_role(raw_role_name)
            if not primary:
                continue

            shared_metadata = {
                "raw_role_name": raw_role_name,
                "performance_type": performance_type,
                "billing_position": position,
                "source_format": pair["source_format"],
            }

            actor = add_node(
                "person",
                actor_name,
                0.92,
                "Darsteller aus strukturierter Besetzung.",
                {
                    "known_as_cast_member": True,
                },
            )
            character = add_node(
                "character",
                primary,
                0.90,
                "Figur aus strukturierter Rollenangabe.",
                shared_metadata,
            )

            add_edge(
                "has_cast",
                media,
                actor,
                0.92,
                "Medium führt die Person in der Besetzung.",
                pair["evidence"],
                shared_metadata,
            )
            add_edge(
                "portrays",
                actor,
                character,
                0.92,
                "Person verkörpert oder spricht die Figur.",
                pair["evidence"],
                shared_metadata,
            )
            add_edge(
                "portrayed_by",
                character,
                actor,
                0.92,
                "Figur wird von der Person verkörpert oder gesprochen.",
                pair["evidence"],
                shared_metadata,
            )
            add_edge(
                "appears_in",
                character,
                media,
                0.90,
                "Figur erscheint im Werk.",
                pair["evidence"],
                shared_metadata,
            )

            if performance_type == "voice":
                add_edge(
                    "voices",
                    actor,
                    character,
                    0.92,
                    "Person spricht die Figur.",
                    pair["evidence"],
                    shared_metadata,
                )

            for alias_name in aliases:
                alias = add_node(
                    "character_alias",
                    alias_name,
                    0.88,
                    "Alias aus Rollenangabe.",
                    shared_metadata,
                )
                add_edge(
                    "alias_of",
                    alias,
                    character,
                    0.92,
                    "Alias gehört zur Hauptfigur.",
                    pair["evidence"],
                    shared_metadata,
                )
                add_edge(
                    "appears_in",
                    alias,
                    media,
                    0.84,
                    "Alias wird im Werk verwendet.",
                    pair["evidence"],
                    shared_metadata,
                )

        return {
            "schema_version": 2,
            "strategy": "character_cast_intelligence_v340",
            "main_node_key": media["key"],
            "cast_pair_count": len(cast_pairs),
            "nodes": nodes,
            "edges": edges,
            "evidence": evidence,
            "warnings": warnings,
            "automatic_import": False,
            "requires_confirmation": True,
        }
