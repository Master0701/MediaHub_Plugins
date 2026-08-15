from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class RenameReviewProvider:
    """Local, read-only rename review used through MediaHub capabilities.

    Explicit SxxExx/Ep markers in the current/proposed filename are treated as
    strong local evidence. A weaker candidate must not silently change them.
    """

    FIELD_NAMES = (
        "media_type", "title", "year", "season", "episode",
        "episode_end", "episode_title", "edition", "part",
    )
    EPISODE_RE = re.compile(
        r"(?i)(?:^|[\s._-])s(?P<season>\d{1,3})e(?P<episode>\d{1,3})"
        r"(?:e(?P<episode_end>\d{1,3}))?"
    )

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value or 0.0)))
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _episode_anchor(cls, source: dict[str, Any]) -> dict[str, str]:
        for key in ("proposed_name", "current_name", "original_name", "source_path"):
            value = str(source.get(key) or "")
            if not value:
                continue
            match = cls.EPISODE_RE.search(Path(value).stem)
            if match:
                return {
                    "season": str(int(match.group("season"))),
                    "episode": str(int(match.group("episode"))),
                    "episode_end": (
                        str(int(match.group("episode_end")))
                        if match.group("episode_end")
                        else ""
                    ),
                }

        renamer = dict(source.get("renamer") or {})
        if renamer.get("season") not in (None, "") and renamer.get("episode") not in (None, ""):
            return {
                "season": str(renamer.get("season") or ""),
                "episode": str(renamer.get("episode") or ""),
                "episode_end": str(renamer.get("episode_end") or ""),
            }
        return {}

    @classmethod
    def _replace_episode_token(cls, name: str, anchor: dict[str, str]) -> str:
        if not name or not anchor:
            return str(name or "")
        season = int(anchor["season"])
        episode = int(anchor["episode"])
        token = f"S{season:02d}E{episode:02d}"
        if anchor.get("episode_end"):
            token += f"E{int(anchor['episode_end']):02d}"

        if cls.EPISODE_RE.search(Path(name).stem):
            return cls.EPISODE_RE.sub(
                lambda m: (m.group(0)[: len(m.group(0)) - len(m.group(0).lstrip(" ._-"))] + token),
                name,
                count=1,
            )
        return name

    def analyze(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        source = dict(payload or {})
        candidates = [dict(item or {}) for item in (source.get("candidates") or [])]
        selected_id = str(source.get("selected_candidate_id") or "")
        selected = next(
            (item for item in candidates if str(item.get("candidate_id") or "") == selected_id),
            None,
        )
        if selected is None and candidates:
            selected = max(candidates, key=lambda item: self._confidence(item.get("confidence")))
        selected = dict(selected or {})

        renamer = dict(source.get("renamer") or {})
        anchor = self._episode_anchor(source)

        fields = {}
        for key in self.FIELD_NAMES:
            value = selected.get(key)
            if value in (None, ""):
                value = renamer.get(key)
            fields[key] = str(value or "")

        warnings = []
        conflicts = []

        # Strong explicit filename/local anchor wins over a conflicting
        # unverified candidate for season/episode.
        for key in ("season", "episode", "episode_end"):
            anchor_value = str(anchor.get(key) or "")
            candidate_value = str(fields.get(key) or "")
            if not anchor_value:
                continue
            if candidate_value and candidate_value != anchor_value:
                conflicts.append({
                    "field": key,
                    "candidate": candidate_value,
                    "local_anchor": anchor_value,
                })
                warnings.append(
                    f"KI-Kandidat wollte {key}={candidate_value}, "
                    f"lokaler Dateiname belegt aber {key}={anchor_value}; "
                    "lokaler Anker wurde beibehalten."
                )
            fields[key] = anchor_value

        confidence = self._confidence(selected.get("confidence") or renamer.get("confidence"))
        candidate_id = str(selected.get("candidate_id") or "")
        reasons = [str(item) for item in (selected.get("reasons") or []) if str(item)]
        rationale = "; ".join(reasons) or (
            "Lokale MediaHub-KI-Review hat den plausibelsten vorhandenen Kandidaten bewertet."
        )
        if conflicts:
            rationale += " Konfliktierende Staffel-/Episodenwerte wurden nicht übernommen."

        suggested_name = str(source.get("proposed_name") or "")
        suggested_name = self._replace_episode_token(suggested_name, anchor)

        return {
            "provider": "MediaHub KI-Assistent",
            "recommendation": (
                "review_conflict" if conflicts
                else ("review_candidate" if candidate_id else "review_local")
            ),
            "suggested_name": suggested_name,
            "relation_type": str(renamer.get("relation_type") or ""),
            "confidence": confidence,
            "rationale": rationale,
            "warnings": warnings,
            "candidate_id": candidate_id,
            "local_episode_anchor": dict(anchor),
            "conflicts": conflicts,
            "structured_recommendation": {
                "candidate_id": candidate_id,
                "candidate_valid": bool(candidate_id),
                "fields": fields,
                "confidence": confidence,
                "rationale": rationale,
                "suggested_name": suggested_name,
                "recommendation": (
                    "review_conflict" if conflicts
                    else ("review_candidate" if candidate_id else "review_local")
                ),
                "local_episode_anchor": dict(anchor),
                "conflicts": conflicts,
            },
            "execution_allowed": False,
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
        }
