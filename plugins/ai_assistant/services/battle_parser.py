from __future__ import annotations

import re
from typing import Any


class BattleParser:
    """Parser für deutsche Kampf- und Duellformulierungen."""

    NAME = (
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*"
        r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*){0,3}?"
    )
    LOCATION = (
        r"[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*"
        r"(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9.'-]*){0,4}?"
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _clean_actor(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"^(?:und|aber|daraufhin|anschließend|danach)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip(" ,.;:")

    @classmethod
    def _clean_location(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.sub(
            r"^(?:der|die|das|dem|den)\s+",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text.strip(" ,.;:")

    @classmethod
    def parse(cls, sentence: str) -> list[dict[str, Any]]:
        text = cls._norm(sentence)
        if not text:
            return []

        patterns = (
            # In Necrus kämpft Arthur gegen David, ...
            re.compile(
                rf"^(?:In|Bei)\s+"
                rf"(?P<location>{cls.LOCATION})\s+"
                rf"kämpft(?:e)?\s+"
                rf"(?P<actor>{cls.NAME})\s+gegen\s+"
                rf"(?P<opponent>{cls.NAME})"
                rf"(?=,|[.!?]|$)",
                flags=re.IGNORECASE,
            ),
            # Auf der Insel kämpfte Arthur gegen David.
            re.compile(
                rf"^Auf\s+(?:der|dem|den)\s+"
                rf"(?P<location>{cls.LOCATION})\s+"
                rf"kämpft(?:e)?\s+"
                rf"(?P<actor>{cls.NAME})\s+gegen\s+"
                rf"(?P<opponent>{cls.NAME})"
                rf"(?=,|[.!?]|$)",
                flags=re.IGNORECASE,
            ),
            # Während der Schlacht kämpfte Thor gegen Hela.
            re.compile(
                rf"^Während\s+(?:der|des|dem)\s+"
                rf"(?P<context>{cls.LOCATION})\s+"
                rf"kämpft(?:e)?\s+"
                rf"(?P<actor>{cls.NAME})\s+gegen\s+"
                rf"(?P<opponent>{cls.NAME})"
                rf"(?=,|[.!?]|$)",
                flags=re.IGNORECASE,
            ),
            # Arthur kämpft gegen David.
            re.compile(
                rf"\b(?P<actor>{cls.NAME})\s+"
                rf"kämpft(?:e)?\s+gegen\s+"
                rf"(?P<opponent>{cls.NAME})"
                rf"(?=,|[.!?]|$)",
                flags=re.IGNORECASE,
            ),
        )

        results: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str | None]] = set()

        for pattern in patterns:
            match = pattern.search(text)
            if not match:
                continue

            groups = match.groupdict()
            actor = cls._clean_actor(groups["actor"])
            opponent = cls._clean_actor(groups["opponent"])
            location = groups.get("location")
            context = groups.get("context")

            if location:
                location = cls._clean_location(location)

            key = (
                actor.casefold(),
                opponent.casefold(),
                location.casefold() if location else None,
            )
            if key in seen:
                continue
            seen.add(key)

            results.append(
                {
                    "actor": actor,
                    "opponent": opponent,
                    "location": location,
                    "context": cls._norm(context) if context else None,
                    "evidence": match.group(0),
                    "parser": "battle_parser_v380",
                }
            )
            break

        return results
