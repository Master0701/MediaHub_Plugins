from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LearningStore:
    """Speichert bestätigte manuelle Korrekturen, wendet aber nichts automatisch an."""

    def __init__(self, base_dir: Path, threshold: int = 3):
        self.path = Path(base_dir) / "config" / "smart_renamer_learning.json"
        self.threshold = max(2, int(threshold))

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"schema_version": 1, "patterns": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"schema_version": 1, "patterns": {}}
        except Exception:
            return {"schema_version": 1, "patterns": {}}

    def record(self, original: str, corrected: str) -> dict[str, Any]:
        key = f"{original}\u0000{corrected}"
        data = self._load()
        patterns = data.setdefault("patterns", {})
        item = patterns.setdefault(key, {
            "original": original,
            "corrected": corrected,
            "count": 0,
            "promoted": False,
        })
        item["count"] = int(item.get("count", 0)) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            **item,
            "suggest_rule": (
                item["count"] >= self.threshold
                and not bool(item.get("promoted"))
            ),
        }

    def suggestions(self) -> list[dict[str, Any]]:
        data = self._load()
        return [
            dict(item)
            for item in data.get("patterns", {}).values()
            if int(item.get("count", 0)) >= self.threshold
            and not bool(item.get("promoted"))
        ]
