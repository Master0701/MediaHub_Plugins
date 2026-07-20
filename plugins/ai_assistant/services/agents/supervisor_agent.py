from __future__ import annotations

from typing import Any


class SupervisorAgent:
    """Entscheidet, welche weiteren Erkennungsstufen für einen Fall nötig sind."""

    ONLINE_THRESHOLD = 0.90
    IN_VIDEO_THRESHOLD = 0.72

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        confidence = float(identification.get("confidence") or 0.0)
        title = str(identification.get("title_candidate") or "").strip()
        external_lookup = bool(identification.get("requires_external_lookup", False))

        steps: list[dict[str, Any]] = []
        if external_lookup or confidence < self.ONLINE_THRESHOLD:
            steps.append({"agent": "online", "required": True, "reason": "Lokale Erkennung ist noch nicht eindeutig genug."})

        unusable_name = not title or title.lower() in {"video", "movie", "film", "episode", "unknown"}
        if unusable_name or confidence < self.IN_VIDEO_THRESHOLD:
            steps.append({
                "agent": "in_video",
                "required": True,
                "reason": "Datei-/Ordnerhinweise reichen nicht aus; Bild, OCR, Untertitel und Audio sollen zusätzliche Beweise liefern.",
            })
        else:
            steps.append({
                "agent": "in_video",
                "required": False,
                "reason": "Für normale Analyse zurückgestellt; bei Widersprüchen oder Schnittfassungsprüfung aktivierbar.",
            })

        return {
            "schema_version": 1,
            "local_confidence": confidence,
            "decision_status": "needs_more_evidence" if any(step["required"] for step in steps) else "locally_sufficient",
            "next_steps": steps,
            "automatic_execution": False,
        }
