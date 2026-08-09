from __future__ import annotations

from copy import deepcopy
from typing import Iterable

PROFILE_SOURCES={"profil","profile"}

def _source(rule: dict) -> str:
    return str((rule or {}).get("source") or "").strip().casefold()

def _kind(rule: dict) -> str:
    return str((rule or {}).get("type") or "").strip().casefold()

def order_rules_for_final_name(rules: Iterable[dict]) -> list[dict]:
    values=[deepcopy(dict(rule or {})) for rule in (rules or [])]
    profile_schema=[
        rule for rule in values
        if _source(rule) in PROFILE_SOURCES and _kind(rule)=="schema"
    ]
    profile_other=[
        rule for rule in values
        if _source(rule) in PROFILE_SOURCES and _kind(rule)!="schema"
    ]
    custom=[
        rule for rule in values
        if _source(rule) not in PROFILE_SOURCES
    ]
    return profile_schema + profile_other + custom
