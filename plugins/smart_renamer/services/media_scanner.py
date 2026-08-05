from __future__ import annotations

from pathlib import Path
from typing import Any

from models.media_item import MediaItem


class MediaScanner:
    """Liest Dateien und Ordner deterministisch in gemeinsame MediaItems ein."""

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
                result.append(
                    MediaItem.from_path(
                        candidate,
                        metadata=dict(item.get("metadata") or {}),
                        source=str(item.get("source") or "filesystem"),
                    )
                )

        return result, skipped
