from __future__ import annotations

from pathlib import Path
from typing import Any

from models.media_item import MediaItem
from services.media_detection import MediaDetector
from services.detection_candidates import DetectionCandidateService
from services.decision_engine import DecisionEngine
from services.folder_structure import FolderStructureAnalyzer
from services.media_file_grouping import MediaFileGrouper


class MediaScanner:
    """Liest Dateien und Ordner deterministisch in gemeinsame MediaItems ein."""

    def __init__(self, decision_hint_provider=None) -> None:
        self.detector = MediaDetector()
        self.candidate_service = DetectionCandidateService(self.detector)
        self.decision_engine = DecisionEngine()
        self.folder_analyzer = FolderStructureAnalyzer()
        self.file_grouper = MediaFileGrouper()
        self.decision_hint_provider = decision_hint_provider

    def scan(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[MediaItem], list[dict[str, str]]]:
        result: list[MediaItem] = []
        skipped: list[dict[str, str]] = []
        seen: set[str] = set()

        for item in items:
            source = Path(str(item.get("path") or ""))
            if not source.exists():
                skipped.append({
                    "path": str(source),
                    "reason": "nicht gefunden",
                })
                continue

            if source.is_dir():
                recursive = bool(item.get("recursive", True))
                iterator = source.rglob("*") if recursive else source.glob("*")
                candidates = sorted(
                    (path for path in iterator if path.is_file()),
                    key=lambda path: str(path).casefold(),
                )
            else:
                candidates = [source]

            for candidate in candidates:
                key = str(candidate.resolve()).casefold()
                if key in seen:
                    continue
                seen.add(key)

                candidate_set = self.candidate_service.analyze(candidate)
                decision_hints: dict[str, Any] = {}
                if callable(self.decision_hint_provider):
                    try:
                        learned = self.decision_hint_provider(candidate)
                    except Exception:
                        learned = {}
                    if isinstance(learned, dict):
                        decision_hints.update(learned)

                # Hinweise des aktuellen Aufrufs haben Vorrang vor Gelerntem.
                decision_hints.update(
                    dict(item.get("decision_hints") or {})
                )

                decision = self.decision_engine.decide(
                    candidate_set,
                    hints=decision_hints,
                )
                selected = next(
                    (
                        value
                        for value in candidate_set.candidates
                        if value.candidate_id == decision.selected_candidate_id
                    ),
                    candidate_set.selected,
                )

                detection = self.detector.detect(candidate).to_dict()
                detection.update(candidate_set.to_dict())
                decision_payload = decision.to_dict()
                decision_payload["hints_used"] = dict(decision_hints)
                detection["decision"] = decision_payload
                detection["decision_state"] = decision.state
                detection["decision_confidence"] = decision.confidence
                detection["review_required"] = decision.review_required

                if selected is not None:
                    detection["selected_candidate_id"] = selected.candidate_id
                    detection["confidence"] = selected.confidence
                    detection["confidence_band"] = selected.confidence_band
                    detection["selected_source"] = selected.source
                    detection["media_type"] = selected.media_type
                    detection["title"] = selected.title
                    detection["year"] = selected.year
                    detection["season"] = selected.season
                    detection["episode"] = selected.episode
                    detection["episode_end"] = selected.episode_end
                    detection["episode_title"] = selected.episode_title
                    detection["edition"] = selected.edition
                    detection["part"] = selected.part

                result.append(
                    MediaItem.from_path(
                        candidate,
                        metadata=dict(item.get("metadata") or {}),
                        source=str(item.get("source") or "filesystem"),
                        detection=detection,
                    )
                )

        # Begleitdateien jetzt zu Medienobjekten gruppieren, bevor
        # Sammlungstyp und Ordnerkontext berechnet werden.
        result, grouping_details = self.file_grouper.group(result)
        for media in result:
            media.detection_data["grouping_summary"] = {
                "grouped_companions_total": sum(
                    len(item.companion_files)
                    for item in result
                ),
                "visible_media_items": len(result),
            }

        detected_types = {
            media.media_type
            for media in result
            if media.media_type not in {"", "unknown"}
        }
        collection_type = (
            "mixed"
            if len(detected_types) > 1
            else (next(iter(detected_types)) if detected_types else "unknown")
        )
        for media in result:
            media.detection_data["collection_media_type"] = collection_type

        # Ordnerkontext wird pro als Verzeichnis übergebenem Scan-Root ergänzt.
        for source_item in items:
            source = Path(str(source_item.get("path") or ""))
            if not source.is_dir():
                continue

            members = []
            try:
                source_resolved = source.resolve()
            except OSError:
                source_resolved = source

            for media in result:
                try:
                    media.path.resolve().relative_to(source_resolved)
                    members.append(media)
                except Exception:
                    continue

            if not members:
                continue

            context = self.folder_analyzer.analyze(source, members)
            payload = context.to_dict()

            for media in members:
                relation = payload["item_relations"].get(str(media.path), {})
                media.detection_data["folder_context"] = payload
                media.detection_data["folder_relation"] = dict(relation)

                # Ordnerstruktur ergänzt fehlende Felder, überschreibt aber
                # niemals explizite/manuelle oder bereits sichere Erkennung.
                if not media.season and relation.get("season"):
                    media.season = str(relation["season"])
                if not media.part and relation.get("part"):
                    media.part = str(relation["part"])
                if relation.get("is_extra_folder"):
                    media.is_extra = True
                    media.detection_data["is_extra"] = True
                    if media.media_type == "unknown":
                        media.media_type = "extra"

        return result, skipped
