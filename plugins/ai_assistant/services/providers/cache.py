from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class ProviderResultCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, provider_id: str, query: dict[str, Any]) -> Path:
        payload = json.dumps(
            {"provider_id": provider_id, "query": query},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        key = hashlib.sha256(payload).hexdigest()
        return self.cache_dir / f"{key}.json"

    def get(
        self,
        provider_id: str,
        query: dict[str, Any],
        ttl_seconds: int,
    ) -> dict[str, Any] | None:
        if ttl_seconds <= 0:
            return None
        path = self._path(provider_id, query)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if time.time() - float(data.get("created_at") or 0) > ttl_seconds:
            path.unlink(missing_ok=True)
            return None
        result = data.get("result")
        return dict(result) if isinstance(result, dict) else None

    def put(
        self,
        provider_id: str,
        query: dict[str, Any],
        result: dict[str, Any],
    ) -> None:
        path = self._path(provider_id, query)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"created_at": time.time(), "result": result},
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)

    def stats(self) -> dict[str, Any]:
        files = list(self.cache_dir.glob("*.json"))
        return {
            "path": str(self.cache_dir),
            "entries": len(files),
            "size_bytes": sum(
                path.stat().st_size for path in files if path.is_file()
            ),
        }
