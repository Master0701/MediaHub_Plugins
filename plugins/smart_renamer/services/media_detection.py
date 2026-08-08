from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = frozenset({
    ".mkv", ".mp4", ".m4v", ".avi", ".mov", ".wmv", ".ts", ".m2ts",
    ".webm", ".mpg", ".mpeg",
})
AUDIO_EXTENSIONS = frozenset({
    ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus", ".wav", ".wma",
})
AUDIOBOOK_EXTENSIONS = frozenset({".m4b", ".aa", ".aax"})

TECHNICAL_TOKENS = re.compile(
    r"""(?ix)
    \b(
        2160p|1080p|1080i|720p|576p|480p|
        uhd|hdr10\+?|hdr|dolby[ ._-]?vision|dv|
        bluray|blu[ ._-]?ray|bdrip|brrip|webrip|web[ ._-]?dl|hdtv|dvdrip|
        remux|x264|x265|h\.?264|h\.?265|hevc|av1|
        aac|ac3|eac3|dts(?:-hd)?|truehd|atmos|
        proper|repack
    )\b
    """
)

EDITION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Director's Cut", re.compile(r"(?i)\bdirector'?s[ ._-]*cut\b")),
    ("Extended Cut", re.compile(r"(?i)\bextended(?:[ ._-]*(?:cut|edition|version))?\b")),
    ("Theatrical Cut", re.compile(r"(?i)\btheatrical(?:[ ._-]*(?:cut|edition|version))?\b")),
    ("Uncut", re.compile(r"(?i)\buncut\b")),
    ("Remastered", re.compile(r"(?i)\bremaster(?:ed)?\b")),
    ("Special Edition", re.compile(r"(?i)\bspecial[ ._-]*edition\b")),
    ("Ultimate Edition", re.compile(r"(?i)\bultimate[ ._-]*edition\b")),
    ("Collector's Edition", re.compile(r"(?i)\bcollector'?s[ ._-]*edition\b")),
)

SERIES_PATTERNS = (
    re.compile(
        r"(?ix)\bS(?P<season>\d{1,3})[ ._-]*E(?P<episode>\d{1,4})\b"
    ),
    re.compile(
        r"(?ix)\b(?P<season>\d{1,3})x(?P<episode>\d{1,4})\b"
    ),
    re.compile(
        r"(?ix)\bStaffel[ ._-]*(?P<season>\d{1,3})"
        r".{0,20}?(?:Folge|Episode)[ ._-]*(?P<episode>\d{1,4})\b"
    ),
)

YEAR_PATTERN = re.compile(r"(?<!\d)(?P<year>(?:19|20)\d{2})(?!\d)")
TRACK_PATTERN = re.compile(r"(?i)^\s*(?P<track>\d{1,3})\s*[-._ ]+\s*(?P<title>.+)$")
AUDIOBOOK_HINT = re.compile(
    r"(?i)\b(h[oö]rbuch|audiobook|kapitel|chapter|teil\s*\d+)\b"
)


@dataclass(frozen=True, slots=True)
class DetectionResult:
    media_type: str = "unknown"
    title: str = ""
    year: str = ""
    season: str = ""
    episode: str = ""
    episode_title: str = ""
    edition: str = ""
    confidence: float = 0.0
    evidence: tuple[str, ...] = ()
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "media_type": self.media_type,
            "title": self.title,
            "year": self.year,
            "season": self.season,
            "episode": self.episode,
            "episode_title": self.episode_title,
            "edition": self.edition,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "extra": dict(self.extra),
        }


