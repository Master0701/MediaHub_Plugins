from __future__ import annotations

from services.episode_identity_resolver import EpisodeIdentityResolver

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
from services.online_visual_reference import OnlineVisualReferenceMatcher
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
        worker_provider: Any = None,
    ):
        self.tools = ToolResolver(mediahub_base, plugin_path)
        self.filename_identifier = FilenameIdentifier()
        self.decision_planner = DecisionPlanner()
        self.source_manager = (
            SourceManager(
                plugin_path,
                knowledge_database_path,
                data_base_dir=mediahub_base,
            )
            if plugin_path is not None
            else None
        )
        self.supervisor = SupervisorAgent()
        self.in_video_agent = InVideoAgent(
            self.tools,
            worker_provider=worker_provider,
        )
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
        self.online_visual_matcher = OnlineVisualReferenceMatcher()
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

        speech_identity = (
            result.get("speech_identity_evidence")
            or {}
        )

        if (
            self.source_manager is not None
            and speech_identity.get("identity_terms")
        ):
            previous_plan = result.get("source_plan") or {}
            previous_query = previous_plan.get("query") or {}

            refreshed_plan = self.source_manager.plan(
                result
            )

            refreshed_query = (
                refreshed_plan.get("query")
                or {}
            )

            result["source_plan"] = refreshed_plan

            query_changed = (
                refreshed_query != previous_query
            )

            has_refreshed_sources = bool(
                refreshed_plan.get(
                    "candidate_sources"
                )
            )

            has_search_variants = bool(
                refreshed_query.get(
                    "search_variants"
                )
            )

            should_retry_online = (
                query_changed
                and has_refreshed_sources
                and has_search_variants
                and self.online_agent is not None
            )

            if should_retry_online:
                result["online"] = self.online_agent.run(
                    result
                )
                result["source_plan"]["executed"] = True
                result["source_plan"]["reason"] = (
                    "Online-Abgleich wurde nach neuer "
                    "In-Video-/Speech-Evidenz erneut ausgeführt."
                )

        self._apply_online_visual_verification(result)
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

        if self.source_manager is not None:
            result["episode_identity"] = (
                EpisodeIdentityResolver(
                    self.source_manager
                ).resolve(
                    result
                )
            )
        else:
            result["episode_identity"] = {
                "schema_version": 1,
                "status": "unavailable",
                "reason": (
                    "Keine Quellenverwaltung für "
                    "Episodenidentifikation verfügbar."
                ),
                "decision_authority": False,
            }

        result["decision"] = self.decision_engine.evaluate(result)
        result["supervisor"] = self.supervisor.evaluate(result)
        result["change_plan"] = self.decision_planner.build(result)
        result["integration"] = AssistantIntegrationAPI.build(result)
        if self.cache is not None:
            self.cache.put(path, result)
        return result


    def _apply_online_visual_verification(
        self,
        result: dict[str, Any],
    ) -> None:
        """Verifiziert den besten Online-Kandidaten mit TMDb-Bildevidenz."""

        online = result.get("online") or {}
        ranking = online.get("ranking") or {}
        best = ranking.get("best_match")

        if not isinstance(best, dict):
            return

        selected_frames = (
            (result.get("in_video") or {})
            .get("agents", {})
            .get("frame_agent", {})
            .get("samples", [])
        )

        if not selected_frames:
            return

        # Der beste Gesamttreffer kann z. B. von Wikipedia stammen.
        # Für visuelle Evidenz suchen wir deshalb separat den
        # inhaltlich passenden TMDb-Treffer.
        target_title = str(
            best.get("title") or ""
        ).strip().casefold()

        target_variant = str(
            best.get("search_variant") or ""
        ).strip().casefold()

        tmdb_candidates = []

        for provider in online.get("provider_results") or []:
            if str(
                provider.get("provider_id") or ""
            ).casefold() != "tmdb":
                continue

            for match in provider.get("matches") or []:
                if isinstance(match, dict):
                    tmdb_candidates.append(match)

        if not tmdb_candidates:
            return

        def normalized_title(value: Any) -> str:
            return (
                str(value or "")
                .strip()
                .casefold()
                .replace(":", "")
                .replace("–", "-")
                .replace("—", "-")
            )

        target_titles = {
            normalized_title(target_title),
            normalized_title(target_variant),
        }

        target_titles.discard("")

        tmdb_match = None

        # 1. Exakter Titel-/Variantenabgleich.
        for candidate in tmdb_candidates:
            candidate_titles = {
                normalized_title(candidate.get("title")),
                normalized_title(
                    candidate.get("original_title")
                ),
            }

            candidate_titles.discard("")

            if target_titles & candidate_titles:
                tmdb_match = candidate
                break

        # 2. Fallback: deutliche Titelüberschneidung.
        if tmdb_match is None:
            best_overlap = 0.0

            for candidate in tmdb_candidates:
                candidate_title = normalized_title(
                    candidate.get("title")
                )

                if not candidate_title:
                    continue

                target_words = set(
                    normalized_title(
                        best.get("title")
                    ).split()
                )

                candidate_words = set(
                    candidate_title.split()
                )

                if not target_words or not candidate_words:
                    continue

                overlap = (
                    len(target_words & candidate_words)
                    / len(target_words | candidate_words)
                )

                if overlap > best_overlap:
                    best_overlap = overlap
                    tmdb_match = candidate

            if best_overlap < 0.50:
                tmdb_match = None

        if tmdb_match is None:
            return

        raw = tmdb_match.get("raw") or {}

        if not isinstance(raw, dict):
            return

        candidate_id = (
            tmdb_match.get("external_id")
            or raw.get("id")
        )

        if not candidate_id:
            return

        ffmpeg = self.tools.find("ffmpeg")

        if not ffmpeg:
            result.setdefault("warnings", []).append(
                "Online-Bildvergleich übersprungen: "
                "ffmpeg wurde nicht gefunden."
            )
            return

        # Bevorzugt mehrere echte Szenenbilder von TMDb.
        # Falls das nicht möglich ist, bleibt die bisherige
        # Poster-/Backdrop-Einzelreferenz als Fallback erhalten.
        references = []

        tmdb_provider = (
            self.source_manager.get_provider("tmdb")
            if self.source_manager is not None
            else None
        )

        if tmdb_provider is not None:
            try:
                media_type = (
                    tmdb_match.get("media_type")
                    or best.get("media_type")
                    or (
                        result.get("identification")
                        or {}
                    ).get("media_type")
                    or "movie"
                )

                references = tmdb_provider.get_images(
                    media_type,
                    candidate_id,
                    limit=12,
                )

            except Exception as exc:
                result.setdefault("warnings", []).append(
                    "TMDb-Backdrop-Abfrage fehlgeschlagen: "
                    f"{exc}"
                )

        try:
            if references:
                visual = (
                    self.online_visual_matcher
                    .compare_references_to_frames(
                        references,
                        selected_frames,
                        ffmpeg,
                    )
                )

                visual["reference_mode"] = (
                    "tmdb_multi_backdrop"
                )

            else:
                reference_url = (
                    self.online_visual_matcher
                    .tmdb_reference_url(raw)
                )

                if not reference_url:
                    return

                image_bytes = (
                    self.online_visual_matcher
                    .download_reference(
                        reference_url
                    )
                )

                reference_hashes = (
                    self.online_visual_matcher
                    .reference_hashes(
                        image_bytes,
                        ffmpeg,
                    )
                )

                if not reference_hashes:
                    return

                visual = (
                    self.online_visual_matcher
                    .compare_reference_to_frames(
                        reference_hashes,
                        selected_frames,
                    )
                )

                visual["reference_url"] = (
                    reference_url
                )
                visual["reference_mode"] = (
                    "single_reference_fallback"
                )

        except Exception as exc:
            result.setdefault("warnings", []).append(
                f"Online-Bildvergleich fehlgeschlagen: {exc}"
            )
            return

        if not visual.get("executed", True):
            result.setdefault("warnings", []).append(
                "Online-Bildvergleich lieferte keine "
                "auswertbare Referenz."
            )
            return

        visual["provider_id"] = "tmdb"
        visual["candidate_id"] = (
            tmdb_match.get("external_id")
            or raw.get("id")
        )
        visual["candidate_title"] = (
            tmdb_match.get("title")
        )
        visual["ranking_best_title"] = (
            best.get("title")
        )
        visual["ranking_best_provider"] = (
            best.get("provider_id")
        )

        best["visual_verification"] = visual
        ranking["visual_verification"] = visual

        online["ranking"] = ranking
        result["online"] = online


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
            cached_online = dict(result.get("online") or {})

            has_cached_online_result = bool(
                cached_online.get("executed")
                and (
                    cached_online.get("provider_results")
                    or (cached_online.get("ranking") or {}).get("best_match")
                )
            )

            if has_cached_online_result:
                cached_online["reason"] = (
                    "Vorhandene gültige Online-Evidenz aus dem Cache "
                    "wurde beibehalten; kein neuer Online-Abgleich erforderlich."
                )
                result["online"] = cached_online
            else:
                result["online"] = {
                    "schema_version": 4,
                    "executed": False,
                    "reason": (
                        "Keine geeignete konfigurierte Quelle verfügbar."
                        if should_run_online
                        else "Aktualisierter QueryPlan erfordert derzeit keinen Online-Abgleich."
                    ),
                    "query": (result.get("source_plan") or {}).get("query") or {},
                    "provider_results": [],
                    "ranking": {
                        "schema_version": 3,
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
    def _append_in_video_evidence(
        result: dict[str, Any],
    ) -> None:
        agents = (
            (result.get("in_video") or {})
            .get("agents")
            or {}
        )

        labels = {
            "frame_agent": "Frames",
            "subtitle_agent": "Untertitel",
            "audio_agent": "Audio",
            "speech_recognition_agent": "Spracherkennung",
            "ocr_agent": "OCR",
            "fingerprint_agent": "Fingerprint",
            "scene_agent": "Szenen",
        }

        for key, label in labels.items():
            data = agents.get(key) or {}
            state = data.get("state")

            if state == "completed":
                result.setdefault(
                    "evidence",
                    [],
                ).append(
                    {
                        "source": label,
                        "status": "Bestätigt",
                        "detail": (
                            "Inhaltsanalyse erfolgreich "
                            "ausgeführt"
                        ),
                    }
                )

                method = key.removesuffix(
                    "_agent"
                )

                if method not in result.setdefault(
                    "methods_used",
                    [],
                ):
                    result["methods_used"].append(
                        method
                    )

            elif state in {
                "unavailable",
                "failed",
                "unsupported",
            }:
                result.setdefault(
                    "warnings",
                    [],
                ).append(
                    f"{label}: "
                    f"{data.get('reason') or state}"
                )

        speech = (
            agents.get(
                "speech_recognition_agent"
            )
            or {}
        )

        if speech.get("state") == "completed":
            identity_terms = [
                str(value).strip()
                for value in (
                    speech.get(
                        "identity_terms"
                    )
                    or []
                )
                if str(value).strip()
            ]

            transcript = str(
                speech.get("transcript")
                or ""
            ).strip()

            result[
                "speech_identity_evidence"
            ] = {
                "schema_version": 1,
                "source": "speech_recognition",
                "provider": speech.get(
                    "provider"
                ),
                "model": speech.get("model"),
                "identity_terms": identity_terms,
                "transcript": transcript,
                "decision_authority": False,
            }

            if identity_terms:
                result.setdefault(
                    "evidence",
                    [],
                ).append(
                    {
                        "source": "Spracherkennung",
                        "status": "Identitätshinweis",
                        "detail": (
                            "Im gesprochenen Inhalt "
                            "wurden mögliche "
                            "Identitätshinweise erkannt: "
                            + ", ".join(
                                identity_terms[:10]
                            )
                        ),
                    }
                )


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
