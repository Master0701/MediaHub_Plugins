from __future__ import annotations

import base64
import json
import os
from pathlib import Path


class ProviderCredentialStore:
    """Local credential store. Uses Windows DPAPI when available."""

    ENV_KEYS = {
        "tmdb": ("MEDIAHUB_TMDB_API_KEY", "MEDIAHUB_TMDB_BEARER_TOKEN"),
        "tvdb": ("MEDIAHUB_TVDB_API_KEY", "MEDIAHUB_TVDB_SUBSCRIBER_PIN"),
    }

    def __init__(
        self,
        plugin_path: Path,
        data_base_dir: Path | None = None,
    ):
        plugin_path = Path(plugin_path).resolve()
        self.legacy_path = (
            plugin_path
            / "config"
            / "provider_credentials.dat"
        )

        if data_base_dir is not None:
            base_dir = Path(
                data_base_dir
            ).resolve()
        elif plugin_path.parent.name.casefold() == "plugins":
            base_dir = plugin_path.parent.parent
        else:
            plugins_parent = next(
                (
                    parent
                    for parent in plugin_path.parents
                    if parent.name.casefold() == "plugins"
                ),
                None,
            )
            base_dir = (
                plugins_parent.parent
                if plugins_parent is not None
                else plugin_path.parent
            )

        self.path = (
            base_dir
            / "plugin_data"
            / "ai_assistant"
            / "provider_credentials.dat"
        )
        self._migrate_legacy_credentials()

    def _migrate_legacy_credentials(self) -> None:
        if self.path.exists() or not self.legacy_path.exists():
            return

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(self.legacy_path.read_bytes())
        temporary.replace(self.path)

    @staticmethod
    def _protect(data: bytes) -> bytes:
        if os.name != "nt":
            return data
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        buf = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(in_blob), "MediaHub", None, None, None, 0, ctypes.byref(out_blob)):
            raise OSError("Windows DPAPI konnte Zugangsdaten nicht schützen.")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)

    @staticmethod
    def _unprotect(data: bytes) -> bytes:
        if os.name != "nt":
            return data
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]

        buf = ctypes.create_string_buffer(data)
        in_blob = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()
        if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)):
            raise OSError("Windows DPAPI konnte Zugangsdaten nicht lesen.")
        try:
            return ctypes.string_at(out_blob.pbData, out_blob.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)

    def load(self) -> dict:
        if not self.path.exists():
            return {}
        raw = base64.b64decode(self.path.read_bytes())
        return json.loads(self._unprotect(raw).decode("utf-8"))

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.path.write_bytes(base64.b64encode(self._protect(raw)))

    def get(self, provider_id: str) -> dict:
        return dict(self.load().get(provider_id) or {})

    def set(self, provider_id: str, values: dict) -> None:
        data = self.load()
        clean = {str(k): str(v) for k, v in values.items() if str(v).strip()}
        if clean:
            data[str(provider_id)] = clean
        else:
            data.pop(str(provider_id), None)
        self.save(data)
        self.apply_to_environment()

    def apply_to_environment(self) -> None:
        data = self.load()
        mapping = {
            "tmdb": {"api_key": "MEDIAHUB_TMDB_API_KEY", "bearer_token": "MEDIAHUB_TMDB_BEARER_TOKEN"},
            "tvdb": {"api_key": "MEDIAHUB_TVDB_API_KEY", "subscriber_pin": "MEDIAHUB_TVDB_SUBSCRIBER_PIN"},
        }
        for provider_id, fields in mapping.items():
            values = data.get(provider_id) or {}
            for field, env_name in fields.items():
                value = str(values.get(field) or "").strip()
                if value:
                    os.environ[env_name] = value
