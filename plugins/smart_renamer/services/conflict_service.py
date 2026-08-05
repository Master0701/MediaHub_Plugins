from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from models.preview import PreviewIssue, PreviewRow, Severity


class ConflictService:
    """Bewertet Vorschauzeilen mit einheitlichen Konfliktstufen."""

    def evaluate(
        self,
        changes: list[dict[str, Any]],
        *,
        backend_id: str,
    ) -> tuple[list[PreviewRow], list[dict[str, Any]]]:
        rows: list[PreviewRow] = []
        target_map: dict[str, list[int]] = {}

        for index, change in enumerate(changes):
            issues: list[PreviewIssue] = []
            for warning in change.get("warnings") or []:
                issues.append(
                    PreviewIssue(
                        code="rule_warning",
                        message=str(warning),
                        severity=Severity.WARNING,
                        source="rule_engine",
                    )
                )

            source = Path(str(change.get("source_path") or ""))
            target = Path(str(change.get("target_path") or ""))

            if target.exists() and os.path.normcase(str(target)) != os.path.normcase(str(source)):
                issues.append(
                    PreviewIssue(
                        code="target_exists",
                        message="Die Zieldatei existiert bereits.",
                        severity=Severity.BLOCKING,
                    )
                )

            row = PreviewRow(
                index=int(change.get("index", index)),
                source_path=str(source),
                original_name=str(change.get("original_name") or source.name),
                proposed_name=str(change.get("proposed_name") or target.name),
                target_path=str(target),
                changed=bool(change.get("changed")),
                item_type=str(change.get("item_type") or "file"),
                backend_id=backend_id,
                rule_sources=list(change.get("applied_rules") or []),
                issues=issues,
                metadata=dict(change.get("metadata") or {}),
            )
            rows.append(row)
            key = os.path.normcase(os.path.abspath(str(target)))
            target_map.setdefault(key, []).append(index)

        conflicts: list[dict[str, Any]] = []
        for target, indexes in target_map.items():
            if len(indexes) < 2:
                continue
            conflicts.append({
                "type": "duplicate_target",
                "severity": Severity.BLOCKING.value,
                "target_path": target,
                "item_indexes": indexes,
            })
            for index in indexes:
                rows[index].issues.append(
                    PreviewIssue(
                        code="duplicate_target",
                        message="Mehrere Einträge verwenden denselben Zielpfad.",
                        severity=Severity.BLOCKING,
                    )
                )

        return rows, conflicts
