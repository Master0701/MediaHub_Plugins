from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ProfileService:
    def __init__(self, plugin_path: Path):
        self.profile_dir = Path(plugin_path) / "profiles"

    def list_profiles(self) -> list[dict[str, Any]]:
        profiles = []
        for path in sorted(self.profile_dir.glob("*.json")):
            profile = self.load_profile(path.stem)
            if profile:
                profiles.append(profile)
        return profiles

    def load_profile(self, profile_id: str) -> dict[str, Any] | None:
        path = self.profile_dir / f"{profile_id}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("id", profile_id)
        data.setdefault("rules", [])
        return data
