from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class LearningReviewStore:
    """Lokale Review-Warteschlange für KI-Lernfälle.

    Rohdaten und private Dateipfade bleiben ausschließlich
    im MediaHub-Laufzeitbereich unter plugin_data.

    Erst später erzeugte, anonymisierte und bestätigte
    Lernregeln dürfen als allgemeiner KI-Lernstand
    exportiert werden.
    """

    VALID_STATES = {
        "pending",
        "correct",
        "wrong",
        "corrected",
        "deferred",
    }

    SCHEMA_VERSION = 1

    def __init__(self, mediahub_base: Path):
        self.mediahub_base = Path(
            mediahub_base
        ).expanduser().resolve()

        self.learning_dir = (
            self.mediahub_base
            / "plugin_data"
            / "ai_assistant"
            / "learning"
        )

        self.learning_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.queue_path = (
            self.learning_dir
            / "review_queue.json"
        )

        self.history_path = (
            self.learning_dir
            / "review_history.json"
        )

        self.rules_path = (
            self.learning_dir
            / "distilled_rules.json"
        )

        self._ensure_files()

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _empty_document(
        self,
        kind: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "kind": kind,
            "updated_at": self._now(),
            "items": [],
        }

    def _ensure_file(
        self,
        path: Path,
        kind: str,
    ) -> None:
        if path.exists():
            return

        self._write(
            path,
            self._empty_document(kind),
        )

    def _ensure_files(self) -> None:
        self._ensure_file(
            self.queue_path,
            "review_queue",
        )

        self._ensure_file(
            self.history_path,
            "review_history",
        )

        self._ensure_file(
            self.rules_path,
            "distilled_rules",
        )

    @staticmethod
    def _read(
        path: Path,
    ) -> dict[str, Any]:
        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (
            FileNotFoundError,
            json.JSONDecodeError,
        ):
            return {}

        return (
            data
            if isinstance(data, dict)
            else {}
        )

    def _write(
        self,
        path: Path,
        data: dict[str, Any],
    ) -> None:
        document = dict(data)
        document["schema_version"] = (
            self.SCHEMA_VERSION
        )
        document["updated_at"] = self._now()

        temp = path.with_suffix(
            path.suffix + ".tmp"
        )

        temp.write_text(
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        temp.replace(path)

    def list_queue(
        self,
    ) -> list[dict[str, Any]]:
        document = self._read(
            self.queue_path
        )

        return [
            dict(item)
            for item in (
                document.get("items")
                or []
            )
            if isinstance(item, dict)
        ]

    def list_history(
        self,
    ) -> list[dict[str, Any]]:
        document = self._read(
            self.history_path
        )

        return [
            dict(item)
            for item in (
                document.get("items")
                or []
            )
            if isinstance(item, dict)
        ]

    def add_case(
        self,
        *,
        source_path: str,
        analysis: dict[str, Any],
        fingerprint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        document = self._read(
            self.queue_path
        )

        items = list(
            document.get("items")
            or []
        )

        case = {
            "id": uuid4().hex,
            "state": "pending",
            "created_at": self._now(),
            "reviewed_at": "",
            "source_path": str(
                source_path or ""
            ),
            "analysis": dict(
                analysis or {}
            ),
            "fingerprint": dict(
                fingerprint or {}
            ),
            "correction": {},
            "review_note": "",
        }

        items.append(case)

        document["kind"] = "review_queue"
        document["items"] = items

        self._write(
            self.queue_path,
            document,
        )

        return dict(case)

    def review_case(
        self,
        case_id: str,
        state: str,
        *,
        correction: dict[str, Any] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        normalized_state = str(
            state or ""
        ).strip().casefold()

        if normalized_state not in (
            self.VALID_STATES
            - {"pending"}
        ):
            raise ValueError(
                "Ungültiger Review-Status: "
                f"{state}"
            )

        queue_document = self._read(
            self.queue_path
        )

        queue_items = list(
            queue_document.get("items")
            or []
        )

        selected = None
        remaining = []

        for item in queue_items:
            current = dict(item or {})

            if (
                str(current.get("id") or "")
                == str(case_id)
                and selected is None
            ):
                selected = current
            else:
                remaining.append(current)

        if selected is None:
            raise KeyError(
                f"Lernfall nicht gefunden: {case_id}"
            )

        selected["state"] = normalized_state
        selected["reviewed_at"] = self._now()
        selected["correction"] = dict(
            correction or {}
        )
        selected["review_note"] = str(
            note or ""
        )

        queue_document["kind"] = (
            "review_queue"
        )
        queue_document["items"] = remaining

        self._write(
            self.queue_path,
            queue_document,
        )

        history_document = self._read(
            self.history_path
        )

        history_items = list(
            history_document.get("items")
            or []
        )

        history_items.append(selected)

        history_document["kind"] = (
            "review_history"
        )
        history_document["items"] = (
            history_items
        )

        self._write(
            self.history_path,
            history_document,
        )

        return dict(selected)

    def release_history_case(
        self,
        case_id: str,
    ) -> dict[str, Any]:
        """Entfernt genau einen abgeschlossenen Lernfall.

        Der Fall wird absichtlich NICHT wieder in die
        Review-Queue gelegt. Dadurch gilt sein Dateipfad
        beim nächsten Massenscan wieder als unbekannt und
        kann vollständig neu analysiert werden.
        """
        normalized_id = str(
            case_id
            or ""
        ).strip()

        if not normalized_id:
            raise ValueError(
                "Lernfall-ID fehlt."
            )

        document = self._read(
            self.history_path
        )

        items = list(
            document.get("items")
            or []
        )

        selected = None
        remaining = []

        for item in items:
            current = dict(
                item
                or {}
            )

            if (
                selected is None
                and str(
                    current.get("id")
                    or ""
                )
                == normalized_id
            ):
                selected = current
            else:
                remaining.append(
                    current
                )

        if selected is None:
            raise KeyError(
                "Abgeschlossener Lernfall "
                f"nicht gefunden: {normalized_id}"
            )

        document["kind"] = (
            "review_history"
        )
        document["items"] = remaining

        self._write(
            self.history_path,
            document,
        )

        return dict(selected)

    def stats(
        self,
    ) -> dict[str, int]:
        queue = self.list_queue()
        history = self.list_history()

        result = {
            "pending": len(queue),
            "correct": 0,
            "wrong": 0,
            "corrected": 0,
            "deferred": 0,
            "reviewed": len(history),
        }

        for item in history:
            state = str(
                item.get("state")
                or ""
            ).casefold()

            if state in result:
                result[state] += 1

        return result
