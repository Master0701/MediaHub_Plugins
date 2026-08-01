from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


def _normalize_title(value: Any) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def _title_similarity(first: str, second: str) -> float:
    first_tokens = set(_normalize_title(first).split())
    second_tokens = set(_normalize_title(second).split())
    if not first_tokens or not second_tokens:
        return 0.0
    if first_tokens == second_tokens:
        return 1.0
    union = len(first_tokens | second_tokens)
    return len(first_tokens & second_tokens) / union if union else 0.0


class IdentityContradictionDetector:
    """Erkennt widersprüchliche Identitätsmerkmale ohne finale Entscheidung."""

    @staticmethod
    def _as_int(value: Any) -> int | None:
        try:
            return None if value in (None, "") else int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _severity(weighted_strength: float, kind: str) -> str:
        if kind in {"fingerprint_identity", "media_type"} and weighted_strength >= 0.75:
            return "critical"
        if weighted_strength >= 0.65:
            return "high"
        if weighted_strength >= 0.40:
            return "medium"
        return "low"

    @staticmethod
    def _penalty(severity: str) -> float:
        return {"critical": 0.34, "high": 0.22, "medium": 0.12, "low": 0.05}.get(severity, 0.05)

    def _conflict(self, kind: str, expected: Any, observed: Any, evidence: dict[str, Any], detail: str) -> dict[str, Any]:
        weighted = float(evidence.get("weighted_strength") or 0.0)
        severity = self._severity(weighted, kind)
        return {
            "kind": kind, "severity": severity, "expected": expected, "observed": observed,
            "source": evidence.get("source"), "independent_group": evidence.get("independent_group"),
            "confidence": evidence.get("confidence"), "weighted_strength": round(weighted, 4),
            "penalty": self._penalty(severity), "detail": detail,
        }

    def _candidate_conflicts(self, candidate: dict[str, Any]) -> list[dict[str, Any]]:
        conflicts=[]
        title=str(candidate.get("title") or "").strip(); year=self._as_int(candidate.get("year"))
        media_type=str(candidate.get("media_type") or "").strip().lower()
        season=self._as_int(candidate.get("season")); episode=self._as_int(candidate.get("episode"))
        for evidence in candidate.get("evidence") or []:
            meta=dict(evidence.get("metadata") or {}); source=str(evidence.get("source") or "").lower()
            observed_title=str(meta.get("title") or meta.get("canonical_title") or evidence.get("value") or "").strip()
            observed_year=self._as_int(meta.get("year")); observed_type=str(meta.get("media_type") or "").strip().lower()
            observed_season=self._as_int(meta.get("season")); observed_episode=self._as_int(meta.get("episode"))
            if title and observed_title and _title_similarity(title, observed_title) < 0.34 and len(_normalize_title(observed_title)) >= 3:
                kind="fingerprint_identity" if source=="fingerprint" else "title"
                conflicts.append(self._conflict(kind,title,observed_title,evidence,"Der Belegtitel weicht deutlich vom Kandidatentitel ab."))
            if year is not None and observed_year is not None and abs(year-observed_year)>=2:
                conflicts.append(self._conflict("year",year,observed_year,evidence,"Das Veröffentlichungsjahr widerspricht dem Kandidaten."))
            compatible={media_type,observed_type} in ({"series","episode"},{"series","season"},{"episode","season"})
            if media_type and observed_type and media_type!=observed_type and not compatible:
                conflicts.append(self._conflict("media_type",media_type,observed_type,evidence,"Der Medientyp widerspricht dem Kandidaten."))
            if season is not None and observed_season is not None and season!=observed_season:
                conflicts.append(self._conflict("season",season,observed_season,evidence,"Die Staffelnummer widerspricht dem Kandidaten."))
            if episode is not None and observed_episode is not None and episode!=observed_episode:
                conflicts.append(self._conflict("episode",episode,observed_episode,evidence,"Die Episodennummer widerspricht dem Kandidaten."))
        unique=[]; seen=set()
        for c in conflicts:
            key=(c["kind"],str(c["expected"]),str(c["observed"]),c["source"],c["independent_group"])
            if key not in seen: seen.add(key); unique.append(c)
        rank={"critical":4,"high":3,"medium":2,"low":1}
        unique.sort(key=lambda x:(rank.get(x["severity"],0),x["weighted_strength"]),reverse=True)
        return unique

    @staticmethod
    def _cross_candidate_conflicts(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(candidates)<2:return []
        a,b=candidates[:2]; sa=float(a.get("evidence_strength") or 0); sb=float(b.get("evidence_strength") or 0)
        if abs(sa-sb)>0.12 or _title_similarity(str(a.get("title") or ""),str(b.get("title") or ""))>=0.55:return []
        return [{"kind":"competing_candidates","severity":"high","first_candidate":a.get("title"),"second_candidate":b.get("title"),"first_strength":round(sa,4),"second_strength":round(sb,4),"penalty":0.18,"detail":"Zwei deutlich unterschiedliche Kandidaten besitzen nahezu gleich starke unabhängige Belege."}]

    def detect(self, evidence_result: dict[str, Any] | None, analysis: dict[str, Any] | None=None) -> dict[str, Any]:
        source=dict(evidence_result or {}); candidates=[]
        for raw in source.get("candidates") or []:
            c=deepcopy(raw); conflicts=self._candidate_conflicts(c)
            penalty=min(0.70,sum(float(x.get("penalty") or 0) for x in conflicts))
            c["contradiction_summary"]={"conflict_count":len(conflicts),"critical_count":sum(x.get("severity")=="critical" for x in conflicts),"high_count":sum(x.get("severity")=="high" for x in conflicts),"medium_count":sum(x.get("severity")=="medium" for x in conflicts),"low_count":sum(x.get("severity")=="low" for x in conflicts),"penalty":round(penalty,4),"conflicts":conflicts}
            c["contradiction_penalty"]=round(penalty,4); c["stage"]="contradictions_checked"; candidates.append(c)
        candidates.sort(key=lambda c:(float(c.get("evidence_strength") or 0)-float(c.get("contradiction_penalty") or 0),float(c.get("candidate_score") or 0)),reverse=True)
        cross=self._cross_candidate_conflicts(candidates)
        if cross:
            for c in candidates[:2]:c["cross_candidate_conflicts"]=deepcopy(cross)
        return {"schema_version":3,"stage":"contradiction_detector","decision_made":False,"candidate_count":len(candidates),"candidates":candidates,"best_candidate":candidates[0] if candidates else None,"cross_candidate_conflicts":cross,"source_stage":source.get("stage"),"detection_policy":{"title_conflicts":True,"year_conflicts":True,"media_type_conflicts":True,"season_episode_conflicts":True,"competing_candidate_detection":True},"limitations":["v2.2.2 erkennt Widersprüche, entscheidet aber noch nicht endgültig.","Titelvarianten können ohne bekannte Aliasbeziehung noch als Konflikt erscheinen.","Die endgültige Vertrauensberechnung folgt in v2.2.3."]}
