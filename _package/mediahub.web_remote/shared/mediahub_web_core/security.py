from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class PairingResult:
    token: str
    device_id: str
    device_name: str


class PairingStore:
    """Lokale Geräte-Kopplung für die gemeinsame MediaHub-Web-Runtime."""

    def __init__(self, base_dir: Path):
        self.path = Path(base_dir) / "config" / "plugins" / "mediahub_web_pairing.json"
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    data.setdefault("pairing_code", self._new_code())
                    data.setdefault("devices", [])
                    return data
            except Exception:
                pass
        data = {"pairing_code": self._new_code(), "devices": []}
        self._save(data)
        return data

    def _save(self, data: dict[str, Any] | None = None) -> None:
        if data is not None:
            self._data = data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.path)

    @staticmethod
    def _new_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @property
    def pairing_code(self) -> str:
        return str(self._data.get("pairing_code") or "")

    def rotate_code(self) -> str:
        self._data["pairing_code"] = self._new_code()
        self._save()
        return self.pairing_code

    def devices(self) -> list[dict[str, Any]]:
        result = []
        for item in list(self._data.get("devices") or []):
            result.append({
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or "Unbekanntes Gerät"),
                "created_at": str(item.get("created_at") or ""),
                "last_seen": str(item.get("last_seen") or ""),
            })
        return result

    def claim(self, code: str, device_name: str) -> PairingResult:
        if not secrets.compare_digest(str(code or "").strip(), self.pairing_code):
            raise ValueError("Der Einmalcode ist ungültig.")
        token = secrets.token_urlsafe(32)
        device_id = secrets.token_hex(8)
        name = str(device_name or "Neues Gerät").strip()[:100] or "Neues Gerät"
        now = _now()
        devices = list(self._data.get("devices") or [])
        devices.append({
            "id": device_id,
            "name": name,
            "token_hash": _hash_token(token),
            "created_at": now,
            "last_seen": now,
        })
        self._data["devices"] = devices[-50:]
        self._data["pairing_code"] = self._new_code()
        self._save()
        return PairingResult(token=token, device_id=device_id, device_name=name)

    def authorize(self, token: str) -> bool:
        token = str(token or "").strip()
        if not token:
            return False
        digest = _hash_token(token)
        changed = False
        for item in list(self._data.get("devices") or []):
            if secrets.compare_digest(str(item.get("token_hash") or ""), digest):
                item["last_seen"] = _now()
                changed = True
                if changed:
                    self._save()
                return True
        return False

    def revoke(self, device_id: str) -> bool:
        before = list(self._data.get("devices") or [])
        after = [item for item in before if str(item.get("id") or "") != str(device_id or "")]
        if len(after) == len(before):
            return False
        self._data["devices"] = after
        self._save()
        return True

    def revoke_all(self) -> int:
        count = len(list(self._data.get("devices") or []))
        self._data["devices"] = []
        self._save()
        return count
