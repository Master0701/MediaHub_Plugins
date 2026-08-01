from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class IdentityCleanupService:
    """Sichere Bereinigung falscher oder doppelter Medienidentitäten."""

    def __init__(self, knowledge_database_path: str | Path, graph_store: Any):
        self.database_path = Path(knowledge_database_path).resolve()
        self.graph_store = graph_store

    @staticmethod
    def _stamp() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def _backup(self) -> dict[str, str | None]:
        backup_dir = self.database_path.parent / (
            f"identity_cleanup_backup_{self._stamp()}"
        )
        backup_dir.mkdir(parents=True, exist_ok=False)

        database_backup = None
        if self.database_path.exists():
            database_backup = backup_dir / self.database_path.name
            shutil.copy2(self.database_path, database_backup)

            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(self.database_path) + suffix)
                if sidecar.exists():
                    shutil.copy2(sidecar, backup_dir / sidecar.name)

        graph_file = Path(self.graph_store.data_file)
        graph_backup = None
        if graph_file.exists():
            graph_backup = backup_dir / "knowledge_graph.json"
            shutil.copy2(graph_file, graph_backup)

        return {
            "backup_dir": str(backup_dir.resolve()),
            "database": (
                str(database_backup.resolve())
                if database_backup is not None
                else None
            ),
            "graph": (
                str(graph_backup.resolve())
                if graph_backup is not None
                else None
            ),
        }

    def _graph_entity(self, entity_id: str) -> dict[str, Any]:
        entity = self.graph_store.get_entity(str(entity_id))
        if entity is None:
            raise KeyError(f"Graph-Entität nicht gefunden: {entity_id}")
        return entity

    @staticmethod
    def _learned_identity_id(entity: dict[str, Any]) -> int | None:
        metadata = dict(entity.get("metadata") or {})
        value = metadata.get("knowledge_identity_id")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def preview(
        self,
        source_entity_id: str,
        target_entity_id: str | None = None,
    ) -> dict[str, Any]:
        source = self._graph_entity(source_entity_id)
        target = (
            self._graph_entity(target_entity_id)
            if target_entity_id
            else None
        )
        if target and source["id"] == target["id"]:
            raise ValueError("Quelle und Ziel dürfen nicht identisch sein.")

        source_learned = self._learned_identity_id(source)
        target_learned = (
            self._learned_identity_id(target)
            if target is not None
            else None
        )

        relations = self.graph_store.relations_for(str(source["id"]))
        orders = self.graph_store.orders_for_entity(str(source["id"]))

        database_counts = {
            "aliases": 0,
            "visual_knowledge": 0,
            "fingerprints": 0,
        }
        if source_learned is not None and self.database_path.exists():
            with sqlite3.connect(self.database_path) as db:
                queries = (
                    (
                        "aliases",
                        "SELECT COUNT(*) FROM ai_learned_aliases "
                        "WHERE identity_id=?",
                    ),
                    (
                        "visual_knowledge",
                        "SELECT COUNT(*) FROM ai_visual_knowledge "
                        "WHERE identity_id=?",
                    ),
                    (
                        "fingerprints",
                        "SELECT COUNT(*) FROM ai_fingerprint_references "
                        "WHERE knowledge_identity_id=?",
                    ),
                )
                for key, query in queries:
                    try:
                        database_counts[key] = int(
                            db.execute(query, (source_learned,)).fetchone()[0]
                        )
                    except sqlite3.OperationalError:
                        database_counts[key] = 0

        return {
            "schema_version": 1,
            "mode": "merge" if target else "delete",
            "source": source,
            "target": target,
            "source_learned_identity_id": source_learned,
            "target_learned_identity_id": target_learned,
            "affected_graph_relations": len(relations),
            "affected_graph_orders": len(orders),
            "database_references": database_counts,
            "backup_required": True,
            "requires_user_confirmation": True,
        }

    def _merge_learning_data(
        self,
        source_id: int,
        target_id: int,
    ) -> None:
        with sqlite3.connect(self.database_path) as db:
            db.execute("PRAGMA foreign_keys=ON")

            aliases = db.execute(
                """
                SELECT alias, normalized_alias, source, confidence,
                       confirmed_by_user
                FROM ai_learned_aliases
                WHERE identity_id=?
                """,
                (source_id,),
            ).fetchall()
            for alias in aliases:
                db.execute(
                    """
                    INSERT OR IGNORE INTO ai_learned_aliases(
                        identity_id, alias, normalized_alias, source,
                        confidence, confirmed_by_user
                    )
                    VALUES(?,?,?,?,?,?)
                    """,
                    (
                        target_id,
                        alias[0],
                        alias[1],
                        alias[2],
                        alias[3],
                        alias[4],
                    ),
                )

            try:
                db.execute(
                    """
                    UPDATE ai_visual_knowledge
                    SET identity_id=?
                    WHERE identity_id=?
                    """,
                    (target_id, source_id),
                )
            except sqlite3.IntegrityError:
                db.execute(
                    "DELETE FROM ai_visual_knowledge WHERE identity_id=?",
                    (source_id,),
                )
            except sqlite3.OperationalError:
                pass

            try:
                db.execute(
                    """
                    UPDATE ai_fingerprint_references
                    SET knowledge_identity_id=?
                    WHERE knowledge_identity_id=?
                    """,
                    (target_id, source_id),
                )
            except sqlite3.OperationalError:
                pass

            db.execute(
                "DELETE FROM ai_learned_aliases WHERE identity_id=?",
                (source_id,),
            )
            db.execute(
                "DELETE FROM ai_learned_identities WHERE id=?",
                (source_id,),
            )
            db.commit()

    def _delete_learning_data(self, source_id: int) -> None:
        with sqlite3.connect(self.database_path) as db:
            for statement in (
                "DELETE FROM ai_visual_knowledge WHERE identity_id=?",
                "DELETE FROM ai_fingerprint_references "
                "WHERE knowledge_identity_id=?",
                "DELETE FROM ai_learned_aliases WHERE identity_id=?",
                "DELETE FROM ai_learned_identities WHERE id=?",
            ):
                try:
                    db.execute(statement, (source_id,))
                except sqlite3.OperationalError:
                    pass
            db.commit()

    def apply(
        self,
        source_entity_id: str,
        target_entity_id: str | None = None,
    ) -> dict[str, Any]:
        preview = self.preview(source_entity_id, target_entity_id)
        source = preview["source"]
        target = preview["target"]
        backup = self._backup()

        source_id = str(source["id"])
        target_id = str(target["id"]) if target else None

        if target:
            target_record = self.graph_store._data["entities"][target_id]
            target_record["aliases"] = sorted(
                {
                    *[str(item) for item in target_record.get("aliases") or []],
                    str(source.get("title") or ""),
                    *[str(item) for item in source.get("aliases") or []],
                }
                - {""}
            )

            for relation in self.graph_store._data["relations"].values():
                if relation.get("source_id") == source_id:
                    relation["source_id"] = target_id
                if relation.get("target_id") == source_id:
                    relation["target_id"] = target_id

            for order in self.graph_store._data["orders"].values():
                entries = order.get("entries") or []
                for entry in entries:
                    if entry.get("entity_id") == source_id:
                        entry["entity_id"] = target_id

        else:
            self.graph_store._data["relations"] = {
                key: value
                for key, value in self.graph_store._data["relations"].items()
                if value.get("source_id") != source_id
                and value.get("target_id") != source_id
            }
            for order in self.graph_store._data["orders"].values():
                order["entries"] = [
                    entry
                    for entry in order.get("entries") or []
                    if entry.get("entity_id") != source_id
                ]

        self.graph_store._data["entities"].pop(source_id, None)

        # Doppelte Relationen nach einer Zusammenführung entfernen.
        seen_relations = set()
        cleaned_relations = {}
        for relation_id, relation in self.graph_store._data["relations"].items():
            signature = (
                relation.get("source_id"),
                relation.get("target_id"),
                relation.get("relation_type"),
            )
            if signature in seen_relations:
                continue
            seen_relations.add(signature)
            cleaned_relations[relation_id] = relation
        self.graph_store._data["relations"] = cleaned_relations
        self.graph_store.save()

        source_learned = preview["source_learned_identity_id"]
        target_learned = preview["target_learned_identity_id"]

        if source_learned is not None and self.database_path.exists():
            if target_learned is not None:
                self._merge_learning_data(source_learned, target_learned)
            else:
                self._delete_learning_data(source_learned)

        return {
            "schema_version": 1,
            "status": "completed",
            "mode": preview["mode"],
            "removed_entity_id": source_id,
            "kept_entity_id": target_id,
            "backup": backup,
            "preview": preview,
        }
