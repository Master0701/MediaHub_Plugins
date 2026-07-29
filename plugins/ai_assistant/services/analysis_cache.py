from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AnalysisCache:
    """SQLite-Cache für vollständige Medienanalysen.

    Die Klasse besitzt ihre Tabelle selbst. Dadurch funktioniert der
    KI-Assistent auch eigenständig und unabhängig von der Reihenfolge,
    in der andere Datenbankdienste gestartet wurden.
    """

    def __init__(self, database_path: str | Path | None):
        self.database_path = (
            Path(database_path).resolve()
            if database_path is not None
            else None
        )
        if self.database_path is not None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        if self.database_path is None:
            raise RuntimeError("Für den Analyse-Cache ist keine Datenbank konfiguriert.")

        connection = sqlite3.connect(
            self.database_path,
            timeout=10.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS identification_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_ns INTEGER NOT NULL,
                    confidence REAL,
                    method_summary TEXT,
                    analysis_payload TEXT,
                    analyzed_at TEXT NOT NULL,
                    UNIQUE(file_path, file_size, modified_ns)
                )
                """
            )

            columns = {
                str(row["name"])
                for row in db.execute(
                    "PRAGMA table_info(identification_cache)"
                ).fetchall()
            }

            migrations = {
                "confidence": "ALTER TABLE identification_cache ADD COLUMN confidence REAL",
                "method_summary": "ALTER TABLE identification_cache ADD COLUMN method_summary TEXT",
                "analysis_payload": "ALTER TABLE identification_cache ADD COLUMN analysis_payload TEXT",
                "analyzed_at": "ALTER TABLE identification_cache ADD COLUMN analyzed_at TEXT",
            }

            for column, statement in migrations.items():
                if column not in columns:
                    db.execute(statement)

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_identification_cache_file
                ON identification_cache(file_path)
                """
            )
            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                    idx_identification_cache_signature
                ON identification_cache(file_path, file_size, modified_ns)
                """
            )
            db.commit()

    @staticmethod
    def _signature(path: Path) -> tuple[str, int, int]:
        resolved = path.resolve()
        stat = resolved.stat()
        return str(resolved), int(stat.st_size), int(stat.st_mtime_ns)

    def get(self, file_path: str | Path) -> dict[str, Any] | None:
        if self.database_path is None:
            return None

        path = Path(file_path)
        file_name, size, modified_ns = self._signature(path)

        # Eine alte oder extern angelegte Datenbank wird hier ebenfalls
        # automatisch repariert.
        self._ensure_schema()

        with self._connect() as db:
            row = db.execute(
                """
                SELECT analysis_payload, analyzed_at
                FROM identification_cache
                WHERE file_path = ?
                  AND file_size = ?
                  AND modified_ns = ?
                LIMIT 1
                """,
                (file_name, size, modified_ns),
            ).fetchone()

        if row is None or not row["analysis_payload"]:
            return None

        try:
            result = json.loads(str(row["analysis_payload"]))
        except (TypeError, json.JSONDecodeError):
            return None

        if not isinstance(result, dict):
            return None

        result.setdefault("cache", {})
        result["cache"]["analyzed_at"] = row["analyzed_at"]
        return result

    def put(
        self,
        file_path: str | Path,
        analysis: dict[str, Any],
    ) -> None:
        if self.database_path is None:
            return

        path = Path(file_path)
        file_name, size, modified_ns = self._signature(path)
        decision = analysis.get("decision") or {}
        methods = analysis.get("methods_used") or []
        analyzed_at = datetime.now(timezone.utc).isoformat()

        self._ensure_schema()

        with self._connect() as db:
            db.execute(
                """
                INSERT INTO identification_cache (
                    file_path,
                    file_size,
                    modified_ns,
                    confidence,
                    method_summary,
                    analysis_payload,
                    analyzed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path, file_size, modified_ns)
                DO UPDATE SET
                    confidence = excluded.confidence,
                    method_summary = excluded.method_summary,
                    analysis_payload = excluded.analysis_payload,
                    analyzed_at = excluded.analyzed_at
                """,
                (
                    file_name,
                    size,
                    modified_ns,
                    float(
                        decision.get("confidence")
                        or (analysis.get("identification") or {}).get(
                            "confidence"
                        )
                        or 0.0
                    ),
                    ", ".join(str(item) for item in methods),
                    json.dumps(
                        analysis,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    analyzed_at,
                ),
            )
            db.commit()

    def clear_file(self, file_path: str | Path) -> int:
        if self.database_path is None:
            return 0

        file_name = str(Path(file_path).resolve())
        self._ensure_schema()

        with self._connect() as db:
            cursor = db.execute(
                "DELETE FROM identification_cache WHERE file_path = ?",
                (file_name,),
            )
            db.commit()
            return int(cursor.rowcount or 0)

    def clear(self) -> int:
        if self.database_path is None:
            return 0

        self._ensure_schema()

        with self._connect() as db:
            cursor = db.execute("DELETE FROM identification_cache")
            db.commit()
            return int(cursor.rowcount or 0)

    # Kompatibilitätsnamen für ältere Aufrufer.
    def delete(self, file_path: str | Path) -> int:
        return self.clear_file(file_path)

    def clear_for(self, file_path: str | Path) -> int:
        return self.clear_file(file_path)
