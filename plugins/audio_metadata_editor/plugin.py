from __future__ import annotations

from pathlib import Path
from typing import Any

from services.audio_metadata_engine import AudioMetadataEngine


class MediaHubAudioMetadataEditorPlugin:
    """Erstes Grundgerüst für Hörbücher und allgemeine Audiodateien."""

    VERSION = "0.0.1"
    AUDIO_METADATA_CONTRACT = "mediahub.audio_metadata.v1"

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.base_dir = Path(getattr(mediahub_api, "base_dir", self.plugin_path))
        self.data_dir = self.base_dir / "plugin_data" / "audio_metadata_editor"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = AudioMetadataEngine(self.plugin_path, mediahub_api=mediahub_api)

    def start(self):
        return None

    def stop(self):
        return None

    def get_runtime_capabilities(self):
        return {
            self.AUDIO_METADATA_CONTRACT: self,
            "audio.metadata.inspect": self,
            "audio.metadata.identify": self,
            "audio.metadata.compare": self,
            "audio.metadata.plan_write": self,
            "audio.metadata.apply_write": self,
        }

    def get_capability_contracts(self):
        policy = {
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
            "backup_required": True,
            "verify_after_write": True,
        }
        return {
            self.AUDIO_METADATA_CONTRACT: {
                "version": 1,
                "mode": "service",
                "available": True,
                "standalone": True,
            },
            "audio.metadata.inspect": {
                "mode": "read_only",
                "execution_allowed": False,
            },
            "audio.metadata.identify": {
                "mode": "advisory",
                "execution_allowed": False,
            },
            "audio.metadata.compare": {
                "mode": "advisory",
                "execution_allowed": False,
            },
            "audio.metadata.plan_write": {
                "mode": "draft",
                "execution_allowed": False,
                **policy,
            },
            "audio.metadata.apply_write": {
                "mode": "confirmed_write",
                "available": False,
                "execution_allowed": False,
                **policy,
            },
        }

    def audio_metadata_status(self) -> dict:
        return self.engine.status()

    def inspect_audio(self, payload: Any = None) -> dict:
        return self.engine.inspect(payload)

    def identify_audio(self, payload: Any = None) -> dict:
        return self.engine.identify(payload)

    def compare_audio_metadata(self, payload: Any = None) -> dict:
        return self.engine.compare(payload)

    def plan_audio_metadata_write(self, payload: Any = None) -> dict:
        return self.engine.plan_write(payload)

    def apply_audio_metadata_write(self, payload: Any = None) -> dict:
        return self.engine.apply_write(payload)

    def audio_metadata_call(self, operation: str, payload: Any = None) -> dict:
        mapping = {
            "status": self.audio_metadata_status,
            "inspect": self.inspect_audio,
            "identify": self.identify_audio,
            "compare": self.compare_audio_metadata,
            "plan_write": self.plan_audio_metadata_write,
            "apply_write": self.apply_audio_metadata_write,
        }
        key = str(operation or "").strip().lower()
        fn = mapping.get(key)
        if fn is None:
            return {
                "ok": False,
                "contract": self.AUDIO_METADATA_CONTRACT,
                "error": f"Unbekannte Operation: {operation!r}",
            }
        return fn() if key == "status" else fn(payload)
