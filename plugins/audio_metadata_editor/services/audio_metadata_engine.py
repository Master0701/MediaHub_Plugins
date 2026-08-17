from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from services.audio_metadata_contract import (
    CONTRACT_ID,
    SAFE_WRITE_POLICY,
    SUPPORTED_AUDIO_EXTENSIONS,
)


class AudioMetadataEngine:
    """v0.0.1-Grundgerüst ohne schreibende Drittanbieter-Backends."""

    def __init__(self, plugin_root: Path, mediahub_api=None):
        self.plugin_root = Path(plugin_root)
        self.mediahub_api = mediahub_api

    def _resolve_tool(self, tool_id: str, executable: str = "") -> str:
        api = self.mediahub_api
        if api is not None:
            for method_name in ("get_tool_path", "resolve_tool", "tool_path"):
                method = getattr(api, method_name, None)
                if callable(method):
                    try:
                        value = method(tool_id)
                    except Exception:  # noqa: BLE001 - MediaHub-Tool-API-Grenze
                        value = None
                    if value:
                        return str(value)
        return shutil.which(executable or tool_id) or ""

    def status(self) -> dict:
        return {
            "available": True,
            "contract": CONTRACT_ID,
            "contract_version": 1,
            "stage": "foundation",
            "standalone": True,
            "tools": {
                "ffmpeg": self._resolve_tool("ffmpeg", "ffmpeg"),
                "ffprobe": self._resolve_tool("ffprobe", "ffprobe"),
                "mediainfo": self._resolve_tool("mediainfo", "mediainfo"),
                "chromaprint_fpcalc": self._resolve_tool("chromaprint_fpcalc", "fpcalc"),
                "mp3tag": self._resolve_tool("mp3tag", "Mp3tag"),
            },
            "tag_backend_ready": False,
            "fingerprint_backend_ready": False,
            "write_backend_ready": False,
        }

    @staticmethod
    def _path(payload: Any) -> Path | None:
        if isinstance(payload, (str, Path)):
            value = str(payload)
        elif isinstance(payload, dict):
            value = str(
                payload.get("path")
                or payload.get("file_path")
                or payload.get("filename")
                or ""
            )
        else:
            value = ""
        value = value.strip()
        return Path(value) if value else None

    def inspect(self, payload: Any) -> dict:
        path = self._path(payload)
        if path is None:
            return {"ok": False, "contract": CONTRACT_ID, "error": "Kein Pfad übergeben."}
        suffix = path.suffix.lower()
        supported = suffix in SUPPORTED_AUDIO_EXTENSIONS
        return {
            "ok": supported,
            "contract": CONTRACT_ID,
            "path": str(path),
            "exists": path.is_file(),
            "extension": suffix,
            "supported": supported,
            "media_kind": "audiobook" if suffix == ".m4b" else "audio",
            "tags": {},
            "chapters": [],
            "fingerprint": None,
            "backend_stage": "foundation",
        }

    def identify(self, payload: Any) -> dict:
        inspection = self.inspect(payload)
        return {
            "ok": bool(inspection.get("ok")),
            "contract": CONTRACT_ID,
            "inspection": inspection,
            "candidates": [],
            "best_candidate": None,
            "confidence": 0.0,
            "sources": [],
            "message": "Fingerprint-, AcoustID/MusicBrainz- und weitere Audioquellen sind vorbereitet, aber noch nicht aktiviert.",
        }

    def compare(self, payload: Any) -> dict:
        source = dict(payload or {}) if isinstance(payload, dict) else {}
        current = dict(source.get("current") or {})
        candidate = dict(source.get("candidate") or {})
        changes = {}
        for field in sorted(set(current) | set(candidate)):
            if current.get(field) != candidate.get(field):
                changes[field] = {
                    "before": current.get(field),
                    "after": candidate.get(field),
                }
        return {
            "ok": True,
            "contract": CONTRACT_ID,
            "changes": changes,
            "write_policy": dict(SAFE_WRITE_POLICY),
        }

    def plan_write(self, payload: Any) -> dict:
        comparison = self.compare(payload)
        return {
            "ok": True,
            "contract": CONTRACT_ID,
            "plan": comparison["changes"],
            "confirmation_required": True,
            "ready_to_apply": False,
            "write_policy": dict(SAFE_WRITE_POLICY),
        }

    def apply_write(self, payload: Any) -> dict:
        return {
            "ok": False,
            "contract": CONTRACT_ID,
            "backend_ready": False,
            "automatic_apply_allowed": False,
            "message": "v0.0.1 enthält absichtlich noch kein echtes Tag-Schreibbackend.",
        }
