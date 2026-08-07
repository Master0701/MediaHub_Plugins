from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .loader import LoadedPlugin


@dataclass(frozen=True, slots=True)
class SelectionPolicy:
    """
    Laufzeit-Policy des Orchestrators.

    Diese Werte sind KEINE Plugin-Capabilities und werden nicht in
    plugin.json dupliziert. Sie steuern nur die Auswahl zwischen mehreren
    bereits nutzbaren Plugins.
    """

    preferred_plugin_ids: tuple[str, ...] = ()
    priorities: Mapping[str, int] | None = None
    allow_fallback: bool = True

    def priority_for(self, plugin_id: str) -> int:
        if self.priorities is None:
            return 0
        return int(self.priorities.get(plugin_id, 0))

    def preference_index(self, plugin_id: str) -> int:
        try:
            return self.preferred_plugin_ids.index(plugin_id)
        except ValueError:
            return len(self.preferred_plugin_ids)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    plugin: LoadedPlugin
    priority: int
    preference_index: int


def rank_candidates(
    plugins: Sequence[LoadedPlugin],
    policy: SelectionPolicy | None = None,
) -> tuple[RankedCandidate, ...]:
    active_policy = policy or SelectionPolicy()

    ranked = [
        RankedCandidate(
            plugin=plugin,
            priority=active_policy.priority_for(
                plugin.manifest.plugin_id
            ),
            preference_index=active_policy.preference_index(
                plugin.manifest.plugin_id
            ),
        )
        for plugin in plugins
    ]

    ranked.sort(
        key=lambda item: (
            -item.priority,
            item.preference_index,
            item.plugin.manifest.plugin_id,
        )
    )
    return tuple(ranked)
