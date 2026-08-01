from __future__ import annotations

from copy import deepcopy
from typing import Any


SOURCE_LABELS = {
    "filename": "Dateiname",
    "online": "Online-Quelle",
    "visual_ocr": "OCR-/Titelkarte",
    "visual_knowledge": "Visual Knowledge",
    "fingerprint": "Fingerprint",
    "learned_knowledge": "Gelerntes Wissen",
    "subtitle": "Untertitel",
    "audio": "Audio",
    "technical": "Technische Merkmale",
    "other": "Sonstiger Beleg",
}

GROUP_LABELS = {
    "filename": "Dateiname",
    "online": "Online",
    "visual_text": "OCR und Titelkarten",
    "visual": "Visuelle Merkmale",
    "knowledge": "Lokales Wissen",
    "fingerprint": "Fingerprint",
    "subtitle": "Untertitel",
    "audio": "Audio",
    "technical": "Technische Merkmale",
    "other": "Sonstige Belege",
}


class IdentityDecisionExplainer:
    """Erzeugt eine verständliche Begründung ohne selbst final zu entscheiden."""

    @staticmethod
    def _pct(value: Any) -> float:
        try:
            return round(float(value) * 100, 1)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _source_label(source: Any) -> str:
        key = str(source or "other").strip().lower()
        return SOURCE_LABELS.get(key, key or "Unbekannt")

    @staticmethod
    def _group_label(group: Any) -> str:
        key = str(group or "other").strip().lower()
        return GROUP_LABELS.get(key, key or "Unbekannt")

    def _used_evidence(
        self,
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        used = []
        for item in candidate.get("evidence") or []:
            if not bool(item.get("used_for_group_score")):
                continue
            used.append(
                {
                    "source": item.get("source"),
                    "source_label": self._source_label(item.get("source")),
                    "group": item.get("independent_group"),
                    "group_label": self._group_label(
                        item.get("independent_group")
                    ),
                    "value": item.get("value"),
                    "confidence_percent": self._pct(
                        item.get("confidence")
                    ),
                    "weighted_strength_percent": self._pct(
                        item.get("weighted_strength")
                    ),
                    "detail": item.get("detail"),
                }
            )

        used.sort(
            key=lambda item: item["weighted_strength_percent"],
            reverse=True,
        )
        return used

    def _supporting_evidence(
        self,
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        supporting = []
        for item in candidate.get("evidence") or []:
            if bool(item.get("used_for_group_score")):
                continue
            supporting.append(
                {
                    "source": item.get("source"),
                    "source_label": self._source_label(item.get("source")),
                    "group": item.get("independent_group"),
                    "group_label": self._group_label(
                        item.get("independent_group")
                    ),
                    "value": item.get("value"),
                    "confidence_percent": self._pct(
                        item.get("confidence")
                    ),
                    "weighted_strength_percent": self._pct(
                        item.get("weighted_strength")
                    ),
                    "detail": item.get("detail"),
                }
            )
        return supporting

    def _missing_evidence(
        self,
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        summary = candidate.get("evidence_summary") or {}
        coverage = summary.get("coverage") or {}
        missing = []
        for group in coverage.get("missing_groups") or []:
            missing.append(
                {
                    "group": group,
                    "group_label": self._group_label(group),
                    "reason": "Für diese Beleggruppe liegt kein verwertbarer Hinweis vor.",
                }
            )
        return missing

    @staticmethod
    def _conflicts(
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        summary = candidate.get("contradiction_summary") or {}
        result = []
        for item in summary.get("conflicts") or []:
            result.append(
                {
                    "kind": item.get("kind"),
                    "severity": item.get("severity"),
                    "expected": item.get("expected"),
                    "observed": item.get("observed"),
                    "source": item.get("source"),
                    "penalty_percent": round(
                        float(item.get("penalty") or 0.0) * 100,
                        1,
                    ),
                    "detail": item.get("detail"),
                }
            )
        return result

    @staticmethod
    def _recommendation(status: str, critical: int) -> str:
        if critical:
            return (
                "Nicht automatisch übernehmen. Kritischen Konflikt prüfen "
                "und zusätzliche unabhängige Belege sammeln."
            )
        if status == "confirmed_ready":
            return (
                "Die Identität ist bereit für die finale semantische "
                "Entscheidung in v2.2.5."
            )
        if status == "probable":
            return (
                "Starker Kandidat. Für eine endgültige Bestätigung fehlt "
                "mindestens ein weiterer unabhängiger Beleg."
            )
        if status == "possible":
            return (
                "Möglicher Treffer. Weitere OCR-, Online-, Fingerprint-, "
                "Audio- oder Untertitelbelege sammeln."
            )
        return (
            "Nur vorläufiger Kandidat. Keine automatische Übernahme; "
            "weitere Analyse erforderlich."
        )

    def _conclusion(
        self,
        candidate: dict[str, Any],
    ) -> str:
        title = str(candidate.get("title") or "Unbekannter Kandidat")
        year = candidate.get("year")
        label = f"{title} ({year})" if year else title
        confidence = float(
            candidate.get("semantic_confidence_percent") or 0.0
        )
        status = str(candidate.get("semantic_status") or "candidate")
        groups = int(
            (
                candidate.get("evidence_summary")
                or {}
            ).get("independent_group_count")
            or 0
        )
        conflicts = int(
            (
                candidate.get("contradiction_summary")
                or {}
            ).get("conflict_count")
            or 0
        )

        return (
            f"{label} erreicht {round(confidence, 1)} % semantisches Vertrauen "
            f"mit {groups} unabhängigen Beleggruppen und {conflicts} "
            f"erkannten Konflikten. Aktuelle Einstufung: {status}."
        )

    def explain(
        self,
        confidence_result: dict[str, Any] | None,
        analysis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = dict(confidence_result or {})
        candidates: list[dict[str, Any]] = []

        for raw in source.get("candidates") or []:
            candidate = deepcopy(raw)
            confidence_summary = candidate.get("confidence_summary") or {}
            contradiction_summary = (
                candidate.get("contradiction_summary") or {}
            )
            status = str(
                candidate.get("semantic_status")
                or confidence_summary.get("status")
                or "candidate"
            )
            critical = int(
                contradiction_summary.get("critical_count") or 0
            )

            used = self._used_evidence(candidate)
            supporting = self._supporting_evidence(candidate)
            missing = self._missing_evidence(candidate)
            conflicts = self._conflicts(candidate)
            limitations = list(confidence_summary.get("limitations") or [])

            why = []
            for item in used:
                why.append(
                    f"{item['group_label']}: {item['value']} "
                    f"({item['weighted_strength_percent']} % gewichtete Stärke)"
                )

            if not why:
                why.append(
                    "Es liegt noch kein ausreichend starker unabhängiger Beleg vor."
                )

            candidate["explainable_decision"] = {
                "title": candidate.get("title"),
                "year": candidate.get("year"),
                "media_type": candidate.get("media_type"),
                "status": status,
                "trust_label": confidence_summary.get("trust_label"),
                "confidence": candidate.get("semantic_confidence"),
                "confidence_percent": candidate.get(
                    "semantic_confidence_percent"
                ),
                "conclusion": self._conclusion(candidate),
                "why": why,
                "used_evidence": used,
                "supporting_evidence": supporting,
                "missing_evidence": missing,
                "conflicts": conflicts,
                "limitations": limitations,
                "recommendation": self._recommendation(status, critical),
                "final_decision_made": False,
            }
            candidate["stage"] = "decision_explained"
            candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                float(item.get("semantic_confidence") or 0.0),
                float(item.get("evidence_strength") or 0.0),
            ),
            reverse=True,
        )

        best = candidates[0] if candidates else None
        runner_up = candidates[1] if len(candidates) > 1 else None

        return {
            "schema_version": 5,
            "stage": "explainable_decision",
            "decision_made": False,
            "candidate_count": len(candidates),
            "candidates": candidates,
            "best_candidate": best,
            "runner_up": runner_up,
            "confidence_gap": source.get("confidence_gap"),
            "source_stage": source.get("stage"),
            "explanation_policy": {
                "used_evidence_visible": True,
                "supporting_evidence_visible": True,
                "missing_evidence_visible": True,
                "conflicts_visible": True,
                "recommendation_visible": True,
                "final_decision_made": False,
            },
            "limitations": [
                "v2.2.4 erklärt die Bewertung, trifft aber noch keine finale Identitätsentscheidung.",
                "Die endgültige Auswahl und Übergabe folgt in v2.2.5.",
            ],
        }
