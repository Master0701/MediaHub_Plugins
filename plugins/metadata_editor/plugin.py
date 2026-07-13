from __future__ import annotations

import json
import shutil
import threading
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from mediahub_web_core.server import acquire_shared_server, release_shared_server
from mediahub_web_core.settings import WebRuntimeSettingsStore, connection_info


class MediaHubMetadataEditorPlugin:
    """Lokaler, sicherer Metadaten- und NFO-Editor für MediaHub."""

    VERSION = "0.2.0"
    EDITABLE_FIELDS = (
        "title", "description", "year", "season", "episode",
        "series", "channel", "playlist", "published_at",
    )
    NFO_TAGS = {
        "title": "title", "description": "plot", "year": "year",
        "season": "season", "episode": "episode", "series": "showtitle",
        "channel": "studio", "playlist": "set", "published_at": "aired",
    }
    IMAGE_NAMES = {
        "poster": ("poster.jpg", "poster.png", "folder.jpg", "folder.png"),
        "fanart": ("fanart.jpg", "fanart.png", "background.jpg", "background.png"),
        "banner": ("banner.jpg", "banner.png"),
        "thumbnail": ("thumb.jpg", "thumb.png", "thumbnail.jpg", "thumbnail.png"),
    }
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, plugin_path: Path, mediahub_api=None):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.base_dir = Path(getattr(mediahub_api, "base_dir", self.plugin_path))
        self.settings_store = WebRuntimeSettingsStore(self.base_dir)
        self.settings = self.settings_store.load()
        self.server = acquire_shared_server(str(self.base_dir), self.settings.host, self.settings.port)
        self.data_dir = self.base_dir / "plugin_data" / "metadata_editor"
        self.drafts_file = self.data_dir / "drafts.json"
        self.backup_dir = self.data_dir / "backups"
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
            "backup_dir": str(self.backup_dir),
            "write_api_available": self._write_api_available(),
            "direct_nfo_available": True,
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
        for path, handler in {
            "/metadata-editor/api/preview": self._preview,
            "/metadata-editor/api/draft": self._save_draft,
            "/metadata-editor/api/commit": self._commit,
            "/metadata-editor/api/draft/delete": self._delete_draft,
            "/metadata-editor/api/inspect-files": self._inspect_files,
            "/metadata-editor/api/nfo/save": self._save_nfo,
            "/metadata-editor/api/image/replace": self._replace_image,
        }.items():
            self.server.add_post_route(path, handler, owner=self)

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
        except Exception as error:
            return default, False, str(error)

    def _status(self, request=None):
        return self._json({
            "available": True,
            "version": self.VERSION,
            "write_api_available": self._write_api_available(),
            "direct_nfo_available": True,
            "safe_mode": True,
            "message": "NFO- und Bildverwaltung mit automatischer Sicherung ist verfügbar.",
        })

    def _library(self, request=None):
        data, available, message = self._api_call("get_library_videos", [])
        items = data.get("videos", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": self._normalize_items(items)}, 200 if available else 409)

    def _channels(self, request=None):
        data, available, message = self._api_call("get_channels", [])
        items = data.get("channels", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, 200 if available else 409)

    def _playlists(self, request=None):
        data, available, message = self._api_call("get_playlists", [])
        items = data.get("playlists", data.get("items", [])) if isinstance(data, dict) else data
        return self._json({"available": available, "message": message, "items": items or []}, 200 if available else 409)

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
        original, edited = dict(source.get("original") or {}), dict(source.get("edited") or {})
        item_id = str(source.get("id") or edited.get("id") or original.get("id") or "").strip()
        changes = {}
        for field in self.EDITABLE_FIELDS:
            before, after = original.get(field, ""), edited.get(field, original.get(field, ""))
            if str(before).strip() != str(after).strip():
                changes[field] = {"before": before, "after": after}
        return item_id, original, edited, changes

    def _preview(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        return self._json({"ok": True, "id": item_id, "original": original, "edited": edited, "changes": changes, "change_count": len(changes)})

    def _drafts(self, request=None):
        drafts = self._read_drafts()
        return self._json({"ok": True, "items": list(drafts.values()), "count": len(drafts)})

    def _save_draft(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id:
            return self._json({"ok": False, "message": "Der Medieneintrag besitzt keine ID."}, 400)
        draft = {"id": item_id, "title": str(edited.get("title") or original.get("title") or "Ohne Titel"), "original": original, "edited": edited, "changes": changes, "updated_at": datetime.now().isoformat(timespec="seconds")}
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); drafts[item_id] = draft; self._write_drafts_unlocked(drafts)
        return self._json({"ok": True, "message": "Metadaten-Entwurf gespeichert.", "draft": draft})

    def _delete_draft(self, payload, request=None):
        item_id = str((payload or {}).get("id") or "").strip()
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); removed = drafts.pop(item_id, None); self._write_drafts_unlocked(drafts)
        return self._json({"ok": bool(removed), "message": "Entwurf gelöscht." if removed else "Entwurf nicht gefunden."}, 200 if removed else 404)

    def _write_api_available(self):
        return self.mediahub_api is not None and hasattr(self.mediahub_api, "execute_action")

    def _commit(self, payload, request=None):
        item_id, original, edited, changes = self._clean_changes(payload)
        if not item_id or not changes:
            return self._json({"ok": False, "message": "Es sind keine speicherbaren Änderungen vorhanden."}, 400)
        if not self._write_api_available():
            return self._json({"ok": False, "draft_only": True, "message": "Die MediaHub-Datenbank kann noch nicht direkt aktualisiert werden. NFO-Dateien lassen sich bereits separat speichern."}, 409)
        args = {"id": item_id, "metadata": edited, "backup": deepcopy(original), "source": "mediahub.metadata_editor"}
        try:
            result = self.mediahub_api.execute_action("metadata.update", args)
        except Exception as error:
            return self._json({"ok": False, "message": str(error)}, 500)
        if not isinstance(result, dict):
            result = {"ok": bool(result), "message": "Metadaten-Aktion ausgeführt."}
        return self._json(result, 200 if result.get("ok") else 409)

    def _media_path(self, item: dict) -> Path | None:
        for key in ("path", "file_path", "filepath", "local_path", "filename"):
            value = str(item.get(key) or "").strip()
            if value:
                path = Path(value).expanduser()
                if path.exists():
                    return path.resolve()
        return None

    def _nfo_path(self, item: dict, media_path: Path | None) -> Path | None:
        explicit = str(item.get("nfo_path") or "").strip()
        if explicit:
            return Path(explicit).expanduser().resolve()
        if media_path is None:
            return None
        return (media_path / "tvshow.nfo") if media_path.is_dir() else media_path.with_suffix(".nfo")

    def _inspect_files(self, payload, request=None):
        item = dict((payload or {}).get("item") or {})
        media_path = self._media_path(item)
        nfo_path = self._nfo_path(item, media_path)
        nfo = {"path": str(nfo_path or ""), "exists": bool(nfo_path and nfo_path.exists()), "content": "", "error": ""}
        if nfo["exists"]:
            try:
                nfo["content"] = nfo_path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                nfo["error"] = "Die NFO-Datei ist nicht UTF-8-kodiert und wird aus Sicherheitsgründen nicht automatisch geändert."
            except Exception as error:
                nfo["error"] = str(error)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        images = {}
        for kind, names in self.IMAGE_NAMES.items():
            found = next((folder / name for name in names if folder and (folder / name).exists()), None)
            images[kind] = {"exists": bool(found), "path": str(found or "")}
        return self._json({"ok": True, "media_path": str(media_path or ""), "folder": str(folder or ""), "nfo": nfo, "images": images})

    def _backup_file(self, source: Path, item_id: str, category: str) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in item_id)[:80] or "media"
        target_dir = self.backup_dir / safe_id / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{stamp}_{source.name}"
        shutil.copy2(source, target)
        return target

    @staticmethod
    def _set_xml_text(root: ET.Element, tag: str, value: Any):
        node = root.find(tag)
        if node is None:
            node = ET.SubElement(root, tag)
        node.text = str(value or "")

    def _save_nfo(self, payload, request=None):
        source = dict(payload or {})
        item = dict(source.get("item") or {})
        edited = dict(source.get("edited") or {})
        item_id = str(item.get("id") or edited.get("id") or "").strip()
        media_path = self._media_path(item)
        nfo_path = self._nfo_path(item, media_path)
        if not item_id or nfo_path is None:
            return self._json({"ok": False, "message": "Kein gültiger lokaler Medien- oder NFO-Pfad vorhanden."}, 400)
        if nfo_path.exists():
            try:
                raw = nfo_path.read_text(encoding="utf-8-sig")
                root = ET.fromstring(raw) if raw.strip() else ET.Element("episodedetails")
                backup = self._backup_file(nfo_path, item_id, "nfo")
            except UnicodeDecodeError:
                return self._json({"ok": False, "message": "NFO ist nicht UTF-8-kodiert. Keine Änderung durchgeführt."}, 409)
            except ET.ParseError as error:
                return self._json({"ok": False, "message": f"NFO enthält ungültiges XML: {error}"}, 409)
            except Exception as error:
                return self._json({"ok": False, "message": str(error)}, 500)
        else:
            root = ET.Element("episodedetails")
            backup = None
        for field, tag in self.NFO_TAGS.items():
            self._set_xml_text(root, tag, edited.get(field, item.get(field, "")))
        try:
            nfo_path.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")
            temporary = nfo_path.with_suffix(nfo_path.suffix + ".tmp")
            tree.write(temporary, encoding="utf-8", xml_declaration=True)
            temporary.replace(nfo_path)
        except Exception as error:
            return self._json({"ok": False, "message": f"NFO konnte nicht gespeichert werden: {error}"}, 500)
        return self._json({"ok": True, "message": "NFO UTF-8-sicher gespeichert.", "path": str(nfo_path), "backup": str(backup or "")})

    def _replace_image(self, payload, request=None):
        source = dict(payload or {})
        item = dict(source.get("item") or {})
        kind = str(source.get("kind") or "").strip().lower()
        source_path = Path(str(source.get("source_path") or "").strip()).expanduser()
        item_id = str(item.get("id") or "").strip()
        if kind not in self.IMAGE_NAMES:
            return self._json({"ok": False, "message": "Unbekannter Bildtyp."}, 400)
        if not source_path.is_file() or source_path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            return self._json({"ok": False, "message": "Die ausgewählte Bilddatei wurde nicht gefunden oder besitzt kein unterstütztes Format."}, 400)
        media_path = self._media_path(item)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        if folder is None or not folder.exists():
            return self._json({"ok": False, "message": "Der lokale Medienordner wurde nicht gefunden."}, 400)
        target = folder / f"{kind}{source_path.suffix.lower()}"
        existing = next((folder / name for name in self.IMAGE_NAMES[kind] if (folder / name).exists()), None)
        try:
            backup = self._backup_file(existing, item_id, f"images/{kind}") if existing else None
            shutil.copy2(source_path, target)
            if existing and existing != target and existing.exists():
                existing.unlink()
        except Exception as error:
            return self._json({"ok": False, "message": f"Bild konnte nicht ersetzt werden: {error}"}, 500)
        return self._json({"ok": True, "message": f"{kind.capitalize()} wurde ersetzt.", "path": str(target), "backup": str(backup or "")})

    def _read_drafts(self):
        with self._draft_lock:
            return self._read_drafts_unlocked()

    def _read_drafts_unlocked(self):
        if not self.drafts_file.exists():
            return {}
        try:
            data = json.loads(self.drafts_file.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_drafts_unlocked(self, drafts):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.drafts_file.with_suffix(".tmp")
        temporary.write_text(json.dumps(drafts, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.drafts_file)
