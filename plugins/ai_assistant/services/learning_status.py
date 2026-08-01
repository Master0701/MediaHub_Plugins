from __future__ import annotations

from pathlib import Path
from typing import Any

from services.fingerprint_store import FingerprintReferenceStore
from services.knowledge_learning import KnowledgeLearningService
from services.visual_knowledge import VisualKnowledgeStore


class LearningStatusService:
    """Diagnose der tatsächlich verwendeten lokalen Lern-Datenbank."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.learning = KnowledgeLearningService(self.database_path)
        self.fingerprints = FingerprintReferenceStore(self.database_path)
        self.visual = VisualKnowledgeStore(self.database_path)

    def status(self) -> dict[str, Any]:
        snapshot = self.learning.export_snapshot()
        visual_snapshot = self.visual.export_snapshot()
        fingerprint_count = 0
        if self.database_path.exists():
            import sqlite3
            with sqlite3.connect(self.database_path) as db:
                row = db.execute(
                    "SELECT COUNT(*) FROM ai_fingerprint_references"
                ).fetchone()
                fingerprint_count = int(row[0] if row else 0)

        return {
            "schema_version": 1,
            "database_path": str(self.database_path),
            "database_exists": self.database_path.exists(),
            "learned_identity_count": len(snapshot.get("identities") or []),
            "learned_alias_count": len(snapshot.get("aliases") or []),
            "fingerprint_reference_count": fingerprint_count,
            "visual_knowledge_count": len(
                visual_snapshot.get("entries") or []
            ),
            "conflict_count": len(snapshot.get("conflicts") or []),
        }
