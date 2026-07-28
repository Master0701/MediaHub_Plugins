from __future__ import annotations

from services.agents_runtime.models import AgentDefinition


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentDefinition] = {}
        self._register_defaults()

    def register(self, definition: AgentDefinition) -> None:
        self._agents[definition.id] = definition

    def get(self, agent_id: str) -> AgentDefinition | None:
        return self._agents.get(str(agent_id))

    def all(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    def for_capability(self, capability: str) -> list[AgentDefinition]:
        return [
            definition
            for definition in self._agents.values()
            if definition.capability == capability
        ]

    def _register_defaults(self) -> None:
        defaults = (
            AgentDefinition(
                id="filename_agent",
                name="Dateiname-Agent",
                capability="media.basic_analysis",
                task_type="media.analyze",
                implemented=True,
                category="local",
                can_run_parallel=True,
                description="Erkennt Titel-, Staffel- und Episodenmuster.",
            ),
            AgentDefinition(
                id="folder_agent",
                name="Ordner-Agent",
                capability="media.basic_analysis",
                task_type="media.analyze",
                implemented=True,
                category="local",
                can_run_parallel=True,
                description="Wertet Ordnernamen und Bibliotheksstruktur aus.",
            ),
            AgentDefinition(
                id="ffprobe_agent",
                name="FFprobe-Agent",
                capability="media.basic_analysis",
                task_type="media.analyze",
                required_tools=("ffprobe",),
                implemented=True,
                category="technical",
                can_run_parallel=True,
                description="Liest technische Stream- und Laufzeitdaten.",
            ),
            AgentDefinition(
                id="mediainfo_agent",
                name="MediaInfo-Agent",
                capability="media.basic_analysis",
                task_type="media.analyze",
                required_tools=("mediainfo",),
                implemented=True,
                category="technical",
                can_run_parallel=True,
                description="Liest Container-, HDR-, Audio- und Tag-Daten.",
            ),
            AgentDefinition(
                id="frame_agent",
                name="Frame-Agent",
                capability="media.frame_analysis",
                task_type="media.frame_analysis",
                required_tools=("ffmpeg", "ffprobe"),
                implemented=True,
                category="in_video",
                can_run_parallel=True,
                description="Analysiert repräsentative Videoframes.",
            ),
            AgentDefinition(
                id="ocr_agent",
                name="OCR-Agent",
                capability="media.ocr",
                task_type="media.ocr",
                required_tools=("ffmpeg", "tesseract"),
                implemented=True,
                category="in_video",
                can_run_parallel=True,
                description="Erkennt Titelkarten und eingeblendete Texte.",
            ),
            AgentDefinition(
                id="audio_agent",
                name="Audio-Agent",
                capability="media.frame_analysis",
                task_type="media.audio",
                required_tools=("ffmpeg", "ffprobe"),
                implemented=True,
                category="in_video",
                can_run_parallel=True,
                description="Analysiert Lautstärke und Audiomerkmale.",
            ),
            AgentDefinition(
                id="subtitle_agent",
                name="Untertitel-Agent",
                capability="media.basic_analysis",
                task_type="media.subtitles",
                required_tools=("ffmpeg", "ffprobe"),
                implemented=True,
                category="in_video",
                can_run_parallel=True,
                description="Extrahiert und analysiert Textuntertitel.",
            ),
            AgentDefinition(
                id="fingerprint_agent",
                name="Fingerprint-Agent",
                capability="fingerprint.register",
                task_type="fingerprint.register",
                required_tools=("ffmpeg", "ffprobe"),
                implemented=True,
                category="identity",
                can_run_parallel=True,
                description="Erstellt normalisierte Video-Fingerprints.",
            ),
            AgentDefinition(
                id="scene_agent",
                name="Szenen-Agent",
                capability="media.frame_analysis",
                task_type="media.scenes",
                required_tools=("ffmpeg", "ffprobe"),
                implemented=True,
                category="in_video",
                can_run_parallel=True,
                description="Erkennt Szenenwechsel und markante Abschnitte.",
            ),
            AgentDefinition(
                id="knowledge_agent",
                name="Wissensdatenbank-Agent",
                capability="knowledge.search",
                task_type="knowledge.search",
                implemented=False,
                category="knowledge",
                description="Gleicht Medien mit Beziehungen und Reihen ab.",
            ),
            AgentDefinition(
                id="online_agent",
                name="Online-Provider-Agent",
                capability="knowledge.search",
                task_type="provider.search",
                implemented=False,
                category="network",
                description="Fragt konfigurierte Online-Quellen ab.",
            ),
            AgentDefinition(
                id="quality_agent",
                name="Qualitäts-Agent",
                capability="quality.evaluate",
                task_type="quality.evaluate",
                required_tools=("ffprobe", "mediainfo"),
                implemented=True,
                category="quality",
                description="Bewertet technische und gemessene Qualität.",
            ),
            AgentDefinition(
                id="supervisor_agent",
                name="Supervisor-Agent",
                capability="local_orchestration",
                task_type="decision.evaluate",
                implemented=False,
                category="decision",
                description="Bewertet Beweise und entscheidet über nächste Schritte.",
            ),
        )
        for definition in defaults:
            self.register(definition)
