from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ReasoningContext:
    context_id: str
    created_at: str
    source: dict[str, Any]
    document: dict[str, Any] = field(default_factory=dict)
    parser_result: dict[str, Any] = field(default_factory=dict)
    semantic_result: dict[str, Any] = field(default_factory=dict)
    knowledge_result: dict[str, Any] = field(default_factory=dict)
    entities: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    accepted: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    open_questions: list[dict[str, Any]] = field(default_factory=list)
    next_tasks: list[dict[str, Any]] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    automatic_import: bool = False
    requires_confirmation: bool = True

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def create(cls, source: dict[str, Any]):
        return cls(uuid.uuid4().hex, cls.now(), dict(source))

    def add_trace(self, stage, action, status="ok", details=None):
        self.trace.append({
            "id": uuid.uuid4().hex,
            "timestamp": self.now(),
            "stage": stage,
            "action": action,
            "status": status,
            "details": dict(details or {}),
        })

    def add_evidence(self, text, stage, source_location=None, metadata=None):
        item = {
            "id": uuid.uuid4().hex,
            "text": str(text),
            "stage": stage,
            "source_location": source_location,
            "metadata": dict(metadata or {}),
        }
        self.evidence.append(item)
        return item

    def add_candidate(self, kind, value, confidence, reason, stage, evidence_id=None):
        item = {
            "id": uuid.uuid4().hex,
            "kind": kind,
            "value": value,
            "confidence": round(float(confidence), 4),
            "reason": reason,
            "stage": stage,
            "evidence_id": evidence_id,
            "status": "candidate",
            "requires_confirmation": True,
        }
        self.candidates.append(item)
        return item

    def reject(self, candidate, reason, stage):
        item = dict(candidate)
        item.update(status="rejected", rejection_reason=reason, rejected_by=stage)
        self.rejected.append(item)
        return item

    def accept(self, candidate, reason, stage):
        item = dict(candidate)
        item.update(status="accepted", acceptance_reason=reason, accepted_by=stage)
        self.accepted.append(item)
        return item

    def add_open_question(self, question, priority, stage):
        self.open_questions.append({
            "id": uuid.uuid4().hex,
            "question": question,
            "priority": int(priority),
            "stage": stage,
            "status": "open",
        })

    def add_next_task(self, task_type, payload, priority, stage):
        self.next_tasks.append({
            "id": uuid.uuid4().hex,
            "task_type": task_type,
            "payload": dict(payload),
            "priority": int(priority),
            "stage": stage,
            "status": "pending",
        })

    def to_dict(self):
        return {
            "schema_version": 1,
            "context_id": self.context_id,
            "created_at": self.created_at,
            "source": self.source,
            "document": self.document,
            "parser_result": self.parser_result,
            "semantic_result": self.semantic_result,
            "knowledge_result": self.knowledge_result,
            "entities": self.entities,
            "relations": self.relations,
            "candidates": self.candidates,
            "accepted": self.accepted,
            "rejected": self.rejected,
            "evidence": self.evidence,
            "open_questions": self.open_questions,
            "next_tasks": self.next_tasks,
            "trace": self.trace,
            "automatic_import": self.automatic_import,
            "requires_confirmation": self.requires_confirmation,
        }


class ReasoningContextStore:
    def __init__(self, base_path):
        base = Path(base_path)
        self.directory = base.with_name("reasoning_contexts")
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, context):
        path = self.directory / f"{context.context_id}.json"
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(context.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
        return path

    def load(self, context_id):
        path = self.directory / f"{context_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def list_contexts(self):
        result = []
        for path in sorted(self.directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            result.append({
                "context_id": data.get("context_id"),
                "created_at": data.get("created_at"),
                "source": data.get("source"),
                "entity_count": len(data.get("entities") or []),
                "candidate_count": len(data.get("candidates") or []),
                "rejected_count": len(data.get("rejected") or []),
                "open_question_count": len(data.get("open_questions") or []),
                "path": str(path.resolve()),
            })
        return result
