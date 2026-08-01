from __future__ import annotations

from copy import deepcopy
from typing import Any


class AssistantIntegrationAPI:
    """Stabile, schreibgeschützte Übergabe an Metadata Editor und Universal Renamer."""

    SCHEMA_VERSION = 3

    @classmethod
    def build(cls, analysis: dict[str, Any]) -> dict[str, Any]:
        identification = analysis.get("identification") or {}
        decision = analysis.get("decision") or {}
        quality = analysis.get("quality") or {}
        semantic = analysis.get("semantic_identity") or {}
        semantic_identity = semantic.get("identity") or {}
        return {
            "schema_version": cls.SCHEMA_VERSION,
            "producer": "mediahub.ai_assistant",
            "producer_version": "2.2.9",
            "source": deepcopy(analysis.get("file") or {}),
            "identity": {
                "media_type": semantic_identity.get("media_type") or decision.get("media_type") or identification.get("media_type"),
                "title": semantic_identity.get("title") or decision.get("title_candidate") or identification.get("title_candidate"),
                "year": semantic_identity.get("year") or identification.get("year"),
                "season": semantic_identity.get("season") or decision.get("season"),
                "episodes": (
                    [semantic_identity.get("episode")]
                    if semantic_identity.get("episode") is not None
                    else deepcopy(decision.get("episodes") or [])
                ),
                "edition": semantic_identity.get("edition") or identification.get("edition_candidate"),
                "confidence": semantic.get("confidence") if semantic else decision.get("confidence"),
                "status": semantic.get("final_status") if semantic else decision.get("status"),
                "needs_user_confirmation": semantic.get("needs_user_confirmation"),
                "allow_learning": semantic.get("allow_learning"),
            },
            "explanation": deepcopy(decision.get("explanation") or {}),
            "quality": {
                "overall_score": quality.get("overall_score"),
                "status": quality.get("status"),
                "label": quality.get("label"),
                "recommendation": deepcopy(quality.get("recommendation") or {}),
            },
            "proposed_actions": {
                "metadata_editor": deepcopy((analysis.get("change_plan") or {}).get("metadata") or {}),
                "universal_renamer": deepcopy((analysis.get("change_plan") or {}).get("rename") or {}),
            },
            "safety": {
                "automatic_change_allowed": False,
                "preview_required": True,
                "confirmation_required": True,
            },
        }
