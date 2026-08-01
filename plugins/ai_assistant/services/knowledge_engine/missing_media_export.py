from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any


class MissingMediaExportService:
    """Erzeugt strukturierte Übergaben für andere MediaHub-Plugins."""

    SUPPORTED_STATUSES = {
        "pending",
        "wanted",
        "later",
        "rejected",
        "resolved",
    }

    def __init__(self, queue: Any):
        self.queue = queue

    def build_payload(
        self,
        *,
        statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        selected = set(statuses or ["pending", "wanted", "later"])
        invalid = selected - self.SUPPORTED_STATUSES
        if invalid:
            raise ValueError(
                "Ungültige Statuswerte: "
                + ", ".join(sorted(invalid))
            )

        items = [
            dict(item)
            for item in self.queue.list()
            if item.get("status") in selected
        ]

        return {
            "schema_version": 1,
            "producer": "mediahub.ai_assistant",
            "producer_version": "2.4.2",
            "kind": "missing_media_export",
            "statuses": sorted(selected),
            "count": len(items),
            "items": items,
            "automatic_download": False,
            "automatic_search": False,
            "automatic_file_change": False,
        }

    def to_json(
        self,
        *,
        statuses: list[str] | None = None,
    ) -> str:
        return json.dumps(
            self.build_payload(statuses=statuses),
            ensure_ascii=False,
            indent=2,
        ) + "\n"

    def to_csv(
        self,
        *,
        statuses: list[str] | None = None,
    ) -> str:
        payload = self.build_payload(statuses=statuses)
        output = StringIO()
        fieldnames = [
            "id",
            "status",
            "group_type",
            "group_name",
            "title",
            "year",
            "media_type",
            "note",
            "created_at",
            "updated_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for item in payload["items"]:
            writer.writerow(
                {
                    key: item.get(key)
                    for key in fieldnames
                }
            )
        return output.getvalue()

    def write_file(
        self,
        destination: str | Path,
        *,
        format_name: str,
        statuses: list[str] | None = None,
    ) -> dict[str, Any]:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)

        normalized_format = str(format_name).strip().lower()
        if normalized_format == "json":
            content = self.to_json(statuses=statuses)
        elif normalized_format == "csv":
            content = self.to_csv(statuses=statuses)
        else:
            raise ValueError(
                f"Nicht unterstütztes Exportformat: {format_name}"
            )

        path.write_text(content, encoding="utf-8-sig")
        return {
            "path": str(path.resolve()),
            "format": normalized_format,
            "count": self.build_payload(
                statuses=statuses
            )["count"],
        }
