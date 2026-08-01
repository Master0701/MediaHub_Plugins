from __future__ import annotations

import re
from typing import Any


class PlotCleaner:
    """Bereinigt extrahierte Handlungstexte vor der Ereignisanalyse."""

    SECTION_HEADINGS = (
        "Handlung",
        "Produktion",
        "Synchronisation",
        "Veröffentlichung",
        "Rezeption",
        "Weblinks",
        "Einzelnachweise",
        "Trivia",
    )

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @classmethod
    def clean(cls, text: str) -> str:
        source = str(text or "")
        if not source:
            return ""

        cleaned = source

        # Wikipedia-Bearbeitungsreste entfernen.
        cleaned = re.sub(
            r"\[\s*Bearbeiten(?:\s*\|\s*Quelltext bearbeiten)?\s*\]",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\[\s*Quelltext bearbeiten\s*\]",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )

        # Führende Abschnittsüberschrift entfernen.
        heading_pattern = "|".join(
            re.escape(item)
            for item in cls.SECTION_HEADINGS
        )
        cleaned = re.sub(
            rf"^\s*(?:{heading_pattern})\b[\s:–—-]*",
            "",
            cleaned,
            count=1,
            flags=re.IGNORECASE,
        )

        # Alles ab einer nachfolgenden echten Abschnittsüberschrift entfernen.
        cleaned = re.split(
            rf"\s+(?=(?:Produktion|Synchronisation|Veröffentlichung|"
            rf"Rezeption|Weblinks|Einzelnachweise|Trivia)\b)",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        # Inhaltsverzeichnisreste am Anfang entfernen.
        cleaned = re.sub(
            r"^\s*(?:Inhaltsverzeichnis\s+)?"
            r"(?:\d+\s+Handlung\s+)?"
            r"(?:\d+\s+Produktion\s+)?"
            r"(?:\d+\s+Synchronisation\s+)?",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        # Typische Navigations- und Markerreste.
        cleaned = re.sub(
            r"\b(?:Bearbeiten|Quelltext bearbeiten)\b",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"\[\s*\d+\s*\]",
            " ",
            cleaned,
        )

        return cls._norm(cleaned)
