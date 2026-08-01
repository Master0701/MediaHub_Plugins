from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SourceConflictResolver:
    """Vergleicht Quellenaussagen und erzeugt bestätigbare Feldvorschläge."""

    def __init__(self, knowledge_database_path: str | Path):
        database = Path(knowledge_database_path)
        self.path = database.with_name("source_conflicts.json")
        self._data = {
            "schema_version": 1,
            "comparisons": [],
            "decisions": [],
        }
        self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize(value: Any) -> str:
        if isinstance(value, list):
            return "|".join(sorted(str(item).strip().casefold() for item in value))
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return " ".join(str(value or "").strip().casefold().split())

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(loaded, dict):
            self._data = loaded
            self._data.setdefault("schema_version", 1)
            self._data.setdefault("comparisons", [])
            self._data.setdefault("decisions", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def compare(
        self,
        source_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        field_values: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for result in source_results:
            source = dict(result.get("source") or {})
            values = dict(result.get("values") or {})
            for field, value in values.items():
                if value in (None, "", [], {}):
                    continue
                field_values[str(field)].append(
                    {
                        "source_id": source.get("id"),
                        "source_name": source.get("name"),
                        "trust": float(source.get("trust") or 0.0),
                        "priority": int(source.get("priority") or 0),
                        "value": value,
                        "normalized": self._normalize(value),
                    }
                )

        fields = []
        conflict_count = 0

        for field, candidates in sorted(field_values.items()):
            grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for candidate in candidates:
                grouped[candidate["normalized"]].append(candidate)

            ranked_values = []
            for normalized, supporters in grouped.items():
                trust_score = sum(item["trust"] for item in supporters)
                priority_score = sum(item["priority"] for item in supporters) / 1000.0
                score = trust_score + priority_score
                representative = max(
                    supporters,
                    key=lambda item: (item["trust"], item["priority"]),
                )
                ranked_values.append(
                    {
                        "value": representative["value"],
                        "normalized": normalized,
                        "support_count": len(supporters),
                        "supporters": supporters,
                        "score": round(score, 4),
                    }
                )

            ranked_values.sort(
                key=lambda item: (
                    -float(item["score"]),
                    -int(item["support_count"]),
                    str(item["normalized"]),
                )
            )
            has_conflict = len(ranked_values) > 1
            if has_conflict:
                conflict_count += 1

            winner = ranked_values[0] if ranked_values else None
            fields.append(
                {
                    "field": field,
                    "has_conflict": has_conflict,
                    "candidate_count": len(ranked_values),
                    "candidates": ranked_values,
                    "recommended_value": winner["value"] if winner else None,
                    "recommended_score": winner["score"] if winner else 0.0,
                    "requires_confirmation": True,
                }
            )

        comparison = {
            "id": uuid.uuid4().hex,
            "schema_version": 1,
            "created_at": self._now(),
            "source_result_count": len(source_results),
            "field_count": len(fields),
            "conflict_count": conflict_count,
            "fields": fields,
            "automatic_import": False,
            "requires_confirmation": True,
        }
        self._data["comparisons"].append(comparison)
        self._save()
        return dict(comparison)

    def get_comparison(self, comparison_id: str) -> dict[str, Any] | None:
        comparison_id = str(comparison_id)
        for item in self._data.get("comparisons") or []:
            if str(item.get("id")) == comparison_id:
                return item
        return None

    def confirm_fields(
        self,
        comparison_id: str,
        selected_fields: dict[str, Any],
        *,
        target_entity_id: str | None = None,
        note: str | None = None,
    ) -> dict[str, Any]:
        comparison = self.get_comparison(comparison_id)
        if comparison is None:
            raise KeyError(f"Vergleich nicht gefunden: {comparison_id}")

        allowed_fields = {
            str(item.get("field"))
            for item in comparison.get("fields") or []
        }
        unknown = set(selected_fields) - allowed_fields
        if unknown:
            raise ValueError(
                "Unbekannte Felder: " + ", ".join(sorted(unknown))
            )

        decision = {
            "id": uuid.uuid4().hex,
            "comparison_id": comparison_id,
            "created_at": self._now(),
            "target_entity_id": target_entity_id,
            "selected_fields": dict(selected_fields),
            "note": note,
            "status": "confirmed",
        }
        self._data["decisions"].append(decision)
        self._save()
        return dict(decision)

    def status(self) -> dict[str, Any]:
        comparisons = self._data.get("comparisons") or []
        decisions = self._data.get("decisions") or []
        return {
            "schema_version": 1,
            "path": str(self.path.resolve()),
            "comparison_count": len(comparisons),
            "decision_count": len(decisions),
            "conflict_count": sum(
                int(item.get("conflict_count") or 0)
                for item in comparisons
            ),
        }
