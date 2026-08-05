from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKING = "blocking"


@dataclass(slots=True)
class PreviewIssue:
    code: str
    message: str
    severity: Severity
    source: str = "pipeline"

    def to_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["severity"] = self.severity.value
        return payload


@dataclass(slots=True)
class PreviewRow:
    index: int
    source_path: str
    original_name: str
    proposed_name: str
    target_path: str
    changed: bool
    item_type: str
    backend_id: str
    rule_sources: list[str] = field(default_factory=list)
    issues: list[PreviewIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return any(issue.severity == Severity.BLOCKING for issue in self.issues)

    @property
    def highest_severity(self) -> Severity:
        order = {
            Severity.INFO: 0,
            Severity.WARNING: 1,
            Severity.ERROR: 2,
            Severity.BLOCKING: 3,
        }
        if not self.issues:
            return Severity.INFO
        return max((issue.severity for issue in self.issues), key=order.get)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "source_path": self.source_path,
            "original_name": self.original_name,
            "proposed_name": self.proposed_name,
            "target_path": self.target_path,
            "changed": self.changed,
            "item_type": self.item_type,
            "backend_id": self.backend_id,
            "rule_sources": list(self.rule_sources),
            "issues": [issue.to_dict() for issue in self.issues],
            "blocked": self.blocked,
            "highest_severity": self.highest_severity.value,
            "metadata": dict(self.metadata),
        }
