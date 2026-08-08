from __future__ import annotations

from pathlib import Path
from typing import Any

from models.media_item import MediaItem
from services.media_detection import MediaDetector
from services.detection_candidates import DetectionCandidateService


class MediaScanner:
    """Liest Dateien und Ordner deterministisch in gemeinsame MediaItems ein."""

    def __init__(self) -> None:
        self.detector = MediaDetector()
        self.candidate_service = DetectionCandidateService(self.detector)

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
                selected = candidate_set.selected
                detection = self.detector.detect(candidate).to_dict()
                detection.update(candidate_set.to_dict())
                if selected is not None:
                    detection["confidence_band"] = selected.confidence_band
                    detection["selected_source"] = selected.source
                result.append(
                    MediaItem.from_path(
                        candidate,
                        metadata=dict(item.get("metadata") or {}),
                        source=str(item.get("source") or "filesystem"),
                        detection=detection,
                    )
                )

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

        return result, skipped
