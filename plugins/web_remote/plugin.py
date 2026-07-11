from __future__ import annotations

import json
from pathlib import Path

from mediahub_web_core.server import LocalWebServer


class MediaHubWebRemotePlugin:
    """Erste lokale WebRemote-Grundversion.

    Die endgültige MediaHub-Brücke wird nach Erweiterung der Plugin-API gesetzt.
    """

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.server = LocalWebServer(host="127.0.0.1", port=8765)
        self.server.add_route("/", self._index)
        self.server.add_route("/api/status", self._status)

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()

    def _index(self):
        html = (self.plugin_path / "index.html").read_bytes()
        return 200, "text/html; charset=utf-8", html

    def _status(self):
        data = {
            "product": "MediaHub WebRemote",
            "version": "0.1.0",
            "server": "online",
            "scope": "local_only",
            "mediahub_connected": self.mediahub_api is not None,
        }
        return 200, "application/json; charset=utf-8", json.dumps(data).encode("utf-8")
