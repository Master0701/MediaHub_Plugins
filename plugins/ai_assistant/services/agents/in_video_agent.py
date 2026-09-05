from __future__ import annotations

from pathlib import Path
from typing import Any

from services.agents.audio_agent import AudioAgent
from services.agents.fingerprint_agent import FingerprintAgent
from services.agents.frame_agent import FrameAgent
from services.agents.ocr_agent import OCRAgent
from services.agents.scene_agent import SceneAgent
from services.agents.speech_recognition_agent import SpeechRecognitionAgent
from services.agents.subtitle_agent import SubtitleAgent
from services.visual_intelligence import VisualIntelligenceEngine


class InVideoAgent:
    """Führt eine begrenzte, echte Inhaltsanalyse mit zentral verwalteten Werkzeugen aus."""
    def __init__(
        self,
        tools=None,
        worker_provider=None,
    ):
        self.tools=tools
        self.frame=FrameAgent(); self.subtitle=SubtitleAgent(); self.audio=AudioAgent(); self.speech=SpeechRecognitionAgent(worker_provider=worker_provider); self.ocr=OCRAgent(); self.fingerprint=FingerprintAgent(); self.scene=SceneAgent(); self.visual=VisualIntelligenceEngine()

    def capabilities(self)->dict[str,Any]:
        return {"schema_version":3,"implemented":True,"implementation_level":"bounded_real_analysis","agents":[
            {"id":"frame","state":"active","purpose":"Reale Frame-Messwerte"},{"id":"subtitle","state":"active","purpose":"Textbeweise aus Untertiteln"},
            {"id":"ocr","state":"active_if_tesseract","purpose":"Titelkarten und Einblendungen"},{"id":"audio","state":"active","purpose":"Lautheit, Dynamik und Clipping"},{"id":"speech_recognition","state":"active_if_provider_available","purpose":"Sprachbasierte Identitätsevidenz"},
            {"id":"fingerprint","state":"active","purpose":"Reproduzierbarer Bildfingerprint"},{"id":"scene","state":"active","purpose":"Szenenwechsel-Stichprobe"},
            {"id":"quality","state":"active","purpose":"Technische und gemessene Bild-/Tonqualität"},{"id":"smart_frame_selection","state":"active","purpose":"Gezielte Auswahl scharfer Intro-, Handlungs- und Abspannbilder"},{"id":"visual_fingerprint","state":"active","purpose":"Toleranter Mehrbild-Fingerprint für lokale Inhaltsvergleiche"},{"id":"scene_signature","state":"active","purpose":"Normalisierte Szenenrhythmus-Signatur mit Intro-, Inhalt- und Outro-Verteilung"},{"id":"ocr_logo_fusion","state":"active","purpose":"Gemeinsame Bewertung von OCR-Text, Framequalität und Titelkartenposition"},{"id":"character_preparation","state":"active","purpose":"Anonyme Gruppierung wiederkehrender Zentralmotive ohne Gesichtserkennung oder Namenszuordnung"},{"id":"intro_outro_detection","state":"active","purpose":"Lokale multimodale Erkennung wahrscheinlicher Vorspann- und Abspannbereiche"},{"id":"visual_knowledge","state":"active_after_confirmation","purpose":"Bestätigte visuelle Signaturen dauerhaft mit Medienidentitäten verknüpfen"},{"id":"online_visual_provider","state":"disabled_by_default","purpose":"Optionale Suche mit ausdrücklich freigegebenen Einzelbildern; niemals komplettes Video"},{"id":"visual_pipeline_validation","state":"active","purpose":"Automatische Konsistenz-, Datenschutz- und Integrationsprüfung der vollständigen Visual-Pipeline"}],
            "shared_analysis":["ffprobe","mediainfo","frame_metrics","audio_metrics","speech_transcript","subtitles","ocr","fingerprints"],
            "edition_targets":["Uncut","Extended","Director's Cut","Theatrical Cut","Remastered"]}

    @staticmethod
    def _smart_sample_points(duration: float) -> list[float]:
        if duration <= 0:
            return [0.0, 3.0, 8.0, 15.0, 30.0]

        points = {
            0.0,
            min(3.0, duration),
            min(8.0, duration),
            min(15.0, duration),
            min(30.0, duration),
            min(60.0, duration),
            min(90.0, duration),
        }

        # Früher Vorspann und Titelkartenbereich.
        for ratio in (0.02, 0.04, 0.06, 0.08, 0.12):
            points.add(duration * ratio)

        # Repräsentative Handlungspunkte.
        for ratio in (0.20, 0.35, 0.50, 0.65, 0.80):
            points.add(duration * ratio)

        # Abspann, Studiologos und letzte Titelhinweise.
        for offset in (180.0, 90.0, 45.0, 15.0):
            points.add(max(0.0, duration - offset))

        normalized = sorted(
            {
                round(min(max(0.0, point), max(0.0, duration - 0.1)), 2)
                for point in points
            }
        )
        return normalized[:20]

    def _plan(self, analysis, required):
        summary = analysis.get("summary") or {}
        duration = float(summary.get("duration_seconds") or 0)
        chapters = int(summary.get("chapters") or 0)
        points = self._smart_sample_points(duration)

        return {
            "schema_version": 4,
            "required": bool(required),
            "sample_plan": {
                "strategy": "smart_temporal_sampling_v1",
                "fixed_seconds": points,
                "intro_candidates": [
                    point
                    for point in points
                    if point <= min(180.0, duration * 0.12)
                ],
                "outro_candidates": [
                    point
                    for point in points
                    if duration and point >= max(0.0, duration - 180.0)
                ],
                "chapter_starts": chapters,
                "scene_change_sampling": True,
                "maximum_frames": 20,
            },
        }

    def run(self,analysis:dict[str,Any],required:bool)->dict[str,Any]:
        plan=self._plan(analysis,required)
        if not required:
            return {**plan,"state":"deferred","reason":"Vorhandene Beweise reichen aus; Tiefenanalyse wurde eingespart."}
        path=Path((analysis.get("file") or {}).get("path") or "")
        summary=analysis.get("summary") or {}; duration=float(summary.get("duration_seconds") or 0)
        ffmpeg=self.tools.find("ffmpeg") if self.tools else None; tess=self.tools.find("tesseract") if self.tools else None
        pts=plan["sample_plan"]["fixed_seconds"]
        results={"frame_agent":self.frame.run(path,ffmpeg,pts),
                 "subtitle_agent":self.subtitle.run(path,ffmpeg,int(summary.get("subtitle_tracks") or 0)),
                 "audio_agent":self.audio.run(path,ffmpeg,duration),
                 "speech_recognition_agent":self.speech.run(path,ffmpeg,duration),
                 "ocr_agent":self.ocr.run(path,ffmpeg,tess,pts),
                 "fingerprint_agent":self.fingerprint.run(path,ffmpeg,duration),
                 "scene_agent":self.scene.run(path,ffmpeg,duration)}
        completed=sum(1 for v in results.values() if v.get("state")=="completed")
        base={**plan,"state":"completed" if completed else "partial","completed_agents":completed,"agents":results,
              "quality_agent":{"active":True,"uses_same_samples":True}}
        base["visual_intelligence"] = self.visual.analyze(base, duration)
        return base

    def plan(self,analysis:dict[str,Any],required:bool)->dict[str,Any]:
        return self.run(analysis,required)
