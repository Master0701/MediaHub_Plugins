from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class MetadataAIReviewProvider:
    """Read-only structured metadata suggestion using existing AI intelligence."""

    EPISODE_RE = re.compile(
        r"(?i)(?:^|[\s._-])S\s*(?P<season>\d{1,3})\s*E\s*(?P<episode>\d{1,3})(?:$|[\s._-])"
    )

    RELEASE_PREFIXES = {"lim", "rsg", "grp", "release"}

    QUALITY_TOKENS = {
        "sd", "hd", "uhd", "480p", "576p", "720p", "1080p", "2160p",
        "4k", "x264", "x265", "h264", "h265", "hevc", "web", "webdl",
        "web-dl", "bluray", "bdrip", "dvdrip", "hdtv",
    }

    def __init__(self, batch_provider):
        self.batch_provider = batch_provider

    @staticmethod
    def _clean(value: Any) -> str:
        return " ".join(str(value or "").strip().split())

    @staticmethod
    def _smart_words(value: str) -> str:
        words = []
        for word in str(value or "").split():
            if not word:
                continue
            if word.isupper() and len(word) <= 4:
                words.append(word)
            elif word.isdigit():
                words.append(word)
            else:
                words.append(word[0].upper() + word[1:])
        return " ".join(words)

    @classmethod
    def _filename_identity(cls, name: str) -> dict[str, Any]:
        stem = Path(str(name or "")).stem
        normalized = stem.replace("_", " ").replace(".", " ")
        normalized = re.sub(r"\s+", " ", normalized).strip()

        match = cls.EPISODE_RE.search(normalized)
        if not match:
            match = re.search(
                r"(?i)S(?P<season>\d{1,3})E(?P<episode>\d{1,3})",
                normalized,
            )

        season = episode = None
        if match:
            season = int(match.group("season"))
            episode = int(match.group("episode"))
            left = normalized[:match.start()].strip(" -._")
        else:
            left = normalized

        left = re.sub(r"\s*-\s*", " ", left)
        tokens = [token for token in re.split(r"\s+", left) if token]

        if tokens and tokens[0].casefold() in cls.RELEASE_PREFIXES:
            tokens = tokens[1:]

        while tokens and tokens[-1].casefold() in cls.QUALITY_TOKENS:
            tokens.pop()

        series = cls._smart_words(" ".join(tokens).strip())
        return {"series": series, "season": season, "episode": episode}

    @classmethod
    def _episode_from_name(cls, name: str):
        identity = cls._filename_identity(name)
        return identity.get("season"), identity.get("episode")

    @classmethod
    def _series_title_from_name(cls, name: str) -> str:
        return str(cls._filename_identity(name).get("series") or "")

    @classmethod
    def _online_metadata_details(cls, online):
        """Extrahiert Beschreibung und Veröffentlichungsdatum aus Online-Evidenz."""
        description_keys = (
            "overview",
            "description",
            "summary",
            "shortDescription",
            "short_description",
            "plot",
        )
        date_keys = (
            "air_date",
            "aired",
            "airDate",
            "firstAired",
            "first_air_time",
            "release_date",
            "published_at",
            "date",
        )

        description = ""
        published_at = ""

        def walk(node):
            nonlocal description, published_at

            if isinstance(node, dict):
                if not description:
                    for key in description_keys:
                        value = node.get(key)
                        if value not in (None, ""):
                            text = str(value).strip()
                            if text:
                                description = text
                                break

                if not published_at:
                    for key in date_keys:
                        value = node.get(key)
                        if value not in (None, ""):
                            text = str(value).strip()
                            if text:
                                published_at = text
                                break

                if description and published_at:
                    return

                for value in node.values():
                    walk(value)
                    if description and published_at:
                        return

            elif isinstance(node, (list, tuple)):
                for value in node:
                    walk(value)
                    if description and published_at:
                        return

        walk(online or {})
        return {
            "description": description,
            "published_at": published_at,
        }

    @classmethod
    def _poster_candidate(cls, online):
        """Findet nur einen Bildvorschlag; verändert keine lokale Datei."""
        keys = {
            "poster_url",
            "poster",
            "image_url",
            "image",
            "thumbnail",
            "thumbnail_url",
        }

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if str(key).casefold() in keys:
                        text = str(value or "").strip()
                        if text.startswith(("https://", "http://")):
                            return text
                    found = walk(value)
                    if found:
                        return found
            elif isinstance(node, (list, tuple)):
                for value in node:
                    found = walk(value)
                    if found:
                        return found
            return ""

        return walk(online or {})

    def analyze(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        source = dict(payload or {})
        item = dict(source.get("item") or source.get("metadata") or {})
        path = self._clean(source.get("path") or item.get("path") or item.get("file_path"))
        original_name = self._clean(
            item.get("filename")
            or item.get("original_name")
            or (Path(path).name if path else "")
            or item.get("title")
        )

        identity = self._filename_identity(original_name)

        metadata_series_raw = self._clean(
            item.get("series")
            or item.get("series_title")
            or item.get("show")
            or item.get("show_title")
        )

        # Existing metadata may itself contain a release-style filename such as
        # "Rsg-12-monkeys-s 01 E 07-sd". Never trust it as a clean series title.
        metadata_series_identity = (
            self._filename_identity(metadata_series_raw)
            if metadata_series_raw
            else {}
        )
        metadata_series = self._clean(
            metadata_series_identity.get("series")
            or metadata_series_raw
        )

        series_candidate = metadata_series or identity.get("series") or ""

        season_candidate = (
            item.get("season")
            if item.get("season") not in (None, "")
            else identity.get("season")
        )
        episode_candidate = (
            item.get("episode")
            if item.get("episode") not in (None, "")
            else identity.get("episode")
        )

        batch_item = {
            **item,
            "source_path": path,
            "original_name": original_name,
            "metadata_read": source.get("metadata_read") or item.get("metadata_read") or {},
            "metadata_review": source.get("metadata_review") or item.get("metadata_review") or {},
        }

        if series_candidate:
            batch_item["series"] = series_candidate
            batch_item["series_title"] = series_candidate
        if season_candidate not in (None, ""):
            batch_item["season"] = season_candidate
        if episode_candidate not in (None, ""):
            batch_item["episode"] = episode_candidate

        reference = dict(source.get("reference") or {})
        if (
            not reference
            and series_candidate
            and season_candidate not in (None, "")
            and episode_candidate not in (None, "")
        ):
            reference = {
                "media_type": "series",
                "proposed_name": (
                    f"{series_candidate} - "
                    f"S{int(season_candidate):02d}E{int(episode_candidate):02d}"
                    f"{Path(original_name).suffix}"
                ),
                "original_name": original_name,
            }

        batch = self.batch_provider.analyze({
            "items": [batch_item],
            "reference": reference,
        })
        result = dict((batch.get("items") or [{}])[0] or {})
        structured = dict(result.get("structured_recommendation") or {})
        sf = dict(structured.get("fields") or {})

        suggested_name = self._clean(result.get("suggested_name"))
        media_type = self._clean(
            result.get("media_type")
            or sf.get("media_type")
            or item.get("media_type")
            or ("series" if identity.get("season") is not None else "")
        )

        fields: dict[str, Any] = {}
        if media_type:
            fields["media_type"] = media_type

        if media_type == "series":
            series = self._clean(
                sf.get("series")
                or sf.get("series_title")
                or series_candidate
                or self._series_title_from_name(suggested_name)
            )
            season, episode = self._episode_from_name(suggested_name)

            if series:
                fields["series"] = series

            resolved_season = season if season is not None else season_candidate
            resolved_episode = episode if episode is not None else episode_candidate

            if resolved_season not in (None, ""):
                fields["season"] = int(resolved_season)
            if resolved_episode not in (None, ""):
                fields["episode"] = int(resolved_episode)

            episode_title = self._clean(result.get("episode_title"))
            if episode_title:
                fields["title"] = episode_title
                fields["episode_title"] = episode_title
        else:
            title = self._clean(sf.get("title") or item.get("title") or Path(original_name).stem)
            if title:
                fields["title"] = title

        year = sf.get("year") or item.get("year")
        if year not in (None, "", 0):
            fields["year"] = year

        for key in ("description", "overview", "published_at"):
            value = self._clean(sf.get(key) or item.get(key))
            if value:
                fields[key] = value

        online = dict(result.get("episode_title_online") or {})
        poster_url = self._poster_candidate(online)
        online_details = self._online_metadata_details(online)

        if (
            not fields.get("description")
            and online_details.get("description")
        ):
            fields["description"] = online_details["description"]

        if (
            not fields.get("published_at")
            and online_details.get("published_at")
        ):
            fields["published_at"] = online_details["published_at"]

        sources = list(online.get("sources") or [])
        episode_source = self._clean(result.get("episode_title_source"))
        if episode_source and episode_source not in sources:
            sources.append(episode_source)

        confidence = max(
            0.0,
            min(
                1.0,
                float(
                    result.get("confidence")
                    or structured.get("confidence")
                    or 0.0
                ),
            ),
        )

        current = {
            key: item.get(key)
            for key in (
                "media_type", "title", "series", "season", "episode",
                "year", "description", "published_at",
            )
        }

        changes = {
            key: {"old": current.get(key), "new": value}
            for key, value in fields.items()
            if str(current.get(key) or "").strip() != str(value or "").strip()
        }

        return {
            "available": True,
            "provider": "MediaHub KI-Assistent",
            "capability": "ai.metadata_review",
            "fields": fields,
            "changes": changes,
            "suggested_name": suggested_name,
            "confidence": confidence,
            "sources": sources,
            "poster_url": poster_url,
            "rationale": self._clean(result.get("rationale")),
            "warnings": list(result.get("warnings") or []),
            "execution_allowed": False,
            "metadata_write_allowed": False,
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
        }
