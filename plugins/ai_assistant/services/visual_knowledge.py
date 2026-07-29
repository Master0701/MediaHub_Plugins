from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class VisualKnowledgeStore:
    """Persistiert bestätigte visuelle Merkmale einer Medienidentität."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_visual_knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identity_id INTEGER NOT NULL,
                    visual_signature TEXT,
                    visual_fingerprint_json TEXT NOT NULL DEFAULT '{}',
                    scene_signature_json TEXT NOT NULL DEFAULT '{}',
                    ocr_logo_json TEXT NOT NULL DEFAULT '{}',
                    intro_outro_json TEXT NOT NULL DEFAULT '{}',
                    subject_profile_json TEXT NOT NULL DEFAULT '{}',
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    confirmed_by_user INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(identity_id, visual_signature)
                )
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_visual_knowledge_identity
                ON ai_visual_knowledge(identity_id)
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_visual_knowledge_signature
                ON ai_visual_knowledge(visual_signature)
                """
            )
            db.commit()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value or {}, ensure_ascii=False, separators=(",", ":"))

    def register_confirmed(
        self,
        identity_id: int,
        visual_intelligence: dict[str, Any] | None,
        *,
        source: str = "user_confirmation",
        confidence: float = 1.0,
        confirmed_by_user: bool = True,
    ) -> dict[str, Any]:
        visual = dict(visual_intelligence or {})
        signature = str(visual.get("visual_signature") or "").strip() or None
        now = datetime.now(timezone.utc).isoformat()

        if not confirmed_by_user:
            return {
                "status": "proposal_only",
                "persisted": False,
                "reason": "Visuelles Wissen wird erst nach Bestätigung gespeichert.",
            }

        with self._connect() as db:
            db.execute(
                """
                INSERT INTO ai_visual_knowledge (
                    identity_id,
                    visual_signature,
                    visual_fingerprint_json,
                    scene_signature_json,
                    ocr_logo_json,
                    intro_outro_json,
                    subject_profile_json,
                    source,
                    confidence,
                    confirmed_by_user,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(identity_id, visual_signature)
                DO UPDATE SET
                    visual_fingerprint_json = excluded.visual_fingerprint_json,
                    scene_signature_json = excluded.scene_signature_json,
                    ocr_logo_json = excluded.ocr_logo_json,
                    intro_outro_json = excluded.intro_outro_json,
                    subject_profile_json = excluded.subject_profile_json,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    confirmed_by_user = 1,
                    updated_at = excluded.updated_at
                """,
                (
                    int(identity_id),
                    signature,
                    self._json(visual.get("visual_fingerprint")),
                    self._json(visual.get("scene_signature")),
                    self._json(visual.get("ocr_logo_fusion")),
                    self._json(visual.get("intro_outro_detection")),
                    self._json(visual.get("character_preparation")),
                    str(source),
                    float(confidence),
                    now,
                    now,
                ),
            )
            db.commit()

        return {
            "status": "confirmed_visual_knowledge_saved",
            "persisted": True,
            "identity_id": int(identity_id),
            "visual_signature": signature,
            "source": str(source),
            "confidence": float(confidence),
        }

    def for_identity(self, identity_id: int) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT *
                FROM ai_visual_knowledge
                WHERE identity_id = ?
                ORDER BY updated_at DESC
                """,
                (int(identity_id),),
            ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            for column, target in (
                ("visual_fingerprint_json", "visual_fingerprint"),
                ("scene_signature_json", "scene_signature"),
                ("ocr_logo_json", "ocr_logo_fusion"),
                ("intro_outro_json", "intro_outro_detection"),
                ("subject_profile_json", "character_preparation"),
            ):
                item[target] = json.loads(item.pop(column) or "{}")
            result.append(item)
        return result

    def find_by_signature(self, signature: str) -> list[dict[str, Any]]:
        value = str(signature or "").strip()
        if not value:
            return []
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT identity_id, visual_signature, source, confidence,
                       confirmed_by_user, updated_at
                FROM ai_visual_knowledge
                WHERE visual_signature = ?
                ORDER BY confidence DESC, updated_at DESC
                """,
                (value,),
            ).fetchall()
        return [dict(row) for row in rows]

    def export_snapshot(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT identity_id, visual_signature, source, confidence,
                       confirmed_by_user, created_at, updated_at
                FROM ai_visual_knowledge
                ORDER BY identity_id, updated_at DESC
                """
            ).fetchall()
        return {
            "schema_version": 1,
            "type": "visual_knowledge_snapshot",
            "entries": [dict(row) for row in rows],
        }
