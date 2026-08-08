from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class NamingProfile:
    profile_id: str
    display_name: str
    multi_episode_template: str
    split_episode_template: str
    split_movie_template: str
    custom_fields: dict[str, str] = field(default_factory=dict)
    builtin: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_PROFILES = {
    "plex": NamingProfile(
        profile_id="plex",
        display_name="Plex",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - pt{part_number}",
        split_movie_template="{title} ({year}) - pt{part_number}",
        builtin=True,
    ),
    "jellyfin": NamingProfile(
        profile_id="jellyfin",
        display_name="Jellyfin",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
        builtin=True,
    ),
    "emby": NamingProfile(
        profile_id="emby",
        display_name="Emby",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
        builtin=True,
    ),
    "kodi": NamingProfile(
        profile_id="kodi",
        display_name="Kodi",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
        builtin=True,
    ),
}


class NamingProfileService:
    def __init__(self, storage_path: Path | str | None = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self._custom_profiles: dict[str, NamingProfile] = {}
        if self.storage_path and self.storage_path.exists():
            self.load()

    def list_profiles(self) -> list[NamingProfile]:
        values = list(BUILTIN_PROFILES.values())
        values.extend(
            self._custom_profiles[key]
            for key in sorted(self._custom_profiles)
        )
        return values

    def get_profile(self, profile_id: str) -> NamingProfile:
        profile_id = (profile_id or "").strip().casefold()
        if profile_id in BUILTIN_PROFILES:
            return BUILTIN_PROFILES[profile_id]
        if profile_id in self._custom_profiles:
            return self._custom_profiles[profile_id]
        raise KeyError(f"Unbekanntes Namensprofil: {profile_id}")

    def save_custom_profile(
        self,
        *,
        profile_id: str,
        display_name: str,
        multi_episode_template: str,
        split_episode_template: str,
        split_movie_template: str,
        custom_fields: dict[str, str] | None = None,
    ) -> NamingProfile:
        profile_id = (profile_id or "").strip().casefold()
        if not profile_id:
            raise ValueError("profile_id darf nicht leer sein.")
        if profile_id in BUILTIN_PROFILES:
            raise ValueError("Eingebaute Profile können nicht überschrieben werden.")

        profile = NamingProfile(
            profile_id=profile_id,
            display_name=display_name.strip() or profile_id,
            multi_episode_template=multi_episode_template,
            split_episode_template=split_episode_template,
            split_movie_template=split_movie_template,
            custom_fields=dict(custom_fields or {}),
            builtin=False,
        )
        self._validate_profile(profile)
        self._custom_profiles[profile_id] = profile
        self.persist()
        return profile

    def delete_custom_profile(self, profile_id: str) -> bool:
        profile_id = (profile_id or "").strip().casefold()
        if profile_id in BUILTIN_PROFILES:
            raise ValueError("Eingebaute Profile können nicht gelöscht werden.")
        removed = self._custom_profiles.pop(profile_id, None) is not None
        if removed:
            self.persist()
        return removed

    def persist(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "profiles": [
                profile.to_dict()
                for profile in self._custom_profiles.values()
            ],
        }
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        profiles: dict[str, NamingProfile] = {}
        for raw in data.get("profiles", []):
            profile = NamingProfile(
                profile_id=str(raw["profile_id"]).strip().casefold(),
                display_name=str(raw.get("display_name") or raw["profile_id"]),
                multi_episode_template=str(raw["multi_episode_template"]),
                split_episode_template=str(raw["split_episode_template"]),
                split_movie_template=str(raw["split_movie_template"]),
                custom_fields=dict(raw.get("custom_fields") or {}),
                builtin=False,
            )
            self._validate_profile(profile)
            profiles[profile.profile_id] = profile
        self._custom_profiles = profiles

    def render_relation_name(
        self,
        profile_id: str,
        relation: dict,
        *,
        title: str,
        year: str = "",
        season: str = "",
    ) -> str:
        profile = self.get_profile(profile_id)
        relation_type = relation.get("relation_type", "single")
        values = {
            "title": title,
            "year": year,
            "season": str(season or "").zfill(2),
            "episode_start": str(
                relation.get("episode_start") or ""
            ).zfill(2),
            "episode_end": str(
                relation.get("episode_end") or ""
            ).zfill(2),
            "part_number": relation.get("part_number") or "",
            "part_count": relation.get("part_count") or "",
        }

        if relation_type == "multi_episode":
            template = profile.multi_episode_template
        elif relation_type == "split_episode":
            template = profile.split_episode_template
        elif relation_type == "split_movie":
            template = profile.split_movie_template
        else:
            raise ValueError(
                f"Für relation_type={relation_type!r} gibt es kein "
                "Relations-Namensschema."
            )

        return template.format(**values).strip()

    @staticmethod
    def _validate_profile(profile: NamingProfile) -> None:
        required = {
            "multi_episode_template": profile.multi_episode_template,
            "split_episode_template": profile.split_episode_template,
            "split_movie_template": profile.split_movie_template,
        }
        for field_name, template in required.items():
            if "{title}" not in template:
                raise ValueError(
                    f"{field_name} muss den Platzhalter {{title}} enthalten."
                )
