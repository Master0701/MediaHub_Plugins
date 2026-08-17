from __future__ import annotations

import base64
import json
import mimetypes
import shutil
import subprocess
import threading
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

from mediahub_metadata_core import (
    SUPPORTED_EXTENSIONS,
    capability_for_extension,
    merge_mediahub_matroska_tags,
    read_embedded_metadata,
    read_mediahub_matroska_tags,
)
from mediahub_web_core.server import acquire_shared_server, release_shared_server
from mediahub_web_core.settings import WebRuntimeSettingsStore, connection_info
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QImageReader
from PySide6.QtWidgets import QListWidgetItem, QWidget


class MediaHubMetadataEditorPlugin:
    """Lokaler, sicherer Metadaten- und NFO-Editor für MediaHub."""

    VERSION = "0.4.2"
    EDITABLE_FIELDS = (
        "media_type",
        "title",
        "description",
        "year",
        "season",
        "episode",
        "episode_title",
        "series",
        "channel",
        "playlist",
        "published_at",
    )
    NFO_TAGS: ClassVar[dict[str, str]] = {
        "title": "title", "description": "plot", "year": "year",
        "season": "season", "episode": "episode", "series": "showtitle",
        "channel": "studio", "playlist": "set", "published_at": "aired",
    }
    IMAGE_NAMES: ClassVar[dict[str, tuple[str, ...]]] = {
        "poster": ("poster.jpg", "poster.png", "folder.jpg", "folder.png"),
        "fanart": ("fanart.jpg", "fanart.png", "background.jpg", "background.png"),
        "banner": ("banner.jpg", "banner.png"),
        "thumbnail": ("thumb.jpg", "thumb.png", "thumbnail.jpg", "thumbnail.png"),
        "season_playlist": ("season.jpg", "season.png", "season-poster.jpg", "season-poster.png", "playlist.jpg", "playlist.png", "folder.jpg", "folder.png"),
    }
    IMAGE_EXTENSIONS: ClassVar[set[str]] = {".jpg", ".jpeg", ".png", ".webp"}
    LOCAL_MEDIA_EXTENSIONS: ClassVar[set[str]] = set(SUPPORTED_EXTENSIONS)

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
        self.recovery_dir = self.data_dir / "recovery"
        self.local_folder_state_file = self.data_dir / "local_folder.json"
        self.local_sources_file = self.data_dir / "local_sources.json"
        self.scan_state_file = self.data_dir / "scan_state.json"
        self._draft_lock = threading.Lock()
        self._session_drafts: dict[str, dict[str, Any]] = {}
        self._register_routes()

    def start(self):
        self.server.start()

    def stop(self):
        release_shared_server(str(self.base_dir), owner=self)


    def get_runtime_capabilities(self):
        capabilities = {
            "metadata.read": self,
            "metadata.review": self,
        }
        if self._write_api_available():
            capabilities["metadata.write"] = self
        return capabilities

    def get_capability_contracts(self):
        write_available = self._write_api_available()
        return {
            "metadata.read": {
                "mode": "read_only",
                "execution_allowed": False,
            },
            "metadata.review": {
                "mode": "advisory",
                "execution_allowed": False,
            },
            "metadata.write": {
                "mode": "confirmed_write",
                "available": write_available,
                "execution_allowed": write_available,
                "automatic_apply_allowed": False,
                "human_confirmation_required": True,
            },
        }

    def _resolve_capability(self, capability):
        api = self.mediahub_api
        if api is None:
            return None
        for name in (
            "resolve_capability",
            "get_capability_provider",
            "find_capability_provider",
            "get_plugin_capability",
        ):
            fn = getattr(api, name, None)
            if callable(fn):
                try:
                    provider = fn(capability)
                except Exception:  # noqa: BLE001 - externe Provider-Grenze
                    provider = None
                if provider is not None:
                    return provider
        return None

    def ai_metadata_status(self):
        provider = self._resolve_capability("ai.metadata_review")
        return {
            "available": provider is not None,
            "provider": "MediaHub KI-Assistent" if provider is not None else "",
        }

    def ai_metadata_review(self, item):
        provider = self._resolve_capability("ai.metadata_review")
        if provider is None:
            return {
                "available": False,
                "fields": {},
                "changes": {},
                "warnings": ["MediaHub KI-Assistent ist nicht verfügbar."],
                "execution_allowed": False,
                "metadata_write_allowed": False,
            }

        payload = {
            "item": dict(item or {}),
            "path": str(
                (item or {}).get("path")
                or (item or {}).get("file_path")
                or ""
            ),
        }

        method = getattr(provider, "analyze_metadata_review", None)
        if not callable(method):
            method = getattr(provider, "analyze", None)
        if not callable(method):
            return {
                "available": False,
                "fields": {},
                "changes": {},
                "warnings": ["KI-Provider unterstützt keine Metadatenprüfung."],
                "execution_allowed": False,
                "metadata_write_allowed": False,
            }

        result = dict(method(payload) or {})
        result["execution_allowed"] = False
        result["metadata_write_allowed"] = False
        result["automatic_apply_allowed"] = False
        result["human_confirmation_required"] = True
        return result

    @staticmethod
    def _metadata_payload_item(payload):
        source = dict(payload or {})
        item = dict(source.get("item") or source.get("metadata") or {})
        path_value = str(source.get("path") or item.get("path") or item.get("file_path") or "").strip()
        if path_value and not item.get("path"):
            item["path"] = path_value
        return item

    def _read_nfo_metadata(self, item):
        media_path = self._media_path(item)
        nfo_path = self._nfo_path(item, media_path)
        values = {}
        if not nfo_path or not nfo_path.exists():
            return values, str(nfo_path or ""), False, ""
        try:
            raw = nfo_path.read_text(encoding="utf-8-sig")
            root = ET.fromstring(raw) if raw.strip() else None
            if root is None:
                return {}, str(nfo_path), True, ""
            reverse = {tag: field for field, tag in self.NFO_TAGS.items()}
            for node in list(root):
                field = reverse.get(str(node.tag).lower())
                if field and node.text not in (None, ""):
                    value = str(node.text).strip()

                    if field in {"year", "season", "episode"}:
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            pass

                    values[field] = value
            return values, str(nfo_path), True, ""
        except Exception as error:  # noqa: BLE001 - NFO-Lesegrenze
            return {}, str(nfo_path), True, str(error)

    def _read_embedded_file_metadata(self, item):
        media_path = self._media_path(dict(item or {}))

        if media_path is None or not media_path.is_file():
            return {}, {
                "available": False,
                "ok": False,
                "message": "Keine lokale Mediendatei vorhanden.",
            }

        capability = capability_for_extension(media_path.suffix)

        if not capability.get("supported"):
            return {}, {
                "available": False,
                "ok": False,
                "message": "Dateiformat wird nicht unterst?tzt.",
            }

        ffprobe = self._tool_path("ffprobe")

        if ffprobe is None:
            return {}, {
                "available": False,
                "ok": False,
                "message": (
                    "FFprobe ist ?ber den MediaHub-Tool-Manager "
                    "nicht verf?gbar."
                ),
            }

        result = read_embedded_metadata(
            media_path,
            ffprobe,
        )

        embedded_values = dict(
            result.get("tags") or {}
        )

        matroska_result = {
            "available": False,
            "ok": False,
            "tags": {},
        }

        if media_path.suffix.lower() == ".mkv":
            mkvtoolnix = self._tool_path("mkvtoolnix")

            if mkvtoolnix is not None:
                mkvextract = (
                    mkvtoolnix.parent
                    / "mkvextract.exe"
                )

                if mkvextract.is_file():
                    try:
                        process = subprocess.run(
                            [
                                str(mkvextract),
                                str(media_path),
                                "tags",
                            ],
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            check=False,
                        )

                        if process.returncode == 0:
                            matroska_values = (
                                read_mediahub_matroska_tags(
                                    process.stdout
                                )
                            )

                            # Die hierarchischen Matroska-Tags
                            # sind f?r Serie/Staffel/Episode
                            # genauer als allgemeine FFprobe-Tags.
                            for key, value in (
                                matroska_values.items()
                            ):
                                if value not in (None, ""):
                                    embedded_values[key] = value

                            # FFprobe flacht hierarchische
                            # Matroska-TITLE-Tags ab. Dadurch
                            # kann der Episodentitel f?lschlich
                            # als allgemeiner Titel erscheinen.
                            #
                            # Den echten Segmenttitel lesen wir
                            # deshalb direkt mit mkvmerge -J.
                            try:
                                identify = subprocess.run(
                                    [
                                        str(mkvtoolnix),
                                        "-J",
                                        str(media_path),
                                    ],
                                    capture_output=True,
                                    text=True,
                                    encoding="utf-8",
                                    errors="replace",
                                    check=False,
                                )

                                if identify.returncode == 0:
                                    identify_data = json.loads(
                                        identify.stdout or "{}"
                                    )

                                    segment_title = str(

                                            identify_data
                                            .get("container", {})
                                            .get("properties", {})
                                            .get("title")
                                            or ""

                                    ).strip()

                                    if segment_title:
                                        embedded_values[
                                            "title"
                                        ] = segment_title

                            except Exception:  # noqa: BLE001,S110 - optionaler MKV-Fallback
                                # Fehler beim zus?tzlichen
                                # MKVToolNix-Lesen darf die
                                # ?brigen Metadaten nicht
                                # unbrauchbar machen.
                                pass

                            matroska_result = {
                                "available": True,
                                "ok": True,
                                "tags": matroska_values,
                                "backend": "mkvextract",
                            }
                        else:
                            matroska_result = {
                                "available": True,
                                "ok": False,
                                "tags": {},
                                "backend": "mkvextract",
                                "returncode": (
                                    process.returncode
                                ),
                                "message": (
                                    process.stderr.strip()
                                    or "MKV-Tags konnten nicht "
                                    "gelesen werden."
                                ),
                            }

                    except Exception as error:  # noqa: BLE001 - MKVToolNix-Prozessgrenze
                        matroska_result = {
                            "available": True,
                            "ok": False,
                            "tags": {},
                            "backend": "mkvextract",
                            "message": str(error),
                        }

        return (
            embedded_values,
            {
                "available": True,
                **result,
                "matroska": matroska_result,
            },
        )

    def read_metadata(self, payload=None):
        item = self._metadata_payload_item(payload)
        normalized = self._normalize_items([item])[0] if item else {}

        embedded_values, embedded_result = (
            self._read_embedded_file_metadata(item)
        )

        nfo_values, nfo_path, nfo_exists, nfo_error = (
            self._read_nfo_metadata(item)
        )

        # Priorit?t:
        # 1. Standard-/MediaHub-Werte
        # 2. eingebettete Datei-Metadaten
        # 3. vorhandene NFO
        merged = dict(normalized)

        for key, value in embedded_values.items():
            if value not in (None, ""):
                merged[key] = value

        for key, value in nfo_values.items():
            if value not in (None, ""):
                merged[key] = value
        return {
            "provider": "MediaHub Metadata Editor",
            "available": True,
            "read_only": True,
            "metadata": merged,
            "sources": {
                "payload": bool(item),
                "embedded": bool(embedded_values),
                "embedded_result": embedded_result,
                "nfo": nfo_exists,
                "nfo_path": nfo_path,
                "nfo_error": nfo_error,
            },
            "execution_allowed": False,
        }

    def review_metadata(self, payload=None):
        source = dict(payload or {})
        detected = dict(source.get("detected") or source.get("proposed") or {})
        read_result = self.read_metadata(source)
        current = dict(read_result.get("metadata") or {})
        fields = ("title", "year", "season", "episode", "series")
        changes = []
        for field in fields:
            before = str(current.get(field) or "").strip()
            after = str(detected.get(field) or "").strip()
            if after and before.casefold() != after.casefold():
                changes.append({"field": field, "before": before, "after": after})
        return {
            "provider": "MediaHub Metadata Editor",
            "available": True,
            "review_only": True,
            "current_metadata": current,
            "proposed_metadata": detected,
            "changes": changes,
            "change_count": len(changes),
            "execution_allowed": False,
            "automatic_apply_allowed": False,
            "human_confirmation_required": True,
        }

    def _read_back_written_metadata(self, item_id: str, edited: dict):
        api = self.mediahub_api
        getter = getattr(api, "get_library_videos", None) if api is not None else None
        if not callable(getter):
            return None
        try:
            data = getter()
        except Exception:  # noqa: BLE001 - MediaHub-API-Grenze
            return None

        items = (
            data.get("videos", data.get("items", []))
            if isinstance(data, dict)
            else data
        )
        target_path = str(
            edited.get("path")
            or edited.get("file_path")
            or ""
        ).strip()

        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            normalized = self._normalize_items([raw])[0]
            candidate_id = str(
                normalized.get("id")
                or normalized.get("video_id")
                or ""
            ).strip()
            candidate_path = str(
                normalized.get("path")
                or normalized.get("file_path")
                or ""
            ).strip()

            if item_id and candidate_id == item_id:
                return normalized
            if (
                target_path
                and candidate_path
                and candidate_path.casefold() == target_path.casefold()
            ):
                return normalized
        return None

    def _verify_written_metadata(
        self,
        *,
        item_id: str,
        edited: dict,
        changes: dict,
    ) -> dict:
        current = self._read_back_written_metadata(item_id, edited)
        if current is None:
            return {
                "available": False,
                "verified": False,
                "mismatches": [],
                "message": (
                    "MediaHub hat keine Rücklesedaten für eine direkte "
                    "Verifikation geliefert."
                ),
            }

        mismatches = []
        for field, change in changes.items():
            expected = change.get("after", "")
            actual = current.get(field, "")
            if str(expected).strip() != str(actual).strip():
                mismatches.append(
                    {
                        "field": field,
                        "expected": expected,
                        "actual": actual,
                    }
                )

        return {
            "available": True,
            "verified": not mismatches,
            "mismatches": mismatches,
            "metadata": current,
            "message": (
                "Geschriebene Metadaten wurden erfolgreich zurückgelesen."
                if not mismatches
                else "Rücklesekontrolle hat Abweichungen festgestellt."
            ),
        }

    def _tool_path(self, tool_id: str) -> Path | None:
        api = getattr(self, "mediahub_api", None)
        getter = getattr(api, "get_tool_path", None) if api is not None else None

        if not callable(getter):
            return None

        try:
            value = str(getter(tool_id) or "").strip()
        except Exception:  # noqa: BLE001 - Tool-Service-API-Grenze
            return None

        if not value:
            return None

        path = Path(value)
        return path if path.is_file() else None

    def _mkvtoolnix_component(
        self,
        executable: str,
    ) -> Path | None:
        main = self._tool_path("mkvtoolnix")

        if main is None:
            return None

        candidate = main.parent / executable

        if not candidate.is_file():
            return None

        return candidate

    def _mkvpropedit_path(self) -> Path | None:
        return self._mkvtoolnix_component(
            "mkvpropedit.exe"
        )

    def _mkvextract_path(self) -> Path | None:
        return self._mkvtoolnix_component(
            "mkvextract.exe"
        )

    @staticmethod
    def _ffmpeg_metadata_arguments(
        metadata: dict,
        allowed_fields,
    ) -> list[str]:
        allowed = set(allowed_fields or ())

        mappings = (
            ("title", "title", metadata.get("title")),
            (
                "description",
                "description",
                metadata.get("description"),
            ),
            (
                "comment",
                "description",
                metadata.get("description"),
            ),
            (
                "date",
                "published_at",
                metadata.get("published_at"),
            ),
            (
                "date",
                "year",
                metadata.get("year"),
            ),
            ("year", "year", metadata.get("year")),
            ("show", "series", metadata.get("series")),
            (
                "season_number",
                "season",
                metadata.get("season"),
            ),
            (
                "episode_id",
                "episode",
                metadata.get("episode"),
            ),
            (
                "episode_sort",
                "episode",
                metadata.get("episode"),
            ),
            (
                "episode_title",
                "episode_title",
                metadata.get("episode_title"),
            ),
            ("network", "channel", metadata.get("channel")),
            (
                "grouping",
                "playlist",
                metadata.get("playlist"),
            ),
        )

        args = []
        emitted = set()

        for tag_name, source_field, raw_value in mappings:
            if source_field not in allowed:
                continue

            value = str(raw_value or "").strip()

            if not value:
                continue

            key = (tag_name, value)

            if key in emitted:
                continue

            emitted.add(key)

            args.extend(
                [
                    "-metadata",
                    f"{tag_name}={value}",
                ]
            )

        return args

    def _extract_mkv_tags(
        self,
        media_path: Path,
        output_path: Path,
    ) -> dict:
        mkvextract = self._mkvextract_path()

        if mkvextract is None:
            return {
                "ok": False,
                "message": (
                    "mkvextract.exe ist ?ber den "
                    "MediaHub-Tool-Manager nicht verf?gbar."
                ),
            }

        output_path.unlink(missing_ok=True)

        completed = subprocess.run(
            [
                str(mkvextract),
                str(media_path),
                "tags",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )

        if completed.returncode not in (0, 1):
            return {
                "ok": False,
                "returncode": completed.returncode,
                "message": (
                    str(
                        completed.stderr
                        or completed.stdout
                        or ""
                    ).strip()
                    or "MKV-Tags konnten nicht extrahiert werden."
                ),
            }

        if output_path.is_file():
            xml_text = output_path.read_text(
                encoding="utf-8-sig",
            )
        else:
            # Keine vorhandenen Tags ist kein Fehler.
            xml_text = ""

        return {
            "ok": True,
            "returncode": completed.returncode,
            "xml": xml_text,
        }

    def _write_mkv_metadata(
        self,
        *,
        item_id: str,
        media_path: Path,
        original: dict,
        edited: dict,
        capability: dict,
    ) -> dict:
        mkvpropedit = self._mkvpropedit_path()

        if mkvpropedit is None:
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "backend": "mkvtoolnix",
                "message": (
                    "mkvpropedit.exe ist ?ber den "
                    "MediaHub-Tool-Manager nicht verf?gbar."
                ),
            }

        allowed = set(
            capability.get("write_fields") or ()
        )

        command = [
            str(mkvpropedit),
            str(media_path),
        ]

        title = ""

        if "title" in allowed:
            title = str(
                edited.get("title") or ""
            ).strip()

            if title:
                command.extend(
                    [
                        "--edit",
                        "info",
                        "--set",
                        f"title={title}",
                    ]
                )

        tag_fields = {
            "description",
            "year",
            "published_at",
            "series",
            "season",
            "episode",
            "episode_title",
        }

        wants_tags = any(
            field in allowed
            and str(edited.get(field) or "").strip()
            for field in tag_fields
        )

        tag_file = None

        if wants_tags:
            mkvextract = self._mkvextract_path()

            if mkvextract is None:
                return {
                    "ok": False,
                    "supported": True,
                    "written": False,
                    "backend": "mkvtoolnix",
                    "message": (
                        "Vorhandene MKV-Tags k?nnen nicht "
                        "sicher erhalten werden, weil "
                        "mkvextract.exe fehlt."
                    ),
                }

            work_dir = (
                self.recovery_dir
                / "_mkv_work"
            )
            work_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            safe_id = "".join(
                c if c.isalnum() or c in "-_"
                else "_"
                for c in str(item_id or "media")
            )[:80]

            tag_file = (
                work_dir
                / f"{safe_id}_tags.xml"
            )

            extracted = self._extract_mkv_tags(
                media_path,
                tag_file,
            )

            if not extracted.get("ok"):
                return {
                    "ok": False,
                    "supported": True,
                    "written": False,
                    "backend": "mkvtoolnix",
                    "message": (
                        "Vorhandene MKV-Tags konnten nicht "
                        "sicher gelesen werden: "
                        + str(
                            extracted.get("message") or ""
                        )
                    ),
                }

            try:
                merged_xml = (
                    merge_mediahub_matroska_tags(
                        extracted.get("xml") or "",
                        edited,
                    )
                )
            except Exception as error:  # noqa: BLE001 - MKV-Tag-Merge-Grenze
                return {
                    "ok": False,
                    "supported": True,
                    "written": False,
                    "backend": "mkvtoolnix",
                    "message": (
                        "MKV-Tag-Struktur konnte nicht "
                        f"vorbereitet werden: {error}"
                    ),
                }

            tag_file.write_text(
                merged_xml,
                encoding="utf-8",
                newline="\n",
            )

            command.extend(
                [
                    "--tags",
                    f"all:{tag_file}",
                ]
            )

        if len(command) == 2:
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "backend": "mkvtoolnix",
                "message": (
                    "F?r MKV sind keine schreibbaren "
                    "?nderungen vorhanden."
                ),
            }

        try:
            backup = self._backup_file(
                media_path,
                item_id,
                "media_metadata",
            )
        except Exception as error:  # noqa: BLE001 - Backup-Grenze
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "backend": "mkvtoolnix",
                "message": (
                    "Sicherung der Mediendatei "
                    f"fehlgeschlagen: {error}"
                ),
            }

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                creationflags=getattr(
                    subprocess,
                    "CREATE_NO_WINDOW",
                    0,
                ),
            )
        except Exception as error:  # noqa: BLE001 - externer MKVToolNix-Prozess
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "backend": "mkvtoolnix",
                "backup": str(backup),
                "message": (
                    "MKVToolNix konnte nicht "
                    f"gestartet werden: {error}"
                ),
            }
        finally:
            if tag_file is not None:
                tag_file.unlink(
                    missing_ok=True,
                )

        if completed.returncode not in (0, 1):
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "backend": "mkvtoolnix",
                "backup": str(backup),
                "returncode": completed.returncode,
                "message": (
                    "mkvpropedit konnte die MKV-"
                    "Metadaten nicht schreiben: "
                    + str(
                        completed.stderr
                        or completed.stdout
                        or ""
                    ).strip()
                ),
            }

        recovery = self._record_recovery(
            action="media_metadata.write",
            item_id=item_id,
            target=str(media_path),
            before=original,
            after=edited,
            result={
                "ok": True,
                "tool": "mkvpropedit",
                "in_place": True,
                "tags_preserved": wants_tags,
                "returncode": completed.returncode,
                "warning": (
                    completed.returncode == 1
                ),
            },
            backup=str(backup),
        )

        return {
            "ok": True,
            "supported": True,
            "written": True,
            "backend": "mkvtoolnix",
            "path": str(media_path),
            "backup": str(backup),
            "recovery": str(recovery),
            "returncode": completed.returncode,
            "message": (
                "MKV-Metadaten wurden mit MKVToolNix "
                "direkt in der Datei ge?ndert; vorhandene "
                "MKV-Tags wurden vor der ?nderung ?bernommen."
            ),
        }

    def _write_embedded_metadata(
        self,
        *,
        item_id: str,
        media_path: Path,
        original: dict,
        edited: dict,
    ) -> dict:
        extension = media_path.suffix.lower()
        capability = capability_for_extension(extension)

        if (
            not capability.get("supported")
            or not capability.get("direct_write")
        ):
            return {
                "ok": False,
                "supported": bool(capability.get("supported")),
                "written": False,
                "message": (
                    f"Direktes Schreiben eingebetteter Metadaten wird f?r "
                    f"{extension or 'dieses Format'} derzeit nicht unterst?tzt."
                ),
            }

        backend = str(
            capability.get("write_backend") or ""
        ).strip()

        if backend == "mkvtoolnix":
            return self._write_mkv_metadata(
                item_id=item_id,
                media_path=media_path,
                original=original,
                edited=edited,
                capability=capability,
            )

        if backend != "ffmpeg":
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "message": (
                    f"F?r {extension} ist kein direkter FFmpeg-Writer "
                    "freigegeben."
                ),
            }

        ffmpeg = self._tool_path("ffmpeg")

        if ffmpeg is None:
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "message": (
                    "FFmpeg ist ?ber den MediaHub-Tool-Manager nicht verf?gbar."
                ),
            }

        try:
            backup = self._backup_file(
                media_path,
                item_id,
                "media_metadata",
            )
        except Exception as error:  # noqa: BLE001 - Backup-Grenze
            return {
                "ok": False,
                "supported": True,
                "written": False,
                "message": (
                    f"Sicherung der Mediendatei fehlgeschlagen: {error}"
                ),
            }

        temporary = media_path.with_name(
            media_path.stem
            + ".mediahub-metadata-tmp"
            + media_path.suffix
        )

        temporary.unlink(missing_ok=True)

        command = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(media_path),
            "-map",
            "0",
            "-map_metadata",
            "0",
            "-c",
            "copy",
            *self._ffmpeg_metadata_arguments(
                edited,
                capability.get("write_fields"),
            ),
            str(temporary),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                creationflags=(
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                ),
            )

            if completed.returncode != 0:
                temporary.unlink(missing_ok=True)

                return {
                    "ok": False,
                    "supported": True,
                    "written": False,
                    "message": (
                        "FFmpeg konnte die eingebetteten Metadaten nicht "
                        "schreiben: "
                        + str(completed.stderr or "").strip()
                    ),
                    "backup": str(backup or ""),
                }

            if not temporary.is_file() or temporary.stat().st_size <= 0:
                temporary.unlink(missing_ok=True)

                return {
                    "ok": False,
                    "supported": True,
                    "written": False,
                    "message": (
                        "FFmpeg hat keine g?ltige Ausgabedatei erzeugt."
                    ),
                    "backup": str(backup or ""),
                }

            temporary.replace(media_path)

        except Exception as error:  # noqa: BLE001 - FFmpeg-/Dateisystem-Grenze
            temporary.unlink(missing_ok=True)

            return {
                "ok": False,
                "supported": True,
                "written": False,
                "message": (
                    f"Eingebettete Metadaten konnten nicht geschrieben "
                    f"werden: {error}"
                ),
                "backup": str(backup or ""),
            }

        recovery = self._record_recovery(
            action="metadata.file.write",
            item_id=item_id,
            target=str(media_path),
            before=original,
            after=edited,
            result={
                "ok": True,
                "tool": "ffmpeg",
                "stream_copy": True,
            },
            backup=str(backup or ""),
        )

        return {
            "ok": True,
            "supported": True,
            "written": True,
            "path": str(media_path),
            "backup": str(backup or ""),
            "recovery": str(recovery),
            "message": (
                "Eingebettete Metadaten wurden ohne Neu-Encoding "
                "in die Mediendatei geschrieben."
            ),
        }

    def write_metadata(self, payload=None):
        source = dict(payload or {})
        confirmed = source.get("confirmed") is True
        confirmation_source = str(
            source.get("confirmation_source") or ""
        ).strip()

        if not confirmed or confirmation_source != "human_gui":
            return {
                "ok": False,
                "confirmation_required": True,
                "human_confirmation_required": True,
                "automatic_apply_allowed": False,
                "message": (
                    "Metadaten werden nur nach ausdrücklicher Bestätigung "
                    "durch den Benutzer geschrieben."
                ),
            }

        item_id, original, edited, changes = self._clean_changes(source)
        if not item_id or not changes:
            return {
                "ok": False,
                "message": "Es sind keine speicherbaren Änderungen vorhanden.",
            }

        is_local_only = (
            str(original.get("source_type") or "").strip()
            == "local_folder"
            and not str(
                original.get("mediahub_id")
                or original.get("video_id")
                or ""
            ).strip()
        )

        if is_local_only:
            media_path = self._media_path(original)

            if media_path is None or not media_path.is_file():
                return {
                    "ok": False,
                    "local_only": True,
                    "message": (
                        "Die lokale Mediendatei wurde nicht gefunden."
                    ),
                }

            file_result = self._write_embedded_metadata(
                item_id=item_id,
                media_path=media_path,
                original=original,
                edited=edited,
            )

            file_result = dict(file_result)
            file_result["local_only"] = True

            return file_result

        if not self._write_api_available():
            return {
                "ok": False,
                "draft_only": True,
                "message": (
                    "Die MediaHub-Datenbank kann in dieser MediaHub-Version "
                    "nicht direkt aktualisiert werden."
                ),
            }

        target = str(
            edited.get("path")
            or original.get("path")
            or edited.get("file_path")
            or original.get("file_path")
            or ""
        )

        prepared_recovery = self._record_recovery(
            action="metadata.update.prepare",
            item_id=item_id,
            target=target,
            before=original,
            after=edited,
            result={
                "status": "prepared",
                "confirmed": True,
                "confirmation_source": confirmation_source,
            },
        )

        args = {
            "id": item_id,
            "metadata": edited,
            "backup": deepcopy(original),
            "source": "mediahub.metadata_editor",
            "confirmation": {
                "confirmed": True,
                "source": confirmation_source,
                "scope": "metadata.write",
            },
        }

        try:
            result = self.mediahub_api.execute_action(
                "metadata.update",
                args,
            )
        except Exception as error:  # noqa: BLE001 - MediaHub-Schreib-API-Grenze
            self._record_recovery(
                action="metadata.update.failed",
                item_id=item_id,
                target=target,
                before=original,
                after=edited,
                result={
                    "ok": False,
                    "error": str(error),
                    "prepared_recovery": str(prepared_recovery),
                },
            )
            return {
                "ok": False,
                "message": str(error),
                "recovery": str(prepared_recovery),
            }

        if not isinstance(result, dict):
            result = {
                "ok": bool(result),
                "message": "Metadaten-Aktion ausgeführt.",
            }
        else:
            result = dict(result)

        if not result.get("ok"):
            self._record_recovery(
                action="metadata.update.failed",
                item_id=item_id,
                target=target,
                before=original,
                after=edited,
                result=result,
            )
            result.setdefault("recovery", str(prepared_recovery))
            return result

        verification = self._verify_written_metadata(
            item_id=item_id,
            edited=edited,
            changes=changes,
        )
        result["verification"] = verification

        if verification.get("available") and not verification.get("verified"):
            rollback_args = {
                "id": item_id,
                "metadata": original,
                "backup": deepcopy(edited),
                "source": "mediahub.metadata_editor.rollback",
                "confirmation": {
                    "confirmed": True,
                    "source": "system_recovery",
                    "scope": "metadata.write.rollback",
                },
            }
            try:
                rollback_result = self.mediahub_api.execute_action(
                    "metadata.update",
                    rollback_args,
                )
                if not isinstance(rollback_result, dict):
                    rollback_result = {"ok": bool(rollback_result)}
            except Exception as error:  # noqa: BLE001 - Recovery-/Rollback-Grenze
                rollback_result = {
                    "ok": False,
                    "message": str(error),
                }

            rollback_recovery = self._record_recovery(
                action="metadata.update.rollback",
                item_id=item_id,
                target=target,
                before=edited,
                after=original,
                result=rollback_result,
            )

            return {
                "ok": False,
                "rolled_back": bool(rollback_result.get("ok")),
                "message": (
                    "Die Rücklesekontrolle hat Abweichungen festgestellt. "
                    "Die vorherigen Metadaten wurden wiederhergestellt."
                    if rollback_result.get("ok")
                    else
                    "Die Rücklesekontrolle hat Abweichungen festgestellt "
                    "und die automatische Wiederherstellung ist fehlgeschlagen."
                ),
                "verification": verification,
                "recovery": str(prepared_recovery),
                "rollback_recovery": str(rollback_recovery),
                "rollback_result": rollback_result,
            }

        completed_recovery = self._record_recovery(
            action="metadata.update",
            item_id=item_id,
            target=target,
            before=original,
            after=edited,
            result={
                **result,
                "prepared_recovery": str(prepared_recovery),
            },
        )
        result.setdefault("message", "Metadaten wurden gespeichert.")
        result["recovery"] = str(completed_recovery)
        result["prepared_recovery"] = str(prepared_recovery)
        result["human_confirmation_required"] = True
        result["automatic_apply_allowed"] = False
        return result

    def get_plugin_settings(self):
        info = connection_info(self.settings)
        active_url = str(info.get("active_url") or "").rstrip("/")
        return {
            "version": self.VERSION,
            "url": f"{active_url}/metadata-editor" if active_url else "/metadata-editor",
            "drafts_file": "",
            "draft_storage": "session_only",
            "backup_dir": str(self.backup_dir),
            "recovery_dir": str(self.recovery_dir),
            "local_sources_file": str(self.local_sources_file),
            "scan_state_file": str(self.scan_state_file),
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
            "/metadata-editor/api/open": self._open_local_target,
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
        except Exception as error:  # noqa: BLE001 - MediaHub-API-Grenze
            return default, False, str(error)

    def _status(self, request=None):
        return self._json({
            "available": True,
            "version": self.VERSION,
            "write_api_available": self._write_api_available(),
            "direct_nfo_available": True,
            "safe_mode": True,
            "message": "Medienbrowser, Metadaten-, NFO- und Bildverwaltung mit automatischer Sicherung sind verfügbar.",
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

            source_type = str(
                normalized.get("source_type") or ""
            ).strip()

            if source_type != "local_folder":
                mediahub_id = str(
                    item.get("video_id")
                    or item.get("id")
                    or ""
                ).strip()

                if mediahub_id:
                    normalized["mediahub_id"] = mediahub_id

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


    def _load_local_sources(self) -> list[str]:
        # Nur Quellordner werden dauerhaft gespeichert, keine Medienliste.
        sources: list[str] = []
        if self.local_sources_file.exists():
            try:
                data = json.loads(
                    self.local_sources_file.read_text(encoding="utf-8-sig")
                )
                raw_sources = data.get("sources", []) if isinstance(data, dict) else []
                seen: set[str] = set()
                for value in raw_sources:
                    path = Path(str(value or "")).expanduser()
                    if not path.is_dir():
                        continue
                    resolved = str(path.resolve())
                    key = resolved.casefold()
                    if key not in seen:
                        seen.add(key)
                        sources.append(resolved)
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                sources = []

        if not sources and self.local_folder_state_file.exists():
            try:
                legacy = json.loads(
                    self.local_folder_state_file.read_text(encoding="utf-8-sig")
                )
                value = str((legacy or {}).get("folder") or "").strip()
                path = Path(value).expanduser() if value else None
                if path is not None and path.is_dir():
                    sources = [str(path.resolve())]
                    self._save_local_sources(sources)
            except (
                OSError,
                UnicodeError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ):
                # Eine defekte alte Zustandsdatei darf den
                # Metadata Editor nicht am Start hindern.
                sources = []
        return sources

    def _save_local_sources(self, sources) -> None:
        unique: list[str] = []
        seen: set[str] = set()
        for value in sources or []:
            path = Path(str(value or "")).expanduser()
            if not path.is_dir():
                continue
            resolved = str(path.resolve())
            key = resolved.casefold()
            if key in seen:
                continue
            seen.add(key)
            unique.append(resolved)

        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.local_sources_file.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"schema_version": 1, "sources": unique},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.local_sources_file)

    def remember_local_source(self, folder) -> list[str]:
        root = Path(str(folder or "")).expanduser()
        if not root.is_dir():
            raise ValueError("Der ausgewählte Ordner wurde nicht gefunden.")
        resolved = str(root.resolve())
        sources = self._load_local_sources()
        if resolved.casefold() not in {source.casefold() for source in sources}:
            sources.append(resolved)
            self._save_local_sources(sources)
        return self._load_local_sources()

    def forget_local_source(self, folder) -> list[str]:
        target = str(Path(str(folder or "")).expanduser().resolve()).casefold()
        sources = [
            source
            for source in self._load_local_sources()
            if source.casefold() != target
        ]
        self._save_local_sources(sources)
        return sources

    def _load_last_local_folder(self) -> str:
        sources = self._load_local_sources()
        return sources[-1] if sources else ""

    def _save_last_local_folder(self, folder: Path) -> None:
        self.remember_local_source(folder)

    def _load_scan_state(self) -> dict[str, dict[str, int]]:
        if not self.scan_state_file.exists():
            return {}
        try:
            data = json.loads(
                self.scan_state_file.read_text(encoding="utf-8-sig")
            )
            files = data.get("files", {}) if isinstance(data, dict) else {}
            return files if isinstance(files, dict) else {}
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ):
            return {}

    def _save_scan_state(self, state: dict[str, dict[str, int]]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.scan_state_file.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"schema_version": 1, "files": state},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.scan_state_file)

    @staticmethod
    def _scan_signature(path: Path) -> dict[str, int]:
        stat = path.stat()
        return {
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
        }

    @staticmethod
    def _scan_state_belongs_to_root(state_path: str, root: Path) -> bool:
        try:
            Path(state_path).resolve().relative_to(root.resolve())
            return True
        except (OSError, ValueError):
            return False

    def scan_local_sources(
        self,
        *,
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source in self._load_local_sources():
            try:
                items = self.scan_local_folder(
                    source,
                    recursive=recursive,
                    remember_source=False,
                )
            except (OSError, ValueError):
                continue
            for item in items:
                key = str(
                    item.get("path")
                    or item.get("file_path")
                    or item.get("id")
                    or ""
                ).casefold()
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                result.append(item)
        return result

    def scan_local_folder(
        self,
        folder,
        *,
        recursive: bool = True,
        remember_source: bool = True,
    ) -> list[dict[str, Any]]:
        root = Path(str(folder or "")).expanduser()
        if not root.is_dir():
            raise ValueError("Der ausgewählte Ordner wurde nicht gefunden.")
        root = root.resolve()

        if remember_source:
            self.remember_local_source(root)

        previous_scan_state = self._load_scan_state()
        next_scan_state = dict(previous_scan_state)
        seen_in_root: set[str] = set()

        iterator = root.rglob("*") if recursive else root.glob("*")
        files = sorted(
            (
                path
                for path in iterator
                if path.is_file()
                and path.suffix.lower() in self.LOCAL_MEDIA_EXTENSIONS
            ),
            key=lambda path: str(path).casefold(),
        )

        result = []
        for position, path in enumerate(files):
            resolved_path = path.resolve()
            state_key = str(resolved_path)
            signature = self._scan_signature(resolved_path)
            previous_signature = previous_scan_state.get(state_key)

            if previous_signature is None:
                scan_status = "new"
            elif previous_signature != signature:
                scan_status = "changed"
            else:
                scan_status = "unchanged"

            next_scan_state[state_key] = signature
            seen_in_root.add(state_key.casefold())

            item = {
                "id": f"local:{resolved_path}",
                "title": path.stem,
                "filename": path.name,
                "path": str(resolved_path),
                "file_path": str(resolved_path),
                "folder": str(path.parent.resolve()),
                "source_type": "local_folder",
                "local_exists": True,
                "file_exists": True,
                "is_downloaded": True,
                "description": "",
                "year": "",
                "season": "",
                "episode": "",
                "series": "",
                "channel": "",
                "playlist": "",
                "published_at": "",
                "scan_status": scan_status,
                "scan_size": signature["size"],
                "scan_mtime_ns": signature["mtime_ns"],
            }

            embedded_values, embedded_result = (
                self._read_embedded_file_metadata(item)
            )

            for key, value in embedded_values.items():
                if value not in (None, ""):
                    item[key] = value

            item["embedded_metadata"] = bool(embedded_values)
            item["embedded_metadata_ok"] = bool(
                embedded_result.get("ok")
            )
            item["embedded_metadata_error"] = (
                ""
                if embedded_result.get("ok")
                else str(embedded_result.get("message") or "")
            )

            nfo_values, nfo_path, nfo_exists, nfo_error = (
                self._read_nfo_metadata(item)
            )

            for key, value in nfo_values.items():
                if value not in (None, ""):
                    item[key] = value

            item["nfo_path"] = nfo_path
            item["nfo_exists"] = nfo_exists
            item["nfo_error"] = nfo_error
            result.append(item)

        for state_key in list(next_scan_state):
            if (
                self._scan_state_belongs_to_root(state_key, root)
                and state_key.casefold() not in seen_in_root
            ):
                next_scan_state.pop(state_key, None)

        self._save_scan_state(next_scan_state)
        return self._normalize_items(result)
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
        draft = {"id": item_id, "title": str(edited.get("title") or original.get("title") or "Ohne Titel"), "original": original, "edited": edited, "changes": changes, "updated_at": datetime.now().astimezone().isoformat(timespec="seconds")}
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); drafts[item_id] = draft; self._write_drafts_unlocked(drafts)
        return self._json({"ok": True, "message": "Metadaten-Entwurf gespeichert.", "draft": draft})

    def _delete_draft(self, payload, request=None):
        item_id = str((payload or {}).get("id") or "").strip()
        with self._draft_lock:
            drafts = self._read_drafts_unlocked(); removed = drafts.pop(item_id, None); self._write_drafts_unlocked(drafts)
        return self._json({"ok": bool(removed), "message": "Entwurf gelöscht." if removed else "Entwurf nicht gefunden."}, 200 if removed else 404)

    def _write_api_available(self):
        api = getattr(self, "mediahub_api", None)
        return api is not None and hasattr(api, "execute_action")

    def _commit(self, payload, request=None):
        result = self.write_metadata(payload)
        status = 200 if result.get("ok") else 409
        return self._json(result, status)

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

    def cache_ai_poster(self, url):
        """Lädt nur eine KI-Poster-Vorschau in den lokalen Plugin-Cache."""
        import hashlib
        import urllib.request

        value = str(url or "").strip()
        if not value.startswith(("https://", "http://")):
            return None

        cache_dir = self.data_dir / "ai_poster_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
        target = cache_dir / f"{digest}.jpg"

        if target.is_file() and target.stat().st_size > 0:
            return target

        request = urllib.request.Request(
            value,
            headers={"User-Agent": "MediaHub/MetadataEditor"},
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            data = response.read(10 * 1024 * 1024 + 1)

        if not data or len(data) > 10 * 1024 * 1024:
            return None

        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(data)
        temporary.replace(target)
        return target

    def _poster_path(self, item) -> Path | None:
        media_path = self._media_path(dict(item or {}))
        folder = (
            media_path
            if media_path and media_path.is_dir()
            else (media_path.parent if media_path else None)
        )

        # Explicit image paths from MediaHub/library data are preferred when valid.
        for key in (
            "poster_path",
            "poster",
            "image_path",
            "cover_path",
            "thumbnail_path",
        ):
            value = str((item or {}).get(key) or "").strip()
            if value:
                candidate = Path(value)
                if candidate.is_file() and candidate.suffix.lower() in self.IMAGE_EXTENSIONS:
                    return candidate

        for name in self.IMAGE_NAMES.get("poster", ()):
            candidate = folder / name if folder else None
            if candidate and candidate.is_file():
                return candidate

        return None

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
            except OSError as error:
                nfo["error"] = str(error)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        images = {}
        for kind, names in self.IMAGE_NAMES.items():
            found = next((folder / name for name in names if folder and (folder / name).exists()), None)
            info = {"exists": bool(found), "path": str(found or ""), "name": "", "size_bytes": 0, "width": 0, "height": 0, "preview": ""}
            if found:
                info["name"] = found.name
                try:
                    info["size_bytes"] = found.stat().st_size
                except OSError:
                    pass
                try:
                    reader = QImageReader(str(found))
                    size = reader.size()
                    if size.isValid():
                        info["width"], info["height"] = size.width(), size.height()
                except (OSError, RuntimeError, ValueError):
                    # Bildabmessungen sind nur Zusatzinformationen.
                    # Ein nicht lesbares Bild darf die Dateiansicht
                    # nicht verhindern.
                    info["width"] = 0
                    info["height"] = 0
                try:
                    mime = mimetypes.guess_type(found.name)[0] or "image/jpeg"
                    encoded = base64.b64encode(found.read_bytes()).decode("ascii")
                    info["preview"] = f"data:{mime};base64,{encoded}"
                except (OSError, UnicodeError, ValueError):
                    # Die Vorschau ist optional. Pfad und sonstige
                    # Bildinformationen bleiben trotzdem verf?gbar.
                    info["preview"] = ""
            images[kind] = info
        return self._json({"ok": True, "media_path": str(media_path or ""), "folder": str(folder or ""), "nfo": nfo, "images": images})

    def _open_local_target(self, payload, request=None):
        source = dict(payload or {})
        item = dict(source.get("item") or {})
        target_type = str(source.get("target") or "folder").strip().lower()
        media_path = self._media_path(item)
        folder = media_path if media_path and media_path.is_dir() else (media_path.parent if media_path else None)
        nfo_path = self._nfo_path(item, media_path)
        if target_type == "video":
            target = media_path
        elif target_type == "nfo":
            target = nfo_path if nfo_path and nfo_path.exists() else None
        else:
            target = folder
        if target is None or not target.exists():
            return self._json({"ok": False, "message": "Das gewünschte lokale Ziel wurde nicht gefunden."}, 404)
        try:
            opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        except Exception as error:  # noqa: BLE001 - Qt/Desktop-Service-Grenze
            return self._json({"ok": False, "message": str(error)}, 500)
        return self._json({"ok": bool(opened), "message": "Lokales Ziel wurde auf dem MediaHub-Rechner geöffnet." if opened else "Das lokale Ziel konnte nicht geöffnet werden.", "path": str(target)}, 200 if opened else 409)

    def _backup_file(self, source: Path, item_id: str, category: str) -> Path:
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in item_id)[:80] or "media"
        target_dir = self.backup_dir / safe_id / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{stamp}_{source.name}"
        shutil.copy2(source, target)
        return target


    def _record_recovery(
        self,
        *,
        action: str,
        item_id: str,
        target: str = "",
        before=None,
        after=None,
        backup: str = "",
        result=None,
    ) -> Path:
        self.recovery_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        safe_id = "".join(
            char if char.isalnum() or char in "-_" else "_"
            for char in str(item_id or "media")
        )[:80] or "media"
        path = self.recovery_dir / f"{stamp}_{safe_id}.json"
        payload = {
            "schema_version": 1,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "action": str(action or ""),
            "item_id": str(item_id or ""),
            "target": str(target or ""),
            "backup": str(backup or ""),
            "before": deepcopy(before),
            "after": deepcopy(after),
            "result": deepcopy(result),
        }
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
        return path

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
            except OSError as error:
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
        except (OSError, ValueError) as error:
            return self._json({"ok": False, "message": f"NFO konnte nicht gespeichert werden: {error}"}, 500)
        recovery = self._record_recovery(
            action="nfo.write",
            item_id=item_id,
            target=str(nfo_path),
            before={"backup": str(backup or ""), "existed": bool(backup)},
            after={
                field: edited.get(field, item.get(field, ""))
                for field in self.EDITABLE_FIELDS
            },
            backup=str(backup or ""),
        )
        return self._json({
            "ok": True,
            "message": "NFO UTF-8-sicher gespeichert.",
            "path": str(nfo_path),
            "backup": str(backup or ""),
            "recovery": str(recovery),
        })

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
        target_stem = "folder" if kind == "season_playlist" else kind
        target = folder / f"{target_stem}{source_path.suffix.lower()}"
        existing = next((folder / name for name in self.IMAGE_NAMES[kind] if (folder / name).exists()), None)
        try:
            backup = self._backup_file(existing, item_id, f"images/{kind}") if existing else None
            shutil.copy2(source_path, target)
            if existing and existing != target and existing.exists():
                existing.unlink()
        except OSError as error:
            return self._json({"ok": False, "message": f"Bild konnte nicht ersetzt werden: {error}"}, 500)
        recovery = self._record_recovery(
            action="image.replace",
            item_id=item_id,
            target=str(target),
            before={
                "backup": str(backup or ""),
                "previous": str(existing or ""),
            },
            after={
                "source": str(source_path),
                "target": str(target),
                "kind": kind,
            },
            backup=str(backup or ""),
        )
        return self._json({
            "ok": True,
            "message": f"{kind.capitalize()} wurde ersetzt.",
            "path": str(target),
            "backup": str(backup or ""),
            "recovery": str(recovery),
        })

    def _read_drafts(self):
        with self._draft_lock:
            return self._read_drafts_unlocked()


    def _read_drafts_unlocked(self):
        return deepcopy(self._session_drafts)

    def _write_drafts_unlocked(self, drafts):
        self._session_drafts = deepcopy(dict(drafts or {}))

    def clear_session_drafts(self) -> None:
        with self._draft_lock:
            self._session_drafts.clear()
    def create_widget(self, parent=None):
        """Erzeugt die native Metadata-Editor-Oberfläche für MediaHub."""
        return NativeMetadataEditorWidget(self, parent=parent)