class MediaDetector:
    """Konservative lokale Erkennung nur aus Pfad, Name und Dateiendung."""

    def detect(self, path: Path) -> DetectionResult:
        path = Path(path)
        suffix = path.suffix.casefold()
        stem = path.stem
        normalized = self._normalize(stem)
        evidence: list[str] = []

        edition = self._detect_edition(stem)
        if edition:
            evidence.append(f"edition:{edition}")

        series = self._detect_series(normalized)
        if series is not None:
            season, episode, match = series
            title, episode_title = self._series_titles(normalized, match)
            year = self._detect_year(normalized)
            evidence.extend(("series_pattern", f"season:{season}", f"episode:{episode}"))
            if year:
                evidence.append(f"year:{year}")
            return DetectionResult(
                media_type="series",
                title=title or self._fallback_title(normalized),
                year=year,
                season=season.zfill(2),
                episode=episode.zfill(2),
                episode_title=episode_title,
                edition=edition,
                confidence=0.96,
                evidence=tuple(evidence),
            )

        if suffix in AUDIOBOOK_EXTENSIONS:
            evidence.append(f"audiobook_extension:{suffix}")
            return DetectionResult(
                media_type="audiobook",
                title=self._clean_title(normalized),
                edition=edition,
                confidence=0.98,
                evidence=tuple(evidence),
            )

        if suffix in AUDIO_EXTENSIONS:
            if AUDIOBOOK_HINT.search(normalized) or AUDIOBOOK_HINT.search(str(path.parent)):
                evidence.append("audiobook_hint")
                return DetectionResult(
                    media_type="audiobook",
                    title=self._clean_audio_title(normalized),
                    edition=edition,
                    confidence=0.86,
                    evidence=tuple(evidence),
                )

            track = TRACK_PATTERN.match(normalized)
            if track:
                evidence.append("numbered_audio_track")
                return DetectionResult(
                    media_type="music",
                    title=self._clean_title(track.group("title")),
                    edition=edition,
                    confidence=0.72,
                    evidence=tuple(evidence),
                    extra={"track": track.group("track").zfill(2)},
                )

            evidence.append(f"audio_extension:{suffix}")
            return DetectionResult(
                media_type="music",
                title=self._clean_audio_title(normalized),
                edition=edition,
                confidence=0.55,
                evidence=tuple(evidence),
            )

        year = self._detect_year(normalized)
        if suffix in VIDEO_EXTENSIONS:
            evidence.append(f"video_extension:{suffix}")
            if year:
                evidence.append(f"year:{year}")
            title = self._movie_title(normalized, year)
            return DetectionResult(
                media_type="movie",
                title=title or self._fallback_title(normalized),
                year=year,
                edition=edition,
                confidence=0.82 if year else 0.62,
                evidence=tuple(evidence),
            )

        if year:
            evidence.append(f"year:{year}")

        return DetectionResult(
            media_type="unknown",
            title=self._clean_title(normalized),
            year=year,
            edition=edition,
            confidence=0.25 if year else 0.10,
            evidence=tuple(evidence),
        )

    @staticmethod
    def _normalize(value: str) -> str:
        text = value.replace("_", " ").replace(".", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _detect_year(value: str) -> str:
        matches = list(YEAR_PATTERN.finditer(value))
        return matches[-1].group("year") if matches else ""

    @staticmethod
    def _detect_edition(value: str) -> str:
        for label, pattern in EDITION_PATTERNS:
            if pattern.search(value):
                return label
        return ""

    @staticmethod
    def _detect_series(value: str):
        for pattern in SERIES_PATTERNS:
            match = pattern.search(value)
            if match:
                return match.group("season"), match.group("episode"), match
        return None

    def _series_titles(self, value: str, match: re.Match[str]) -> tuple[str, str]:
        left = value[:match.start()].strip(" -._")
        right = value[match.end():].strip(" -._")
        title = self._clean_title(left)
        episode_title = self._clean_title(right)
        return title, episode_title

    def _movie_title(self, value: str, year: str) -> str:
        text = value
        if year:
            text = re.sub(
                rf"(?<!\d){re.escape(year)}(?!\d).*?$",
                "",
                text,
                count=1,
            )
        return self._clean_title(text)

    def _clean_audio_title(self, value: str) -> str:
        text = AUDIOBOOK_HINT.sub(" ", value)
        text = re.sub(r"(?i)\b(?:cd|disc|disk)\s*\d+\b", " ", text)
        return self._clean_title(text)

    def _clean_title(self, value: str) -> str:
        text = TECHNICAL_TOKENS.sub(" ", value)
        for _, pattern in EDITION_PATTERNS:
            text = pattern.sub(" ", text)
        text = re.sub(r"[\[\](){}]+", " ", text)
        text = re.sub(r"\s*[-–—]\s*$", "", text)
        text = re.sub(r"\s+", " ", text).strip(" -._")
        return text

    @staticmethod
    def _fallback_title(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" -._")
