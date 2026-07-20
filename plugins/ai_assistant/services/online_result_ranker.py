from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


class OnlineResultRanker:
    """Bewertet Treffer verschiedener Quellen mit einer einheitlichen Skala."""

    def rank(self, query: dict[str, Any], provider_results: list[dict[str, Any]]) -> dict[str, Any]:
        ranked: list[dict[str, Any]] = []
        query_title = _normalize(query.get("title"))
        query_year = query.get("year")
        query_type = query.get("media_type")

        for provider in provider_results:
            trust = float(provider.get("trust") or 0.5)
            priority = int(provider.get("priority") or 50)
            for raw_match in provider.get("matches") or []:
                match = dict(raw_match)
                candidate_title = _normalize(match.get("title") or match.get("name"))
                title_similarity = SequenceMatcher(None, query_title, candidate_title).ratio() if query_title and candidate_title else 0.0

                year_score = 0.5
                if query_year and match.get("year"):
                    try:
                        difference = abs(int(query_year) - int(match.get("year")))
                        year_score = 1.0 if difference == 0 else 0.55 if difference == 1 else 0.0
                    except (TypeError, ValueError):
                        year_score = 0.5

                type_score = 0.5
                candidate_type = match.get("media_type") or match.get("type")
                if query_type and candidate_type:
                    type_score = 1.0 if str(query_type).lower() == str(candidate_type).lower() else 0.0

                provider_score = min(max(priority / 100.0, 0.0), 1.0)
                score = (
                    title_similarity * 0.55
                    + year_score * 0.12
                    + type_score * 0.13
                    + trust * 0.15
                    + provider_score * 0.05
                )
                ranked.append({
                    **match,
                    "provider_id": provider.get("provider_id"),
                    "provider_name": provider.get("provider_name"),
                    "score": round(score, 4),
                    "score_percent": round(score * 100),
                    "score_details": {
                        "title_similarity": round(title_similarity, 4),
                        "year": round(year_score, 4),
                        "media_type": round(type_score, 4),
                        "provider_trust": round(trust, 4),
                        "provider_priority": priority,
                    },
                })

        ranked.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        gap = round(float(best["score"]) - float(second["score"]), 4) if best and second else None
        return {
            "matches": ranked,
            "best_match": best,
            "match_count": len(ranked),
            "confidence": float(best.get("score") or 0.0) if best else 0.0,
            "confidence_gap": gap,
            "decision": self._decision(best, gap),
        }

    @staticmethod
    def _decision(best: dict[str, Any] | None, gap: float | None) -> str:
        if not best:
            return "no_match"
        score = float(best.get("score") or 0.0)
        if score >= 0.90 and (gap is None or gap >= 0.08):
            return "strong_match"
        if score >= 0.75:
            return "probable_match"
        return "ambiguous"
