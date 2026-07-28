from __future__ import annotations

from typing import Any


class SourceSelectionPolicy:
    UNKNOWN_TYPES = {"", "unknown", "other", "unbekannt", "none"}

    TYPE_FALLBACKS = {
        "unknown": {"movie", "series", "audiobook"},
        "other": {"movie", "series", "audiobook"},
        "video": {"movie", "series"},
        "episode": {"series"},
        "tv": {"series"},
    }

    @classmethod
    def normalized_media_type(cls, value: Any) -> str:
        return str(value or "").strip().casefold()

    @classmethod
    def has_searchable_identity(
        cls,
        query: dict[str, Any],
    ) -> bool:
        return bool(
            str(query.get("title") or "").strip()
            or str(query.get("external_id") or "").strip()
            or list(query.get("aliases") or [])
        )

    @classmethod
    def provider_supports(
        cls,
        provider_media_types: list[str],
        query: dict[str, Any],
    ) -> bool:
        if not provider_media_types:
            return cls.has_searchable_identity(query)

        if not cls.has_searchable_identity(query):
            return False

        supported = {
            cls.normalized_media_type(item)
            for item in provider_media_types
        }
        media_type = cls.normalized_media_type(
            query.get("media_type")
        )

        if media_type in supported:
            return True

        if media_type in cls.UNKNOWN_TYPES:
            return bool(
                supported & {"movie", "series", "audiobook"}
            )

        return bool(
            supported & cls.TYPE_FALLBACKS.get(media_type, set())
        )

    @classmethod
    def selection_mode(
        cls,
        query: dict[str, Any],
    ) -> str:
        media_type = cls.normalized_media_type(
            query.get("media_type")
        )
        return (
            "cross_media_type"
            if media_type in cls.UNKNOWN_TYPES
            else "media_type"
        )

    @classmethod
    def selection_reason(
        cls,
        query: dict[str, Any],
        count: int,
    ) -> str:
        if count <= 0:
            if not cls.has_searchable_identity(query):
                return (
                    "Es fehlen Titel, Alias oder externe ID "
                    "für eine Online-Suche."
                )
            return (
                "Keine aktivierte und vollständig konfigurierte "
                "Quelle unterstützt die vorhandenen Suchhinweise."
            )

        if cls.selection_mode(query) == "cross_media_type":
            return (
                "Der Medientyp ist noch unbekannt. Die Quellen werden "
                "anhand des Titelhinweises medientypübergreifend abgefragt."
            )

        return (
            "Geeignete Quellen wurden anhand von Medientyp und "
            "vorhandenen Suchhinweisen ausgewählt."
        )
