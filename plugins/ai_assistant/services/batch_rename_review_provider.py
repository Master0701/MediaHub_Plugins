from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class BatchRenameReviewProvider:
    EPISODE_TITLE_PLACEHOLDERS = {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "unbekannt",
        "untitled",
        "ohne titel",
        "kein titel",
        "nicht bekannt",
        "not available",
    }

    @classmethod
    def _is_placeholder_episode_title(cls, value):
        normalized = " ".join(str(value or "").strip().casefold().split())
        return normalized in cls.EPISODE_TITLE_PLACEHOLDERS


    """Read-only KI batch review with real reference/schema interpretation."""

    _EPISODE_RE = re.compile(
        r"(?i)(?:^|[\s._-])s(?P<season>\d{1,3})e(?P<episode>\d{1,3})(?:e(?P<episode_end>\d{1,3}))?"
    )
    _YEAR_RE = re.compile(r"(?<!\d)(?P<year>(?:19|20)\d{2})(?!\d)")
    _TECH_RE = re.compile(
        r"(?i)\b(?:"
        r"\d{3,4}p|4k|8k|uhd|hdr10\+?|dolby[ ._-]?vision|dv|"
        r"x26[45]|h26[45]|hevc|avc|av1|web[ ._-]?dl|webrip|bluray|brrip|"
        r"dvdrip|remux|proper|repack|aac|ac3|eac3|dts(?:-hd)?|atmos|"
        r"10bit|8bit|multi|german|deutsch|english|eng|ger|sd"
        r")\b"
    )
    _SEP_RE = re.compile(r"[\s._-]+")
    _TRAILING_SEPARATOR_RE = re.compile(r"(?:\s*[-–—:|]\s*)+$")

    def __init__(self, single_provider, episode_title_resolver=None):
        self.single_provider = single_provider
        self.episode_title_resolver = episode_title_resolver

    def set_episode_title_resolver(self, resolver):
        self.episode_title_resolver = resolver

    @classmethod
    def _episode_info(cls, item):
        values = [
            str(item.get("original_name") or ""),
            str(item.get("source_path") or ""),
            str(item.get("proposed_name") or ""),
        ]
        for value in values:
            match = cls._EPISODE_RE.search(Path(value).stem)
            if match:
                return {
                    "season": int(match.group("season")),
                    "episode": int(match.group("episode")),
                    "episode_end": (
                        int(match.group("episode_end"))
                        if match.group("episode_end")
                        else None
                    ),
                }

        season = cls._int_or_none(item.get("season"))
        episode = cls._int_or_none(item.get("episode"))
        if season is not None and episode is not None:
            return {"season": season, "episode": episode, "episode_end": None}
        return {}

    @staticmethod
    def _int_or_none(value):
        try:
            if value in (None, ""):
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _deep_values(value, keys):
        wanted={str(k).casefold() for k in keys}
        found=[]
        def walk(node):
            if isinstance(node, dict):
                for key,item in node.items():
                    if str(key).casefold() in wanted and item not in (None,"",[],{}):
                        found.append(item)
                    walk(item)
            elif isinstance(node, (list,tuple)):
                for item in node:
                    walk(item)
        walk(value)
        return found

    @classmethod
    def _first_metadata_value(cls, item, *keys):
        for source_key in ("metadata_review","metadata_read"):
            source=item.get(source_key)
            for value in cls._deep_values(source, keys):
                if isinstance(value, (str,int,float)):
                    text=str(value).strip()
                    if text:
                        return text
        return ""

    @classmethod
    def _media_type(cls, item):
        explicit=str(
            item.get("media_type")
            or (item.get("renamer") or {}).get("media_type")
            or ""
        ).strip().lower()

        if explicit in {"series","serie","episode","tv"}:
            return "series"
        if explicit in {"movie","film"}:
            return "movie"
        if explicit in {"audiobook","hörbuch","hoerbuch"}:
            return "audiobook"

        if cls._episode_info(item):
            return "series"

        metadata_type=cls._first_metadata_value(
            item,"media_type","mediatype","type","content_type"
        ).lower()
        if metadata_type in {"series","serie","episode","tv","tvshow"}:
            return "series"
        if metadata_type in {"movie","film"}:
            return "movie"

        # A year without episode markers is useful evidence for a movie,
        # but not strong enough when nothing else exists.
        stem=Path(str(item.get("original_name") or item.get("source_path") or "")).stem
        if cls._YEAR_RE.search(stem):
            return "movie"
        return "unknown"

    @classmethod
    def _clean_words(cls, text):
        text=cls._TECH_RE.sub(" ",str(text or ""))
        text=cls._EPISODE_RE.sub(" ",text)
        text=cls._YEAR_RE.sub(" ",text)
        text=cls._SEP_RE.sub(" ",text)
        return " ".join(text.split()).strip()

    @staticmethod
    def _smart_title(text):
        normalized=str(text or "")
        normalized=re.sub(r"(?<=\d)(?=[A-Za-zÄÖÜäöüß])", " ", normalized)
        normalized=re.sub(r"(?<=[A-Za-zÄÖÜäöüß])(?=\d)", " ", normalized)
        words=[]
        for word in normalized.split():
            if word.isupper() and len(word) <= 4:
                words.append(word)
            elif word.isdigit():
                words.append(word)
            else:
                words.append(word[:1].upper()+word[1:])
        return " ".join(words).strip()

    @classmethod
    def _reference_series_title(cls, reference):
        proposed=Path(str(
            reference.get("proposed_name")
            or reference.get("original_name")
            or ""
        )).stem
        match=cls._EPISODE_RE.search(proposed)
        if match:
            left=proposed[:match.start()]
            left=cls._TRAILING_SEPARATOR_RE.sub("",left).strip(" ._-")
            cleaned=cls._clean_words(left)
            if cleaned:
                return cls._smart_title(cleaned)

        for key in ("series","title"):
            value=str(reference.get(key) or "").strip()
            if value:
                return cls._smart_title(value)
        return ""

    @classmethod
    def _reference_episode_title(cls, reference):
        proposed=Path(str(reference.get("proposed_name") or "")).stem
        match=cls._EPISODE_RE.search(proposed)
        if not match:
            return ""
        tail=proposed[match.end():]
        tail=tail.strip(" ._-–—:|")
        return cls._clean_words(tail)

    @classmethod
    def _series_title(cls, item, reference):
        # Metadata is strongest when available.
        metadata=cls._first_metadata_value(
            item,"series","series_title","show","show_title","tvshow","album"
        )
        if metadata:
            return cls._smart_title(metadata)

        ref_title=cls._reference_series_title(reference) if reference else ""
        raw=Path(str(item.get("original_name") or item.get("source_path") or "")).stem

        if ref_title:
            normalized_raw=re.sub(r"[^a-z0-9]+","",raw.casefold())
            normalized_ref=re.sub(r"[^a-z0-9]+","",ref_title.casefold())
            # Reference spelling is preferred when the same title can be
            # recognized in the target's noisy filename.
            if normalized_ref and normalized_ref in normalized_raw:
                return ref_title

        for key in ("series","title"):
            value=str(item.get(key) or "").strip()
            if value and value.lower() not in {"unknown","unbekannt"}:
                return cls._smart_title(value)

        match=cls._EPISODE_RE.search(raw)
        prefix=raw[:match.start()] if match else raw
        prefix=cls._clean_words(prefix)
        # Remove common release prefixes that are separated before the title.
        prefix=re.sub(r"(?i)^(?:lim|rsg|grp|release)\s+", "", prefix).strip()
        return cls._smart_title(prefix)

    @classmethod
    def _metadata_diagnostics(cls, item):
        read=item.get("metadata_read")
        review=item.get("metadata_review")
        title_keys=(
            "episode_title","episodetitle","episode_name","episodename",
            "title","name",
        )

        read_values_all=[
            str(v).strip()
            for v in cls._deep_values(read,title_keys)
            if isinstance(v,(str,int,float)) and str(v).strip()
        ]
        review_values_all=[
            str(v).strip()
            for v in cls._deep_values(review,title_keys)
            if isinstance(v,(str,int,float)) and str(v).strip()
        ]
        read_values=[
            v for v in read_values_all
            if not cls._is_placeholder_episode_title(v)
        ]
        review_values=[
            v for v in review_values_all
            if not cls._is_placeholder_episode_title(v)
        ]
        ignored_placeholders=[
            v for v in review_values_all + read_values_all
            if cls._is_placeholder_episode_title(v)
        ]

        def contains_nfo(node):
            if isinstance(node,dict):
                for key,value in node.items():
                    if str(key).casefold()=="nfo":
                        return True
                    if contains_nfo(value):
                        return True
            elif isinstance(node,(list,tuple)):
                return any(contains_nfo(x) for x in node)
            return False

        return {
            "metadata_read_present": bool(read),
            "metadata_review_present": bool(review),
            "nfo_present": bool(contains_nfo(read) or contains_nfo(review)),
            "episode_title_values_read": read_values,
            "episode_title_values_review": review_values,
            "episode_title_field_count": len(read_values)+len(review_values),
            "ignored_episode_title_placeholders": ignored_placeholders,
        }

    @classmethod
    def _episode_title_info(cls, item, reference=None, online_resolver=None):
        # 1) Metadata Editor review/read, including nested NFO-like data.
        for source_key, source_label, confidence in (
            ("metadata_review", "metadata_review", 0.99),
            ("metadata_read", "metadata_read", 0.98),
        ):
            source=item.get(source_key)
            values=cls._deep_values(
                source,
                (
                    "episode_title","episodetitle","episode_name","episodename",
                    "title","name",
                ),
            )
            series_values=cls._deep_values(
                source,
                ("series","series_title","show","show_title","tvshow"),
            )
            series_names={
                str(v).strip().casefold()
                for v in series_values
                if str(v).strip()
            }
            for value in values:
                if not isinstance(value,(str,int,float)):
                    continue
                title=str(value).strip()
                if (
                    title
                    and not cls._is_placeholder_episode_title(title)
                    and title.casefold() not in series_names
                ):
                    return {
                        "title":title,
                        "source":source_label,
                        "confidence":confidence,
                    }

        # 2) Explicit item fields.
        for key in ("episode_title","episode_name","episodetitle"):
            value=str(item.get(key) or "").strip()
            if value and not cls._is_placeholder_episode_title(value):
                return {"title":value,"source":"item","confidence":0.92}

        # 3) Existing local/single KI review as fallback.
        local=dict(item.get("local_review") or item.get("single_review") or {})
        structured=dict(local.get("structured_recommendation") or {})
        fields=dict(structured.get("fields") or {})
        value=str(fields.get("episode_title") or "").strip()
        if value and not cls._is_placeholder_episode_title(value):
            try:
                confidence=max(
                    0.0,
                    min(
                        1.0,
                        float(
                            structured.get("confidence")
                            or local.get("confidence")
                            or 0.85
                        ),
                    ),
                )
            except (TypeError,ValueError):
                confidence=0.85
            return {
                "title":value,
                "source":"local_ai_review",
                "confidence":confidence,
            }

        if callable(online_resolver):
            info=cls._episode_info(item)
            series_title=cls._series_title(item, reference or {})
            if info and series_title:
                try:
                    online=dict(online_resolver({
                        "title":series_title,
                        "media_type":"series",
                        "season":info.get("season"),
                        "episode":info.get("episode"),
                        "year":item.get("year"),
                    }) or {})
                except Exception as exc:
                    online={
                        "available":False,
                        "accepted":False,
                        "episode_title":"",
                        "confidence":0.0,
                        "sources":[],
                        "reason":f"Online-Episodentitelprüfung fehlgeschlagen: {exc}",
                    }
                title=str(online.get("episode_title") or "").strip()
                if (
                    online.get("accepted")
                    and title
                    and not cls._is_placeholder_episode_title(title)
                ):
                    return {
                        "title":title,
                        "source":"online_fusion",
                        "confidence":max(
                            0.0,min(1.0,float(online.get("confidence") or 0.0))
                        ),
                        "online":online,
                    }
                return {
                    "title":"",
                    "source":"",
                    "confidence":0.0,
                    "online":online,
                }

        return {"title":"","source":"","confidence":0.0,"online":{}}

    @classmethod
    def _episode_title(cls, item):
        return str(cls._episode_title_info(item).get("title") or "")

    @classmethod
    def _movie_title_year(cls, item):
        title=cls._first_metadata_value(item,"movie_title","title","name")
        year=cls._first_metadata_value(item,"year","release_year","date")

        if not title:
            raw=Path(str(item.get("original_name") or item.get("source_path") or "")).stem
            year_match=cls._YEAR_RE.search(raw)
            before=raw[:year_match.start()] if year_match else raw
            title=cls._smart_title(cls._clean_words(before))

        if year:
            m=cls._YEAR_RE.search(str(year))
            year=m.group("year") if m else ""
        else:
            raw=Path(str(item.get("original_name") or item.get("source_path") or "")).stem
            m=cls._YEAR_RE.search(raw)
            year=m.group("year") if m else ""
        return title.strip(),year

    @staticmethod
    def _extension(item):
        for value in (
            item.get("original_name"),
            item.get("source_path"),
            item.get("proposed_name"),
        ):
            suffix=Path(str(value or "")).suffix
            if suffix:
                return suffix
        return ""

    @classmethod
    def _cleanup_name(cls, name, extension=""):
        name=str(name or "").strip()
        ext=extension or Path(name).suffix
        stem=Path(name).stem if Path(name).suffix else name
        stem=cls._TRAILING_SEPARATOR_RE.sub("",stem).rstrip(" ._-")
        stem=re.sub(r"\s{2,}"," ",stem)
        return stem + ext

    def _format_series(self,item,reference,schema):
        cls=self.__class__
        info=cls._episode_info(item)
        if not info:
            return "",0.0,["Keine Staffel-/Episodennummer erkannt."],{"title":"","source":"","confidence":0.0}

        title=cls._series_title(item,reference)
        episode_title_info=cls._episode_title_info(
            item,
            reference,
            self.episode_title_resolver,
        )
        episode_title=str(episode_title_info.get("title") or "")
        season=info["season"]; episode=info["episode"]; episode_end=info.get("episode_end")
        token=f"S{season:02d}E{episode:02d}"
        if episode_end is not None:
            token+=f"E{episode_end:02d}"

        extension=cls._extension(item)

        template=str((schema or {}).get("template") or "").strip()
        if template:
            values={
                "[titel]":title,
                "[title]":title,
                "[serie]":title,
                "[series]":title,
                "[staffel]":f"{season:02d}",
                "[season]":f"{season:02d}",
                "[episode]":f"{episode:02d}",
                "[episodentitel]":episode_title,
                "[episode_title]":episode_title,
            }
            rendered=template
            for key,value in values.items():
                rendered=rendered.replace(key,value)
            # unknown placeholders mean we should not pretend the render was
            # complete; fall back to the reference-oriented safe format.
            if "[" not in rendered and "]" not in rendered:
                return cls._cleanup_name(rendered,extension),0.90,[],episode_title_info

        parts=[title,token]
        if episode_title:
            parts.append(episode_title)
        suggested=" - ".join(part for part in parts if part)
        warnings=[]
        if not episode_title:
            warnings.append("Episodentitel noch nicht bekannt; kein leerer Trenner angehängt.")
        confidence=0.92 if title else 0.72
        if episode_title:
            confidence=min(0.98,confidence+0.04)
        return cls._cleanup_name(suggested,extension),confidence,warnings,episode_title_info

    @classmethod
    def _format_movie(cls,item):
        title,year=cls._movie_title_year(item)
        extension=cls._extension(item)
        if not title:
            return "",0.0,["Filmtitel konnte nicht sicher ermittelt werden."]
        suggested=title + (f" ({year})" if year else "")
        confidence=0.88 if year else 0.68
        return cls._cleanup_name(suggested,extension),confidence,[]

    def analyze(self, payload: dict[str, Any] | None):
        source=dict(payload or {})
        items=[dict(x or {}) for x in (source.get("items") or [])]
        reference=dict(source.get("reference") or {})
        schema=dict(source.get("schema") or {})
        reference_type=self._media_type(reference) if reference else ""
        results=[]
        groups={}

        for index,item in enumerate(items):
            local_review=self.single_provider.analyze(item)
            media_type=self._media_type(item)
            groups.setdefault(media_type,0)
            groups[media_type]+=1

            warnings=list(local_review.get("warnings") or [])
            metadata_review=dict(item.get("metadata_review") or {})

            episode_title_info={"title":"","source":"","confidence":0.0}
            if media_type=="series":
                suggested,confidence,extra,episode_title_info=self._format_series(item,reference,schema)
                metadata_diagnostics=self._metadata_diagnostics(item)
                ignored=metadata_diagnostics.get("ignored_episode_title_placeholders") or []
                if ignored:
                    extra=list(extra or [])
                    extra.append(
                        "Metadaten-Platzhalter als Episodentitel ignoriert: "
                        + ", ".join(dict.fromkeys(str(x) for x in ignored))
                    )
            elif media_type=="movie":
                suggested,confidence,extra=self._format_movie(item)
            else:
                suggested=self._cleanup_name(
                    str(local_review.get("suggested_name") or item.get("proposed_name") or ""),
                    self._extension(item),
                )
                confidence=float(local_review.get("confidence") or 0.0)
                extra=["Medientyp noch nicht eindeutig erkannt."]

            warnings.extend(extra)

            if reference_type and media_type not in ("unknown",reference_type):
                warnings.append(
                    f"Referenz ist '{reference_type}', Eintrag ist '{media_type}'. "
                    "Referenzschema wurde nicht blind auf einen anderen Medientyp übertragen."
                )

            # Reference can only steer same media type (or formerly unknown
            # entries that filename/metadata now classifies to that type).
            reference_applied=bool(
                reference and media_type!="unknown" and media_type==reference_type
            )

            rationale=(
                "Referenz, Dateiname und verfügbare Metadaten wurden gemeinsam ausgewertet."
                if reference_applied
                else str(local_review.get("rationale") or "")
                or "Lokale MediaHub-KI-Analyse."
            )

            results.append({
                "index":index,
                "source_path":str(item.get("source_path") or ""),
                "original_name":str(item.get("original_name") or ""),
                "media_type":media_type,
                "suggested_name":suggested,
                "candidate_id":str(local_review.get("candidate_id") or ""),
                "confidence":max(0.0,min(1.0,float(confidence or 0.0))),
                "rationale":rationale,
                "warnings":warnings,
                "structured_recommendation":dict(local_review.get("structured_recommendation") or {}),
                "metadata_review":metadata_review,
                "reference_applied":reference_applied,
                "episode_title":str(episode_title_info.get("title") or ""),
                "episode_title_source":str(episode_title_info.get("source") or ""),
                "episode_title_confidence":max(
                    0.0,min(1.0,float(episode_title_info.get("confidence") or 0.0))
                ),
                "episode_title_online":dict(episode_title_info.get("online") or {}),
                "metadata_diagnostics":(
                    metadata_diagnostics
                    if media_type=="series"
                    else self._metadata_diagnostics(item)
                ),
                "schema_reference":{
                    "template":str(schema.get("template") or ""),
                    "reference_name":str(reference.get("proposed_name") or reference.get("original_name") or ""),
                    "reference_media_type":reference_type,
                },
                "execution_allowed":False,
                "automatic_apply_allowed":False,
                "human_confirmation_required":True,
            })

        return {
            "provider":"MediaHub KI-Assistent",
            "available":True,
            "mode":"batch_reference_intelligence",
            "item_count":len(results),
            "groups":groups,
            "reference_used":bool(reference),
            "schema_used":bool(schema),
            "items":results,
            "execution_allowed":False,
            "automatic_apply_allowed":False,
            "metadata_write_allowed":False,
            "human_confirmation_required":True,
        }
