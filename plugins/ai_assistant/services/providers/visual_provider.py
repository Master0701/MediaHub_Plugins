from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError


class VisualProviderDisabled(RuntimeError):
    pass


class VisualProvider:
    """Konfigurierbarer visueller Online-Provider.

    Standardmäßig deaktiviert. Es werden ausschließlich explizit freigegebene
    Einzelbilder übertragen, niemals komplette Videos oder Audiospuren.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        endpoint: str | None = None,
        api_token: str | None = None,
        timeout: float = 30.0,
        maximum_frames: int = 4,
    ):
        self.enabled = bool(enabled)
        self.endpoint = str(endpoint or "").strip() or None
        self.api_token = str(api_token or "").strip() or None
        self.timeout = max(1.0, float(timeout))
        self.maximum_frames = max(1, min(int(maximum_frames), 8))

    def status(self) -> dict[str, Any]:
        return {
            "id": "visual_provider",
            "enabled": self.enabled,
            "configured": bool(self.endpoint),
            "endpoint": self.endpoint,
            "maximum_frames": self.maximum_frames,
            "requires_user_approval": True,
            "complete_video_transfer": False,
            "audio_transfer": False,
        }

    def prepare_request(
        self,
        visual_intelligence: dict[str, Any],
        *,
        user_approved: bool,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise VisualProviderDisabled(
                "Der visuelle Online-Provider ist deaktiviert."
            )
        if not self.endpoint:
            raise VisualProviderDisabled(
                "Für den visuellen Online-Provider ist kein Endpoint konfiguriert."
            )
        if not user_approved:
            raise VisualProviderDisabled(
                "Für die Übertragung ausgewählter Frames fehlt die Benutzerfreigabe."
            )

        selected = list(
            visual_intelligence.get("selected_frames") or []
        )[: self.maximum_frames]

        frames = []
        for item in selected:
            hashes = dict(item.get("perceptual_hashes") or {})
            frames.append(
                {
                    "second": float(item.get("second") or 0.0),
                    "score": float(item.get("score") or 0.0),
                    "position": str(item.get("position") or "unknown"),
                    "ocr_text": item.get("ocr_text"),
                    "ahash": hashes.get("ahash"),
                    "dhash": hashes.get("dhash"),
                    "center_dhash": hashes.get("center_dhash"),
                }
            )

        return {
            "schema_version": 1,
            "type": "visual_lookup_request",
            "privacy": {
                "user_approved": True,
                "complete_video_transfer": False,
                "audio_transfer": False,
                "frame_count": len(frames),
            },
            "visual_signature": visual_intelligence.get("visual_signature"),
            "visual_fingerprint": visual_intelligence.get("visual_fingerprint"),
            "scene_signature": visual_intelligence.get("scene_signature"),
            "ocr_logo_fusion": visual_intelligence.get("ocr_logo_fusion"),
            "intro_outro_detection": visual_intelligence.get(
                "intro_outro_detection"
            ),
            "frames": frames,
        }

    def execute(
        self,
        visual_intelligence: dict[str, Any],
        *,
        user_approved: bool,
    ) -> dict[str, Any]:
        payload = self.prepare_request(
            visual_intelligence,
            user_approved=user_approved,
        )
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        req = urllib_request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib_request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
                status_code = int(getattr(response, "status", 200))
        except HTTPError as exc:
            return {
                "state": "failed",
                "error": f"HTTP {exc.code}",
                "status_code": int(exc.code),
            }
        except URLError as exc:
            return {
                "state": "failed",
                "error": str(exc.reason),
                "status_code": None,
            }
        except Exception as exc:
            return {
                "state": "failed",
                "error": str(exc),
                "status_code": None,
            }

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except Exception:
            parsed = {"raw_response": raw.decode("utf-8", errors="replace")}

        return {
            "state": "completed",
            "status_code": status_code,
            "provider_response": parsed,
            "privacy": payload["privacy"],
        }
