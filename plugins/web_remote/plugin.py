from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

from mediahub_web_core.server import LocalWebServer


class MediaHubWebRemotePlugin:
    VERSION = "0.5.3"

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.server = LocalWebServer(host="127.0.0.1", port=8765)
        self._activity_lock = threading.Lock()
        self._activities = deque(maxlen=80)
        self._last_connected = None
        self._last_download_signature = None
        self._last_done_count = 0
        self.server.add_route("/", self._index)
        self.server.add_route("/api/status", self._status)
        self.server.add_route("/api/channels", self._channels)
        self.server.add_route("/api/plugins", self._plugins)
        self.server.add_route("/api/downloads", self._downloads)
        self.server.add_route("/api/activities", self._activity_feed)
        self._add_activity("system", "WebRemote gestartet", "Das lokale Control Center ist bereit.", "info")

    def start(self):
        self.server.start()

    def stop(self):
        self._add_activity("system", "WebRemote beendet", "Der lokale Webserver wird gestoppt.", "info")
        self.server.stop()

    def _index(self):
        return 200, "text/html; charset=utf-8", (self.plugin_path / "index.html").read_bytes()

    def _json(self, data, status=200):
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _add_activity(self, category, title, detail="", level="info"):
        item = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "category": category,
            "title": title,
            "detail": detail,
            "level": level,
        }
        with self._activity_lock:
            self._activities.appendleft(item)

    def _read_status(self):
        if self.mediahub_api is None:
            return {"connected": False, "channels": 0, "playlists": 0, "videos": 0}
        return self.mediahub_api.get_status()

    def _observe_status(self, mediahub):
        connected = bool(mediahub.get("connected"))
        if self._last_connected is None:
            self._last_connected = connected
            self._add_activity("connection", "MediaHub verbunden" if connected else "MediaHub nicht verbunden", level="success" if connected else "warning")
        elif connected != self._last_connected:
            self._last_connected = connected
            self._add_activity("connection", "MediaHub verbunden" if connected else "Verbindung zu MediaHub verloren", level="success" if connected else "error")

    def _observe_download(self, data):
        active = bool(data.get("active"))
        title = str(data.get("current_title") or "")
        done = int(data.get("done_count") or 0)
        total = int(data.get("total_count") or 0)
        status = str(data.get("status") or "")
        signature = (active, title, status, total)
        if self._last_download_signature is None:
            self._last_download_signature = signature
            self._last_done_count = done
            if active:
                self._add_activity("download", "Download läuft", title or status, "success")
            return
        old_active, old_title, _, _ = self._last_download_signature
        if active and (not old_active or title != old_title):
            self._add_activity("download", "Download gestartet", title or "Unbekanntes Video", "success")
        if old_active and not active:
            self._add_activity("download", "Download beendet", old_title or status, "success")
        if done > self._last_done_count:
            self._add_activity("download", "Video abgeschlossen", f"{done} von {total} erledigt", "success")
        self._last_download_signature = signature
        self._last_done_count = done

    def _status(self):
        mediahub = self._read_status()
        self._observe_status(mediahub)
        return self._json({
            "product": "MediaHub WebRemote", "version": self.VERSION,
            "server": "online", "scope": "computer_only", "mediahub": mediahub,
        })

    def _downloads(self):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "get_download_status"):
            return self._json({"available": False, "active": False, "message": "Downloadstatus ist in dieser MediaHub-Version nicht verfügbar.", "queue": []})
        try:
            data = self.mediahub_api.get_download_status()
            data["available"] = True
            self._observe_download(data)
            return self._json(data)
        except Exception as error:
            return self._json({"available": False, "active": False, "message": str(error), "queue": []}, status=500)

    def _activity_feed(self):
        try:
            self._observe_status(self._read_status())
            if self.mediahub_api is not None and hasattr(self.mediahub_api, "get_download_status"):
                self._observe_download(self.mediahub_api.get_download_status())
        except Exception:
            pass
        with self._activity_lock:
            items = list(self._activities)
        return self._json({"available": True, "source": "webremote_observer", "activities": items, "count": len(items)})

    def _plugins(self):
        return self._json({"available": True, "plugins": [
            {"id": "mediahub.web_remote", "name": "WebRemote", "version": self.VERSION, "installed": True, "running": True},
            {"id": "mediahub.mobile_dashboard", "name": "Mobile Dashboard", "installed": False, "running": False},
            {"id": "mediahub.metadata_editor", "name": "Metadaten-Editor", "installed": False, "running": False},
            {"id": "mediahub.ai_assistant", "name": "KI-Assistent", "installed": False, "running": False},
            {"id": "mediahub.smart_renamer", "name": "Smart Renamer", "installed": False, "running": False},
        ]})

    def _channels(self):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, "get_channels"):
            return self._json({"channels": [], "available": False, "message": "Kanaldaten sind in dieser MediaHub-Version nicht verfügbar."})
        try:
            channels = self.mediahub_api.get_channels()
            return self._json({"channels": channels, "available": True, "count": len(channels)})
        except Exception as error:
            return self._json({"channels": [], "available": False, "message": str(error)}, status=500)
