from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from mediahub_smart_renamer_runtime.services.naming_profiles import NamingProfileService


@dataclass(slots=True)
class RelationPreview:
    source_path: str
    relation_type: str
    profile_id: str
    profile_name: str
    current_name: str
    suggested_name: str
    recommended_action: str
    confidence: float
    review_required: bool
    evidence: list[str]
    warnings: list[str]
    options: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RelationPreviewService:
    def __init__(
        self,
        profile_service: NamingProfileService | None = None,
    ):
        self.profile_service = profile_service or NamingProfileService()

    def build_preview(
        self,
        item,
        *,
        profile_id: str = "plex",
    ) -> RelationPreview:
        relation = dict(
            (item.detection_data or {}).get("media_relation") or {}
        )
        relation_type = relation.get("relation_type", "single")
        profile = self.profile_service.get_profile(profile_id)

        suggested_name = ""
        warnings: list[str] = []
        options: list[str] = []

        if relation_type in {"multi_episode", "split_episode", "split_movie"}:
            suggested_base = self.profile_service.render_relation_name(
                profile_id,
                relation,
                title=item.title or Path(item.path).stem,
                year=item.year or "",
                season=item.season or "",
            )
            suggested_name = suggested_base + item.extension

        action = relation.get("recommended_action", "none")

        if relation_type == "multi_episode":
            warnings.append(
                "Eine Datei enthält vermutlich mehrere Episoden. "
                "Vor einer Umbenennung muss bestätigt werden, ob die "
                "Episoden wirklich gemeinsam in dieser Datei enthalten sind."
            )
            options.extend([
                "nur_umbenennen",
                "als_multi_episode_beibehalten",
                "split_kandidat",
                "manuell_pruefen",
            ])
        elif relation_type == "split_episode":
            warnings.append(
                "Eine Episode scheint auf mehrere Dateien verteilt zu sein."
            )
            options.extend([
                "profilkonform_benennen",
                "merge_kandidat",
                "manuell_pruefen",
            ])
        elif relation_type == "split_movie":
            warnings.append(
                "Ein Film scheint auf mehrere Dateien verteilt zu sein."
            )
            options.extend([
                "profilkonform_benennen",
                "merge_kandidat",
                "manuell_pruefen",
            ])
        elif relation.get("missing_episode_candidates"):
            warnings.append(
                "Es gibt eine Episodenlücke. Das beweist weder, dass die "
                "Episode fehlt, noch dass sie in einer anderen Datei steckt."
            )
            options.extend([
                "als_fehlend_markieren_nach_bestaetigung",
                "in_multi_episode_enthalten_pruefen",
                "manuell_pruefen",
            ])

        if relation.get("review_required"):
            warnings.append("Review erforderlich: keine automatische Ausführung.")

        return RelationPreview(
            source_path=str(item.path),
            relation_type=relation_type,
            profile_id=profile.profile_id,
            profile_name=profile.display_name,
            current_name=Path(item.path).name,
            suggested_name=suggested_name,
            recommended_action=action,
            confidence=float(relation.get("confidence") or 0),
            review_required=bool(relation.get("review_required")),
            evidence=list(relation.get("evidence") or []),
            warnings=warnings,
            options=options,
        )

    def build_many(
        self,
        items,
        *,
        profile_id: str = "plex",
    ) -> list[dict[str, Any]]:
        return [
            self.build_preview(item, profile_id=profile_id).to_dict()
            for item in items
            if (item.detection_data or {}).get("media_relation")
        ]
