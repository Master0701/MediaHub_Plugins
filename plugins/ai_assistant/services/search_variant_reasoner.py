from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from services.input_quality import evaluate_text


@dataclass(frozen=True, slots=True)
class SearchVariant:
    title: str
    score: float
    source: str
    reasons: tuple[str, ...]
    media_type: str | None = None
    quality_score: float = 1.0
    quality_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["reasons"] = list(self.reasons)
        data["quality_reasons"] = list(self.quality_reasons)
        return data


class SearchVariantReasoner:
    """Erzeugt gewichtete Titelvarianten aus Datei-, OCR- und Wissensdaten."""

    TECHNICAL_TOKENS = {
        "1080p", "1080i", "720p", "2160p", "4320p", "4k", "8k", "uhd",
        "hdr", "hdr10", "hdr10plus", "dv", "dolbyvision", "bluray", "bdrip",
        "brrip", "webrip", "webdl", "hdtv", "dvdrip", "remux", "x264",
        "x265", "h264", "h265", "hevc", "avc", "av1", "aac", "ac3",
        "eac3", "dts", "truehd", "atmos", "proper", "repack", "internal",
        "german", "deutsch", "english", "multi", "dubbed", "subbed", "dl",
        "dd", "5", "1", "7", "1ch", "10bit", "8bit", "extended", "uncut",
        "remastered", "theatrical", "directors", "cut",
    }
    RELEASE_GROUP = re.compile(r"(?:[-_. ](?:[A-Z0-9]{2,12}))$", re.I)
    EPISODE_PATTERN = re.compile(r"\b(?:s\d{1,3}e\d{1,4}|e\d{1,4})\b", re.I)
    YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
    NOISE_PATTERN = re.compile(r"^(?:\d{3,4}[pi]|\d+(?:\.\d+)?(?:mbps|kbps|bit))$", re.I)

    def __init__(self, knowledge_database_path: Path | None = None):
        self.knowledge_database_path = Path(knowledge_database_path) if knowledge_database_path else None

    def build(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        file_info = analysis.get("file") or {}
        media_type = identification.get("media_type")
        raw: list[tuple[str, float, str, tuple[str, ...]]] = []

        identity_hint_title = str(
            identification.get("identity_hint_title") or ""
        ).strip()

        if identity_hint_title:
            self._append(
                raw,
                identity_hint_title,
                1.15,
                "identity_hint",
                "Strukturierte Identität aus vorgelagerter Medienerkennung",
            )

        self._append(
            raw,
            identification.get("title_candidate"),
            1.0,
            "filename",
            "Titelkandidat aus Datei-/Ordnername",
        )
        self._append(
            raw,
            identification.get("parent_title_candidate"),
            0.88,
            "folder",
            "Titelkandidat aus übergeordnetem Ordner",
        )
        self._append(
            raw,
            identification.get("normalized_name")
            or file_info.get("name"),
            0.92,
            "normalized_filename",
            "Technische Bestandteile entfernt",
        )

        expanded: list[SearchVariant] = []
        for value, score, source, reasons in raw:
            expanded.extend(self._expand_candidate(value, score, source, reasons, media_type))

        expanded.extend(self._ocr_variants(analysis, media_type))
        knowledge_matches = self._knowledge_matches([item.title for item in expanded])
        for entity, matched_value in knowledge_matches:
            canonical = str(entity.get("title") or "").strip()
            aliases = [str(x).strip() for x in entity.get("aliases") or [] if str(x).strip()]
            metadata = entity.get("metadata") or {}
            titles = [
                (canonical, 1.08, "knowledge_title", "Kanonischer Titel aus lokaler Wissensbasis"),
                (metadata.get("german_title"), 1.03, "knowledge_german", "Deutscher Titel aus lokaler Wissensbasis"),
                (metadata.get("english_title"), 1.01, "knowledge_english", "Englischer Titel aus lokaler Wissensbasis"),
                (metadata.get("original_title"), 1.0, "knowledge_original", "Originaltitel aus lokaler Wissensbasis"),
            ]
            titles.extend((alias, 0.98, "knowledge_alias", f"Alias zu '{matched_value}' aus lokaler Wissensbasis") for alias in aliases)
            for value, score, source, reason in titles:
                if value:
                    expanded.append(SearchVariant(self._clean_title(str(value)), min(score, 1.0), source, (reason,), entity.get("media_type") or media_type))

        dedup: dict[str, SearchVariant] = {}
        rejected: list[dict[str, Any]] = []
        for item in expanded:
            key = self._variant_key(item.title)
            if not key:
                continue
            known = (
                item.source.startswith("knowledge_")
                or item.source == "identity_hint"
            )
            quality_source = (
                "ocr"
                if item.source == "ocr"
                else (
                    "fallback"
                    if "Fallback" in item.reasons
                    else item.source
                )
            )
            quality = evaluate_text(item.title, source=quality_source, known_alias=known)
            adjusted_score = item.score * (0.45 + 0.55 * quality.score)
            adjusted = SearchVariant(item.title, round(adjusted_score, 3), item.source, item.reasons, item.media_type, quality.score, quality.reasons)
            if len(key.split()) == 1:
                adjusted = SearchVariant(adjusted.title, round(adjusted.score * self._single_word_factor(key), 3), adjusted.source, adjusted.reasons + ("Einzelwort-Suche vorsichtig gewichtet",), adjusted.media_type, adjusted.quality_score, adjusted.quality_reasons)
            is_fallback = any("Fallback" in reason for reason in item.reasons)
            fallback_too_weak = is_fallback and not known and (len(key.split()) < 3 or quality.score < 0.82)
            if (not quality.accepted or fallback_too_weak) and not known:
                reasons = list(quality.reasons)
                if fallback_too_weak:
                    reasons.append("Gekürzte Fallback-Variante ohne Wissensbeleg gesperrt")
                rejected.append({"title": item.title, "source": item.source, "quality_score": quality.score, "reasons": reasons})
                continue
            previous = dedup.get(key)
            if previous is None or adjusted.score > previous.score:
                dedup[key] = adjusted

        variants = sorted(
            dedup.values(),
            key=lambda x: (
                x.score,
                x.quality_score,
                len(x.title),
            ),
            reverse=True,
        )[:20]

        primary_sources = (
            "identity_hint",
            "filename",
            "folder",
            "normalized_filename",
        )

        primary_variant = next(
            (
                item
                for source in primary_sources
                for item in variants
                if item.source == source
            ),
            variants[0] if variants else None,
        )

        return {
            "schema_version": 2,
            "primary_title": (
                primary_variant.title
                if primary_variant
                else str(
                    identification.get("title_candidate")
                    or ""
                )
            ),
            "variant_count": len(variants),
            "variants": [item.as_dict() for item in variants],
            "knowledge_matches": len(knowledge_matches),
            "strategy": "query_reasoner_2_quality_gate" if variants else "no_searchable_title",
            "quality_gate": {"schema_version": 1, "accepted": len(variants), "rejected": rejected[:20]},
        }

    @staticmethod
    def _append(target, value, score, source, reason):
        text = str(value or "").strip()
        if text:
            target.append((text, score, source, (reason,)))

    def _expand_candidate(self, value: str, score: float, source: str, reasons: tuple[str, ...], media_type: str | None) -> list[SearchVariant]:
        cleaned = self._clean_title(value)
        if not cleaned:
            return []
        variants = [SearchVariant(cleaned, round(score, 3), source, reasons, media_type)]
        split = self._split_compounds(cleaned)
        if self._variant_key(split) != self._variant_key(cleaned):
            variants.append(SearchVariant(split, round(score * 0.96, 3), source, reasons + ("Zusammengeklebte Wörter oder Zahlen getrennt",), media_type))
        tokens = split.split()
        if len(tokens) >= 3:
            for width in range(len(tokens) - 1, 1, -1):
                short = " ".join(tokens[:width])
                if len(self._variant_key(short).replace(" ", "")) >= 5:
                    variants.append(SearchVariant(short, round(score * 0.70, 3), source, reasons + ("Gekürzte Fallback-Variante",), media_type))
        for token in tokens:
            if len(self._variant_key(token)) >= 4 and not token.isdigit():
                variants.append(SearchVariant(token, round(score * 0.32, 3), source, reasons + ("Schwacher Einzelwort-Fallback",), media_type))
        return variants

    def _ocr_variants(self, analysis: dict[str, Any], media_type: str | None) -> list[SearchVariant]:
        findings = (((analysis.get("in_video") or {}).get("agents") or {}).get("ocr_agent") or {}).get("findings") or []
        result = []
        for finding in findings:
            text = str(finding.get("text") or "").strip()
            if 3 <= len(text) <= 100:
                cleaned = self._clean_title(text)

                narrative_time_patterns = (
                    r"^(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
                    r"eleven|twelve|several|many|a|an)\s+"
                    r"(?:second|seconds|minute|minutes|hour|hours|day|days|"
                    r"week|weeks|month|months|year|years)\s+"
                    r"(?:earlier|later|ago)$",
                    r"^(?:earlier|later)\s+that\s+"
                    r"(?:day|night|week|month|year)$",
                    r"^(?:the\s+)?(?:next|following|previous)\s+"
                    r"(?:day|night|morning|evening|week|month|year)$",
                    r"^(?:present\s+day|present\s+time)$",
                )

                narrative_time_card = any(
                    re.fullmatch(
                        pattern,
                        cleaned.casefold(),
                        flags=re.IGNORECASE,
                    )
                    is not None
                    for pattern in narrative_time_patterns
                )

                if narrative_time_card:
                    continue

                quality = evaluate_text(cleaned, source="ocr")
                if cleaned and quality.accepted:
                    result.append(SearchVariant(cleaned, round(0.68 * quality.score, 3), "ocr", ("OCR-Titelhinweis", "OCR-Qualitätsprüfung bestanden"), media_type, quality.score, quality.reasons))
        return result

    def _clean_title(self, value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value))
        text = re.sub(r"\.(mkv|mp4|avi|mov|m4v|ts|m2ts|webm|wmv|mpg|mpeg)$", "", text, flags=re.I)

        # Vom Dateisystem erzeugte Kopie-Suffixe gehören nicht
        # zur Medienidentität und dürfen keine Suchvariante erzeugen.
        text = re.sub(
            r"(?i)\s+-\s+(?:Kopie|Copy)(?:\s*\(\d+\))?$",
            "",
            text,
        ).strip()

        text = re.sub(
            r"(?i)\s+(?:Kopie|Copy)\s*\(\d+\)$",
            "",
            text,
        ).strip()
        text = re.sub(r"[\[({].*?[\])}]", " ", text)
        text = self.EPISODE_PATTERN.sub(" ", text)
        text = self.YEAR_PATTERN.sub(" ", text)
        text = re.sub(r"[._]+", " ", text)
        text = re.sub(r"\s+-\s+[A-Za-z0-9]{2,12}$", " ", text)
        tokens = []
        for token in self._normalize_spaces(text.replace("-", " ")).split():
            key = token.casefold().replace("-", "")
            if key in self.TECHNICAL_TOKENS or self.NOISE_PATTERN.match(token):
                continue
            tokens.append(token)
        return self._normalize_spaces(" ".join(tokens))

    @staticmethod
    def _split_compounds(value: str) -> str:
        text = re.sub(r"\b(NCIS|CSI|FBI|SG)(?=[A-Z]{2,}|\d)", r"\1 ", value, flags=re.I)
        text = re.sub(r"(?<=[a-zäöüß])(?=[A-ZÄÖÜ])", " ", text)
        text = re.sub(r"(?<=[A-Za-zÄÖÜäöüß])(?=\d)|(?<=\d)(?=[A-Za-zÄÖÜäöüß])", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _knowledge_matches(self, candidates: Iterable[str]) -> list[tuple[dict[str, Any], str]]:
        entities = self._load_entities()
        candidate_keys = {self._variant_key(x): x for x in candidates if self._variant_key(x)}
        result = []
        seen = set()
        for entity in entities:
            values = [entity.get("title"), *(entity.get("aliases") or [])]
            metadata = entity.get("metadata") or {}
            values += [metadata.get("german_title"), metadata.get("english_title"), metadata.get("original_title")]
            for value in values:
                key = self._variant_key(str(value or ""))
                if not key:
                    continue
                for candidate_key, original in candidate_keys.items():
                    if key == candidate_key or (len(candidate_key) >= 3 and candidate_key.replace(" ", "") == key.replace(" ", "")):
                        entity_id = str(entity.get("id") or entity.get("title"))
                        if entity_id not in seen:
                            result.append((entity, original)); seen.add(entity_id)
        return result

    def _load_entities(self) -> list[dict[str, Any]]:
        path = self.knowledge_database_path
        if path is None:
            return []
        graph = path.parent / "knowledge_graph" / "knowledge_graph.json" if path.suffix else path / "knowledge_graph" / "knowledge_graph.json"
        if graph.is_file():
            try:
                data = json.loads(graph.read_text(encoding="utf-8"))
                return [dict(x) for x in (data.get("entities") or {}).values() if isinstance(x, dict)]
            except (OSError, json.JSONDecodeError):
                pass
        if path.is_file():
            try:
                with sqlite3.connect(path) as db:
                    rows = db.execute("SELECT m.id,m.title,m.media_type,m.year,a.alias FROM media_items m LEFT JOIN aliases a ON a.media_item_id=m.id").fetchall()
                grouped: dict[Any, dict[str, Any]] = {}
                for item_id, title, media_type, year, alias in rows:
                    item = grouped.setdefault(item_id, {"id": str(item_id), "title": title, "media_type": media_type, "year": year, "aliases": []})
                    if alias: item["aliases"].append(alias)
                return list(grouped.values())
            except (sqlite3.Error, OSError):
                return []
        return []

    @staticmethod
    def _single_word_factor(key: str) -> float:
        return 0.28 if len(key) <= 4 else 0.45 if len(key) <= 7 else 0.58

    @staticmethod
    def _normalize_spaces(value: str) -> str:
        return re.sub(r"\s+", " ", str(value)).strip()

    @classmethod
    def _variant_key(cls, value: str) -> str:
        text = unicodedata.normalize("NFKD", str(value).casefold())
        text = "".join(c for c in text if not unicodedata.combining(c))
        return cls._normalize_spaces(re.sub(r"[^a-z0-9]+", " ", text))
