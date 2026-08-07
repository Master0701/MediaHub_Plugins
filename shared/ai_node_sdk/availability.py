from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .loader import LoadedPlugin


@dataclass(frozen=True, slots=True)
class PluginRuntimeStatus:
    installed: bool = True
    enabled: bool = True
    reachable: bool = True
    healthy: bool = True
    platform_compatible: bool = True

    @property
    def usable(self) -> bool:
        return (
            self.installed
            and self.enabled
            and self.reachable
            and self.healthy
            and self.platform_compatible
        )


@dataclass(frozen=True, slots=True)
class AvailabilityResult:
    usable: bool
    reason: str = ""
    missing_tools: tuple[str, ...] = ()


def check_availability(
    plugin: LoadedPlugin,
    *,
    runtime: PluginRuntimeStatus,
    available_tools: Iterable[str] = (),
) -> AvailabilityResult:
    if not runtime.installed:
        return AvailabilityResult(False, "Plugin ist nicht installiert.")
    if not runtime.enabled:
        return AvailabilityResult(False, "Plugin ist deaktiviert.")
    if not runtime.reachable:
        return AvailabilityResult(False, "Plugin ist nicht erreichbar.")
    if not runtime.healthy:
        return AvailabilityResult(False, "Plugin-Health-Check ist fehlgeschlagen.")
    if not runtime.platform_compatible:
        return AvailabilityResult(False, "Plugin ist auf dieser Plattform nicht kompatibel.")

    available = {str(item).strip() for item in available_tools if str(item).strip()}
    missing = tuple(
        tool
        for tool in plugin.manifest.required_tools
        if tool not in available
    )

    if missing:
        return AvailabilityResult(
            False,
            "Benötigte Tools fehlen.",
            missing_tools=missing,
        )

    return AvailabilityResult(True)
