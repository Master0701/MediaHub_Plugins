from __future__ import annotations

from typing import Any

from services.agent_costs import AgentCostModel


class SupervisorAgent:
    """Plant weitere Agentenstufen nach Sicherheit, Nutzen und Aufwand."""

    ONLINE_THRESHOLD = 0.90
    IN_VIDEO_THRESHOLD = 0.72
    FINAL_THRESHOLD = 0.92

    def __init__(self):
        self.costs = AgentCostModel()

    def evaluate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        confidence = float(identification.get("confidence") or 0.0)
        title = str(identification.get("title_candidate") or "").strip()
        external_lookup = bool(identification.get("requires_external_lookup", False))
        online = analysis.get("online") or {}
        online_ranking = online.get("ranking") or {}
        online_confidence = float(online_ranking.get("confidence") or 0.0)
        combined_confidence = max(confidence, online_confidence)

        unusable_name = not title or title.lower() in {"video", "movie", "film", "episode", "unknown"}
        steps: list[dict[str, Any]] = []

        if not online.get("executed") and (external_lookup or confidence < self.ONLINE_THRESHOLD):
            steps.append(self.costs.decorate({
                "agent": "online",
                "required": True,
                "state": "pending",
                "reason": "Lokale Erkennung ist noch nicht eindeutig genug.",
            }))
        elif online.get("executed"):
            steps.append(self.costs.decorate({
                "agent": "online",
                "required": False,
                "state": "completed",
                "reason": f"Online-Abgleich ausgeführt; Sicherheit {round(online_confidence * 100)} %.",
            }))

        in_video_required = unusable_name or combined_confidence < self.IN_VIDEO_THRESHOLD
        if online.get("executed") and online_ranking.get("decision") in {"no_match", "ambiguous"}:
            in_video_required = True

        steps.append(self.costs.decorate({
            "agent": "in_video",
            "required": in_video_required,
            "state": "pending" if in_video_required else "deferred",
            "reason": (
                "Datei-, Ordner- und Online-Hinweise reichen nicht aus; Bild, OCR, Untertitel und Audio sollen zusätzliche Beweise liefern."
                if in_video_required
                else "Aufwendige Videoanalyse bleibt zurückgestellt und wird erst bei Widersprüchen oder Editionsprüfung aktiviert."
            ),
        }))

        required = [step for step in steps if step["required"]]
        if combined_confidence >= self.FINAL_THRESHOLD and not required:
            decision_status = "sufficient"
        elif required:
            decision_status = "needs_more_evidence"
        else:
            decision_status = "review_recommended"

        return {
            "schema_version": 2,
            "local_confidence": confidence,
            "online_confidence": online_confidence,
            "combined_confidence": combined_confidence,
            "decision_status": decision_status,
            "next_steps": steps,
            "estimated_remaining_cost": sum(step["cost"] for step in required),
            "automatic_execution": True,
            "cost_scale": self.costs.describe(),
        }
