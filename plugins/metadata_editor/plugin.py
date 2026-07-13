from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from mediahub_web_core.server import acquire_shared_server, release_shared_server
from mediahub_web_core.settings import WebRuntimeSettingsStore, connection_info


class MediaHubMetadataEditorPlugin:
    """Sicherer Metadaten-Editor für MediaHub.

    Version 0.1.0 liest Bibliotheksdaten über die öffentliche Plugin-API,
    erstellt Vergleiche und speichert lokale Entwürfe. Das endgültige
    Schreiben wird nur ausgeführt, wenn MediaHub die freigegebene Aktion
    ``metadata.update`` bereitstellt.
    """

    VERSION = "0.1.0"
    EDITABLE_FIELDS = (
        "title",
        "description",
        "year",
        "season",
        "episode",
        "series",
        "channel",
        "playlist",
        "published_at",
    )

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.base_dir = Path(getattr(mediahub_api, "base_dir", self.plugin_path))
        self.settings_store = WebRuntimeSettingsStore(self.base_dir)
        self.settings = self.settings_store.load()
        self.server = acquire_shared_server(str(self.base_dir), self.settings.host, self.settings.port)
        self.data_dir = self.base_dir / "plugin_data" / "metadata_editor"
        self.drafts_file = self.data_dir / "drafts.json"
        self._draft_lock = threading.Lock()
        self._register_routes()

    def start(self):
        self.server.start()

    def stop(self):
        release_shared_server(str(self.base_dir), owner=self)

    def get_plugin_settings(self):
        info = connection_info(self.settings)
        active_url = str(info.get("active_url") or "").rstrip("/")
        return {
            "version": self.VERSION,
            "url": f"{active_url}/metadata-editor" if active_url else "/metadata-editor",
            "drafts_file": str(self.drafts_file),
            "write_api_available": self._write_api_available(),
        }

    def _register_routes(self):
        routes = {
            "/metadata-editor": self._index,
            "/metadata-editor/": self._index,
            "/metadata-editor/api/status": self._status,
            "/metadata-editor/api/library": self._library,
            "/metadata-editor/api/channels": self._channels,
            "/metadata-editor/api/playlists": self._playlists,
            "/metadata-editor/api/drafts": self._drafts,
            "/metadata-editor/assets/mediahub.css": self._stylesheet,
        }
        for path, handler in routes.items():
            self.server.add_route(path, handler, owner=self)
        self.server.add_post_route("/metadata-editor/api/preview", self._preview, owner=self)
        self.server.add_post_route("/metadata-editor/api/draft", self._save_draft, owner=self)
        self.server.add_post_route("/metadata-editor/api/commit", self._commit, owner=self)
        self.server.add_post_route("/metadata-editor/api/draft/delete", self._delete_draft, owner=self)

    def _index(self, request=None):
        return 200, "text/html; charset=utf-8", (self.plugin_path / "index.html").read_bytes()

    def _stylesheet(self, request=None):
        return 200, "text/css; charset=utf-8", (self.plugin_path / "assets" / "css" / "mediahub.css").read_bytes()

    @staticmethod
    def _json(data: Any, status: int = 200):
        return status, "application/json; charset=utf-8", json.dumps(data, ensure_ascii=False).encode("utf-8")

    def _api_call(self, method: str, default):
        if self.mediahub_api is None or not hasattr(self.mediahub_api, method):
            return default, False, f"{method} ist in dieser MediaHub-Version nicht verfügbar."
        try:
            return getattr(self.mediahub_api, method)(), True, ""
        except Exception as error:  # Plugin darf MediaHub nicht mitreißen.
            return default, False, str(error)

    def _status(self, request=None):
        return self._json({
            "available": True,
            "version": self.VERSION,
            "write_api_available": self._write_api_available(),
            "safe_mode": True,
            "message": (
                "Metadaten können endgültig gespeichert werden."
                if self._write_api_available()
                else "Entwurfsmodus aktiv: MediaHub stellt noch keine Metadaten-Schreibaktion bereit."
            ),
        })

    def _library(self, request=None):
        data, available, message = self._api_call("get_library_videos", [])
        items = data.get("videos", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({
            "available": available,
            "message": message,
            "items": self._normalize_items(items),
        }, status=200 if available else 409)

    def _channels(self, request=None):
        data, available, message = self._api_call("get_channels", [])
        items = data.get("channels", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, status=200 if available else 409)

    def _playlists(self, request=None):
        data, available, message = self._api_call("get_playlists", [])
        items = data.get("playlists", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, status=200 if available else 409)

    def _normalize_items(self, items):
        result = []
        for position, raw in enumerate(items or []):
            item = dict(raw) if isinstance(raw, dict) else {"title": str(raw)}
            item_id = str(item.get("id") or item.get("video_id") or item.get("path") or position)
            normalized = {"id": item_id, **item}
            normalized.setdefault("title", item.get("name") or item.get("filename") or "Ohne Titel")
            normalized.setdefault("description", item.get("summary") or "")
            normalized.setdefault("year", item.get("release_year") or "")
            normalized.setdefault("season", item.get("season_number") or "")
            normalized.setdefault("episode", item.get("episode_number") or "")
            normalized.setdefault("series", item.get("series_name") or item.get("show") or "")
            normalized.setdefault("channel", item.get("channel_name") or "")
            normalized.setdefault("playlist", item.get("playlist_name") or "")
            normalized.setdefault("published_at", item.get("release_date") or item.get("published") or "")
            result.append(normalized)
        return result

    def _clean_changes(self, payload):
        source = dict(payload or {})
        original = dict(source.get("original") or {})
        edited = dict(source.get("edited") or {})
        item_id = str(source.get("id") or edited.get("id") or original.get("id") or "").strip()
        changes = {}
        for field in self.EDITABLE_FIELDS:
            before = original.get(field, "")
            after = edited.get(field, before)
            if str(before).strip() != str(after).strip():
                changes[field] = {"before": before, "after": after}
        return item_id, original, edited, changes

    def _preview(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        return self._json({
            "ok": True,
            "id": item_id,
            "original": original,
            "edited": edited,
            "changes": changes,
            "change_count": len(changes),
        })

    def _drafts(self, request=None):
        drafts = self._read_drafts()
        return self._json({"ok": True, "items": list(drafts.values()), "count": len(drafts)})

    def _save_draft(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        draft = {
            "id": item_id,
            "title": str(edited.get("title") or original.get("title") or "Ohne Titel"),
            "original": original,
            "edited": edited,
            "changes": changes,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        with self._draft_lock:
            drafts = self._read_drafts_unlocked()
            drafts[item_id] = draft
            self._write_drafts_unlocked(drafts)
        return self._json({"ok": True, "message": "Metadaten-Entwurf gespeichert.", "draft": draft})

    def _delete_draft(self, payload, request=None):
        item_id = str((payload or {}).get("id") or "").strip()
        with self._draft_lock:
            drafts = self._read_drafts_unlocked()
            removed = drafts.pop(item_id, None)
            self._write_drafts_unlocked(drafts)
        return self._json({"ok": bool(removed), "message": "Entwurf gelöscht." if removed else "Entwurf nicht gefunden."}, 200 if removed else 404)

    def _write_api_available(self):
        return self.mediahub_api is not None and hasattr(self.mediahub_api, "execute_action")

    def _commit(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id or not changes:
            return self._json({"ok": False, "message": "Es sind keine speicherbaren Änderungen vorhanden."}, 400)
        if not self._write_api_available():
            return self._json({
                "ok": False,
                "draft_only": True,
                "message": "MediaHub stellt noch keine Metadaten-Schreibaktion bereit. Bitte den Entwurf speichern.",
            }, 409)
        backup = deepcopy(original)
        args = {"id": item_id, "metadata": edited, "backup": backup, "source": "mediahub.metadata_editor"}
        try:
            result = self.mediahub_api.execute_action("metadata.update", args)
        except Exception as error:
            return self._json({"ok": False, "message": str(error)}, 500)
        if not isinstance(result, dict):
            result = {"ok": bool(result), "message": "Metadaten-Aktion ausgeführt."}
        if not result.get("ok"):
            result.setdefault("draft_only", True)
        return self._json(result, 200 if result.get("ok") else 409)

    def _read_drafts(self):
        with self._draft_lock:
            return self._read_drafts_unlocked()

    def _read_drafts_unlocked(self):
        if not self.drafts_file.exists():
            return {}
        try:
            data = json.loads(self.drafts_file.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_drafts_unlocked(self, drafts):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.drafts_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.drafts_file)
