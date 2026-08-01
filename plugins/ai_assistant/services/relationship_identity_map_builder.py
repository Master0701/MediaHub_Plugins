from __future__ import annotations

from typing import Any


class RelationshipIdentityMapBuilder:
    """Vereinigt sichere Event- und Besetzungsidentitäten."""

    BLOCKED_ALIASES = {
        "amnesty",
        "barthel",
        "beetle",
        "drehbuch",
        "in",
        "james",
        "kordax'",
        "königreichs",
        "leslie",
        "millionen",
        "stab",
        "titel",
        "verbrecherboss",
        "warner",
        "wilsons",
    }

    HONORIFICS = {
        "dr",
        "dr.",
        "king",
        "könig",
        "königin",
        "prinz",
        "prinzessin",
    }

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _safe_alias(cls, value: str) -> bool:
        alias = cls._norm(value).casefold()
        if not alias or alias in cls.BLOCKED_ALIASES:
            return False
        if len(alias) < 2:
            return False
        if " " in alias:
            return False
        return alias.replace("'", "").replace("-", "").isalpha()

    @classmethod
    def _safe_canonical(cls, value: str) -> bool:
        title = cls._norm(value)
        if not title:
            return False
        lowered = title.casefold()
        if any(
            lowered.startswith(f"{prefix} ")
            for prefix in (
                "titel",
                "stab",
                "drehbuch",
                "in",
                "warner",
                "millionen",
            )
        ):
            return False
        return True

    @classmethod
    def _cast_aliases(
        cls,
        node: dict[str, Any],
    ) -> list[str]:
        title = cls._norm(node.get("title"))
        if not title:
            return []

        words = title.split()
        aliases: list[str] = []

        if words:
            first = words[0].casefold()
            if first not in cls.HONORIFICS:
                aliases.append(first)

        metadata = dict(node.get("metadata") or {})
        raw_role = cls._norm(metadata.get("raw_role_name"))
        if raw_role:
            for part in raw_role.split("/"):
                candidate = cls._norm(part).casefold()
                if " " not in candidate:
                    aliases.append(candidate)

        return aliases

    @classmethod
    def build(
        cls,
        *,
        event_intelligence: dict[str, Any] | None,
        cast_resolution: dict[str, Any] | None,
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        event_map = dict(
            (
                dict(event_intelligence or {})
                .get("identity_resolution")
                or {}
            ).get("alias_map")
            or {}
        )

        for alias, canonical in event_map.items():
            alias_text = cls._norm(alias).casefold()
            canonical_text = cls._norm(canonical)

            if not cls._safe_alias(alias_text):
                continue
            if not cls._safe_canonical(canonical_text):
                continue

            result[alias_text] = canonical_text

        for node in dict(cast_resolution or {}).get("nodes") or []:
            if node.get("node_type") != "character":
                continue

            canonical = cls._norm(node.get("title"))
            if not cls._safe_canonical(canonical):
                continue

            for alias in cls._cast_aliases(node):
                if cls._safe_alias(alias):
                    # Cast identities are stronger than guessed event aliases.
                    result[alias] = canonical

        return result
