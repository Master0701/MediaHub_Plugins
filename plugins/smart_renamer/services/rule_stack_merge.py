from __future__ import annotations

from copy import deepcopy
from typing import Iterable

PROFILE_SOURCES={"profil","profile"}

def is_profile_rule(rule: dict) -> bool:
    return str((rule or {}).get("source") or "").strip().casefold() in PROFILE_SOURCES

def merge_profile_rules(existing_rules: Iterable[dict], profile_rules: Iterable[dict]) -> list[dict]:
    """
    Replace only profile rules.

    Execution order is intentional:
    1) active profile rules create the profile-compliant target name
    2) user / AI / plugin / ReNamer rules modify that result afterwards

    This means custom rules remain visible in the preview while Plex,
    Jellyfin, Emby or Kodi is active.
    """
    existing=[deepcopy(dict(rule or {})) for rule in (existing_rules or [])]
    incoming=[deepcopy(dict(rule or {})) for rule in (profile_rules or [])]

    for rule in incoming:
        rule.setdefault("enabled",True)
        rule["source"]="Profil"

    persistent=[rule for rule in existing if not is_profile_rule(rule)]
    return incoming + persistent
