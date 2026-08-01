from __future__ import annotations

from typing import Any


class CharacterAliasIdentityFusion:
    """Erzeugt einen bereinigten Figuren-/Alias-Teilgraphen."""

    BLOCKED_ALIASES = {
        "dr",
        "dr.",
        "doctor",
        "king",
        "queen",
        "könig",
        "königin",
        "prinz",
        "prinzessin",
        "herrscher",
        "verbrecherboss",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _character_key(cls, title: str) -> str:
        return f"character:{cls._norm(title).casefold()}"

    @classmethod
    def _alias_key(cls, title: str) -> str:
        return f"character_alias:{cls._norm(title).casefold()}"

    @classmethod
    def _valid_alias(cls, value: str) -> bool:
        alias = cls._norm(value)
        if not alias:
            return False
        if alias.casefold() in cls.BLOCKED_ALIASES:
            return False
        return len(alias) >= 2

    @classmethod
    def _cast_character_titles(
        cls,
        cast_resolution: dict[str, Any] | None,
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for node in dict(cast_resolution or {}).get("nodes") or []:
            if node.get("node_type") != "character":
                continue
            title = cls._norm(node.get("title"))
            key = cls._norm(node.get("key"))
            if title:
                result[
                    key.casefold() if key else cls._character_key(title)
                ] = title
        return result

    @classmethod
    def _cast_person_titles(
        cls,
        cast_resolution: dict[str, Any] | None,
    ) -> set[str]:
        return {
            cls._norm(node.get("title")).casefold()
            for node in dict(cast_resolution or {}).get("nodes") or []
            if node.get("node_type") == "person"
            and cls._norm(node.get("title"))
        }

    @classmethod
    def _cast_alias_map(
        cls,
        cast_resolution: dict[str, Any] | None,
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        character_titles = cls._cast_character_titles(cast_resolution)

        for node in dict(cast_resolution or {}).get("nodes") or []:
            node_type = node.get("node_type")
            title = cls._norm(node.get("title"))
            if not title:
                continue

            if node_type == "character":
                words = title.split()
                if words and cls._valid_alias(words[0]):
                    result.setdefault(words[0].casefold(), title)

                raw_role = cls._norm(
                    dict(node.get("metadata") or {}).get("raw_role_name")
                )
                for part in raw_role.split("/"):
                    alias = cls._norm(part)
                    if (
                        cls._valid_alias(alias)
                        and alias.casefold() != title.casefold()
                    ):
                        result[alias.casefold()] = title

            elif node_type == "character_alias":
                metadata = dict(node.get("metadata") or {})
                canonical = cls._norm(
                    metadata.get("canonical_title")
                    or metadata.get("primary_title")
                )
                if canonical and cls._valid_alias(title):
                    result[title.casefold()] = canonical

        for edge in dict(cast_resolution or {}).get("edges") or []:
            if edge.get("edge_type") != "alias_of":
                continue

            source_key = cls._norm(edge.get("source_node_key"))
            target_key = cls._norm(edge.get("target_node_key"))
            if not source_key.startswith("character_alias:"):
                continue
            if not target_key.startswith("character:"):
                continue

            alias = source_key.split(":", 1)[1]
            canonical = character_titles.get(target_key.casefold())
            if not canonical:
                canonical = target_key.split(":", 1)[1]

            if cls._valid_alias(alias):
                result[alias.casefold()] = canonical

        return result

    @classmethod
    def _flatten_map(
        cls,
        identity_map: dict[str, str],
    ) -> dict[str, str]:
        raw = {
            cls._norm(alias).casefold(): cls._norm(canonical)
            for alias, canonical in dict(identity_map or {}).items()
            if cls._valid_alias(alias) and cls._norm(canonical)
        }

        flattened: dict[str, str] = {}
        for alias, canonical in raw.items():
            visited = {alias}
            current = canonical
            while True:
                next_value = raw.get(current.casefold())
                if not next_value:
                    break
                if next_value.casefold() in visited:
                    break
                visited.add(next_value.casefold())
                current = next_value
            flattened[alias] = current
        return flattened

    @classmethod
    def build(
        cls,
        *,
        identity_map: dict[str, str] | None,
        cast_resolution: dict[str, Any] | None,
        source: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(source or {})
        source_id = source.get("id")
        person_titles = cls._cast_person_titles(cast_resolution)
        cast_map = cls._cast_alias_map(cast_resolution)

        merged: dict[str, str] = {}
        for alias, canonical in dict(identity_map or {}).items():
            alias_text = cls._norm(alias)
            canonical_text = cls._norm(canonical)
            if not cls._valid_alias(alias_text):
                continue
            if not canonical_text:
                continue
            if canonical_text.casefold() in person_titles:
                continue
            merged[alias_text.casefold()] = canonical_text

        # Castdaten sind stärker als heuristische Event-Zuordnungen.
        merged.update(cast_map)
        canonical_map = cls._flatten_map(merged)

        canonical_titles = {
            cls._norm(value)
            for value in canonical_map.values()
            if cls._norm(value)
            and cls._norm(value).casefold() not in person_titles
        }

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for canonical in sorted(canonical_titles, key=str.casefold):
            nodes.append({
                "key": cls._character_key(canonical),
                "node_type": "character",
                "title": canonical,
                "confidence": 0.97,
                "metadata": {
                    "identity_fusion": "character_alias_identity_fusion_v4112",
                },
                "reason": "Kanonische Figurenidentität.",
                "source_id": source_id,
                "requires_confirmation": True,
            })

        for alias, canonical in sorted(canonical_map.items()):
            alias_title = cls._norm(alias)
            canonical_title = cls._norm(canonical)
            if not cls._valid_alias(alias_title):
                continue
            if not canonical_title:
                continue
            if canonical_title.casefold() in person_titles:
                continue
            if alias_title.casefold() == canonical_title.casefold():
                continue

            alias_key = cls._alias_key(alias_title)
            canonical_key = cls._character_key(canonical_title)

            nodes.append({
                "key": alias_key,
                "node_type": "character_alias",
                "title": alias_title,
                "confidence": 0.96,
                "metadata": {
                    "canonical_title": canonical_title,
                    "identity_fusion": "character_alias_identity_fusion_v4112",
                },
                "reason": "Alias einer kanonischen Figur.",
                "source_id": source_id,
                "requires_confirmation": True,
            })
            edges.append({
                "edge_type": "alias_of",
                "source_node_key": alias_key,
                "target_node_key": canonical_key,
                "confidence": 0.96,
                "metadata": {
                    "identity_fusion": "character_alias_identity_fusion_v4112",
                },
                "reason": "Alias auf kanonische Figurenidentität.",
                "source_id": source_id,
                "requires_confirmation": True,
            })

        return {
            "schema_version": 1,
            "strategy": "character_alias_identity_fusion_v4112",
            "canonical_map": canonical_map,
            "canonical_count": len(canonical_titles),
            "alias_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "filtered_person_count": len(person_titles),
            "automatic_import": False,
            "requires_confirmation": True,
        }
