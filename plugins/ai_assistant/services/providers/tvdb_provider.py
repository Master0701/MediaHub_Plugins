from __future__ import annotations

import os
from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult
from services.providers.http_client import request_json


class TvdbProvider(BaseProvider):
    provider_type = "tvdb"
    API_BASE = "https://api4.thetvdb.com/v4"

    def _api_key(self) -> str:
        return os.environ.get(str(self.config.get("api_key_env") or "MEDIAHUB_TVDB_API_KEY"), "")

    def is_configured(self) -> bool:
        return self.enabled and bool(self._api_key())

    def _token(self) -> str:
        body = {"apikey": self._api_key()}
        pin_env = str(self.config.get("subscriber_pin_env") or "MEDIAHUB_TVDB_SUBSCRIBER_PIN")
        pin = os.environ.get(pin_env)
        if pin:
            body["pin"] = pin
        response = request_json(f"{self.API_BASE}/login", method="POST", body=body)
        token = ((response.get("data") or {}).get("token") or response.get("token") or "")
        if not token:
            raise RuntimeError("TheTVDB lieferte kein Anmeldetoken.")
        return str(token)

    def search(self, query: dict[str, Any]) -> ProviderResult:
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        if not self.is_configured():
            return ProviderResult(self.id, self.name, "not_configured", message="TheTVDB-API-Schlüssel fehlt.")

        media_type = str(query.get("media_type") or "").lower()
        tvdb_type = "series" if media_type == "series" else "movie" if media_type == "movie" else None
        data = request_json(
            f"{self.API_BASE}/search",
            params={"query": query.get("title"), "type": tvdb_type, "limit": 10},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        matches = []
        for item in (data.get("data") or [])[:10]:
            item_type = str(item.get("type") or tvdb_type or "").lower()
            matches.append({
                "external_id": str(item.get("tvdb_id") or item.get("id") or ""),
                "title": item.get("name") or item.get("seriesName") or item.get("movieName"),
                "original_title": item.get("name_translated") or item.get("name"),
                "year": _year(item.get("year") or item.get("first_air_time")),
                "media_type": "series" if item_type == "series" else "movie" if item_type == "movie" else item_type,
                "overview": item.get("overview") or "",
                "language": item.get("primary_language"),
                "aliases": item.get("aliases") or [],
                "provider_confidence": 0.9 if item.get("name") else 0.7,
                "raw": {
                    "tvdb_id": item.get("tvdb_id"),
                    "slug": item.get("slug"),
                    "image_url": (
                        item.get("image_url")
                        or item.get("imageUrl")
                        or item.get("image")
                        or item.get("thumbnail")
                    ),
                    "poster_url": (
                        item.get("poster_url")
                        or item.get("posterUrl")
                    ),
                },
            })
        return ProviderResult(self.id, self.name, "ok", matches, f"{len(matches)} TheTVDB-Treffer geladen.")

    @staticmethod
    def _normalized_title(value: Any) -> str:
        return "".join(
            ch for ch in str(value or "").casefold()
            if ch.isalnum()
        )

    def resolve_episode(self, query: dict[str, Any]) -> dict[str, Any]:
        """Resolve one concrete series episode using TheTVDB v4."""
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider_type,
                "message": "Quelle ist deaktiviert.",
            }
        if not self.is_configured():
            return {
                "status": "not_configured",
                "provider": self.provider_type,
                "message": "TheTVDB-API-Schlüssel fehlt.",
            }

        try:
            season = int(query.get("season"))
            episode = int(query.get("episode"))
        except (TypeError, ValueError):
            return {
                "status": "invalid_query",
                "provider": self.provider_type,
                "message": "Staffel oder Episode fehlt.",
            }

        search_result = self.search({
            **dict(query or {}),
            "media_type": "series",
        })
        if search_result.status not in {"ok", "success"}:
            return {
                "status": search_result.status,
                "provider": self.provider_type,
                "message": search_result.message,
            }

        matches = list(search_result.matches or [])
        if not matches:
            return {
                "status": "not_found",
                "provider": self.provider_type,
                "message": "Serie bei TheTVDB nicht gefunden.",
            }

        wanted = self._normalized_title(query.get("title"))
        exact = [
            item for item in matches
            if self._normalized_title(item.get("title")) == wanted
            or self._normalized_title(item.get("original_title")) == wanted
        ]
        series = (exact or matches)[0]
        series_id = str(series.get("external_id") or "").strip()
        if not series_id:
            return {
                "status": "not_found",
                "provider": self.provider_type,
                "message": "TheTVDB-Serie ohne ID.",
            }

        language = str(self.config.get("language") or "deu")
        # Existing configurations often use de-DE. TVDB expects a language code
        # on the language-specific episode route; map common German/English forms.
        language_map = {
            "de-de": "deu",
            "de": "deu",
            "ger": "deu",
            "en-us": "eng",
            "en-gb": "eng",
            "en": "eng",
        }
        lang = language_map.get(language.casefold(), language)

        data = request_json(
            f"{self.API_BASE}/series/{series_id}/episodes/default/{lang}",
            params={"season": season, "page": 0},
            headers={"Authorization": f"Bearer {self._token()}"},
        )
        payload = data.get("data") or {}
        if isinstance(payload, dict):
            episodes = payload.get("episodes") or payload.get("data") or []
        elif isinstance(payload, list):
            episodes = payload
        else:
            episodes = []

        def number(item, *keys):
            for key in keys:
                value = item.get(key)
                try:
                    if value not in (None, ""):
                        return int(value)
                except (TypeError, ValueError):
                    pass
            return None

        found = None
        for item in episodes:
            if not isinstance(item, dict):
                continue
            item_season = number(
                item,
                "seasonNumber",
                "season_number",
                "airedSeason",
                "season",
            )
            item_episode = number(
                item,
                "number",
                "episodeNumber",
                "episode_number",
                "airedEpisodeNumber",
            )
            if item_episode == episode and (
                item_season in (None, season)
            ):
                found = item
                break

        if not found:
            return {
                "status": "not_found",
                "provider": self.provider_type,
                "message": "TheTVDB-Episode nicht gefunden.",
            }

        title = str(
            found.get("name")
            or found.get("episodeName")
            or found.get("title")
            or ""
        ).strip()
        if not title:
            return {
                "status": "not_found",
                "provider": self.provider_type,
                "message": "TheTVDB-Episode besitzt keinen Titel.",
            }

        return {
            "status": "ok",
            "provider": self.provider_type,
            "provider_name": self.name,
            "episode_title": title,
            "series_title": str(series.get("title") or ""),
            "series_external_id": series_id,
            "season": season,
            "episode": episode,
            "confidence": 0.96 if exact else 0.84,
            "language": lang,
            "evidence": {
                "series_match": dict(series),
                "episode_id": str(found.get("id") or ""),
                "air_date": str(
                    found.get("aired")
                    or found.get("airDate")
                    or found.get("firstAired")
                    or found.get("first_air_time")
                    or ""
                ),
                "overview": str(
                    found.get("overview")
                    or found.get("description")
                    or found.get("summary")
                    or found.get("shortDescription")
                    or ""
                ),
            },
            "message": "TheTVDB-Episodentitel geladen.",
        }


def _year(value: Any) -> int | None:
    text = str(value or "")
    return int(text[:4]) if len(text) >= 4 and text[:4].isdigit() else None
