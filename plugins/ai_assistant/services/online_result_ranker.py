from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, ClassVar


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _number_score(expected: Any, actual: Any) -> float:
    if expected in (None, "", []): return 0.5
    if actual in (None, "", []): return 0.25
    try:
        left = expected if isinstance(expected, list) else [expected]
        right = actual if isinstance(actual, list) else [actual]
        return 1.0 if {int(v) for v in left} == {int(v) for v in right} else 0.0
    except (TypeError, ValueError): return 0.25


class OnlineResultRanker:
    """Evidence-basiertes Ranking mit Schutz gegen schwache Zufallstreffer."""
    WEIGHTS: ClassVar[dict[str, float]] = {"title": .34, "variant": .14, "year": .10, "media_type": .15, "season_episode": .12, "runtime": .10, "provider": .05}

    def rank(self, query: dict[str, Any], provider_results: list[dict[str, Any]]) -> dict[str, Any]:
        ranked = []
        primary = _normalize(query.get("title")); query_type = str(query.get("media_type") or "").lower(); query_year = query.get("year")
        for provider in provider_results:
            provider_score = min(max(float(provider.get("trust") or .5), 0), 1) * .8 + min(max(int(provider.get("priority") or 50)/100,0),1)*.2
            for raw in provider.get("matches") or []:
                match = dict(raw); active = _normalize(match.get("search_variant") or primary)
                variant_weight = min(max(float(match.get("search_variant_score") or 1.0), 0), 1)
                titles = [match.get("title"), match.get("original_title"), *(match.get("aliases") or [])]
                similarities = [SequenceMatcher(None, active, _normalize(v)).ratio() for v in titles if v]
                title_score = max(similarities, default=0.0)
                exact_alias = any(active and active == _normalize(v) for v in titles if v)
                year_score = .5
                if query_year and match.get("year"):
                    try:
                        diff = abs(int(query_year)-int(match["year"])); year_score = 1 if diff==0 else .7 if diff==1 else .2 if diff<=3 else 0
                    except (TypeError, ValueError): pass
                candidate_type = str(match.get("media_type") or match.get("type") or "").lower()
                type_score = .5 if not query_type or not candidate_type else (1 if query_type == candidate_type else 0)
                season_episode = _number_score(query.get("season"), match.get("season"))*.45 + _number_score(query.get("episodes"), match.get("episodes") or match.get("episode"))*.55
                runtime_score = .5
                if query.get("duration_seconds") and match.get("duration_seconds"):
                    try:
                        diff = abs(float(query["duration_seconds"])-float(match["duration_seconds"])); runtime_score = 1 if diff<=120 else .8 if diff<=300 else .35 if diff<=900 else 0
                    except (TypeError, ValueError): pass
                evidence = sum([title_score >= .86, exact_alias, type_score == 1, year_score >= .7, runtime_score >= .8, season_episode >= .9])
                weak_single = len(active.split()) == 1 and variant_weight < .55
                score = title_score*.34 + variant_weight*.14 + year_score*.10 + type_score*.15 + season_episode*.12 + runtime_score*.10 + provider_score*.05
                penalties = []
                if weak_single: score *= .42; penalties.append("weak_single_word_variant")
                if title_score < .55: score *= .35; penalties.append("low_title_similarity")
                if query_type and candidate_type and query_type != candidate_type: score *= .45; penalties.append("media_type_conflict")
                if evidence < 2 and not exact_alias: score *= .55; penalties.append("insufficient_combined_evidence")
                score = min(max(score,0),1)
                ranked.append({**match, "provider_id": provider.get("provider_id"), "provider_name": provider.get("provider_name"), "score": round(score,4), "score_percent": round(score*100,1), "evidence_count": evidence, "penalties": penalties, "score_details": {"title":round(title_score,4),"variant":round(variant_weight,4),"year":round(year_score,4),"media_type":round(type_score,4),"season_episode":round(season_episode,4),"runtime":round(runtime_score,4),"provider":round(provider_score,4),"exact_alias":exact_alias,"weights":dict(self.WEIGHTS)}})
        ranked.sort(key=lambda x:x["score"], reverse=True); best=ranked[0] if ranked else None; second=ranked[1] if len(ranked)>1 else None; gap=round(best["score"]-second["score"],4) if best and second else None
        return {"schema_version":3,"matches":ranked,"best_match":best,"match_count":len(ranked),"confidence":float(best.get("score") or 0) if best else 0.0,"confidence_gap":gap,"decision":self._decision(best,gap),"weights":dict(self.WEIGHTS)}

    @staticmethod
    def _decision(best, gap):
        if not best: return "no_match"
        score=float(best.get("score") or 0); evidence=int(best.get("evidence_count") or 0)
        if score>=.88 and evidence>=3 and (gap is None or gap>=.06): return "strong_match"
        if score>=.72 and evidence>=2 and (gap is None or gap>=.025): return "probable_match"
        return "ambiguous"
