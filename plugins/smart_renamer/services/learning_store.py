from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


class LearningStore:
    """
    Speichert bestätigte Benutzerentscheidungen lokal.

    Gelernte Daten erzeugen ausschließlich Hinweise für die Decision Engine.
    Sie lösen niemals automatisch eine Umbenennung oder Metadatenänderung aus.
    """

    SCHEMA_VERSION = 2

    def __init__(self, base_dir: Path, threshold: int = 3):
        self.path = Path(base_dir) / "config" / "smart_renamer_learning.json"
        self.threshold = max(2, int(threshold))

    def _empty(self) -> dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "patterns": {},
            "decisions": {},
        }

    def _load(self) -> dict[str, Any]:
        if not self.path.is_file():
            return self._empty()

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return self._empty()

        if not isinstance(raw, dict):
            return self._empty()

        # Abwärtskompatibilität zum bisherigen Schema 1.
        data = self._empty()
        data["patterns"] = (
            raw.get("patterns")
            if isinstance(raw.get("patterns"), dict)
            else {}
        )
        data["decisions"] = (
            raw.get("decisions")
            if isinstance(raw.get("decisions"), dict)
            else {}
        )
        return data

    def _save(self, data: dict[str, Any]) -> None:
        data["schema_version"] = self.SCHEMA_VERSION
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def record(self, original: str, corrected: str) -> dict[str, Any]:
        """Bestehender Korrektur-Lernpfad bleibt unverändert kompatibel."""
        key = f"{original}\u0000{corrected}"
        data = self._load()
        patterns = data.setdefault("patterns", {})
        item = patterns.setdefault(
            key,
            {
                "original": original,
                "corrected": corrected,
                "count": 0,
                "promoted": False,
            },
        )
        item["count"] = int(item.get("count", 0)) + 1
        self._save(data)

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

    def record_decision(
        self,
        original_path: str | Path,
        *,
        candidate_id: str = "",
        media_type: str = "",
        title: str = "",
        year: str = "",
        season: str = "",
        episode: str = "",
        edition: str = "",
        source: str = "user",
    ) -> dict[str, Any]:
        """
        Speichert eine ausdrücklich bestätigte Erkennungsentscheidung.

        Der Schlüssel ist bewusst konservativ: normalisierter Dateistamm plus
        Endung. Dadurch wird eine Entscheidung nicht ungefragt auf andere Titel
        übertragen.
        """
        fingerprint = self.fingerprint(original_path)
        data = self._load()
        decisions = data.setdefault("decisions", {})

        item = decisions.setdefault(
            fingerprint,
            {
                "fingerprint": fingerprint,
                "original_path": str(original_path),
                "count": 0,
                "candidate_id": "",
                "media_type": "",
                "title": "",
                "year": "",
                "season": "",
                "episode": "",
                "edition": "",
                "source": "user",
            },
        )

        item.update(
            {
                "original_path": str(original_path),
                "candidate_id": str(candidate_id or ""),
                "media_type": str(media_type or ""),
                "title": str(title or ""),
                "year": str(year or ""),
                "season": str(season or ""),
                "episode": str(episode or ""),
                "edition": str(edition or ""),
                "source": str(source or "user"),
                "count": int(item.get("count", 0)) + 1,
            }
        )
        self._save(data)

        return {
            **item,
            "automatic_application": False,
        }

    def decision_hints_for(
        self,
        original_path: str | Path,
    ) -> dict[str, Any]:
        """
        Liefert ausschließlich Ranking-Hinweise für exakt passende Fingerprints.
        """
        data = self._load()
        item = data.get("decisions", {}).get(
            self.fingerprint(original_path)
        )
        if not isinstance(item, dict):
            return {}

        hints: dict[str, Any] = {
            "learning_match": True,
            "learning_count": int(item.get("count", 0)),
            "learning_source": str(item.get("source") or "user"),
        }

        if item.get("candidate_id"):
            hints["preferred_candidate_id"] = str(item["candidate_id"])
        if item.get("media_type"):
            hints["preferred_media_type"] = str(item["media_type"])
        if item.get("title"):
            hints["preferred_title"] = str(item["title"])

        # Diese Felder werden für spätere Quellen gespeichert, beeinflussen in
        # v0.4.9 aber noch nicht eigenständig den Score.
        for key in ("year", "season", "episode", "edition"):
            if item.get(key):
                hints[f"learned_{key}"] = str(item[key])

        return hints

    def list_decisions(self) -> list[dict[str, Any]]:
        data = self._load()
        return [
            dict(item)
            for _, item in sorted(
                data.get("decisions", {}).items(),
                key=lambda value: value[0],
            )
            if isinstance(item, dict)
        ]

    def delete_decision(self, original_path: str | Path) -> bool:
        data = self._load()
        decisions = data.setdefault("decisions", {})
        removed = decisions.pop(self.fingerprint(original_path), None)
        if removed is None:
            return False
        self._save(data)
        return True

    @staticmethod
    def fingerprint(original_path: str | Path) -> str:
        path = Path(str(original_path))
        stem = path.stem.casefold()
        stem = stem.replace("_", " ").replace(".", " ")
        stem = re.sub(r"\s+", " ", stem).strip()
        suffix = path.suffix.casefold()
        return f"{stem}|{suffix}"
