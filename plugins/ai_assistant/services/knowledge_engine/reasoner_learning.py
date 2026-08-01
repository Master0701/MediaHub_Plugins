from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ReasonerLearningStore:
    """Speichert bestätigte und abgelehnte Reasoner-Entscheidungen."""

    def __init__(self, knowledge_database_path: str | Path):
        database = Path(knowledge_database_path)
        self.path = database.with_name("reasoner_learning.json")
        self._data = {
            "schema_version": 1,
            "decisions": [],
            "relation_stats": {},
            "evidence_stats": {},
        }
        self._load()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

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
            self._data.setdefault("decisions", [])
            self._data.setdefault("relation_stats", {})
            self._data.setdefault("evidence_stats", {})

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _decision_value(decision: str) -> int:
        mapping = {
            "accepted": 1,
            "rejected": -1,
            "later": 0,
        }
        if decision not in mapping:
            raise ValueError(f"Ungültige Lernentscheidung: {decision}")
        return mapping[decision]

    def record(
        self,
        proposal: dict[str, Any],
        decision: str,
        *,
        note: str | None = None,
    ) -> dict[str, Any]:
        value = self._decision_value(decision)
        relation_type = str(proposal.get("relation_type") or "unknown")
        evidence_types = sorted(
            {
                str(item.get("type") or "unknown")
                for item in proposal.get("evidence") or []
            }
        )

        record = {
            "id": uuid.uuid4().hex,
            "created_at": self._now(),
            "decision": decision,
            "value": value,
            "proposal_id": proposal.get("id"),
            "kind": proposal.get("kind"),
            "relation_type": relation_type,
            "confidence": proposal.get("confidence"),
            "evidence_types": evidence_types,
            "source_title": proposal.get("source_title"),
            "target_title": proposal.get("target_title"),
            "entity_title": proposal.get("entity_title"),
            "group_name": proposal.get("group_name"),
            "note": note,
        }
        self._data["decisions"].append(record)

        relation_stats = self._data["relation_stats"].setdefault(
            relation_type,
            {"accepted": 0, "rejected": 0, "later": 0},
        )
        relation_stats[decision] = relation_stats.get(decision, 0) + 1

        for evidence_type in evidence_types:
            stats = self._data["evidence_stats"].setdefault(
                evidence_type,
                {"accepted": 0, "rejected": 0, "later": 0},
            )
            stats[decision] = stats.get(decision, 0) + 1

        self._save()
        return record

    @staticmethod
    def _adjustment(stats: dict[str, int]) -> float:
        accepted = int(stats.get("accepted") or 0)
        rejected = int(stats.get("rejected") or 0)
        total = accepted + rejected
        if total < 2:
            return 0.0

        ratio = (accepted - rejected) / total
        return max(-0.12, min(0.12, ratio * 0.12))

    def adjust_proposal(
        self,
        proposal: dict[str, Any],
    ) -> dict[str, Any]:
        result = dict(proposal)
        base_confidence = float(result.get("confidence") or 0.0)

        relation_adjustment = self._adjustment(
            self._data.get("relation_stats", {}).get(
                str(result.get("relation_type") or "unknown"),
                {},
            )
        )

        evidence_adjustments = []
        for evidence in result.get("evidence") or []:
            evidence_type = str(evidence.get("type") or "unknown")
            evidence_adjustments.append(
                self._adjustment(
                    self._data.get("evidence_stats", {}).get(
                        evidence_type,
                        {},
                    )
                )
            )

        evidence_adjustment = (
            sum(evidence_adjustments) / len(evidence_adjustments)
            if evidence_adjustments
            else 0.0
        )
        total_adjustment = max(
            -0.18,
            min(0.18, relation_adjustment + evidence_adjustment),
        )

        result["base_confidence"] = round(base_confidence, 4)
        result["learning_adjustment"] = round(total_adjustment, 4)
        result["confidence"] = round(
            max(0.0, min(0.99, base_confidence + total_adjustment)),
            4,
        )
        result["learning_applied"] = bool(total_adjustment)
        return result

    def adjust_many(
        self,
        proposals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [self.adjust_proposal(item) for item in proposals]

    def status(self) -> dict[str, Any]:
        decisions = self._data.get("decisions") or []
        return {
            "schema_version": 1,
            "path": str(self.path.resolve()),
            "decision_count": len(decisions),
            "accepted_count": sum(
                1 for item in decisions if item.get("decision") == "accepted"
            ),
            "rejected_count": sum(
                1 for item in decisions if item.get("decision") == "rejected"
            ),
            "later_count": sum(
                1 for item in decisions if item.get("decision") == "later"
            ),
            "relation_stats": self._data.get("relation_stats") or {},
            "evidence_stats": self._data.get("evidence_stats") or {},
        }
