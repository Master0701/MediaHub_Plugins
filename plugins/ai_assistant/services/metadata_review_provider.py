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

    def __init__(self, batch_provider, media_analyzer=None):
        self.batch_provider = batch_provider
        self.media_analyzer = media_analyzer

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
    def _movie_filename_identity(
        cls,
        name: str,
    ) -> dict[str, Any]:
        """Extrahiert Film-Titel, Jahr und Edition aus Release-Dateinamen."""

        stem = Path(str(name or "")).stem

        normalized = (
            stem
            .replace("_", " ")
            .replace(".", " ")
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        ).strip()

        if not normalized:
            return {}

        # Seriennamen gehören weiterhin ausschließlich in den
        # bestehenden Serienparser.
        if cls.EPISODE_RE.search(normalized) or re.search(
            r"(?i)\bS\d{1,3}\s*E\d{1,3}\b",
            normalized,
        ):
            return {}

        tokens = [
            token
            for token in re.split(r"\s+", normalized)
            if token
        ]

        if (
            tokens
            and tokens[0].casefold()
            in cls.RELEASE_PREFIXES
        ):
            tokens = tokens[1:]

        if not tokens:
            return {}

        # Das letzte plausible Jahr verwenden. Dadurch wird z. B.
        # "2001 A Space Odyssey 1968" korrekt als Jahr 1968
        # behandelt und nicht als Jahr 2001.
        year_index = None
        year = None

        for index, token in enumerate(tokens):
            value = token.strip("()[]{}")

            if not re.fullmatch(
                r"(?:18|19|20|21)\d{2}",
                value,
            ):
                continue

            number = int(value)

            if 1888 <= number <= 2199:
                year_index = index
                year = number

        if year_index is None:
            return {}

        title_tokens = tokens[:year_index]

        while (
            title_tokens
            and title_tokens[-1].casefold()
            in cls.QUALITY_TOKENS
        ):
            title_tokens.pop()

        title = cls._smart_words(
            " ".join(title_tokens).strip(" -._")
        )

        if not title:
            return {}

        tail = " ".join(
            tokens[year_index + 1:]
        ).strip()

        tail_folded = tail.casefold()

        edition = ""

        edition_patterns = (
            (
                r"\bdirector(?:'s|s)?\s+cut\b",
                "Director's Cut",
            ),
            (
                r"\btheatrical\s+cut\b",
                "Theatrical Cut",
            ),
            (
                r"\bextended(?:\s+(?:cut|edition))?\b",
                "Extended",
            ),
            (
                r"\buncut\b",
                "Uncut",
            ),
            (
                r"\bunrated\b",
                "Unrated",
            ),
            (
                r"\bremaster(?:ed)?\b",
                "Remastered",
            ),
            (
                r"\bspecial\s+edition\b",
                "Special Edition",
            ),
            (
                r"\bcollector(?:'s|s)?\s+edition\b",
                "Collector's Edition",
            ),
            (
                r"\bfinal\s+cut\b",
                "Final Cut",
            ),
        )

        for pattern, label in edition_patterns:
            if re.search(pattern, tail_folded):
                edition = label
                break

        return {
            "media_type": "movie",
            "title": title,
            "year": year,
            "edition": edition or None,
            "source": "filename",
        }

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

    @staticmethod
    def _year_value(value: Any) -> int | None:
        if value in (None, "", 0):
            return None

        match = re.search(
            r"(?<!\d)(18\d{2}|19\d{2}|20\d{2}|21\d{2})(?!\d)",
            str(value),
        )
        if not match:
            return None

        return int(match.group(1))

    @staticmethod
    def _identity_text(value: Any) -> str:
        text = str(value or "").casefold()
        text = re.sub(r"[^a-z0-9äöüß]+", " ", text)
        return " ".join(text.split())

    @classmethod
    def _verification_conflicts(
        cls,
        item: dict[str, Any],
        identity: dict[str, Any],
    ) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []

        current_year = cls._year_value(
            item.get("year")
            or item.get("release_year")
        )
        verified_year = cls._year_value(
            identity.get("year")
        )

        if (
            current_year is not None
            and verified_year is not None
            and current_year != verified_year
        ):
            conflicts.append(
                {
                    "field": "year",
                    "metadata": current_year,
                    "verified": verified_year,
                }
            )

        current_type = cls._clean(
            item.get("media_type")
        ).casefold()
        verified_type = cls._clean(
            identity.get("media_type")
        ).casefold()

        aliases = {
            "film": "movie",
            "movie": "movie",
            "serie": "series",
            "series": "series",
            "episode": "series",
            "tv": "series",
        }

        current_type = aliases.get(
            current_type,
            current_type,
        )
        verified_type = aliases.get(
            verified_type,
            verified_type,
        )

        if (
            current_type
            and verified_type
            and current_type != verified_type
        ):
            conflicts.append(
                {
                    "field": "media_type",
                    "metadata": current_type,
                    "verified": verified_type,
                }
            )

        current_title = cls._identity_text(
            item.get("title")
        )
        verified_title = cls._identity_text(
            identity.get("title")
        )

        if current_title and verified_title:
            same_identity = (
                current_title == verified_title
                or current_title in verified_title
                or verified_title in current_title
            )

            if not same_identity:
                conflicts.append(
                    {
                        "field": "title",
                        "metadata": item.get("title"),
                        "verified": identity.get("title"),
                    }
                )

        return conflicts

    @staticmethod
    def _verified_identity_is_trustworthy(
        identity: dict[str, Any],
    ) -> bool:
        if not identity:
            return False

        try:
            confidence = float(
                identity.get("confidence") or 0.0
            )
        except (TypeError, ValueError):
            confidence = 0.0

        status = str(
            identity.get("status") or ""
        ).strip().casefold()

        # Schwache oder unklare Identitäten dürfen bestehende
        # Dateiname-/Metadaten-Kandidaten nicht überschreiben.
        if confidence < 0.62:
            return False

        if status in {
            "insufficient",
            "unknown",
            "conflict",
        }:
            return False

        return True

    @staticmethod
    def _analysis_identity(
        analysis: dict[str, Any],
    ) -> dict[str, Any]:
        integration = dict(
            analysis.get("integration") or {}
        )
        identity = dict(
            integration.get("identity") or {}
        )

        if identity:
            return identity

        semantic = dict(
            analysis.get("semantic_identity") or {}
        )
        identity = dict(
            semantic.get("identity") or {}
        )

        if identity:
            return identity

        decision = dict(
            analysis.get("decision") or {}
        )
        identification = dict(
            analysis.get("identification") or {}
        )

        return {
            "media_type": (
                decision.get("media_type")
                or identification.get("media_type")
            ),
            "title": (
                decision.get("title_candidate")
                or identification.get("title_candidate")
            ),
            "year": identification.get("year"),
            "season": decision.get("season"),
            "episodes": decision.get("episodes") or [],
            "edition": identification.get(
                "edition_candidate"
            ),
            "confidence": decision.get(
                "confidence"
            ),
            "status": decision.get("status"),
        }

    def _verified_media_analysis(
        self,
        item: dict[str, Any],
        path: str,
        identity_hint: dict[str, Any] | None = None,
    ) -> tuple[
        dict[str, Any],
        dict[str, Any],
        list[dict[str, Any]],
        list[str],
    ]:
        analyzer = self.media_analyzer

        if analyzer is None or not path:
            return {}, {}, [], []

        media_path = Path(path)

        if not media_path.is_file():
            return {}, {}, [], []

        warnings: list[str] = []

        try:
            analysis = dict(
                analyzer.analyze(
                    media_path,
                    identity_hint=identity_hint,
                )
                or {}
            )
        except Exception as exc:  # noqa: BLE001 - Analyse-Provider-Grenze
            return (
                {},
                {},
                [],
                [
                    (
                        "MediaAnalyzer-Verifikation "
                        f"fehlgeschlagen: {exc}"
                    )
                ],
            )

        identity = self._analysis_identity(
            analysis
        )
        conflicts = self._verification_conflicts(
            item,
            identity,
        )

        in_video = dict(
            analysis.get("in_video") or {}
        )

        # Bestehende Metadaten sind nur Evidenz.
        # Widersprechen sie der ermittelten Identität,
        # wird die vorhandene In-Video-Pipeline bewusst
        # als zusätzliche Beweisquelle erzwungen.
        if (
            conflicts
            and in_video.get("state") != "completed"
        ):
            try:
                analysis = dict(
                    analyzer.analyze(
                        media_path,
                        force=True,
                        require_in_video=True,
                        identity_hint=identity_hint,
                    )
                    or {}
                )
                identity = self._analysis_identity(
                    analysis
                )
                conflicts = self._verification_conflicts(
                    item,
                    identity,
                )
            except Exception as exc:  # noqa: BLE001 - Analyse-Provider-Grenze
                warnings.append(
                    "Erzwungene In-Video-Verifikation "
                    f"fehlgeschlagen: {exc}"
                )

        return analysis, identity, conflicts, warnings

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
        movie_identity = self._movie_filename_identity(
            original_name
        )

        # Eine Fassung kann bereits in vorhandenen Metadaten stehen,
        # obwohl der echte Dateiname sie nicht enthält.
        #
        # Beispiel:
        # Datei:
        #   12.Monkeys.1995.GERMAN.1040p.microHD.x264-Raistlin911.mkv
        #
        # vorhandener Metadatentitel:
        #   12 Monkeys 1995 Remastered 1080p ...
        #
        # Diese Information ist lokale Evidenz und kein Online-Beweis.
        metadata_title_identity = self._movie_filename_identity(
            self._clean(item.get("title"))
        )

        metadata_edition = self._clean(
            metadata_title_identity.get("edition")
        )

        (
            verified_analysis,
            verified_identity,
            verification_conflicts,
            verification_warnings,
        ) = self._verified_media_analysis(
            item,
            path,
            identity_hint=movie_identity,
        )

        verified_identity_trusted = (
            self._verified_identity_is_trustworthy(
                verified_identity
            )
        )

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
            (
                verified_identity.get("media_type")
                if verified_identity_trusted
                else None
            )
            or movie_identity.get("media_type")
            or result.get("media_type")
            or sf.get("media_type")
            or item.get("media_type")
            or (
                "series"
                if identity.get("season") is not None
                else ""
            )
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
            title = self._clean(
                (
                    verified_identity.get("title")
                    if verified_identity_trusted
                    else None
                )
                or movie_identity.get("title")
                or sf.get("title")
                or item.get("title")
                or Path(original_name).stem
            )
            if title:
                fields["title"] = title

        if media_type == "movie":
            year = (
                (
                    verified_identity.get("year")
                    if verified_identity_trusted
                    else None
                )
                or movie_identity.get("year")
                or sf.get("year")
                or item.get("year")
            )
        else:
            year = (
                sf.get("year")
                or item.get("year")
                or verified_identity.get("year")
            )

        if year not in (None, "", 0):
            fields["year"] = year

        if media_type == "movie":
            edition = self._clean(
                (
                    verified_identity.get("edition")
                    if verified_identity_trusted
                    else None
                )
                or movie_identity.get("edition")
                or metadata_edition
                or sf.get("edition")
                or item.get("edition")
            )

            if edition:
                fields["edition"] = edition

        # Beschreibung/Overview dürfen weiterhin aus vorhandenen
        # Metadaten stammen. published_at dagegen wird bewusst nicht
        # ungeprüft übernommen: Container- oder Dateizeitstempel sind
        # kein verlässliches Veröffentlichungsdatum.
        for key in ("description", "overview"):
            value = self._clean(sf.get(key) or item.get(key))
            if value:
                fields[key] = value

        episode_online = dict(
            result.get("episode_title_online") or {}
        )

        analyzer_online = dict(
            verified_analysis.get("online") or {}
        )

        poster_url = (
            self._poster_candidate(episode_online)
            or self._poster_candidate(analyzer_online)
        )

        online_details = self._online_metadata_details(
            {
                "episode": episode_online,
                "media_analysis": analyzer_online,
            }
        )

        if (
            not fields.get("description")
            and online_details.get("description")
        ):
            fields["description"] = online_details["description"]

        # Ein Veröffentlichungsdatum wird nur als KI-Vorschlag
        # ausgegeben, wenn dafür echte Online-Evidenz vorhanden ist.
        verified_published_at = self._clean(
            online_details.get("published_at")
        )
        if verified_published_at:
            fields["published_at"] = verified_published_at

        sources = list(
            episode_online.get("sources") or []
        )

        for source_name in (
            analyzer_online.get("sources") or []
        ):
            if source_name not in sources:
                sources.append(source_name)
        episode_source = self._clean(result.get("episode_title_source"))
        if episode_source and episode_source not in sources:
            sources.append(episode_source)

        verified_confidence = (
            verified_identity.get("confidence")
            if verified_identity_trusted
            else None
        )

        confidence_source = (
            verified_confidence
            if verified_confidence not in (None, "")
            else (
                result.get("confidence")
                or structured.get("confidence")
                or 0.0
            )
        )

        try:
            confidence = max(
                0.0,
                min(
                    1.0,
                    float(confidence_source),
                ),
            )
        except (TypeError, ValueError):
            confidence = 0.0

        # Ein Konflikt ist nicht mehr offen, wenn die verifizierte
        # Medienidentität für dieses Feld bereits einen eindeutigen Wert
        # geliefert hat. Der alte Metadatenwert darf dann nicht weiter
        # Confidence und Benutzerwarnungen belasten.
        resolved_conflicts: list[dict[str, Any]] = []
        open_conflicts: list[dict[str, Any]] = []

        for conflict in verification_conflicts:
            field = self._clean(conflict.get("field"))

            if (
                field
                and field in verified_identity
                and verified_identity.get(field) not in (None, "")
            ):
                resolved_conflicts.append(conflict)
            else:
                open_conflicts.append(conflict)

        verification_conflicts = open_conflicts

        if verification_conflicts:
            confidence = min(confidence, 0.74)

        current = {
            key: item.get(key)
            for key in (
                "media_type", "title", "series", "season", "episode",
                "year", "edition", "description", "published_at",
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
            "rationale": (
                "MediaHub-KI-Medienanalyse hat Dateiname, "
                "technische Daten, verfügbare Quellen und "
                "bei Widersprüchen die In-Video-Erkennung "
                "gemeinsam bewertet."
                if verified_analysis
                else self._clean(result.get("rationale"))
            ),
            "warnings": (
                list(result.get("warnings") or [])
                + verification_warnings
                + [
                    (
                        "Metadaten-Widerspruch: "
                        f"{conflict['field']} "
                        f"{conflict['metadata']!r} → "
                        f"{conflict['verified']!r}"
                    )
                    for conflict in verification_conflicts
                ]
            ),
            "verification": {
                "used": bool(verified_analysis),
                "conflicts": verification_conflicts,
                "in_video_state": str(
                    (
                        verified_analysis.get("in_video")
                        or {}
                    ).get("state")
                    or ""
                ),
                "methods_used": list(
                    verified_analysis.get(
                        "methods_used"
                    )
                    or []
                ),
            },
            "execution_allowed": False,
            "metadata_write_allowed": False,
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
        }
