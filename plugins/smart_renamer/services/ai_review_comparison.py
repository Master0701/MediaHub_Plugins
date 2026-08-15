from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class AIReviewComparisonService:
    """Compare local preview/detection values with structured AI review."""

    FIELDS = (
        ("media_type", "Medientyp"),
        ("title", "Titel"),
        ("year", "Jahr"),
        ("season", "Staffel"),
        ("episode", "Episode"),
        ("episode_end", "Episode-Ende"),
        ("episode_title", "Episodentitel"),
        ("edition", "Edition"),
        ("part", "Teil"),
    )
    EPISODE_RE = re.compile(
        r"(?i)(?:^|[\s._-])s(?P<season>\d{1,3})e(?P<episode>\d{1,3})"
        r"(?:e(?P<episode_end>\d{1,3}))?"
    )

    @staticmethod
    def _text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _episode_from_name(cls, value: Any) -> dict[str, str]:
        match=cls.EPISODE_RE.search(Path(str(value or "")).stem)
        if not match:
            return {}
        return {
            "season": str(int(match.group("season"))),
            "episode": str(int(match.group("episode"))),
            "episode_end": (
                str(int(match.group("episode_end")))
                if match.group("episode_end")
                else ""
            ),
        }

    def compare(
        self,
        local_payload: dict[str, Any] | None,
        ai_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        local = dict(local_payload or {})
        ai = dict(ai_result or {})
        structured = dict(ai.get("structured_recommendation") or {})
        ai_fields = dict(structured.get("fields") or ai.get("recommended_fields") or {})

        rows = []
        differences = 0
        conflict_fields=[]

        for key, label in self.FIELDS:
            local_value = self._text(local.get(key))
            ai_value = self._text(ai_fields.get(key))
            differs = bool(ai_value and local_value and local_value.casefold() != ai_value.casefold())
            if differs:
                differences += 1
                conflict_fields.append(key)
            rows.append({
                "field": key,
                "label": label,
                "local": local_value,
                "ai": ai_value,
                "different": differs,
            })

        # Also compare explicit SxxExx tokens in the actual names. This catches
        # contradictions even when structured fields are missing/empty.
        local_name = (
            local.get("proposed_name")
            or local.get("original_name")
            or local.get("source_path")
            or ""
        )
        ai_name = (
            structured.get("suggested_name")
            or ai.get("suggested_name")
            or ""
        )
        local_ep=self._episode_from_name(local_name)
        ai_ep=self._episode_from_name(ai_name)
        name_episode_conflicts=[]
        if local_ep and ai_ep:
            for key,label in (("season","Staffel"),("episode","Episode"),("episode_end","Episode-Ende")):
                lv=str(local_ep.get(key) or "")
                av=str(ai_ep.get(key) or "")
                if lv and av and lv != av:
                    differences += 1
                    conflict_fields.append(key)
                    name_episode_conflicts.append({
                        "field":key,
                        "label":label,
                        "local":lv,
                        "ai":av,
                    })

        # Provider may already report conflicts found while protecting local
        # filename anchors.
        provider_conflicts=list(
            structured.get("conflicts")
            or ai.get("conflicts")
            or []
        )
        if provider_conflicts:
            differences += len(provider_conflicts)
            for item in provider_conflicts:
                key=str((item or {}).get("field") or "")
                if key:
                    conflict_fields.append(key)

        local_confidence = self._confidence(
            local.get("decision_confidence") or local.get("confidence")
        )
        ai_confidence = self._confidence(
            structured.get("confidence") or ai.get("confidence")
        )

        candidate_id = self._text(
            structured.get("candidate_id")
            or ai.get("recommended_candidate_id")
        )
        candidate_valid = bool(
            structured.get("candidate_valid")
            if "candidate_valid" in structured
            else bool(candidate_id)
        )

        if not ai.get("available"):
            status = "no_ai"
            summary = "Kein KI-Provider verfügbar."
        elif differences:
            labels={
                "season":"Staffel",
                "episode":"Episode",
                "episode_end":"Episode-Ende",
                "media_type":"Medientyp",
                "title":"Titel",
                "year":"Jahr",
            }
            hard_conflict = bool(name_episode_conflicts or provider_conflicts)
            names=[]
            for key in conflict_fields:
                label=labels.get(key,key)
                if label not in names:
                    names.append(label)
            suffix=(" ("+", ".join(names)+")") if names else ""
            if hard_conflict:
                status = "conflict"
                summary=f"Konflikt: {differences} Abweichung(en){suffix}."
            else:
                status = "different"
                summary=f"Abweichung: {differences} Feld(er){suffix}."
        else:
            status = "agree"
            summary = "Lokale Erkennung und KI-Empfehlung stimmen in den belegten Feldern überein."

        return {
            "status": status,
            "summary": summary,
            "differences": differences,
            "conflict_fields": list(dict.fromkeys(conflict_fields)),
            "name_episode_conflicts": name_episode_conflicts,
            "provider_conflicts": provider_conflicts,
            "fields": rows,
            "local_confidence": local_confidence,
            "ai_confidence": ai_confidence,
            "candidate_id": candidate_id,
            "candidate_valid": candidate_valid,
            "rationale": self._text(
                structured.get("rationale") or ai.get("rationale")
            ),
            "suggested_name": self._text(ai_name),
            "advisory_only": True,
            "automatic_apply_allowed": False,
            "execution_allowed": False,
            "human_confirmation_required": True,
        }

    def format_text(self, comparison: dict[str, Any] | None) -> str:
        result = dict(comparison or {})
        if not result:
            return ""

        lines = [
            "",
            "Lokale Erkennung ↔ KI-Empfehlung:",
            "Status: " + str(result.get("summary") or "—"),
            (
                "Confidence lokal/KI: "
                f"{float(result.get('local_confidence') or 0)*100:.0f}% / "
                f"{float(result.get('ai_confidence') or 0)*100:.0f}%"
            ),
        ]

        if result.get("candidate_id"):
            validity = "gültig" if result.get("candidate_valid") else "ungültig"
            lines.append("KI-Kandidat: " + str(result.get("candidate_id")) + f" ({validity})")

        for item in result.get("fields") or []:
            local_value = str(item.get("local") or "—")
            ai_value = str(item.get("ai") or "—")
            if not item.get("ai"):
                continue
            marker = " ≠ " if item.get("different") else " = "
            lines.append(str(item.get("label") or item.get("field") or "Feld") + ": " + local_value + marker + ai_value)

        for item in result.get("name_episode_conflicts") or []:
            lines.append(
                "Namenskonflikt "
                + str(item.get("label") or item.get("field") or "")
                + ": "
                + str(item.get("local") or "—")
                + " ≠ "
                + str(item.get("ai") or "—")
            )

        if result.get("suggested_name"):
            lines.append("KI-Namensvorschlag: " + str(result["suggested_name"]))
        if result.get("rationale"):
            lines.append("KI-Begründung: " + str(result["rationale"]))

        lines.extend(["", "Nur Vergleich · keine automatische Übernahme."])
        return "\n".join(lines)
