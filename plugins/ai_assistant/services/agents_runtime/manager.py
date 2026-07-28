from __future__ import annotations

from typing import Any

from services.agents_runtime.models import AgentStatus
from services.agents_runtime.registry import AgentRegistry


class AgentManager:
    def __init__(self, capability_manager):
        self.capability_manager = capability_manager
        self.registry = AgentRegistry()

    def status(self) -> dict[str, Any]:
        capability_status = self.capability_manager.status()
        capabilities = capability_status.get("capabilities") or {}
        agents = []

        for definition in self.registry.all():
            capability = dict(capabilities.get(definition.capability) or {})
            missing = list(capability.get("missing_tools") or [])
            capability_available = bool(capability.get("available"))

            available = bool(
                definition.implemented
                and capability_available
                and not missing
            )

            if not definition.implemented:
                reason = "Agent ist registriert, aber noch nicht angebunden."
            elif missing:
                reason = "Fehlende Werkzeuge: " + ", ".join(missing)
            elif not capability_available:
                reason = "Benötigte Fähigkeit ist nicht verfügbar."
            else:
                reason = ""

            agents.append(
                AgentStatus(
                    definition=definition,
                    available=available,
                    missing_tools=missing,
                    reason=reason,
                ).as_dict()
            )

        return {
            "total": len(agents),
            "available": sum(1 for item in agents if item["available"]),
            "implemented": sum(1 for item in agents if item["implemented"]),
            "pending": sum(1 for item in agents if not item["implemented"]),
            "parallel_capable": sum(
                1 for item in agents if item["can_run_parallel"]
            ),
            "agents": agents,
        }

    def candidates_for_capability(
        self,
        capability: str,
    ) -> list[dict[str, Any]]:
        status = self.status()
        return [
            item
            for item in status["agents"]
            if item["capability"] == capability
        ]
