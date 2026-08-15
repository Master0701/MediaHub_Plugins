from __future__ import annotations

from typing import Any


class EpisodeTitleResolver:
    """Fuse concrete episode-title candidates from existing online providers."""

    MIN_CONFIDENCE = 0.72

    def __init__(self, source_manager, fusion, *, min_confidence: float | None = None):
        self.source_manager = source_manager
        self.fusion = fusion
        self.min_confidence = (
            self.MIN_CONFIDENCE
            if min_confidence is None
            else max(0.0, min(1.0, float(min_confidence)))
        )

    def resolve(self, query: dict[str, Any] | None) -> dict[str, Any]:
        source = dict(query or {})
        title = str(source.get("title") or "").strip()
        try:
            season = int(source.get("season"))
            episode = int(source.get("episode"))
        except (TypeError, ValueError):
            season = episode = 0

        if not title or season <= 0 or episode <= 0:
            return {
                "available": False,
                "accepted": False,
                "episode_title": "",
                "confidence": 0.0,
                "sources": [],
                "provider_results": [],
                "reason": "Serie, Staffel oder Episode fehlt.",
            }

        provider_results = list(
            self.source_manager.resolve_episode_candidates({
                **source,
                "media_type": "series",
                "title": title,
                "season": season,
                "episode": episode,
            })
            or []
        )

        fusion_sources = {}
        successful = []
        for item in provider_results:
            if str(item.get("status") or "").lower() not in {"ok", "success"}:
                continue
            value = str(item.get("episode_title") or "").strip()
            if not value:
                continue
            source_name = str(
                item.get("provider")
                or item.get("provider_name")
                or "unknown"
            ).casefold()
            confidence = max(
                0.0,
                min(1.0, float(item.get("confidence") or 0.0)),
            )
            successful.append(item)
            fusion_sources[source_name] = {
                "candidates": [{
                    "field": "episode_title",
                    "value": value,
                    "confidence": confidence,
                    "source_name": source_name,
                    "reason": (
                        f"{title} S{season:02d}E{episode:02d} "
                        f"bei {source_name} aufgelöst."
                    ),
                    "evidence": [dict(item.get("evidence") or {})],
                }],
            }

        if not fusion_sources:
            statuses = [
                f"{item.get('provider')}: {item.get('status')}"
                for item in provider_results
            ]
            return {
                "available": bool(provider_results),
                "accepted": False,
                "episode_title": "",
                "confidence": 0.0,
                "sources": [],
                "provider_results": provider_results,
                "reason": (
                    "Kein konfigurierter Online-Provider lieferte einen "
                    "Episodentitel."
                    + ((" (" + ", ".join(statuses) + ")") if statuses else "")
                ),
            }

        fused = self.fusion.fuse(sources=fusion_sources)
        field = dict(
            (fused.get("fused_fields") or {}).get("episode_title") or {}
        )
        value = str(field.get("value") or "").strip()
        confidence = max(
            0.0,
            min(1.0, float(field.get("confidence") or 0.0)),
        )
        sources = list(field.get("sources") or [])
        accepted = bool(value and confidence >= self.min_confidence)

        return {
            "available": True,
            "accepted": accepted,
            "episode_title": value if accepted else "",
            "candidate_title": value,
            "confidence": confidence,
            "sources": sources,
            "provider_results": provider_results,
            "fusion": fused,
            "reason": (
                "Online-Episodentitel durch Quellenfusion bestätigt."
                if accepted
                else (
                    "Online-Kandidat unter Mindest-Confidence "
                    f"{self.min_confidence:.0%}."
                )
            ),
        }
