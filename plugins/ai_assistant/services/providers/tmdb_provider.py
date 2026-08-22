from __future__ import annotations

import os
from typing import Any

from services.providers.base_provider import BaseProvider, ProviderResult
from services.providers.http_client import request_json


class TmdbProvider(BaseProvider):
    provider_type = "tmdb"
    API_BASE = "https://api.themoviedb.org/3"

    def _credential(self) -> tuple[str, str] | None:
        bearer_env = str(self.config.get("bearer_token_env") or "MEDIAHUB_TMDB_BEARER_TOKEN")
        api_key_env = str(self.config.get("api_key_env") or "MEDIAHUB_TMDB_API_KEY")
        if os.environ.get(bearer_env):
            return "bearer", os.environ[bearer_env]
        if os.environ.get(api_key_env):
            return "api_key", os.environ[api_key_env]
        return None

    def is_configured(self) -> bool:
        return self.enabled and self._credential() is not None

    def search(self, query: dict[str, Any]) -> ProviderResult:
        credential = self._credential()
        if not self.enabled:
            return ProviderResult(self.id, self.name, "disabled", message="Quelle ist deaktiviert.")
        if credential is None:
            return ProviderResult(self.id, self.name, "not_configured", message="TMDb-Zugangsdaten fehlen.")

        media_type = str(query.get("media_type") or "").lower()
        endpoint_type = "tv" if media_type == "series" else "movie" if media_type == "movie" else "multi"
        params: dict[str, Any] = {
            "query": query.get("title"),
            "language": self.config.get("language", "de-DE"),
            "include_adult": "false",
            "page": 1,
        }
        if query.get("year"):
            params["first_air_date_year" if endpoint_type == "tv" else "primary_release_year"] = query["year"]

        headers: dict[str, str] = {}
        if credential[0] == "bearer":
            headers["Authorization"] = f"Bearer {credential[1]}"
        else:
            params["api_key"] = credential[1]

        data = request_json(f"{self.API_BASE}/search/{endpoint_type}", params=params, headers=headers)
        matches = []

        query_title = self._normalized_title(query.get("title"))

        for item in (data.get("results") or [])[:10]:
            item_type = item.get("media_type") or ("series" if endpoint_type == "tv" else "movie")
            if item_type == "tv":
                item_type = "series"

            date = item.get("first_air_date") or item.get("release_date") or ""

            title = item.get("name") or item.get("title")
            original_title = item.get("original_name") or item.get("original_title")

            aliases: list[str] = []

            item_id = str(item.get("id") or "").strip()

            # TMDb-Suchergebnisse enthalten nicht alle offiziellen
            # Alternativtitel. Kandidaten, deren normaler oder originaler
            # Titel nicht exakt der Suchanfrage entspricht, werden deshalb
            # gezielt um TMDb-Aliase ergänzt.
            direct_title_match = query_title in {
                self._normalized_title(title),
                self._normalized_title(original_title),
            }

            if item_id and not direct_title_match:
                alias_params: dict[str, Any] = {}

                if credential[0] != "bearer":
                    alias_params["api_key"] = credential[1]

                try:
                    if item_type == "movie":
                        alias_data = request_json(
                            f"{self.API_BASE}/movie/{item_id}/alternative_titles",
                            params=alias_params,
                            headers=headers,
                        )

                        alias_rows = alias_data.get("titles") or []

                        aliases = [
                            str(row.get("title") or "").strip()
                            for row in alias_rows
                            if str(row.get("title") or "").strip()
                        ]

                    elif item_type == "series":
                        alias_data = request_json(
                            f"{self.API_BASE}/tv/{item_id}/alternative_titles",
                            params=alias_params,
                            headers=headers,
                        )

                        alias_rows = alias_data.get("results") or []

                        aliases = [
                            str(
                                row.get("title")
                                or row.get("name")
                                or ""
                            ).strip()
                            for row in alias_rows
                            if str(
                                row.get("title")
                                or row.get("name")
                                or ""
                            ).strip()
                        ]

                except Exception:
                    # Alternativtitel sind zusätzliche Evidenz.
                    # Ein Fehler dieser Zusatzabfrage darf den normalen
                    # TMDb-Suchtreffer nicht zerstören.
                    aliases = []

            # Doppelte Titel sowie Haupt-/Originaltitel nicht nochmals
            # als Alias an den Ranker übergeben.
            known_titles = {
                self._normalized_title(title),
                self._normalized_title(original_title),
            }

            unique_aliases: list[str] = []
            seen_aliases: set[str] = set()

            for alias in aliases:
                normalized = self._normalized_title(alias)

                if (
                    not normalized
                    or normalized in known_titles
                    or normalized in seen_aliases
                ):
                    continue

                seen_aliases.add(normalized)
                unique_aliases.append(alias)

            matches.append({
                "external_id": item_id,
                "title": title,
                "original_title": original_title,
                "aliases": unique_aliases,
                "year": int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None,
                "release_date": date or None,
                "published_at": date or None,
                "media_type": item_type,
                "overview": item.get("overview") or "",
                "language": item.get("original_language"),
                "popularity": item.get("popularity"),
                "provider_confidence": min(float(item.get("vote_average") or 0.0) / 10.0, 1.0),
                "raw": {"id": item.get("id"), "poster_path": item.get("poster_path")},
            })
        return ProviderResult(self.id, self.name, "ok", matches, f"{len(matches)} TMDb-Treffer geladen.")

    @staticmethod
    def _normalized_title(value: Any) -> str:
        return "".join(
            ch for ch in str(value or "").casefold()
            if ch.isalnum()
        )

    def resolve_episode(self, query: dict[str, Any]) -> dict[str, Any]:
        """Resolve one concrete series episode using the existing TMDb provider."""
        if not self.enabled:
            return {
                "status": "disabled",
                "provider": self.provider_type,
                "message": "Quelle ist deaktiviert.",
            }
        credential = self._credential()
        if credential is None:
            return {
                "status": "not_configured",
                "provider": self.provider_type,
                "message": "TMDb-Zugangsdaten fehlen.",
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
                "message": "Serie bei TMDb nicht gefunden.",
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
                "message": "TMDb-Serie ohne ID.",
            }

        params: dict[str, Any] = {
            "language": self.config.get("language", "de-DE"),
        }
        headers: dict[str, str] = {}
        if credential[0] == "bearer":
            headers["Authorization"] = f"Bearer {credential[1]}"
        else:
            params["api_key"] = credential[1]

        data = request_json(
            f"{self.API_BASE}/tv/{series_id}/season/{season}/episode/{episode}",
            params=params,
            headers=headers,
        )
        title = str(data.get("name") or "").strip()
        if not title:
            return {
                "status": "not_found",
                "provider": self.provider_type,
                "message": "TMDb-Episode besitzt keinen Titel.",
            }

        exact_series = bool(exact)
        return {
            "status": "ok",
            "provider": self.provider_type,
            "provider_name": self.name,
            "episode_title": title,
            "series_title": str(series.get("title") or ""),
            "series_external_id": series_id,
            "season": season,
            "episode": episode,
            "confidence": 0.96 if exact_series else 0.84,
            "language": self.config.get("language", "de-DE"),
            "evidence": {
                "series_match": dict(series),
                "episode_id": str(data.get("id") or ""),
                "air_date": str(data.get("air_date") or ""),
            },
            "message": "TMDb-Episodentitel geladen.",
        }
