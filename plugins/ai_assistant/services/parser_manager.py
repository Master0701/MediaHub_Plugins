from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParserDescriptor:
    parser_id: str
    name: str
    source_types: tuple[str, ...]
    domains: tuple[str, ...]
    priority: int


class BaseSourceParser:
    descriptor: ParserDescriptor

    def supports(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> bool:
        source_type = str(source.get("source_type") or "")
        if (
            self.descriptor.source_types
            and source_type not in self.descriptor.source_types
        ):
            return False

        url = str(scan_result.get("url") or source.get("url") or "")
        domain = urlparse(url).netloc.casefold()
        if self.descriptor.domains:
            return any(
                domain == item or domain.endswith("." + item)
                for item in self.descriptor.domains
            )
        return True

    def parse(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError


class GenericHtmlParser(BaseSourceParser):
    descriptor = ParserDescriptor(
        parser_id="generic_html",
        name="Generischer HTML-Parser",
        source_types=("website", "custom_url"),
        domains=(),
        priority=10,
    )

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    def parse(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        title = self._normalize(scan_result.get("title"))
        headings = [
            self._normalize(item)
            for item in scan_result.get("headings") or []
            if self._normalize(item)
        ]
        text = str(scan_result.get("text_preview") or "")

        years = sorted(
            {
                int(value)
                for value in re.findall(r"\b(19\d{2}|20\d{2})\b", text)
            }
        )
        media_type = None
        lowered = text.casefold()
        for candidate, terms in (
            ("movie", ("film", "spielfilm", "movie")),
            ("series", ("fernsehserie", "tv-serie", "series")),
            ("audiobook", ("hörbuch", "audiobook")),
        ):
            if any(term in lowered for term in terms):
                media_type = candidate
                break

        relation_terms = sorted(
            {
                term
                for term in (
                    "sequel",
                    "prequel",
                    "spin-off",
                    "spinoff",
                    "crossover",
                    "reboot",
                    "remake",
                    "franchise",
                    "universum",
                    "chronologie",
                    "timeline",
                )
                if term in lowered
            }
        )

        fields = {}
        if title:
            fields["title"] = title
        if years:
            fields["year_candidates"] = years
        if media_type:
            fields["media_type"] = media_type
        if relation_terms:
            fields["relation_terms"] = relation_terms

        return {
            "schema_version": 1,
            "parser_id": self.descriptor.parser_id,
            "parser_name": self.descriptor.name,
            "source_id": source.get("id"),
            "source_name": source.get("name"),
            "source_url": scan_result.get("url"),
            "fields": fields,
            "headings": headings[:50],
            "confidence": 0.58,
            "limitations": [
                "Generische HTML-Erkennung kann Seitentitel und "
                "Navigationsbegriffe mit Medienangaben verwechseln."
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }


class WikipediaParser(GenericHtmlParser):
    descriptor = ParserDescriptor(
        parser_id="wikipedia",
        name="Wikipedia-Parser",
        source_types=("website", "custom_url"),
        domains=("wikipedia.org",),
        priority=100,
    )

    @staticmethod
    def _clean_wikipedia_title(value: str) -> str:
        title = str(value or "")
        title = re.sub(
            r"\s*[–-]\s*Wikipedia\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        )
        return " ".join(title.strip().split())

    def parse(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        result = super().parse(
            source=source,
            scan_result=scan_result,
        )
        result["parser_id"] = self.descriptor.parser_id
        result["parser_name"] = self.descriptor.name
        result["confidence"] = 0.82

        title = self._clean_wikipedia_title(
            str(scan_result.get("title") or "")
        )
        if title:
            result["fields"]["title"] = title

        headings = {
            str(item).casefold()
            for item in scan_result.get("headings") or []
        }
        text = str(scan_result.get("text_preview") or "")
        lowered = text.casefold()

        metadata = {}
        if any("handlung" in item for item in headings):
            metadata["has_plot_section"] = True
        if any("besetzung" in item for item in headings):
            metadata["has_cast_section"] = True
        if any("produktion" in item for item in headings):
            metadata["has_production_section"] = True

        sequel_match = re.search(
            r"(?i)(?:fortsetzung|nachfolger)\s+"
            r"(?:ist|war|wurde)?\s*"
            r"([A-ZÄÖÜ][^.!?\n]{2,100})",
            text,
        )
        if sequel_match:
            metadata["possible_sequel_title"] = " ".join(
                sequel_match.group(1).split()
            )

        if "dc extended universe" in lowered:
            metadata["universe"] = "DC Extended Universe"

        if metadata:
            result["fields"]["metadata"] = metadata

        result["limitations"] = [
            "Wikipedia-Text wird in Phase 1 ohne DOM-spezifische "
            "Infobox-Auswertung verarbeitet.",
            "Gefundene Beziehungen bleiben Vorschläge.",
        ]
        return result


class ParserManager:
    """Wählt geeignete Parser aus und vereinheitlicht deren Ergebnisse."""

    def __init__(self):
        self._parsers: list[BaseSourceParser] = []
        self.register(WikipediaParser())
        self.register(GenericHtmlParser())

    def register(self, parser: BaseSourceParser) -> None:
        parser_id = parser.descriptor.parser_id
        self._parsers = [
            item
            for item in self._parsers
            if item.descriptor.parser_id != parser_id
        ]
        self._parsers.append(parser)
        self._parsers.sort(
            key=lambda item: -int(item.descriptor.priority)
        )

    def descriptors(self) -> list[dict[str, Any]]:
        return [
            {
                "parser_id": item.descriptor.parser_id,
                "name": item.descriptor.name,
                "source_types": list(item.descriptor.source_types),
                "domains": list(item.descriptor.domains),
                "priority": item.descriptor.priority,
            }
            for item in self._parsers
        ]

    def select_parser(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> BaseSourceParser:
        for parser in self._parsers:
            if parser.supports(
                source=source,
                scan_result=scan_result,
            ):
                return parser
        raise LookupError("Kein geeigneter Parser gefunden.")

    def parse(
        self,
        *,
        source: dict[str, Any],
        scan_result: dict[str, Any],
    ) -> dict[str, Any]:
        parser = self.select_parser(
            source=source,
            scan_result=scan_result,
        )
        result = parser.parse(
            source=source,
            scan_result=scan_result,
        )
        return {
            "schema_version": 1,
            "selected_parser": parser.descriptor.parser_id,
            "result": result,
            "automatic_import": False,
            "requires_confirmation": True,
        }