class NativeMetadataEditorWidget(QWidget):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QComboBox,
            QFormLayout,
            QFrame,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QListWidget,
            QPushButton,
            QScrollArea,
            QSpinBox,
            QSplitter,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )
        self.plugin = plugin
        self._QPixmap = QPixmap
        self._items = []
        self._library_items = []
        self._local_items = []
        self._local_sources = self.plugin._load_local_sources()
        self._local_folder = (
            self._local_sources[-1] if self._local_sources else ""
        )
        self._current = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        source_bar = QHBoxLayout()
        source_label = QLabel("Quelle:")
        source_label.setStyleSheet("font-weight: bold;")
        source_bar.addWidget(source_label)

        self.btn_mediahub_source = QPushButton("MediaHub / YouTube")
        self.btn_mediahub_source.clicked.connect(
            lambda: self._select_source_category("MediaHub / YouTube")
        )
        self.btn_folder = QPushButton("Lokalen Ordner wählen…")
        self.btn_folder.clicked.connect(self._choose_local_folder)
        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_refresh.clicked.connect(self.refresh)

        source_bar.addWidget(self.btn_mediahub_source)
        source_bar.addWidget(self.btn_folder)
        source_bar.addStretch(1)
        source_bar.addWidget(self.btn_refresh)
        root.addLayout(source_bar)

        search_bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Medien durchsuchen …")
        self.search.textChanged.connect(self._apply_filter)
        search_bar.addWidget(self.search, 1)
        root.addLayout(search_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Kategorien"))
        self.categories = QListWidget()
        for text in (
            "Alle Medien",
            "MediaHub / YouTube",
            "Lokaler Ordner",
            "Kanäle",
            "Serien",
            "Playlists",
            "Entwürfe",
        ):
            self.categories.addItem(text)
        self.categories.setCurrentRow(0)
        self.categories.currentRowChanged.connect(self._apply_filter)
        left_layout.addWidget(self.categories, 1)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(QLabel("Medien"))
        self.media_list = QListWidget()
        self.media_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.media_list.currentRowChanged.connect(self._load_selected)
        center_layout.addWidget(self.media_list, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        # ------------------------------------------------------------------
        # Concept layout: editor left, old metadata/poster/actions right,
        # AI comparison across the bottom.
        # ------------------------------------------------------------------
        content_split = QSplitter(Qt.Orientation.Horizontal)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        editor_group = QGroupBox("Metadaten bearbeiten  (Entwurf – noch nicht gespeichert)")
        editor_layout = QVBoxLayout(editor_group)

        self.title_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setVisible(False)

        self.description_preview = QLineEdit()
        self.description_preview.setReadOnly(True)
        self.description_preview.setPlaceholderText("Keine Beschreibung")
        self.description_preview.setToolTip(
            "Vollständige Beschreibung über „Beschreibung bearbeiten…“ öffnen."
        )

        self.btn_description_edit = QPushButton("Beschreibung bearbeiten…")
        self.btn_description_edit.clicked.connect(self._edit_description_dialog)
        self.media_type_edit = QComboBox()
        self.media_type_edit.addItem("Video", "video")
        self.media_type_edit.addItem("Film", "movie")
        self.media_type_edit.addItem("Serie", "series")

        self.year_edit = QSpinBox()
        self.year_edit.setRange(0, 9999)
        self.year_edit.setSpecialValueText("")
        self.season_edit = QSpinBox()
        self.season_edit.setRange(0, 9999)
        self.episode_edit = QSpinBox()
        self.episode_edit.setRange(0, 99999)
        self.series_edit = QLineEdit()
        self.channel_edit = QLineEdit()
        self.playlist_edit = QLineEdit()
        self.date_edit = QLineEdit()
        self.path_label = QLabel("-")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        basic_group = QGroupBox("Grunddaten")
        basic_form = QFormLayout(basic_group)

        basic_form.setVerticalSpacing(10)
        basic_form.setHorizontalSpacing(12)

        basic_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )

        basic_form.setRowWrapPolicy(
            QFormLayout.RowWrapPolicy.DontWrapRows
        )

        basic_group.setMinimumHeight(255)

        for widget in (
            self.title_edit,
            self.media_type_edit,
            self.description_preview,
            self.year_edit,
            self.date_edit,
        ):
            widget.setMinimumHeight(30)

        self.btn_description_edit.setMinimumHeight(30)

        basic_form.addRow(
            "Titel",
            self.title_edit,
        )

        basic_form.addRow(
            "Medientyp",
            self.media_type_edit,
        )

        description_row = QHBoxLayout()
        description_row.setSpacing(8)
        description_row.addWidget(
            self.description_preview,
            1,
        )
        description_row.addWidget(
            self.btn_description_edit,
        )

        basic_form.addRow(
            "Beschreibung",
            description_row,
        )

        basic_form.addRow(
            "Jahr",
            self.year_edit,
        )

        basic_form.addRow(
            "Ver?ffentlichung / Ausstrahlung",
            self.date_edit,
        )

        editor_layout.addWidget(basic_group)

        series_group = QGroupBox("Seriendaten")
        series_form = QFormLayout(series_group)
        series_form.setVerticalSpacing(8)
        series_form.addRow("Serie", self.series_edit)

        season_episode_row = QHBoxLayout()
        season_episode_row.setSpacing(10)
        season_episode_row.addWidget(QLabel("Staffel"))
        season_episode_row.addWidget(self.season_edit, 1)
        season_episode_row.addSpacing(18)
        season_episode_row.addWidget(QLabel("Episode"))
        season_episode_row.addWidget(self.episode_edit, 1)
        series_form.addRow(season_episode_row)

        self.episode_title_edit = QLineEdit()
        self.episode_title_edit.setPlaceholderText(
            "wird nach KI-Prüfung / Metadaten-Erkennung angezeigt"
        )
        series_form.addRow("Episodentitel", self.episode_title_edit)
        editor_layout.addWidget(series_group)

        source_group = QGroupBox("Quelle / Zuordnung")
        source_form = QFormLayout(source_group)
        source_form.setVerticalSpacing(8)
        source_form.addRow("Kanal / Sender", self.channel_edit)
        source_form.addRow("Playlist", self.playlist_edit)
        source_form.addRow("Pfad", self.path_label)
        editor_layout.addWidget(source_group)

        editor_scroll = QScrollArea()
        editor_scroll.setWidgetResizable(True)
        editor_scroll.setFrameShape(QFrame.Shape.NoFrame)
        editor_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        editor_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        editor_scroll.setWidget(editor_group)
        left_layout.addWidget(editor_scroll, 4)

        self.diff_label = QLabel("Keine Änderungen")
        self.diff_label.setWordWrap(True)
        left_layout.addWidget(self.diff_label)

        # AI comparison panel at the bottom-left, concept-style.
        ai_compare_group = QGroupBox("KI-Metadaten-Vorschau  (nur Entwurf)")
        ai_compare_layout = QVBoxLayout(ai_compare_group)

        self.ai_metadata_preview = QTextEdit()
        self.ai_metadata_preview.setReadOnly(True)
        self.ai_metadata_preview.setMinimumHeight(120)
        self.ai_metadata_preview.setPlaceholderText(
            "Alt → Neu, Quelle, Confidence und Begründung erscheinen hier."
        )
        ai_compare_layout.addWidget(self.ai_metadata_preview)
        left_layout.addWidget(ai_compare_group, 1)
        left_layout.setStretchFactor(editor_scroll, 4)
        left_layout.setStretchFactor(ai_compare_group, 1)

        # Right sidebar: old metadata + poster + KI actions.
        right_sidebar = QWidget()
        sidebar = QVBoxLayout(right_sidebar)
        sidebar.setContentsMargins(0, 0, 0, 0)
        sidebar.setSpacing(8)

        old_group = QGroupBox("Vorhandene / alte Metadaten  (NFO / Datei)")
        old_layout = QVBoxLayout(old_group)
        self.original_metadata_preview = QTextEdit()
        self.original_metadata_preview.setReadOnly(True)
        self.original_metadata_preview.setMinimumHeight(210)
        old_layout.addWidget(self.original_metadata_preview)
        sidebar.addWidget(old_group)

        poster_group = QGroupBox("Poster  (Vorschau)")
        poster_layout = QVBoxLayout(poster_group)
        self.poster_preview = QLabel("Kein Poster")
        self.poster_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.poster_preview.setMinimumSize(220, 315)
        self.poster_preview.setMaximumSize(260, 370)
        self.poster_preview.setStyleSheet(
            "QLabel { border: 1px solid #777; background: rgba(0,0,0,0.08); }"
        )
        self.poster_preview.setToolTip(
            "Aktuelles Poster oder KI-/Online-Poster des ausgewählten Mediums"
        )
        poster_layout.addWidget(
            self.poster_preview,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        poster_layout.addStretch(1)
        sidebar.addWidget(poster_group)

        ai_action_group = QGroupBox("KI")
        ai_action_layout = QVBoxLayout(ai_action_group)
        self.btn_ai_metadata = QPushButton("KI-Metadaten prüfen")
        self.ai_metadata_status_label = QLabel("KI: wird geprüft")
        self.ai_metadata_status_label.setWordWrap(True)
        self.btn_ai_metadata.clicked.connect(self._review_metadata_with_ai)
        ai_action_layout.addWidget(self.btn_ai_metadata)
        ai_action_layout.addWidget(self.ai_metadata_status_label)
        sidebar.addWidget(ai_action_group)

        sidebar.addStretch(1)

        content_split.addWidget(left_column)
        content_split.addWidget(right_sidebar)
        content_split.setStretchFactor(0, 4)
        content_split.setStretchFactor(1, 2)
        content_split.setSizes([980, 430])

        right_layout.addWidget(content_split, 1)

        buttons = QHBoxLayout()
        self.btn_draft = QPushButton("Entwurf speichern")
        self.btn_commit = QPushButton("Metadaten übernehmen…")
        self.btn_nfo = QPushButton("NFO speichern")
        self.btn_poster = QPushButton("Poster ersetzen")
        self.btn_reset = QPushButton("Zurücksetzen")
        self.btn_draft.clicked.connect(self._save_draft)
        self.btn_commit.clicked.connect(self._commit_metadata)
        self.btn_nfo.clicked.connect(self._save_nfo)
        self.btn_poster.clicked.connect(self._replace_poster)
        self.btn_reset.clicked.connect(self._reset_fields)
        for button in (
            self.btn_draft,
            self.btn_commit,
            self.btn_nfo,
            self.btn_poster,
            self.btn_reset,
        ):
            buttons.addWidget(button)
        right_layout.addLayout(buttons)
        right_layout.addStretch(1)

        for widget in (
            self.title_edit, self.description_edit, self.series_edit,
            self.episode_title_edit,
            self.channel_edit, self.playlist_edit, self.date_edit,
        ):
            widget.textChanged.connect(self._update_diff)
        for widget in (self.year_edit, self.season_edit, self.episode_edit):
            widget.valueChanged.connect(self._update_diff)
        self.media_type_edit.currentIndexChanged.connect(self._update_diff)

        splitter.addWidget(left)
        splitter.addWidget(center)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 4)
        splitter.setSizes([170, 320, 650])
        root.addWidget(splitter, 1)
        self._refresh_ai_metadata_status()
        self.refresh()


    def refresh(self):
        from PySide6.QtWidgets import QMessageBox

        try:
            raw = (
                self.plugin.mediahub_api.get_library_videos()
                if self.plugin.mediahub_api
                else []
            )
            if isinstance(raw, dict):
                raw = raw.get("videos", raw.get("items", []))
            self._library_items = self.plugin._normalize_items(raw)
        except Exception as error:  # noqa: BLE001 - MediaHub-Bibliotheks-API-Grenze
            self._library_items = []
            QMessageBox.warning(
                self,
                "Metadata Editor",
                f"MediaHub-Bibliothek konnte nicht geladen werden:\n{error}",
            )

        self._local_sources = self.plugin._load_local_sources()
        if self._local_sources:
            try:
                self._local_items = self.plugin.scan_local_sources()
            except Exception as error:  # noqa: BLE001 - lokaler Scan-Grenze
                self._local_items = []
                QMessageBox.warning(
                    self,
                    "Metadata Editor",
                    f"Lokale Quellen konnten nicht aktualisiert werden:\n{error}",
                )
        else:
            self._local_items = []

        self._rebuild_items()
    def _rebuild_items(self):
        merged = {}
        for item in [*self._library_items, *self._local_items]:
            key = str(
                item.get("path")
                or item.get("file_path")
                or item.get("id")
                or ""
            ).casefold()
            if key and key in merged:
                # Lokale Dateidaten ergänzen bestehende MediaHub-Einträge.
                existing = merged[key]

                preserved_mediahub_id = str(
                    existing.get("mediahub_id")
                    or existing.get("video_id")
                    or (
                        existing.get("id")
                        if str(existing.get("source_type") or "")
                        != "local_folder"
                        else ""
                    )
                    or ""
                ).strip()

                existing.update(
                    {
                        k: v
                        for k, v in item.items()
                        if v not in (None, "", [], {})
                        and k not in {"mediahub_id"}
                    }
                )

                if preserved_mediahub_id:
                    existing["mediahub_id"] = preserved_mediahub_id
            else:
                merged[key or f"id:{len(merged)}"] = dict(item)
        self._items = list(merged.values())
        self._apply_filter()


    def _choose_local_folder(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        start = self._local_folder or str(self.plugin.base_dir)
        folder = QFileDialog.getExistingDirectory(
            self,
            "Medienordner hinzufügen",
            start,
        )
        if not folder:
            return

        try:
            self._local_sources = self.plugin.remember_local_source(folder)
            self._local_folder = folder
            self._local_items = self.plugin.scan_local_sources()
            self._rebuild_items()

            for row in range(self.categories.count()):
                item = self.categories.item(row)
                if item and item.text() == "Lokaler Ordner":
                    self.categories.setCurrentRow(row)
                    break

            QMessageBox.information(
                self,
                "Metadata Editor",
                (
                    f"{len(self._local_items)} lokale Mediendatei(en) aus "
                    f"{len(self._local_sources)} Quelle(n) eingelesen."
                ),
            )
        except Exception as error:  # noqa: BLE001 - GUI/Dateisystem-Grenze
            QMessageBox.warning(
                self,
                "Metadata Editor",
                f"Ordner konnte nicht eingelesen werden:\n{error}",
            )
    def _select_source_category(self, label):
        for row in range(self.categories.count()):
            item = self.categories.item(row)
            if item and item.text() == label:
                self.categories.setCurrentRow(row)
                return

    def _apply_filter(self, *args):
        query = self.search.text().strip().lower()
        category = self.categories.currentItem().text() if self.categories.currentItem() else "Alle Medien"
        drafts = self.plugin._read_drafts() if category == "Entwürfe" else {}
        self.media_list.blockSignals(True)
        self.media_list.clear()
        visible = []
        for item in self._items:
            if category == "Entwürfe" and str(item.get("id")) not in drafts:
                continue
            if category == "MediaHub / YouTube" and str(item.get("source_type") or "") == "local_folder":
                continue
            if category == "Lokaler Ordner" and str(item.get("source_type") or "") != "local_folder":
                continue
            if category == "Kanäle" and not str(item.get("channel") or "").strip():
                continue
            if category == "Serien" and not str(item.get("series") or "").strip():
                continue
            if category == "Playlists" and not str(item.get("playlist") or "").strip():
                continue
            haystack = " ".join(str(item.get(key) or "") for key in ("title", "series", "channel", "playlist", "path")).lower()
            if query and query not in haystack:
                continue
            visible.append(item)
            text = str(item.get("title") or "Ohne Titel")
            context = str(item.get("series") or item.get("channel") or item.get("playlist") or "").strip()
            if context:
                text += f"\n{context}"
            row = QListWidgetItem(text)
            row.setData(256, item)
            self.media_list.addItem(row)
        self.media_list.blockSignals(False)
        if visible:
            self.media_list.setCurrentRow(0)
        else:
            self._current = None
            self._clear_fields()

    def _load_selected(self, row):
        item = self.media_list.item(row)
        self._current = dict(item.data(256) or {}) if item is not None else None
        if not self._current:
            self._clear_fields()
            return
        draft = self.plugin._read_drafts().get(str(self._current.get("id")))
        values = dict(draft.get("edited") or {}) if draft else self._current
        self._set_fields(values)

    def _set_fields(self, item):
        self._loading = True
        self.title_edit.setText(str(item.get("title") or ""))

        media_type = str(
            item.get("media_type") or "video"
        ).strip().lower()
        index = self.media_type_edit.findData(media_type)
        self.media_type_edit.setCurrentIndex(
            max(index, 0)
        )

        self.description_edit.setPlainText(
            str(item.get("description") or "")
        )
        self._sync_description_preview()
        self.year_edit.setValue(self._number(item.get("year")))
        self.season_edit.setValue(self._number(item.get("season")))
        self.episode_edit.setValue(self._number(item.get("episode")))
        self.series_edit.setText(str(item.get("series") or ""))
        self.episode_title_edit.setText(
            str(item.get("episode_title") or "")
        )
        self.channel_edit.setText(str(item.get("channel") or ""))
        self.playlist_edit.setText(str(item.get("playlist") or ""))
        self.date_edit.setText(str(item.get("published_at") or ""))
        path = item.get("path") or item.get("file_path") or item.get("filepath") or item.get("local_path") or item.get("filename") or "-"
        self.path_label.setText(str(path))
        self._update_poster_preview(item)
        self._update_original_metadata_preview(item)
        self.ai_metadata_preview.clear()
        self._loading = False
        self._update_diff()

    def _update_poster_preview(self, item=None):
        from PySide6.QtCore import Qt

        current = dict(item or self._current or {})
        path = self.plugin._poster_path(current)

        if not path:
            self.poster_preview.clear()
            self.poster_preview.setText("Kein Poster")
            self.poster_preview.setToolTip("Für dieses Medium wurde kein Poster gefunden.")
            return

        pixmap = self._QPixmap(str(path))
        if pixmap.isNull():
            self.poster_preview.clear()
            self.poster_preview.setText("Poster\nnicht lesbar")
            self.poster_preview.setToolTip(str(path))
            return

        scaled = pixmap.scaled(
            self.poster_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.poster_preview.setText("")
        self.poster_preview.setPixmap(scaled)
        self.poster_preview.setToolTip(str(path))

    def _clear_fields(self):
        self._set_fields({})

    @staticmethod
    def _number(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def _edited(self):
        item = dict(self._current or {})
        item.update({
            "title": self.title_edit.text().strip(),
            "media_type": str(
                self.media_type_edit.currentData() or "video"
            ),
            "description": self.description_edit.toPlainText().strip(),
            "year": self.year_edit.value() or "",
            "season": self.season_edit.value(),
            "episode": self.episode_edit.value(),
            "series": self.series_edit.text().strip(),
            "episode_title": self.episode_title_edit.text().strip(),
            "channel": self.channel_edit.text().strip(),
            "playlist": self.playlist_edit.text().strip(),
            "published_at": self.date_edit.text().strip(),
        })
        return item

    def _update_diff(self, *args):
        if self._loading or not self._current:
            return
        _, _, _, changes = self.plugin._clean_changes({"id": self._current.get("id"), "original": self._current, "edited": self._edited()})
        if not changes:
            self.diff_label.setText("Keine Änderungen")
        else:
            self.diff_label.setText("Geändert: " + ", ".join(changes.keys()))

    def _update_original_metadata_preview(self, item):
        labels = (
            ("title", "Titel"),
            ("series", "Serie"),
            ("season", "Staffel"),
            ("episode", "Episode"),
            ("year", "Jahr"),
            ("description", "Beschreibung"),
            ("published_at", "Datum"),
            ("nfo_path", "NFO"),
        )
        lines = []
        for key, label in labels:
            value = (item or {}).get(key)
            if value not in (None, "", 0):
                lines.append(f"{label}: {value}")

        if not lines:
            lines.append("Keine vorhandenen Metadaten erkannt.")

        self.original_metadata_preview.setPlainText("\n".join(lines))

    def _populate_editor_from_ai(self, result):
        fields = dict(result.get("fields") or {})

        media_type = str(
            fields.get("media_type")
            or result.get("media_type")
            or ""
        ).strip().lower()

        if media_type not in {"movie", "series", "video"}:
            if (
                fields.get("series")
                or fields.get("season") not in (None, "", 0)
                or fields.get("episode") not in (None, "", 0)
            ):
                media_type = "series"
            elif str(
                fields.get("type")
                or fields.get("kind")
                or ""
            ).strip().lower() in {"movie", "film"}:
                media_type = "movie"

        if media_type in {"movie", "series", "video"}:
            index = self.media_type_edit.findData(media_type)

            if index >= 0:
                self.media_type_edit.setCurrentIndex(index)

        if "title" in fields:
            self.title_edit.setText(str(fields.get("title") or ""))
            self.episode_title_edit.setText(
                str(fields.get("episode_title") or fields.get("title") or "")
            )
        if "description" in fields:
            self.description_edit.setPlainText(
                str(fields.get("description") or "")
            )
            self._sync_description_preview()
        if "year" in fields:
            try:
                self.year_edit.setValue(int(fields.get("year") or 0))
            except (TypeError, ValueError):
                pass
        if "season" in fields:
            try:
                self.season_edit.setValue(int(fields.get("season") or 0))
            except (TypeError, ValueError):
                pass
        if "episode" in fields:
            try:
                self.episode_edit.setValue(int(fields.get("episode") or 0))
            except (TypeError, ValueError):
                pass
        if "series" in fields:
            self.series_edit.setText(str(fields.get("series") or ""))
        if "published_at" in fields:
            self.date_edit.setText(str(fields.get("published_at") or ""))

        self._update_diff()

    def _show_ai_poster_preview(self, result):
        url = str(result.get("poster_url") or "").strip()
        if not url:
            return

        try:
            path = self.plugin.cache_ai_poster(url)
        except Exception:  # noqa: BLE001 - KI-/Poster-Provider-Grenze
            path = None

        if not path:
            return

        from PySide6.QtCore import Qt

        pixmap = self._QPixmap(str(path))
        if pixmap.isNull():
            return

        scaled = pixmap.scaled(
            self.poster_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.poster_preview.setText("")
        self.poster_preview.setPixmap(scaled)
        self.poster_preview.setToolTip(
            "KI-/Online-Poster-Vorschlag\n" + url
        )

    def _sync_description_preview(self):
        value = self.description_edit.toPlainText().strip()
        compact = " ".join(value.split())
        if len(compact) > 140:
            compact = compact[:137].rstrip() + "…"
        self.description_preview.setText(compact)
        self.description_preview.setToolTip(value or "Keine Beschreibung")

    def _edit_description_dialog(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QTextEdit,
            QVBoxLayout,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Beschreibung bearbeiten")
        dialog.resize(760, 460)

        layout = QVBoxLayout(dialog)

        info = QLabel(
            "Beschreibung vollständig lesen oder bearbeiten. "
            "Mit „Übernehmen“ wird nur der aktuelle Entwurf geändert."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        editor = QTextEdit(dialog)
        editor.setPlainText(self.description_edit.toPlainText())
        editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        editor.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        editor.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        layout.addWidget(editor, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        if save_button is not None:
            save_button.setText("Übernehmen")

        cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        if cancel_button is not None:
            cancel_button.setText("Abbrechen")

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.description_edit.setPlainText(editor.toPlainText())
            self._sync_description_preview()
            self._update_diff()

    def _refresh_ai_metadata_status(self):
        status = self.plugin.ai_metadata_status()
        available = bool(status.get("available"))
        self.btn_ai_metadata.setEnabled(available)
        self.ai_metadata_status_label.setText(
            "KI: MediaHub KI-Assistent"
            if available
            else "KI: nicht verfügbar"
        )

    @staticmethod
    def _display_metadata_value(value):
        return "—" if value in (None, "", 0) else str(value)

    def _review_metadata_with_ai(self):
        from PySide6.QtWidgets import QMessageBox

        self._refresh_ai_metadata_status()
        if not self._current:
            QMessageBox.information(
                self,
                "KI-Metadaten",
                "Bitte zuerst ein Medium auswählen.",
            )
            return

        result = self.plugin.ai_metadata_review(self._current)
        if not result.get("available"):
            self.ai_metadata_preview.setPlainText(
                "\n".join(
                    map(
                        str,
                        result.get("warnings")
                        or ["KI nicht verfügbar."],
                    )
                )
            )
            return

        labels = {
            "media_type": "Medientyp",
            "series": "Serie",
            "title": "Titel / Episodentitel",
            "season": "Staffel",
            "episode": "Episode",
            "year": "Jahr",
            "description": "Beschreibung",
            "published_at": "Datum",
        }
        fields = dict(result.get("fields") or {})
        changes = dict(result.get("changes") or {})
        lines = ["KI-Metadaten-Vorschau", ""]
        ordered = (
            "media_type",
            "series",
            "season",
            "episode",
            "title",
            "year",
            "description",
            "published_at",
        )
        shown = set()

        for key in ordered:
            if key not in fields and key not in changes:
                continue
            shown.add(key)
            change = dict(changes.get(key) or {})
            old = change.get("old", self._current.get(key))
            new = change.get("new", fields.get(key))
            lines.append(
                f"{labels.get(key, key)}: "
                f"{self._display_metadata_value(old)}  →  "
                f"{self._display_metadata_value(new)}"
            )

        for key, value in fields.items():
            if key in shown:
                continue
            lines.append(
                f"{labels.get(key, key)}: "
                f"{self._display_metadata_value(self._current.get(key))}  →  "
                f"{self._display_metadata_value(value)}"
            )

        sources = list(result.get("sources") or [])
        if sources:
            lines.extend(("", "Quelle: " + ", ".join(map(str, sources))))

        lines.append(
            f"Confidence: {float(result.get('confidence') or 0.0) * 100:.0f}%"
        )

        rationale = str(result.get("rationale") or "").strip()
        if rationale:
            lines.append("Begründung: " + rationale)

        warnings = list(result.get("warnings") or [])
        if warnings:
            lines.append("Hinweise: " + "; ".join(map(str, warnings)))

        lines.extend((
            "",
            "Nur Vorschau · keine automatische Übernahme.",
            "Übernahme nur nach ausdrücklicher Bestätigung.",
        ))
        self.ai_metadata_preview.setPlainText("\n".join(lines))

        # Nur die sichtbaren Eingabefelder übernehmen. Es wird weder gespeichert
        # noch in NFO/Container geschrieben, bis der Benutzer später bestätigt.
        self._populate_editor_from_ai(result)
        self._show_ai_poster_preview(result)

    def _save_draft(self):
        if not self._current:
            return
        status, _, body = self.plugin._save_draft({"id": self._current.get("id"), "original": self._current, "edited": self._edited()})
        self._show_result(status, body)

    def _commit_metadata(self):
        from PySide6.QtWidgets import QMessageBox

        if not self._current:
            return

        edited = self._edited()
        item_id, original, _, changes = self.plugin._clean_changes(
            {
                "id": (
                    self._current.get("mediahub_id")
                    or self._current.get("video_id")
                    or self._current.get("id")
                ),
                "original": self._current,
                "edited": edited,
            }
        )
        if not item_id or not changes:
            QMessageBox.information(
                self,
                "Metadata Editor",
                "Es sind keine Metadatenänderungen vorhanden.",
            )
            return

        labels = {
            "title": "Titel",
            "media_type": "Medientyp",
            "description": "Beschreibung",
            "year": "Jahr",
            "season": "Staffel",
            "episode": "Episode",
            "episode_title": "Episodentitel",
            "series": "Serie",
            "channel": "Kanal / Sender",
            "playlist": "Playlist",
            "published_at": "Veröffentlichung / Ausstrahlung",
        }
        lines = ["Folgende Metadaten werden geschrieben:", ""]
        for field, change in changes.items():
            before = self._display_metadata_value(change.get("before"))
            after = self._display_metadata_value(change.get("after"))
            lines.append(f"{labels.get(field, field)}: {before}  →  {after}")

        lines.extend(
            (
                "",
                "Vor dem Schreiben wird ein Recovery-Eintrag erstellt.",
                "Die Änderung wird anschließend erneut aus MediaHub gelesen und geprüft.",
                "",
                "Metadaten jetzt übernehmen?",
            )
        )

        answer = QMessageBox.question(
            self,
            "Metadaten übernehmen",
            "\n".join(lines),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        status, _, body = self.plugin._commit(
            {
                "id": item_id,
                "original": original,
                "edited": edited,
                "confirmed": True,
                "confirmation_source": "human_gui",
            }
        )
        self._show_result(status, body)
        if int(status) < 400:
            self.refresh()

    def _save_nfo(self):
        if not self._current:
            return
        status, _, body = self.plugin._save_nfo({"item": self._current, "edited": self._edited()})
        self._show_result(status, body)

    def _replace_poster(self):
        from PySide6.QtWidgets import QFileDialog
        if not self._current:
            return
        filename, _ = QFileDialog.getOpenFileName(self, "Poster auswählen", "", "Bilder (*.jpg *.jpeg *.png *.webp)")
        if not filename:
            return
        status, _, body = self.plugin._replace_image({"item": self._current, "kind": "poster", "source_path": filename})
        self._show_result(status, body)
        if int(status) < 400:
            self._update_poster_preview(self._current)

    def _reset_fields(self):
        if self._current:
            self._set_fields(self._current)

    def _show_result(self, status, body):
        from PySide6.QtWidgets import QMessageBox
        try:
            data = json.loads(body.decode("utf-8"))
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            AttributeError,
        ):
            data = {"message": str(body)}
        message = str(data.get("message") or "Aktion abgeschlossen.")
        (QMessageBox.information if int(status) < 400 else QMessageBox.warning)(self, "Metadata Editor", message)
        self._update_diff()
