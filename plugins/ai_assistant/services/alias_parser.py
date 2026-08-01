from __future__ import annotations

import re
from typing import Any


class AliasParser:
    """Kleiner Parser für explizite Alias-Aussagen."""

    SEPARATORS = (
        " auch bekannt als ",
        " alias ",
    )

    FOLLOWING_VERBS = (
        "verteidigt",
        "verteidigte",
        "kämpft",
        "kämpfte",
        "arbeitet",
        "arbeitete",
        "lebt",
        "wohnte",
        "wohnt",
        "heiratete",
        "rettet",
        "rettete",
        "findet",
        "fand",
        "ist",
        "war",
        "wurde",
        "hat",
        "bekam",
        "beschützt",
        "beschützte",
        "entführt",
        "entführte",
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _trim_alias_tail(cls, value: str) -> str:
        text = cls._norm(value)
        text = re.split(r"[.,;:!?]", text, maxsplit=1)[0].strip()

        verb_pattern = (
            r"\s+(?:" +
            "|".join(re.escape(item) for item in cls.FOLLOWING_VERBS) +
            r")\b"
        )
        text = re.split(
            verb_pattern,
            text,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        return text

    @classmethod
    def parse(cls, text: str) -> list[dict[str, str]]:
        source_text = str(text or "")
        lowered = source_text.casefold()
        results: list[dict[str, str]] = []

        for separator in cls.SEPARATORS:
            sep_lower = separator.casefold()
            search_from = 0

            while True:
                index = lowered.find(sep_lower, search_from)
                if index < 0:
                    break

                left_context = source_text[:index]
                right_context = source_text[index + len(separator):]

                left_sentence = re.split(
                    r"(?<=[.!?])\s+",
                    left_context,
                )[-1]
                primary = cls._norm(left_sentence)

                alias = cls._trim_alias_tail(right_context)

                primary = re.sub(
                    r"^(?:und|sowie|während|danach|anschließend)\s+",
                    "",
                    primary,
                    flags=re.IGNORECASE,
                ).strip()

                primary = re.sub(
                    r"\s+(?:ist|war|wurde)$",
                    "",
                    primary,
                    flags=re.IGNORECASE,
                ).strip()

                if primary and alias:
                    results.append(
                        {
                            "primary": primary,
                            "alias": alias,
                            "evidence": (
                                f"{primary}{separator}{alias}"
                            ),
                            "separator": separator.strip(),
                        }
                    )

                search_from = index + len(separator)

        unique: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for item in results:
            key = (
                item["primary"].casefold(),
                item["alias"].casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique
