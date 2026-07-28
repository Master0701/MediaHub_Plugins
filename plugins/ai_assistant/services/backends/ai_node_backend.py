from __future__ import annotations

import json
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.backends.base import (
    AIBackend,
    BackendCapability,
    BackendStatus,
)


class AINodeBackend(AIBackend):
    id = "ai_node"
    name = "Raspberry-Pi-AI-Node"
    backend_type = "remote"

    def __init__(
        self,
        host: str = "",
        port: int = 8765,
        api_token: str = "",
        timeout: float = 4.0,
    ):
        self.host = str(host).strip()
        self.port = int(port)
        self.api_token = str(api_token).strip()
        self.timeout = float(timeout)

    @property
    def base_url(self) -> str:
        if not self.host:
            return ""
        if self.host.startswith(("http://", "https://")):
            return self.host.rstrip("/")
        return f"http://{self.host}:{self.port}"

    def status(self) -> BackendStatus:
        if not self.host:
            return BackendStatus(
                id=self.id,
                name=self.name,
                available=False,
                backend_type=self.backend_type,
                message="Kein AI-Node konfiguriert.",
                capabilities=self._capabilities(False),
            )

        try:
            started = perf_counter()
            root = self._request_json("/")
            health = self._request_json("/health")
            latency_ms = round((perf_counter() - started) * 1000, 1)

            version = (
                root.get("version")
                or health.get("version")
                or "unbekannt"
            )

            return BackendStatus(
                id=self.id,
                name=self.name,
                available=True,
                backend_type=self.backend_type,
                message=f"AI-Node erreichbar – Version {version}",
                capabilities=self._capabilities(True),
                metadata={
                    "host": self.host,
                    "port": self.port,
                    "version": version,
                    "name": root.get("name"),
                    "status": health.get("status"),
                    "timestamp": health.get("timestamp"),
                    "latency_ms": latency_ms,
                    "plugins": dict(health.get("plugins") or {}),
                    "system": dict(health.get("system") or {}),
                    "controls_mediahub": False,
                },
            )
        except Exception as exc:
            return BackendStatus(
                id=self.id,
                name=self.name,
                available=False,
                backend_type=self.backend_type,
                message=f"AI-Node nicht erreichbar: {exc}",
                capabilities=self._capabilities(False),
                metadata={
                    "host": self.host,
                    "port": self.port,
                    "controls_mediahub": False,
                },
            )

    def supports(self, task_type: str, payload: dict[str, Any]) -> bool:
        if task_type != "media.analyze":
            return False
        return bool(
            payload.get("ai_node_path")
            or payload.get("remote_file_id")
        )

    def execute(
        self,
        task_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.supports(task_type, payload):
            raise RuntimeError(
                "Der AI-Node kann diese Aufgabe noch nicht sicher "
                "ausführen. Es fehlt ein für den Node erreichbarer "
                "Dateipfad oder eine übertragene Datei."
            )

        raise NotImplementedError(
            "Die geschützte Job-API des AI-Nodes wird im nächsten "
            "Ausbauschritt angebunden."
        )

    def _capabilities(
        self,
        available: bool,
    ) -> tuple[BackendCapability, ...]:
        return (
            BackendCapability(
                id="node.health",
                available=available,
            ),
            BackendCapability(
                id="media.analyze",
                available=False,
                reason=(
                    "Job-Endpunkt und sichere Dateiübergabe "
                    "werden noch angebunden."
                ),
            ),
        )

    def _request_json(self, path: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            headers=self._headers(),
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(
                    response.read().decode("utf-8", errors="replace")
                )
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers
