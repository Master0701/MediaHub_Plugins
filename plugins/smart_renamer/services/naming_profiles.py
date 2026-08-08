from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class NamingProfile:
    profile_id: str
    display_name: str
    multi_episode_template: str
    split_episode_template: str
    split_movie_template: str
    custom_fields: dict[str, str] = field(default_factory=dict)


BUILTIN_PROFILES = {
    "plex": NamingProfile(
        profile_id="plex",
        display_name="Plex",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - pt{part_number}",
        split_movie_template="{title} ({year}) - pt{part_number}",
    ),
    "jellyfin": NamingProfile(
        profile_id="jellyfin",
        display_name="Jellyfin",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
    ),
    "emby": NamingProfile(
        profile_id="emby",
        display_name="Emby",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
    ),
    "kodi": NamingProfile(
        profile_id="kodi",
        display_name="Kodi",
        multi_episode_template="{title} - S{season}E{episode_start}-E{episode_end}",
        split_episode_template="{title} - S{season}E{episode_start} - part{part_number}",
        split_movie_template="{title} ({year}) - part{part_number}",
    ),
}


class NamingProfileService:
    def list_profiles(self) -> list[NamingProfile]:
        return list(BUILTIN_PROFILES.values())

    def get_profile(self, profile_id: str) -> NamingProfile:
        profile_id = (profile_id or "").strip().casefold()
        if profile_id not in BUILTIN_PROFILES:
            raise KeyError(f"Unbekanntes Namensprofil: {profile_id}")
        return BUILTIN_PROFILES[profile_id]

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
