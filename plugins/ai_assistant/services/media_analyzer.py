from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from services.agents import InVideoAgent, OnlineAgent, SupervisorAgent
from services.analysis_cache import AnalysisCache
from services.decision_engine import DecisionEngine
from services.decision_planner import DecisionPlanner
from services.filename_identifier import FilenameIdentifier
from services.fingerprint_store import FingerprintReferenceStore
from services.integration_api import AssistantIntegrationAPI
from services.semantic_identity import (
    IdentityCandidateBuilder,
    IdentityEvidenceCollector,
    IdentityContradictionDetector,
    IdentityConfidenceCalculator,
    IdentityDecisionExplainer,
    SemanticIdentityEngine,
)
from services.quality_engine import QualityEngine, QualityProfileStore
from services.source_manager import SourceManager
from services.tool_resolver import ToolResolver

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".m2ts",
    ".webm", ".wmv", ".mpg", ".mpeg"
}


class MediaAnalyzer:
    """Schnelle technische Analyse mit MediaInfo, ffprobe und Cache."""

    def __init__(
        self,
        mediahub_base: Path,
        knowledge_database_path: Path | None = None,
        plugin_path: Path | None = None,
    ):
        self.tools = ToolResolver(mediahub_base, plugin_path)
        self.filename_identifier = FilenameIdentifier()
        self.decision_planner = DecisionPlanner()
        self.source_manager = SourceManager(plugin_path, knowledge_database_path) if plugin_path is not None else None
        self.supervisor = SupervisorAgent()
        self.in_video_agent = InVideoAgent(self.tools)
        self.quality_engine = QualityEngine(QualityProfileStore(knowledge_database_path))
        self.fingerprint_store = FingerprintReferenceStore(knowledge_database_path)
        self.decision_engine = DecisionEngine(self.fingerprint_store)
        self.identity_candidate_builder = IdentityCandidateBuilder(knowledge_database_path)
        self.identity_evidence_collector = IdentityEvidenceCollector()
        self.identity_contradiction_detector = IdentityContradictionDetector()
        self.identity_confidence_calculator = IdentityConfidenceCalculator()
        self.identity_decision_explainer = IdentityDecisionExplainer()
        self.semantic_identity_engine = SemanticIdentityEngine()
        self.online_agent = OnlineAgent(self.source_manager) if self.source_manager is not None else None
        self.cache = (
            AnalysisCache(knowledge_database_path)
            if knowledge_database_path is not None
            else None
        )


    def analyze(
        self,
        file_path: str | Path,
        force: bool = False,
        require_in_video: bool = False,
        identity_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Nicht unterstützte Videodatei: {path.suffix}")

        if self.cache is not None and not force:
            cached = self.cache.get(path)
            if cached is not None:
                return self._refresh_cached_reasoning(
                    path,
                    cached,
                    identity_hint=identity_hint,
                )

        result: dict[str, Any] = {
            "file": {
                "path": str(path.resolve()),
                "name": path.name,
                "size_bytes": path.stat().st_size,
                "extension": path.suffix.lower(),
            },
            "mediainfo": None,
            "ffprobe": None,
            "summary": {},
            "warnings": [],
            "methods_used": ["filename"],
            "cache": {"hit": False, "message": "Neue Analyse durchgeführt.", "forced": force},
            "identification": self._apply_identity_hint(
                self.filename_identifier.identify(path),
                identity_hint,
            ),
        }

        mediainfo = self.tools.find("mediainfo")
        if mediainfo:
            try:
                result["mediainfo"] = self._run_json(
                    [str(mediainfo), "--Output=JSON", str(path)]
                )
                result["methods_used"].append("mediainfo")
            except Exception as exc:
                result["warnings"].append(f"MediaInfo fehlgeschlagen: {exc}")
        else:
            result["warnings"].append(
                "MediaInfo ist noch nicht installiert; ffprobe-Fallback wird verwendet."
            )

        ffprobe = self.tools.find("ffprobe")
        if ffprobe:
            try:
                result["ffprobe"] = self._run_json([
                    str(ffprobe),
                    "-v", "error",
                    "-show_format",
                    "-show_streams",
                    "-show_chapters",
                    "-of", "json",
                    str(path),
                ])
                result["methods_used"].append("ffprobe")
            except Exception as exc:
                result["warnings"].append(f"ffprobe fehlgeschlagen: {exc}")
        else:
            result["warnings"].append("ffprobe wurde nicht gefunden.")

        result["summary"] = self._build_summary(result)
        result["evidence"] = self._build_evidence(result)
        result["source_plan"] = self.source_manager.plan(result) if self.source_manager is not None else None
        initial_supervisor = self.supervisor.evaluate(result)
        should_run_online = any(
            step.get("agent") == "online" and step.get("required")
            for step in (initial_supervisor.get("next_steps") or [])
        )
        has_online_sources = bool((result.get("source_plan") or {}).get("candidate_sources"))
        if self.online_agent is not None and should_run_online and has_online_sources:
            result["online"] = self.online_agent.run(result)
            result["source_plan"]["executed"] = True
            result["source_plan"]["reason"] = "Konfigurierte Online-Quellen wurden automatisch ausgeführt."
        else:
            result["online"] = {
                "schema_version": 2,
                "executed": False,
                "reason": (
                    "Keine geeignete konfigurierte Quelle verfügbar."
                    if should_run_online
                    else "Lokale Sicherheit reicht aus; Online-Abgleich wurde eingespart."
                ),
                "provider_results": [],
                "ranking": {
                    "schema_version": 2, "matches": [], "best_match": None, "match_count": 0,
                    "confidence": 0.0, "confidence_gap": None, "decision": "not_executed",
                    "weights": dict(self.online_agent.ranker.WEIGHTS) if self.online_agent is not None else {},
                },
            }
        result["supervisor"] = self.supervisor.evaluate(result)
        in_video_required = (
            require_in_video
            or any(
                step.get("agent") == "in_video"
                and step.get("required")
                for step in (
                    result["supervisor"].get("next_steps")
                    or []
                )
            )
        )
        result["in_video"] = self.in_video_agent.run(
            result,
            in_video_required,
        )
        self._append_in_video_evidence(result)
        result["quality"] = self.quality_engine.evaluate(result)
        semantic_candidates = self.identity_candidate_builder.build(result)
        semantic_evidence = self.identity_evidence_collector.collect(
            semantic_candidates,
            result,
        )
        semantic_contradictions = self.identity_contradiction_detector.detect(
            semantic_evidence,
            result,
        )
        semantic_confidence = self.identity_confidence_calculator.calculate(
            semantic_contradictions,
            result,
        )
        semantic_explanation = self.identity_decision_explainer.explain(
            semantic_confidence,
            result,
        )
        result["semantic_identity"] = self.semantic_identity_engine.finalize(
            semantic_explanation,
            result,
        )
        result["decision"] = self.decision_engine.evaluate(result)
        result["supervisor"] = self.supervisor.evaluate(result)
        result["change_plan"] = self.decision_planner.build(result)
        result["integration"] = AssistantIntegrationAPI.build(result)
        if self.cache is not None:
            self.cache.put(path, result)
        return result


    def _refresh_cached_reasoning(
        self,
        path: Path,
        cached: dict[str, Any],
        identity_hint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = dict(cached)
        result["cache"] = {
            **dict(result.get("cache") or {}),
            "hit": True,
            "message": (
                "Unveränderte Datei – technische und In-Video-Analyse "
                "aus dem Cache verwendet; Quellen- und "
                "Entscheidungslogik aktualisiert."
            ),
            "reasoning_refreshed": True,
        }

        result["identification"] = self._apply_identity_hint(
            result.get("identification") or {},
            identity_hint,
        )

        result["evidence"] = self._build_evidence(result)

        if self.source_manager is not None:
            result["source_plan"] = self.source_manager.plan(result)

        initial_supervisor = self.supervisor.evaluate(result)
        should_run_online = any(
            step.get("agent") == "online"
            and step.get("required")
            for step in (
                initial_supervisor.get("next_steps")
                or []
            )
        )
        previous_semantic_status = str(
            (result.get("semantic_identity") or {}).get("final_status")
            or "unknown"
        )
        if previous_semantic_status != "confirmed":
            should_run_online = True
        has_sources = bool(
            (result.get("source_plan") or {}).get(
                "candidate_sources"
            )
        )

        if (
            self.online_agent is not None
            and should_run_online
            and has_sources
        ):
            result["online"] = self.online_agent.run(result)
            result["source_plan"]["executed"] = True
            result["source_plan"]["reason"] = (
                "Quellenlogik wurde auf Basis der gespeicherten "
                "lokalen Analyse erneut ausgeführt."
            )
        elif should_run_online:
            result["online"] = {
                "schema_version": 2,
                "executed": False,
                "reason": (
                    "Keine geeignete konfigurierte Quelle verfügbar."
                ),
                "provider_results": [],
                "ranking": {
                    "schema_version": 2,
                    "matches": [],
                    "best_match": None,
                    "match_count": 0,
                    "confidence": 0.0,
                    "confidence_gap": None,
                    "decision": "not_executed",
                    "weights": (
                        dict(self.online_agent.ranker.WEIGHTS)
                        if self.online_agent is not None
                        else {}
                    ),
                },
            }

        if not bool((result.get("source_plan") or {}).get("executed")):
            result["online"] = {
                "schema_version": 4,
                "executed": False,
                "reason": (
                    "Keine geeignete konfigurierte Quelle verfügbar."
                    if should_run_online
                    else "Aktualisierter QueryPlan erfordert derzeit keinen Online-Abgleich; alte Online-Ergebnisse wurden verworfen."
                ),
                "query": (result.get("source_plan") or {}).get("query") or {},
                "provider_results": [],
                "ranking": {
                    "schema_version": 3, "matches": [], "best_match": None,
                    "match_count": 0, "confidence": 0.0, "confidence_gap": None,
                    "decision": "not_executed",
                    "weights": dict(self.online_agent.ranker.WEIGHTS) if self.online_agent is not None else {},
                },
            }

        result["supervisor"] = self.supervisor.evaluate(result)
        semantic_candidates = self.identity_candidate_builder.build(result)
        semantic_evidence = self.identity_evidence_collector.collect(
            semantic_candidates,
            result,
        )
        semantic_contradictions = self.identity_contradiction_detector.detect(
            semantic_evidence,
            result,
        )
        semantic_confidence = self.identity_confidence_calculator.calculate(
            semantic_contradictions,
            result,
        )
        semantic_explanation = self.identity_decision_explainer.explain(
            semantic_confidence,
            result,
        )
        result["semantic_identity"] = self.semantic_identity_engine.finalize(
            semantic_explanation,
            result,
        )
        result["decision"] = self.decision_engine.evaluate(result)
        result["supervisor"] = self.supervisor.evaluate(result)
        result["change_plan"] = self.decision_planner.build(result)
        result["integration"] = AssistantIntegrationAPI.build(result)

        if self.cache is not None:
            self.cache.put(path, result)

        return result



    @staticmethod
    def _apply_identity_hint(
        identification: dict[str, Any],
        identity_hint: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Ergänzt eine bereits geprüfte Identität als priorisierten Hint.

        Der ursprüngliche Filename-Identifier bleibt erhalten. Der Hint
        überschreibt nur strukturierte Identitätsfelder, die ausdrücklich
        geliefert wurden.
        """
        merged = dict(identification or {})

        if not isinstance(identity_hint, dict):
            return merged

        title = str(identity_hint.get("title") or "").strip()
        media_type = str(
            identity_hint.get("media_type") or ""
        ).strip()

        year = identity_hint.get("year")
        edition = str(
            identity_hint.get("edition") or ""
        ).strip()

        if title:
            merged["title_candidate"] = title
            merged["identity_hint_title"] = title

        if media_type:
            merged["media_type"] = media_type
            merged["identity_hint_media_type"] = media_type

        if year not in (None, ""):
            try:
                year = int(year)
            except (TypeError, ValueError):
                pass
            else:
                merged["year"] = year
                merged["year_candidate"] = year
                merged["identity_hint_year"] = year

        if edition:
            merged["edition"] = edition
            merged["identity_hint_edition"] = edition

        if title or media_type or year not in (None, "") or edition:
            merged["identity_hint_applied"] = True

        return merged


    @staticmethod
    def _append_in_video_evidence(result: dict[str, Any]) -> None:
        agents = ((result.get("in_video") or {}).get("agents") or {})
        labels = {"frame_agent":"Frames", "subtitle_agent":"Untertitel", "audio_agent":"Audio", "ocr_agent":"OCR", "fingerprint_agent":"Fingerprint", "scene_agent":"Szenen"}
        for key, label in labels.items():
            data = agents.get(key) or {}
            state = data.get("state")
            if state == "completed":
                result.setdefault("evidence", []).append({"source": label, "status": "Bestätigt", "detail": "Inhaltsanalyse erfolgreich ausgeführt"})
                method = key.removesuffix("_agent")
                if method not in result.setdefault("methods_used", []): result["methods_used"].append(method)
            elif state in {"unavailable", "failed", "unsupported"}:
                result.setdefault("warnings", []).append(f"{label}: {data.get('reason') or state}")

    def register_fingerprint_reference(self, analysis: dict[str, Any]) -> dict[str, Any]:
        agents = ((analysis.get("in_video") or {}).get("agents") or {})
        fingerprint = (agents.get("fingerprint_agent") or {}).get("video_fingerprint")
        identity = analysis.get("decision") or analysis.get("identification") or {}
        return self.fingerprint_store.register(fingerprint, identity, (analysis.get("file") or {}).get("path"))

    def export_integration_payload(self, analysis: dict[str, Any]) -> dict[str, Any]:
        return AssistantIntegrationAPI.build(analysis)

    def clear_cache_for(self, file_path: str | Path) -> int:
        return self.cache.delete(Path(file_path)) if self.cache is not None else 0

    def clear_cache(self) -> int:
        return self.cache.clear() if self.cache is not None else 0

    @staticmethod
    def _run_json(command: list[str]) -> dict[str, Any]:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or f"Exit-Code {completed.returncode}")
        return json.loads(completed.stdout)


    @staticmethod
    def _mediainfo_tracks(result: dict[str, Any]) -> list[dict[str, Any]]:
        media = result.get("mediainfo") or {}
        tracks = ((media.get("media") or {}).get("track") or [])
        return tracks if isinstance(tracks, list) else []

    @classmethod
    def _build_evidence(cls, result: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        identification = result.get("identification") or {}
        if identification.get("title_candidate"):
            evidence.append({
                "source": "Dateiname",
                "status": "Hinweis",
                "detail": identification.get("title_candidate"),
            })
        if result.get("ffprobe"):
            evidence.append({
                "source": "ffprobe",
                "status": "Bestätigt",
                "detail": "Container, Streams, Kapitel und Laufzeit gelesen",
            })
        if result.get("mediainfo"):
            evidence.append({
                "source": "MediaInfo",
                "status": "Bestätigt",
                "detail": "Zusätzliche Container-, HDR-, Audio- und Tag-Daten gelesen",
            })
        else:
            evidence.append({
                "source": "MediaInfo",
                "status": "Fehlt",
                "detail": "Wird nach zentraler Tool-Installation automatisch ergänzt",
            })
        return evidence

    @staticmethod
    def _build_summary(result: dict[str, Any]) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "duration_seconds": None,
            "container": None,
            "video_codec": None,
            "width": None,
            "height": None,
            "audio_tracks": 0,
            "subtitle_tracks": 0,
            "chapters": 0,
            "title_tags": [],
        }

        probe = result.get("ffprobe") or {}
        fmt = probe.get("format") or {}
        streams = probe.get("streams") or []
        chapters = probe.get("chapters") or []

        try:
            summary["duration_seconds"] = round(float(fmt.get("duration")), 3)
        except (TypeError, ValueError):
            pass

        summary["container"] = fmt.get("format_long_name") or fmt.get("format_name")
        summary["chapters"] = len(chapters)

        for stream in streams:
            kind = stream.get("codec_type")
            if kind == "video" and summary["video_codec"] is None:
                summary["video_codec"] = stream.get("codec_long_name") or stream.get("codec_name")
                summary["width"] = stream.get("width")
                summary["height"] = stream.get("height")
            elif kind == "audio":
                summary["audio_tracks"] += 1
            elif kind == "subtitle":
                summary["subtitle_tracks"] += 1

            tags = stream.get("tags") or {}
            for key in ("title", "handler_name"):
                value = tags.get(key)
                if value and value not in summary["title_tags"]:
                    summary["title_tags"].append(value)

        format_tags = fmt.get("tags") or {}
        for key in ("title", "show", "episode_id", "comment"):
            value = format_tags.get(key)
            if value and value not in summary["title_tags"]:
                summary["title_tags"].append(value)


        for track in MediaAnalyzer._mediainfo_tracks(result):
            track_type = str(track.get("@type") or "").lower()
            if track_type == "general":
                if not summary["duration_seconds"]:
                    try:
                        summary["duration_seconds"] = round(float(track.get("Duration")), 3)
                    except (TypeError, ValueError):
                        pass
                summary["container"] = (
                    summary["container"]
                    or track.get("Format")
                    or track.get("Format_Commercial")
                )
            elif track_type == "video":
                summary["video_codec"] = (
                    summary["video_codec"]
                    or track.get("Format_Commercial_IfAny")
                    or track.get("Format")
                )
                summary["width"] = summary["width"] or track.get("Width")
                summary["height"] = summary["height"] or track.get("Height")
                summary["hdr_format"] = (
                    track.get("HDR_Format")
                    or track.get("HDR_Format_Commercial")
                    or track.get("HDR_Format_String")
                )
            elif track_type == "audio":
                summary["mediainfo_audio_tracks"] = (
                    summary.get("mediainfo_audio_tracks", 0) + 1
                )
            elif track_type == "text":
                summary["mediainfo_subtitle_tracks"] = (
                    summary.get("mediainfo_subtitle_tracks", 0) + 1
                )

        return summary
