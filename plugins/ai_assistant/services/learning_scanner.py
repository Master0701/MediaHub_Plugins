from __future__ import annotations

from pathlib import Path
from threading import Event
from typing import Any, Callable


class LearningScanner:
    """Scannt Mediendateien mit der echten MediaHub-KI.

    Der Scanner besitzt keine eigene Erkennungslogik.
    Jede Datei wird über MetadataAIReviewProvider analysiert
    und anschließend in LearningReviewStore abgelegt.
    """

    VIDEO_SUFFIXES = {
        ".mkv",
        ".mp4",
        ".avi",
        ".mov",
        ".m4v",
        ".ts",
        ".m2ts",
        ".webm",
        ".wmv",
        ".mpg",
        ".mpeg",
    }

    def __init__(
        self,
        metadata_review_provider,
        review_store,
    ):
        self.metadata_review_provider = (
            metadata_review_provider
        )
        self.review_store = review_store

    @staticmethod
    def _resolved_key(
        path: str | Path,
    ) -> str:
        return str(
            Path(path)
            .expanduser()
            .resolve()
        ).casefold()

    def known_paths(self) -> set[str]:
        known: set[str] = set()

        for item in (
            self.review_store.list_queue()
            + self.review_store.list_history()
        ):
            value = str(
                item.get("source_path")
                or ""
            ).strip()

            if not value:
                continue

            try:
                known.add(
                    self._resolved_key(value)
                )
            except OSError:
                known.add(
                    value.casefold()
                )

        return known

    def discover(
        self,
        folder: str | Path,
        *,
        recursive: bool = True,
    ) -> list[Path]:
        root = Path(
            folder
        ).expanduser().resolve()

        if not root.exists():
            raise FileNotFoundError(root)

        if not root.is_dir():
            raise NotADirectoryError(root)

        iterator = (
            root.rglob("*")
            if recursive
            else root.glob("*")
        )

        files = [
            path
            for path in iterator
            if (
                path.is_file()
                and path.suffix.casefold()
                in self.VIDEO_SUFFIXES
            )
        ]

        return sorted(
            files,
            key=lambda item: str(
                item
            ).casefold(),
        )

    def analyze_file(
        self,
        file_path: str | Path,
    ) -> dict[str, Any]:
        path = Path(
            file_path
        ).expanduser().resolve()

        if not path.is_file():
            raise FileNotFoundError(path)

        review = (
            self.metadata_review_provider
            .analyze(
                {
                    "path": str(path),
                    "item": {
                        "path": str(path),
                        "file_path": str(path),
                        "filename": path.name,
                        "original_name": path.name,
                    },
                }
            )
        )

        if not isinstance(review, dict):
            raise RuntimeError(
                "Metadata-Review lieferte "
                "kein gültiges Ergebnis."
            )

        return dict(review)

    def scan(
        self,
        folder: str | Path,
        *,
        recursive: bool = True,
        skip_known: bool = True,
        cancel_event: Event | None = None,
        pause_event: Event | None = None,
        progress_callback: (
            Callable[
                [dict[str, Any]],
                None,
            ]
            | None
        ) = None,
    ) -> dict[str, Any]:
        files = self.discover(
            folder,
            recursive=recursive,
        )

        known = (
            self.known_paths()
            if skip_known
            else set()
        )

        result: dict[str, Any] = {
            "folder": str(
                Path(folder)
                .expanduser()
                .resolve()
            ),
            "total_found": len(files),
            "analyzed": 0,
            "queued": 0,
            "skipped": 0,
            "failed": 0,
            "cancelled": False,
            "errors": [],
        }

        for index, path in enumerate(
            files,
            start=1,
        ):
            if (
                cancel_event is not None
                and cancel_event.is_set()
            ):
                result["cancelled"] = True
                break

            # Pause erfolgt absichtlich nur zwischen
            # zwei Dateien. Eine bereits laufende
            # Medienanalyse wird immer sauber beendet.
            pause_reported = False

            while (
                pause_event is not None
                and pause_event.is_set()
            ):
                if (
                    cancel_event is not None
                    and cancel_event.is_set()
                ):
                    result["cancelled"] = True
                    break

                if (
                    not pause_reported
                    and progress_callback
                ):
                    progress_callback(
                        {
                            "index": index,
                            "total": len(files),
                            "path": str(path),
                            "status": "paused",
                        }
                    )
                    pause_reported = True

                # Event.wait() vermeidet aktives
                # CPU-Spinning während der Pause.
                if cancel_event is not None:
                    cancel_event.wait(0.1)
                else:
                    from time import sleep
                    sleep(0.1)

            if result["cancelled"]:
                break

            key = self._resolved_key(
                path
            )

            if (
                skip_known
                and key in known
            ):
                result["skipped"] += 1

                if progress_callback:
                    progress_callback(
                        {
                            "index": index,
                            "total": len(files),
                            "path": str(path),
                            "status": "skipped",
                        }
                    )

                continue

            try:
                review = self.analyze_file(
                    path
                )

                case = (
                    self.review_store
                    .add_case(
                        source_path=str(path),
                        analysis=review,
                    )
                )

                known.add(key)

                result["analyzed"] += 1
                result["queued"] += 1

                if progress_callback:
                    progress_callback(
                        {
                            "index": index,
                            "total": len(files),
                            "path": str(path),
                            "status": "queued",
                            "case_id": case.get(
                                "id"
                            ),
                        }
                    )

            except Exception as exc:
                result["failed"] += 1

                error = {
                    "path": str(path),
                    "error": str(exc),
                }

                result["errors"].append(
                    error
                )

                if progress_callback:
                    progress_callback(
                        {
                            "index": index,
                            "total": len(files),
                            "path": str(path),
                            "status": "failed",
                            "error": str(exc),
                        }
                    )

        return result
