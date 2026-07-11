from __future__ import annotations

import json
from pathlib import Path

from mediahub_web_core.server import LocalWebServer


class MediaHubWebRemotePlugin:
    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.server = LocalWebServer(host="127.0.0.1", port=8765)
        self.server.add_route("/", self._index)
        self.server.add_route("/api/status", self._status)
        self.server.add_route("/api/channels", self._channels)
        self.server.add_route("/api/plugins", self._plugins)
        self.server.add_route("/api/downloads", self._downloads)

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()

    def _index(self):
        return 200, "text/html; charset=utf-8", (self.plugin_path / "index.html").read_bytes()

    def _json(self, data, status=200):
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _status(self):
        mediahub = self.mediahub_api.get_status() if self.mediahub_api is not None else {
            "connected": False, "channels": 0, "playlists": 0, "videos": 0,
        }
        return self._json({
            "product": "MediaHub WebRemote", "version": "0.5.2",
            "server": "online", "scope": "computer_only", "mediahub": mediahub,
        })

    def _downloads(self):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "get_download_status"):
            return self._json({
                "available": False,
                "active": False,
                "message": "Downloadstatus ist in dieser MediaHub-Version nicht verfügbar.",
                "queue": [],
            })
        try:
            data = self.mediahub_api.get_download_status()
            data["available"] = True
            return self._json(data)
        except Exception as error:
            return self._json({"available": False, "active": False, "message": str(error), "queue": []}, status=500)

    def _plugins(self):
        return self._json({
            "available": True,
            "plugins": [
                {"id": "mediahub.web_remote", "name": "WebRemote", "version": "0.5.2", "installed": True, "running": True},
                {"id": "mediahub.mobile_dashboard", "name": "Mobile Dashboard", "installed": False, "running": False},
                {"id": "mediahub.metadata_editor", "name": "Metadaten-Editor", "installed": False, "running": False},
                {"id": "mediahub.ai_assistant", "name": "KI-Assistent", "installed": False, "running": False},
                {"id": "mediahub.smart_renamer", "name": "Smart Renamer", "installed": False, "running": False},
            ],
        })

    def _channels(self):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "get_channels"):
            return self._json({"channels": [], "available": False, "message": "Kanaldaten sind in dieser MediaHub-Version nicht verfügbar."})
        try:
            channels = self.mediahub_api.get_channels()
            return self._json({"channels": channels, "available": True, "count": len(channels)})
        except Exception as error:
            return self._json({"channels": [], "available": False, "message": str(error)}, status=500)
