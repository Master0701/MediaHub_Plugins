from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class EvidenceItem:
    source: str
    label: str
    value: str
    confidence: float = 0.0
    supports_decision: bool | None = None
    severity: str = "info"
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionEvidenceService:
    """
    Erzeugt nachvollziehbare Belege für einen Review-/Decision-Fusion-Fall.

    Die Belege erklären nur, warum eine Entscheidung vorgeschlagen wird.
    Sie dürfen niemals eine Dateisystem-Ausführung freigeben.
    """

    def build(
        self,
        renamer: dict[str, Any],
        ai: dict[str, Any] | None = None,
        fusion: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        renamer = dict(renamer or {})
        ai = dict(ai or {})
        fusion = dict(fusion or {})

        evidence: list[EvidenceItem] = []

        relation = str(renamer.get("relation_type") or "single")
        renamer_conf = self._clamp(
            renamer.get("confidence")
            or renamer.get("decision_confidence")
            or 0.0
        )
        evidence.append(
            EvidenceItem(
                source="renamer",
                label="Renamer-Erkennung",
                value=relation,
                confidence=renamer_conf,
                supports_decision=self._supports(
                    relation, fusion.get("decision")
                ),
                detail=str(
                    renamer.get("detection_reason")
                    or renamer.get("reason")
                    or "Lokale Medien-/Namensanalyse."
                ),
            )
        )

        title = str(
            renamer.get("title")
            or renamer.get("detected_title")
            or ""
        )
        if title:
            evidence.append(
                EvidenceItem(
                    source="metadata",
                    label="Erkannter Titel",
                    value=title,
                    confidence=self._clamp(
                        renamer.get("title_confidence")
                        or renamer_conf
                    ),
                    detail="Titel-/Metadatenhinweis aus der lokalen Erkennung.",
                )
            )

        season = renamer.get("season")
        episode = renamer.get("episode")
        if season not in (None, "") or episode not in (None, ""):
            value = self._episode_value(season, episode)
            evidence.append(
                EvidenceItem(
                    source="relation",
                    label="Staffel/Episode",
                    value=value,
                    confidence=renamer_conf,
                    detail="Strukturhinweis für Serienrelationen.",
                )
            )

        reasons = list(renamer.get("review_reasons") or [])
        for reason in reasons:
            reason = dict(reason or {})
            evidence.append(
                EvidenceItem(
                    source="review",
                    label=str(reason.get("label") or "Review-Grund"),
                    value=str(reason.get("code") or "review"),
                    confidence=renamer_conf,
                    severity=str(reason.get("severity") or "review"),
                    detail=str(reason.get("message") or ""),
                )
            )

        if ai.get("available"):
            ai_decision = str(
                ai.get("recommendation")
                or ai.get("relation_type")
                or ""
            )
            evidence.append(
                EvidenceItem(
                    source="ai",
                    label="KI-Empfehlung",
                    value=ai_decision or "ohne Entscheidung",
                    confidence=self._clamp(ai.get("confidence") or 0.0),
                    supports_decision=self._supports(
                        ai_decision, fusion.get("decision")
                    ),
                    severity=(
                        "warning"
                        if fusion.get("agreement") == "conflict"
                        else "info"
                    ),
                    detail=str(ai.get("rationale") or ""),
                )
            )

            suggested_name = str(ai.get("suggested_name") or "")
            if suggested_name:
                evidence.append(
                    EvidenceItem(
                        source="ai",
                        label="KI-Namensvorschlag",
                        value=suggested_name,
                        confidence=self._clamp(ai.get("confidence") or 0.0),
                        detail="Nur Vorschlag; keine automatische Übernahme.",
                    )
                )

        if fusion:
            agreement = str(fusion.get("agreement") or "no_ai")
            evidence.append(
                EvidenceItem(
                    source="fusion",
                    label="Decision Fusion",
                    value=agreement,
                    confidence=self._clamp(fusion.get("confidence") or 0.0),
                    severity=(
                        "warning" if agreement == "conflict" else "info"
                    ),
                    detail=str(fusion.get("reason") or ""),
                )
            )

        conflicts = [
            item.to_dict()
            for item in evidence
            if item.supports_decision is False
            or item.severity == "warning"
        ]

        return {
            "items": [item.to_dict() for item in evidence],
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "sources": sorted({item.source for item in evidence}),
            "explainable": bool(evidence),
            "execution_allowed": False,
            "human_confirmation_required": True,
        }

    @staticmethod
    def _episode_value(season: Any, episode: Any) -> str:
        try:
            season_i = int(season)
            season_text = f"S{season_i:02d}"
        except (TypeError, ValueError):
            season_text = f"S{season}" if season not in (None, "") else "S?"
        try:
            episode_i = int(episode)
            episode_text = f"E{episode_i:02d}"
        except (TypeError, ValueError):
            episode_text = f"E{episode}" if episode not in (None, "") else "E?"
        return season_text + episode_text

    @staticmethod
    def _clamp(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _normalise(value: Any) -> str:
        return str(value or "").strip().casefold().replace(" ", "_").replace("-", "_")

    def _supports(self, candidate: Any, decision: Any) -> bool | None:
        candidate_n = self._normalise(candidate)
        decision_n = self._normalise(decision)
        if not candidate_n or not decision_n:
            return None
        return candidate_n == decision_n
