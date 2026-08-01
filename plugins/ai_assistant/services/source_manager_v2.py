from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class SourceManagerV2:
    """Zentrale Verwaltung strukturierter und benutzerdefinierter Quellen."""

    SOURCE_TYPES = {
        "api",
        "website",
        "custom_url",
        "local_cache",
        "knowledge_pack",
        "provider",
    }

    DEFAULT_SOURCES = [
        {
            "id": "tmdb",
            "name": "TMDb",
            "source_type": "api",
            "enabled": True,
            "priority": 100,
            "trust": 0.96,
            "language": "de",
            "region": "DE",
            "requires_api_key": True,
            "user_defined": False,
        },
        {
            "id": "tvdb",
            "name": "TheTVDB",
            "source_type": "api",
            "enabled": False,
            "priority": 90,
            "trust": 0.94,
            "language": "de",
            "region": "DE",
            "requires_api_key": True,
            "user_defined": False,
        },
        {
            "id": "wikidata",
            "name": "Wikidata",
            "source_type": "api",
            "enabled": True,
            "priority": 80,
            "trust": 0.90,
            "language": "de",
            "region": None,
            "requires_api_key": False,
            "user_defined": False,
        },
        {
            "id": "wikipedia",
            "name": "Wikipedia",
            "source_type": "website",
            "enabled": True,
            "priority": 70,
            "trust": 0.84,
            "language": "de",
            "region": None,
            "requires_api_key": False,
            "user_defined": False,
        },
        {
            "id": "local_cache",
            "name": "Lokaler Quellen-Cache",
            "source_type": "local_cache",
            "enabled": True,
            "priority": 60,
            "trust": 0.88,
            "language": None,
            "region": None,
            "requires_api_key": False,
            "user_defined": False,
        },
    ]

    def __init__(self, knowledge_database_path: str | Path):
        database = Path(knowledge_database_path)
        self.path = database.with_name("source_manager.json")
        self.cache_path = database.with_name("source_cache")
        self._data = {
            "schema_version": 1,
            "sources": [],
            "scan_jobs": [],
            "import_previews": [],
        }
        self._load()
        self._ensure_defaults()

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
            self._data.setdefault("sources", [])
            self._data.setdefault("scan_jobs", [])
            self._data.setdefault("import_previews", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _ensure_defaults(self) -> None:
        known = {str(item.get("id")) for item in self._data["sources"]}
        changed = False
        for source in self.DEFAULT_SOURCES:
            if source["id"] not in known:
                self._data["sources"].append(
                    {
                        **source,
                        "created_at": self._now(),
                        "updated_at": self._now(),
                        "cache_ttl_hours": 168,
                        "notes": None,
                    }
                )
                changed = True
        if changed:
            self._save()

    @staticmethod
    def _validate_url(url: str) -> str:
        parsed = urlparse(str(url).strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Bitte eine gültige HTTP- oder HTTPS-URL eingeben.")
        return parsed.geturl()

    def list_sources(self) -> list[dict[str, Any]]:
        return sorted(
            [dict(item) for item in self._data["sources"]],
            key=lambda item: (
                not bool(item.get("enabled")),
                -int(item.get("priority") or 0),
                str(item.get("name") or "").casefold(),
            ),
        )

    def add_custom_source(
        self,
        *,
        name: str,
        url: str,
        category: str = "general",
        trust: float = 0.75,
        priority: int = 50,
        language: str | None = "de",
        notes: str | None = None,
    ) -> dict[str, Any]:
        name = str(name or "").strip()
        if not name:
            raise ValueError("Ein Quellenname ist erforderlich.")

        normalized_url = self._validate_url(url)
        trust = float(trust)
        if not 0.0 <= trust <= 1.0:
            raise ValueError("Vertrauen muss zwischen 0 und 1 liegen.")

        source = {
            "id": uuid.uuid4().hex,
            "name": name,
            "source_type": "custom_url",
            "url": normalized_url,
            "category": str(category or "general"),
            "enabled": True,
            "priority": int(priority),
            "trust": trust,
            "language": language,
            "region": None,
            "requires_api_key": False,
            "user_defined": True,
            "cache_ttl_hours": 168,
            "notes": notes,
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        self._data["sources"].append(source)
        self._save()
        return dict(source)

    def update_source(
        self,
        source_id: str,
        **changes: Any,
    ) -> dict[str, Any]:
        source = self.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")

        allowed = {
            "name",
            "enabled",
            "priority",
            "trust",
            "language",
            "region",
            "cache_ttl_hours",
            "notes",
            "category",
        }
        for key, value in changes.items():
            if key not in allowed:
                continue
            if key == "trust":
                value = float(value)
                if not 0.0 <= value <= 1.0:
                    raise ValueError("Vertrauen muss zwischen 0 und 1 liegen.")
            source[key] = value
        source["updated_at"] = self._now()
        self._save()
        return dict(source)

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        source_id = str(source_id)
        for source in self._data["sources"]:
            if str(source.get("id")) == source_id:
                return source
        return None

    def remove_source(self, source_id: str) -> bool:
        source = self.get_source(source_id)
        if source is None:
            return False
        if not source.get("user_defined"):
            raise ValueError("Vordefinierte Quellen können nur deaktiviert werden.")
        self._data["sources"] = [
            item
            for item in self._data["sources"]
            if str(item.get("id")) != str(source_id)
        ]
        self._save()
        return True

    def create_scan_preview(
        self,
        source_id: str,
        *,
        requested_url: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source = self.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")
        if not source.get("enabled"):
            raise ValueError("Die Quelle ist deaktiviert.")

        url = requested_url or source.get("url")
        if url:
            url = self._validate_url(url)

        job_id = uuid.uuid4().hex
        preview = {
            "schema_version": 1,
            "job_id": job_id,
            "source_id": source_id,
            "source_name": source.get("name"),
            "source_type": source.get("source_type"),
            "url": url,
            "context": dict(context or {}),
            "status": "preview_only",
            "created_at": self._now(),
            "trust": source.get("trust"),
            "priority": source.get("priority"),
            "cache_ttl_hours": source.get("cache_ttl_hours"),
            "planned_steps": [
                "robots_and_policy_check",
                "fetch_or_api_request",
                "structured_extraction",
                "conflict_comparison",
                "import_preview",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
            "network_execution_started": False,
        }
        self._data["scan_jobs"].append(preview)
        self._save()
        return dict(preview)

    def register_import_preview(
        self,
        *,
        job_id: str,
        extracted: dict[str, Any],
        conflicts: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        preview = {
            "id": uuid.uuid4().hex,
            "job_id": str(job_id),
            "created_at": self._now(),
            "extracted": dict(extracted or {}),
            "conflicts": list(conflicts or []),
            "status": "pending_confirmation",
            "automatic_import": False,
            "requires_confirmation": True,
        }
        self._data["import_previews"].append(preview)
        self._save()
        return dict(preview)

    def status(self) -> dict[str, Any]:
        sources = self.list_sources()
        return {
            "schema_version": 1,
            "path": str(self.path.resolve()),
            "cache_path": str(self.cache_path.resolve()),
            "source_count": len(sources),
            "enabled_count": sum(1 for item in sources if item.get("enabled")),
            "custom_source_count": sum(
                1 for item in sources if item.get("user_defined")
            ),
            "scan_preview_count": len(self._data["scan_jobs"]),
            "import_preview_count": len(self._data["import_previews"]),
        }
