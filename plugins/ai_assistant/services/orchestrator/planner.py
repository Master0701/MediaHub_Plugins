from __future__ import annotations

from typing import Any

from services.orchestrator.models import (
    OrchestratorPlan,
    OrchestratorStep,
    StepState,
)


class LocalOrchestratorPlanner:
    REQUEST_STEPS = {
        "media.identify": (
            ("basic_analysis", "Technische Medienanalyse", "media.analyze", "media.basic_analysis"),
            ("frame_analysis", "Frame- und Bildanalyse", "media.frame_analysis", "media.frame_analysis"),
            ("ocr_analysis", "Texterkennung im Video", "media.ocr", "media.ocr"),
            ("knowledge_search", "Abgleich mit der Wissensdatenbank", "knowledge.search", "knowledge.search"),
            ("fingerprint", "Fingerprint-Abgleich", "fingerprint.register", "fingerprint.register"),
        ),
        "media.analyze": (
            ("basic_analysis", "Technische Medienanalyse", "media.analyze", "media.basic_analysis"),
        ),
    }

    def __init__(self, capability_manager):
        self.capability_manager = capability_manager

    def create_plan(self, request_type: str, payload: dict[str, Any]) -> OrchestratorPlan:
        plan = OrchestratorPlan(request_type=str(request_type), payload=dict(payload))
        definitions = self.REQUEST_STEPS.get(
            plan.request_type,
            self.REQUEST_STEPS["media.analyze"],
        )
        known = (self.capability_manager.status().get("capabilities") or {})

        for step_id, title, task_type, capability in definitions:
            item = dict(known.get(capability) or {})
            available = bool(item.get("available"))
            required_tools = list(
                item.get("required_tools")
                or self.capability_manager.required_tools_for(capability)
            )
            missing_tools = list(item.get("missing_tools") or [])
            step = OrchestratorStep(
                id=step_id,
                title=title,
                task_type=task_type,
                capability=capability,
                required_tools=required_tools,
                state=StepState.READY if available else StepState.BLOCKED,
                reason="" if available else "Fehlende Werkzeuge: " + ", ".join(missing_tools),
            )
            plan.steps.append(step)
            if step.state is StepState.BLOCKED:
                plan.warnings.append(f"{step.title} ist blockiert: {step.reason}")

        return plan
