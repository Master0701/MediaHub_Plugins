from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from services.agents_runtime import AgentManager
from services.backends import BackendManager
from services.tasks import TaskManager, TaskState
from services.capability_manager import CapabilityManager
from services.orchestrator import LocalAIOrchestrator
from services.knowledge_database import KnowledgeDatabase
from services.knowledge_engine import KnowledgeEngine
from services.media_analyzer import MediaAnalyzer
from services.mediahub_reader import MediaHubDatabaseReader
from services.paths import resolve_database_paths
from services.tool_resolver import ToolResolver

try:
    from PySide6.QtCore import QObject, Qt, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QFileDialog,
        QHBoxLayout,
        QLabel,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    QWidget = object

try:
    from mediahub_web_core.server import acquire_shared_server, release_shared_server
    from mediahub_web_core.settings import WebRuntimeSettingsStore, connection_info
except ImportError:
    acquire_shared_server = None
    release_shared_server = None
    WebRuntimeSettingsStore = None
    connection_info = None



class WebFileDialogBridge(QObject):
    """Öffnet den nativen Qt-Dateidialog sicher im GUI-Hauptthread."""

    request_dialog = Signal()

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._path = None
        self._error = None
        self.request_dialog.connect(self._open_dialog, Qt.QueuedConnection)

    @Slot()
    def _open_dialog(self):
        try:
            parent = QApplication.activeWindow()
            path, _ = QFileDialog.getOpenFileName(
                parent,
                "Videodatei für KI-Analyse auswählen",
                "",
                "Videodateien (*.mkv *.mp4 *.avi *.mov *.m4v *.ts *.m2ts *.webm *.wmv *.mpg *.mpeg);;Alle Dateien (*.*)",
            )
            self._path = path or None
            self._error = None
        except Exception as exc:
            self._path = None
            self._error = str(exc)
        finally:
            self._event.set()

    def choose_file(self, timeout=180):
        with self._lock:
            self._event.clear()
            self._path = None
            self._error = None
            self.request_dialog.emit()
            if not self._event.wait(timeout=timeout):
                return None, "Der Dateidialog hat nicht rechtzeitig geantwortet."
            return self._path, self._error


class MediaHubAIAssistantPlugin:
    VERSION = "1.7.0"

    def __init__(self, plugin_path: str | Path, mediahub_api: Any = None, **kwargs: Any):
        self.plugin_path = Path(plugin_path)
        self.mediahub_api = mediahub_api
        self.logger = logging.getLogger("mediahub.plugins.ai_assistant")
        self.running = False
        self.server = None
        self.last_web_analyzed_path = None
        self.file_dialog_bridge = WebFileDialogBridge()
        app = QApplication.instance()
        if app is not None:
            self.file_dialog_bridge.moveToThread(app.thread())

        self.base_dir, self.mediahub_db_path, self.knowledge_db_path = (
            resolve_database_paths(self.mediahub_api, self.plugin_path)
        )
        self.knowledge = KnowledgeDatabase(self.knowledge_db_path)
        self.mediahub_reader = MediaHubDatabaseReader(self.mediahub_db_path)
        self.tool_resolver = ToolResolver(self.base_dir)
        self.capability_manager = CapabilityManager(
            self.plugin_path,
            self.tool_resolver,
        )
        self.agent_manager = AgentManager(
            self.capability_manager,
        )
        self.media_analyzer = MediaAnalyzer(self.base_dir, self.knowledge_db_path, self.plugin_path)
        self.backend_manager = BackendManager(
            self.media_analyzer,
            ai_node_config=self._resolve_ai_node_config(),
        )
        self.task_manager = TaskManager(self.backend_manager)
        self.orchestrator = LocalAIOrchestrator(
            self.capability_manager,
            self.task_manager,
        )
        self.knowledge_engine = KnowledgeEngine(self.knowledge_db_path)

        if acquire_shared_server and WebRuntimeSettingsStore:
            settings = WebRuntimeSettingsStore(self.base_dir).load()
            self.server = acquire_shared_server(
                str(self.base_dir), settings.host, settings.port
            )
            self._register_routes()

    def _resolve_ai_node_config(self) -> dict[str, Any]:
        """Liest die aktuelle AI-Node-Verbindung aus MediaHub."""

        config = {
            "host": os.getenv("MEDIAHUB_AI_NODE_HOST", ""),
            "port": int(os.getenv("MEDIAHUB_AI_NODE_PORT", "8765")),
            "api_token": os.getenv("MEDIAHUB_AI_NODE_API_TOKEN", ""),
            "timeout": 4.0,
        }

        api = self.mediahub_api
        base_dir = getattr(api, "base_dir", None) if api is not None else None

        if base_dir:
            settings_file = Path(base_dir) / "config" / "settings.json"
            try:
                settings = json.loads(
                    settings_file.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                settings = {}

            ai = settings.get("ai")
            if isinstance(ai, dict):
                config.update(
                    {
                        "host": str(
                            ai.get("node_host")
                            or ai.get("host")
                            or config["host"]
                        ).strip(),
                        "port": int(
                            ai.get("api_port")
                            or ai.get("port")
                            or config["port"]
                        ),
                        "api_token": str(
                            ai.get("api_token")
                            or config["api_token"]
                        ).strip(),
                    }
                )

        return config

    def _refresh_ai_node_backend(self) -> None:
        """Aktualisiert den AI-Node ohne Plugin-Neustart."""

        manager = getattr(self, "backend_manager", None)
        if manager is not None:
            manager.update_ai_node_config(
                self._resolve_ai_node_config()
            )


    def start(self):
        self.knowledge.initialize()
        self.knowledge_engine.ensure_schema()
        if self.server is not None:
            self.server.start()
        self.running = True
        return True

    def stop(self):
        if self.server is not None and release_shared_server is not None:
            release_shared_server(str(self.base_dir), owner=self)
        self.running = False

    def get_plugin_settings(self):
        url = "/ai-assistant"
        if connection_info and WebRuntimeSettingsStore:
            settings = WebRuntimeSettingsStore(self.base_dir).load()
            info = connection_info(settings)
            active_url = str(info.get("active_url") or "").rstrip("/")
            if active_url:
                url = f"{active_url}/ai-assistant"
        return {
            "version": self.VERSION,
            "url": url,
            "knowledge_database": str(self.knowledge_db_path),
            "mediahub_database": str(self.mediahub_db_path),
            "mediahub_database_read_only": True,
            "llm_provider": "Noch nicht eingerichtet",
            "fast_rule_engine": True,
            "sources": self.media_analyzer.source_manager.status(),
            "in_video": self.media_analyzer.in_video_agent.capabilities(),
            "quality_engine": {"implemented": True, "reference_profiles": True, "audio_quality": True},
            "decision_engine": {"schema_version": 2, "explanations": True, "conflict_detection": True},
            "fingerprints": self.media_analyzer.fingerprint_store.stats(),
            "integration_api": {"schema_version": 1, "targets": ["mediahub.metadata_editor", "mediahub.universal_renamer"]},
            "backends": self.backend_manager.status(),
            "tasks": self.task_manager.status(),
            "orchestrator": self.orchestrator.status(),
        }

    def get_status(self):
        self._refresh_ai_node_backend()
        return {
            "plugin": {
                "id": "mediahub.ai_assistant",
                "name": "MediaHub KI-Assistent",
                "version": self.VERSION,
                "running": self.running,
            },
            "paths": {
                "mediahub_base": str(self.base_dir),
                "mediahub_database": str(self.mediahub_db_path),
                "knowledge_database": str(self.knowledge_db_path),
            },
            "knowledge_database": self.knowledge.health(),
            "knowledge_engine": self.knowledge_engine.status(),
            "knowledge_engine_stats": self.knowledge_engine.stats(),
            "mediahub_database": self.mediahub_reader.status(),
            "tools": self.tool_resolver.status(),
            "capabilities": self.capability_manager.status(),
            "agents": self.agent_manager.status(),
            "sources": self.media_analyzer.source_manager.status(),
            "in_video": self.media_analyzer.in_video_agent.capabilities(),
            "quality_engine": {"implemented": True, "reference_profiles": True, "audio_quality": True},
            "decision_engine": {"schema_version": 2, "explanations": True, "conflict_detection": True},
            "fingerprints": self.media_analyzer.fingerprint_store.stats(),
            "integration_api": {"schema_version": 1, "targets": ["mediahub.metadata_editor", "mediahub.universal_renamer"]},
            "backends": self.backend_manager.status(),
            "tasks": self.task_manager.status(),
            "orchestrator": self.orchestrator.status(),
            "performance": {
                "sqlite_wal": True,
                "indexed_core_tables": True,
                "read_only_mediahub_access": True,
                "llm_required_for_basic_queries": False,
            },
        }


    @staticmethod
    def format_analysis_summary(result):
        identification = result.get("identification") or {}
        summary = result.get("summary") or {}
        cache = result.get("cache") or {}
        warnings = result.get("warnings") or []

        duration = summary.get("duration_seconds")
        duration_text = "-"
        if duration is not None:
            total = round(float(duration))
            duration_text = f"{total // 60:02d}:{total % 60:02d} Minuten"

        lines = [
            "ERKENNUNGSVORSCHLAG",
            "-------------------",
            f"Typ: {identification.get('media_type') or '-'}",
            f"Titel: {identification.get('title_candidate') or '-'}",
            f"Staffel: {identification.get('season') or '-'}",
            f"Folge(n): {', '.join(str(v) for v in (identification.get('episodes') or [])) or identification.get('episode') or '-'}",
            f"Jahr: {identification.get('year') or '-'}",
            f"Fassung(en): {', '.join(identification.get('edition_candidates') or []) or identification.get('edition_candidate') or '-'}",
            f"Begründung: {', '.join(identification.get('reasons') or []) or '-'}",
            f"Sicherheit Dateiname: {round(float(identification.get('confidence') or 0) * 100)} %",
            "",
            "KI-ENTSCHEIDUNG",
            "---------------",
            f"Status: {(result.get('decision') or {}).get('status') or '-'}",
            f"Gesamtsicherheit: {(result.get('decision') or {}).get('confidence_percent') or '-'} %",
            f"Vertrauen: {(result.get('decision') or {}).get('trust_label') or '-'}",
            f"Unabhängige Bestätigungen: {(result.get('decision') or {}).get('independent_confirmations', 0)}",
            f"Empfehlung: {(result.get('decision') or {}).get('recommendation') or '-'}",
            f"Warum: {((result.get('decision') or {}).get('explanation') or {}).get('conclusion') or '-'}",
            *[f"- {text}" for text in (((result.get('decision') or {}).get('explanation') or {}).get('why') or [])],
            *(["Noch nicht eindeutig:"] + [f"- {text}" for text in (((result.get('decision') or {}).get('explanation') or {}).get('limitations') or [])] if (((result.get('decision') or {}).get('explanation') or {}).get('limitations') or []) else []),
            *(["Widersprüche:"] + [
                f"- {item.get('left_source')}: {item.get('left_value')} <> {item.get('right_source')}: {item.get('right_value')}"
                for item in ((result.get('decision') or {}).get('conflicts') or [])
            ] if ((result.get('decision') or {}).get('conflicts') or []) else []),
            "",
            "KI-BEWEISE",
            "-----------",
            *[
                f"{'✔' if item.get('supports') else '○'} {item.get('label')}: {item.get('value')} "
                f"({item.get('confidence_percent')} %, Gewicht {round(float(item.get('weight') or 0) * 100)} %)"
                for item in ((result.get('decision') or {}).get('all_evidence') or [])
            ],
            "",
            "TECHNISCHE DATEN",
            "-----------------",
            f"Laufzeit: {duration_text}",
            f"Container: {summary.get('container') or '-'}",
            f"Video: {summary.get('video_codec') or '-'}",
            f"Auflösung: {summary.get('width') or '-'} × {summary.get('height') or '-'}",
            f"HDR/Dolby Vision: {summary.get('hdr_format') or '-'}",
            f"Tonspuren: {summary.get('audio_tracks', 0)}",
            f"Untertitel: {summary.get('subtitle_tracks', 0)}",
            f"Kapitel: {summary.get('chapters', 0)}",
            "",
            "QUALITÄTSBEWERTUNG",
            "-------------------",
            f"Gesamt: {(result.get('quality') or {}).get('overall_score') or '-'} %",
            f"Bild: {((result.get('quality') or {}).get('video') or {}).get('score') or '-'} %",
            f"Ton: {((result.get('quality') or {}).get('audio') or {}).get('score') or '-'} %",
            f"Status: {(result.get('quality') or {}).get('label') or '-'}",
            "",
            "IN-VIDEO-ANALYSE",
            "-----------------",
            f"Status: {(result.get('in_video') or {}).get('state') or '-'}",
            f"Ausgeführte Agenten: {(result.get('in_video') or {}).get('completed_agents', 0)}",
            *[f"{name}: {(data or {}).get('state', '-')}" for name, data in (((result.get('in_video') or {}).get('agents') or {}).items())],
            "",
            "ANALYSEWEG",
            "-----------",
            f"Cache: {'verwendet' if cache.get('hit') else 'neu analysiert'}",
            f"Cache-Zeitpunkt: {cache.get('analyzed_at') or '-'}",
            f"Werkzeuge: {', '.join(result.get('methods_used') or [])}",
            *[f"{item.get('source')}: {item.get('status')} – {item.get('detail')}" for item in (result.get('evidence') or [])],
            "",
            "WARNUNGEN",
            "---------",
            *(warnings or ["Keine"]),
        ]
        return "\n".join(lines)


    def register_fingerprint_reference(self, analysis):
        """Speichert einen vom Benutzer bestätigten Fingerprint als lokale Referenz."""
        return self.media_analyzer.register_fingerprint_reference(analysis)

    def get_integration_payload(self, analysis):
        """Stabile Übergabe an Metadata Editor und Universal Renamer."""
        return self.media_analyzer.export_integration_payload(analysis)

    def analyze_media_file(self, file_path, force=False):
        self._refresh_ai_node_backend()

        execution = self.orchestrator.run(
            "media.analyze",
            {
                "file_path": str(file_path),
                "force": bool(force),
            },
        )

        result = dict(execution.get("result") or {})
        result["orchestration"] = dict(
            execution.get("orchestration") or {}
        )
        return result

    def clear_analysis_cache(self, file_path=None):
        if file_path:
            return self.media_analyzer.clear_cache_for(file_path)
        return self.media_analyzer.clear_cache()

    def create_widget(self, parent=None):
        """Erzeugt die normale Plugin-Oberfläche für MediaHub."""
        return AIAssistantWidget(self, parent=parent)

    def create_window(self, parent=None):
        """Erzeugt ein echtes, eigenständiges Desktop-Fenster.

        Neuere MediaHub-Versionen verwenden diese Methode bevorzugt für
        Plugins mit ``ui.type = window``. Ältere Versionen fallen weiterhin
        auf ``create_widget`` zurück.
        """
        window = QWidget(parent, Qt.WindowType.Window)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        window.setWindowTitle(f"MediaHub KI-Assistent {self.VERSION}")
        window.resize(1420, 860)
        window.setMinimumSize(1000, 650)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(AIAssistantWidget(self, parent=window), 1)
        return window

    def create_settings_widget(self, parent=None):
        """Plugin-spezifische Einstellungen für das Plugin Center."""
        return AIAssistantSettingsWidget(self, parent=parent)

    def _register_routes(self):
        self.server.add_route("/ai-assistant", self._index, owner=self)
        self.server.add_route("/ai-assistant/", self._index, owner=self)
        self.server.add_route("/ai-assistant/api/status", self._status, owner=self)
        self.server.add_route("/ai-assistant/api/analyze", self._analyze_path, owner=self)
        self.server.add_route("/ai-assistant/api/open-file", self._open_file, owner=self)
        self.server.add_route("/ai-assistant/api/open-last", self._open_last_file, owner=self)
        self.server.add_route("/ai-assistant/api/files", self._browse_files, owner=self)
        self.server.add_route("/ai-assistant/api/analyze-selected", self._analyze_selected, owner=self)
        self.server.add_route("/ai-assistant/api/native-select", self._native_select_and_analyze, owner=self)
        self.server.add_route("/ai-assistant/api/knowledge/search", self._knowledge_search, owner=self)
        self.server.add_route("/ai-assistant/api/knowledge/seed", self._knowledge_seed, owner=self)
        self.server.add_route("/ai-assistant/api/knowledge/index", self._knowledge_index, owner=self)

    def _index(self, request=None):
        return (
            200,
            "text/html; charset=utf-8",
            (self.plugin_path / "index.html").read_bytes(),
        )





    def _native_select_and_analyze(self, request=None):
        app = QApplication.instance()
        if app is None:
            payload = {"error": "Die MediaHub-Oberfläche ist nicht verfügbar."}
            status = 500
        else:
            path, error = self.file_dialog_bridge.choose_file()
            if error:
                payload = {"error": error}
                status = 500
            elif not path:
                payload = {"cancelled": True, "message": "Keine Datei ausgewählt."}
                status = 200
            else:
                try:
                    payload = self.analyze_media_file(path)
                    self.last_web_analyzed_path = str(Path(path))
                    status = 200
                except Exception as exc:
                    payload = {"error": str(exc), "path": path}
                    status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    @staticmethod
    def _request_query_value(request, key):
        from urllib.parse import parse_qs, unquote_plus, urlparse

        visited = set()

        def parse_string(value):
            if not isinstance(value, str):
                return None
            try:
                query = urlparse(value).query
                if not query and "?" in value:
                    query = value.split("?", 1)[1]
                if query:
                    parsed = parse_qs(query, keep_blank_values=True)
                    if parsed.get(key):
                        return unquote_plus(str(parsed[key][0]))
            except Exception:
                return None
            return None

        def walk(value, depth=0):
            if value is None or depth > 4:
                return None

            ident = id(value)
            if ident in visited:
                return None
            visited.add(ident)

            if isinstance(value, str):
                return parse_string(value)

            if isinstance(value, dict):
                if key in value:
                    found = value.get(key)
                    if isinstance(found, list):
                        found = found[0] if found else None
                    if found is not None:
                        return str(found)
                for nested in value.values():
                    found = walk(nested, depth + 1)
                    if found is not None:
                        return found
                return None

            if isinstance(value, (list, tuple)):
                for nested in value:
                    found = walk(nested, depth + 1)
                    if found is not None:
                        return found
                return None

            try:
                attrs = vars(value)
            except Exception:
                attrs = {}

            preferred = (
                "query", "query_params", "params", "args", "url", "path",
                "raw_path", "target", "request_target", "scope", "request"
            )
            for name in preferred:
                if name in attrs:
                    found = walk(attrs[name], depth + 1)
                    if found is not None:
                        return found

            for nested in attrs.values():
                found = walk(nested, depth + 1)
                if found is not None:
                    return found

            return parse_string(str(value))

        return walk(request)


    @staticmethod
    def _windows_roots():
        import string

        roots = []
        for letter in string.ascii_uppercase:
            path = Path(f"{letter}:\\")
            try:
                if path.exists():
                    roots.append(path)
            except OSError:
                continue
        return roots

    @staticmethod
    def _video_extensions():
        return {
            ".mkv", ".mp4", ".avi", ".mov", ".m4v", ".ts", ".m2ts",
            ".webm", ".wmv", ".mpg", ".mpeg"
        }

    def _browse_files(self, request=None):
        raw_path = self._request_query_value(request, "path")

        try:
            if not raw_path:
                payload = {
                    "kind": "roots",
                    "current": None,
                    "parent": None,
                    "entries": [
                        {
                            "name": str(root),
                            "path": str(root),
                            "type": "directory",
                        }
                        for root in self._windows_roots()
                    ],
                }
            else:
                current = Path(raw_path)
                if not current.exists() or not current.is_dir():
                    raise NotADirectoryError(current)

                entries = []
                try:
                    children = sorted(
                        current.iterdir(),
                        key=lambda p: (not p.is_dir(), p.name.lower())
                    )
                except PermissionError:
                    raise PermissionError(f"Kein Zugriff auf: {current}")

                for child in children:
                    try:
                        if child.is_dir():
                            entries.append({
                                "name": child.name,
                                "path": str(child),
                                "type": "directory",
                            })
                        elif child.is_file() and child.suffix.lower() in self._video_extensions():
                            entries.append({
                                "name": child.name,
                                "path": str(child),
                                "type": "file",
                                "size_bytes": child.stat().st_size,
                            })
                    except (OSError, PermissionError):
                        continue

                parent = None
                try:
                    if current.parent != current:
                        parent = str(current.parent)
                except Exception:
                    parent = None

                payload = {
                    "kind": "directory",
                    "current": str(current),
                    "parent": parent,
                    "entries": entries,
                }
            status = 200
        except Exception as exc:
            payload = {"error": str(exc), "path": raw_path}
            status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _analyze_selected(self, request=None):
        raw_path = self._request_query_value(request, "path")
        if not raw_path:
            payload = {"error": "Keine Videodatei ausgewählt."}
            status = 400
        else:
            try:
                path = Path(raw_path)
                if not path.is_file():
                    raise FileNotFoundError(path)
                if path.suffix.lower() not in self._video_extensions():
                    raise ValueError("Die ausgewählte Datei ist keine unterstützte Videodatei.")
                payload = self.analyze_media_file(path)
                self.last_web_analyzed_path = str(path)
                status = 200
            except Exception as exc:
                payload = {"error": str(exc), "path": raw_path}
                status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _analyze_path(self, request=None):
        raw_path = self._request_query_value(request, "path")
        if not raw_path:
            return (
                400,
                "application/json; charset=utf-8",
                json.dumps(
                    {"error": "Kein Dateipfad angegeben.", "request_type": type(request).__name__},
                    ensure_ascii=False
                ).encode("utf-8"),
            )

        try:
            result = self.analyze_media_file(raw_path)
            self.last_web_analyzed_path = str(Path(raw_path))
            status = 200
        except Exception as exc:
            result = {"error": str(exc), "path": raw_path}
            status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(result, ensure_ascii=False).encode("utf-8"),
        )


    def _open_last_file(self, request=None):
        raw_path = self.last_web_analyzed_path
        if not raw_path:
            payload = {"error": "Es wurde noch keine Datei erfolgreich analysiert."}
            status = 400
        else:
            try:
                path = Path(raw_path)
                if not path.is_file():
                    raise FileNotFoundError(path)
                if hasattr(os, "startfile"):
                    os.startfile(str(path))
                else:
                    raise RuntimeError("Datei öffnen wird auf diesem System nicht unterstützt.")
                payload = {"ok": True, "path": str(path)}
                status = 200
            except Exception as exc:
                payload = {"error": str(exc), "path": raw_path}
                status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _open_file(self, request=None):
        raw_path = self._request_query_value(request, "path")
        if not raw_path:
            payload = {"error": "Kein Dateipfad angegeben."}
            status = 400
        else:
            try:
                path = Path(raw_path)
                if not path.is_file():
                    raise FileNotFoundError(path)
                if hasattr(os, "startfile"):
                    os.startfile(str(path))
                else:
                    raise RuntimeError("Datei öffnen wird auf diesem System nicht unterstützt.")
                payload = {"ok": True, "path": str(path)}
                status = 200
            except Exception as exc:
                payload = {"error": str(exc), "path": raw_path}
                status = 400

        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )



    def _knowledge_index(self, request=None):
        try:
            payload = {
                "results": self.knowledge_engine.all_items(),
                "stats": self.knowledge_engine.stats(),
            }
            status = 200
        except Exception as exc:
            payload = {"error": str(exc)}
            status = 400
        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _knowledge_search(self, request=None):
        query = self._request_query_value(request, "q")
        try:
            payload = {
                "query": query or "",
                "results": self.knowledge_engine.search(query or ""),
                "stats": self.knowledge_engine.stats(),
            }
            status = 200
        except Exception as exc:
            payload = {"error": str(exc), "query": query}
            status = 400
        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _knowledge_seed(self, request=None):
        try:
            created = self.knowledge_engine.seed_demo_data()
            payload = {
                "ok": True,
                "created": created,
                "stats": self.knowledge_engine.stats(),
            }
            status = 200
        except Exception as exc:
            payload = {"error": str(exc)}
            status = 400
        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _status(self, request=None):
        return (
            200,
            "application/json; charset=utf-8",
            json.dumps(self.get_status(), ensure_ascii=False).encode("utf-8"),
        )


class AIAssistantSettingsWidget(QWidget):
    """Einstellungen des KI-Assistenten im Plugin Center."""

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        title = QLabel("Analyse-Cache")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        hint = QLabel(
            "Bereits analysierte, unveränderte Dateien werden aus dem Cache geladen. "
            "Nach dem Löschen wird die nächste Analyse vollständig neu ausgeführt."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.status = QLabel()
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        buttons = QHBoxLayout()
        refresh = QPushButton("Cache-Status aktualisieren")
        refresh.clicked.connect(self.refresh_status)
        buttons.addWidget(refresh)

        clear = QPushButton("Gesamten Analyse-Cache löschen")
        clear.clicked.connect(self.clear_cache)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        root.addLayout(buttons)
        root.addStretch(1)
        self.refresh_status()

    def refresh_status(self):
        try:
            db_path = Path(self.plugin.knowledge_db_path)
            count = 0
            if db_path.exists():
                import sqlite3
                with sqlite3.connect(db_path, timeout=5.0) as db:
                    row = db.execute(
                        "SELECT COUNT(*) FROM identification_cache"
                    ).fetchone()
                    count = int(row[0] if row else 0)
            self.status.setText(
                f"Gespeicherte Analysen: {count}\n"
                f"Cache-Datenbank: {db_path}"
            )
        except Exception as exc:
            self.status.setText(f"Cache-Status konnte nicht gelesen werden: {exc}")

    def clear_cache(self):
        answer = QMessageBox.question(
            self,
            "Analyse-Cache löschen",
            "Sollen wirklich alle gespeicherten Dateianalysen gelöscht werden?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted = int(self.plugin.clear_analysis_cache() or 0)
            QMessageBox.information(
                self,
                "Analyse-Cache",
                f"Der Analyse-Cache wurde gelöscht. Entfernte Einträge: {deleted}",
            )
            self.refresh_status()
        except Exception as exc:
            QMessageBox.warning(self, "Analyse-Cache", str(exc))


class AIAssistantWidget(QWidget):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.last_analyzed_path = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("MediaHub KI-Assistent")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            "Schnelle lokale Wissensdatenbank und Vorbereitung der "
            "Film-, Serien- und Editionserkennung."
        )
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)

        status_page = QWidget()
        status_layout = QVBoxLayout(status_page)
        self.status_text = QPlainTextEdit()
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        tabs.addTab(status_page, "Systemstatus")

        capability_page = QWidget()
        capability_layout = QVBoxLayout(capability_page)

        capability_hint = QLabel(
            "Übersicht über Backends, KI-Fähigkeiten und benötigte Werkzeuge."
        )
        capability_hint.setWordWrap(True)
        capability_layout.addWidget(capability_hint)

        self.capability_status_text = QPlainTextEdit()
        self.capability_status_text.setReadOnly(True)
        capability_layout.addWidget(self.capability_status_text, 1)

        tabs.addTab(capability_page, "Backends & Fähigkeiten")

        roadmap = QPlainTextEdit()
        roadmap.setReadOnly(True)
        roadmap.setPlainText(
            "Nächste Entwicklungsschritte:\n\n"
            "• Such- und Beziehungs-Engine\n"
            "• Bestandsvergleich mit MediaHub\n"
            "• gestufte Videodatei-Analyse\n"
            "• Film-/Serien- und Editionserkennung\n"
            "• optionaler austauschbarer KI-Provider\n\n"
            "Einfache Abfragen laufen ohne Sprachmodell."
        )
        roadmap_page = QWidget()
        roadmap_layout = QVBoxLayout(roadmap_page)
        roadmap_layout.addWidget(roadmap)
        tabs.addTab(roadmap_page, "Ausbauplan")

        knowledge_page = QWidget()
        knowledge_layout = QVBoxLayout(knowledge_page)
        knowledge_hint = QLabel(
            "Durchsuche die lokale Wissensdatenbank nach Titeln, Aliasnamen "
            "und Beziehungen."
        )
        knowledge_hint.setWordWrap(True)
        knowledge_layout.addWidget(knowledge_hint)

        knowledge_buttons = QHBoxLayout()
        self.knowledge_query = QPlainTextEdit()
        self.knowledge_query.setMaximumHeight(54)
        self.knowledge_query.setPlaceholderText("Zum Beispiel: 12 Monkeys")
        knowledge_buttons.addWidget(self.knowledge_query, 1)

        search_button = QPushButton("Wissen durchsuchen")
        search_button.clicked.connect(self.search_knowledge)
        knowledge_buttons.addWidget(search_button)

        seed_button = QPushButton("Testdaten anlegen")
        seed_button.clicked.connect(self.seed_knowledge)
        knowledge_buttons.addWidget(seed_button)
        knowledge_layout.addLayout(knowledge_buttons)

        self.knowledge_text = QPlainTextEdit()
        self.knowledge_text.setReadOnly(True)
        knowledge_layout.addWidget(self.knowledge_text, 1)
        tabs.addTab(knowledge_page, "Wissenssuche")

        analysis_page = QWidget()
        analysis_layout = QVBoxLayout(analysis_page)
        analysis_hint = QLabel(
            "Wähle eine Videodatei. Version 0.2.0 liest technische Daten über "
            "MediaInfo und ffprobe aus; eine Titelidentifikation folgt später."
        )
        analysis_hint.setWordWrap(True)
        analysis_layout.addWidget(analysis_hint)
        analysis_buttons = QHBoxLayout()
        choose = QPushButton("Videodatei analysieren")
        choose.clicked.connect(self.choose_media_file)
        analysis_buttons.addWidget(choose)
        self.open_file_button = QPushButton("Datei öffnen")
        self.open_file_button.setEnabled(False)
        self.open_file_button.clicked.connect(self.open_last_file)
        analysis_buttons.addWidget(self.open_file_button)
        analysis_buttons.addStretch(1)
        analysis_layout.addLayout(analysis_buttons)
        self.analysis_text = QPlainTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text, 1)
        tabs.addTab(analysis_page, "Dateianalyse")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        refresh = QPushButton("Status aktualisieren")
        refresh.clicked.connect(self.refresh_status)
        buttons.addWidget(refresh)
        root.addLayout(buttons)

        self.refresh_status()

    def choose_media_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Videodatei auswählen",
            "",
            "Videodateien (*.mkv *.mp4 *.avi *.mov *.m4v *.ts *.m2ts *.webm *.wmv *.mpg *.mpeg);;Alle Dateien (*.*)",
        )
        if not path:
            return
        try:
            result = self.plugin.analyze_media_file(path)
            self.last_analyzed_path = path
            self.open_file_button.setEnabled(True)
        except Exception as exc:
            self.analysis_text.setPlainText(f"Analysefehler:\n{exc}")
            return
        text = self.plugin.format_analysis_summary(result)
        text += "\n\nROHDATEN\n--------\n"
        text += json.dumps(result, ensure_ascii=False, indent=2)
        self.analysis_text.setPlainText(text)

    def seed_knowledge(self):
        try:
            result = self.plugin.knowledge_engine.seed_demo_data()
            self.knowledge_text.setPlainText(
                "Testdaten wurden angelegt.\n\n"
                + json.dumps(result, ensure_ascii=False, indent=2)
            )
        except Exception as exc:
            self.knowledge_text.setPlainText(f"Fehler:\n{exc}")

    def search_knowledge(self):
        query = self.knowledge_query.toPlainText().strip()
        if not query:
            self.knowledge_text.setPlainText("Bitte einen Suchbegriff eingeben.")
            return
        try:
            result = self.plugin.knowledge_engine.search(query)
            self.knowledge_text.setPlainText(
                json.dumps(result, ensure_ascii=False, indent=2)
            )
        except Exception as exc:
            self.knowledge_text.setPlainText(f"Fehler:\n{exc}")

    def open_last_file(self):
        if not self.last_analyzed_path:
            return
        try:
            if hasattr(os, "startfile"):
                os.startfile(self.last_analyzed_path)
            else:
                raise RuntimeError("Datei öffnen wird auf diesem System nicht unterstützt.")
        except Exception as exc:
            self.analysis_text.appendPlainText(f"\nDatei konnte nicht geöffnet werden: {exc}")

    @staticmethod
    def _tool_line(tool_id, item):
        installed = bool((item or {}).get("installed"))
        required = bool((item or {}).get("required"))
        marker = "✔" if installed else "✖"
        kind = "Pflichtwerkzeug" if required else "optional"
        path = (item or {}).get("path")
        suffix = f" – {path}" if path else ""
        return f"{marker} {tool_id} ({kind}){suffix}"

    @staticmethod
    def _capability_label(capability_id):
        labels = {
            "fingerprint.register": "Fingerprint-Referenzen",
            "knowledge.search": "Wissensdatenbank",
            "media.basic_analysis": "Basis-Medienanalyse",
            "media.frame_analysis": "Frame- und Bildanalyse",
            "media.mkv_analysis": "MKV-Analyse",
            "media.mkv_editing": "MKV-Bearbeitung",
            "media.ocr": "Texterkennung im Video (OCR)",
            "quality.evaluate": "Qualitätsbewertung",
        }
        return labels.get(capability_id, capability_id)

    @staticmethod
    def _format_value(value, suffix=""):
        if value is None:
            return "-"
        return f"{value}{suffix}"

    def _format_ai_node_details(self, metadata):
        plugins = dict(metadata.get("plugins") or {})
        system = dict(metadata.get("system") or {})

        return [
            "",
            "AI-NODE-DETAILS",
            "===============",
            f"Adresse: {metadata.get('host') or '-'}",
            f"API-Port: {metadata.get('port') or '-'}",
            f"Version: {metadata.get('version') or '-'}",
            "Antwortzeit: "
            + self._format_value(metadata.get("latency_ms"), " ms"),
            f"API-Status: {metadata.get('status') or '-'}",
            "",
            "AI-Plugins:",
            f"  Erkannt: {plugins.get('detected', 0)}",
            f"  Aktiviert: {plugins.get('enabled', 0)}",
            f"  Geladen: {plugins.get('loaded', 0)}",
            f"  Fehler: {plugins.get('errors', 0)}",
            "",
            "System:",
            "  CPU: "
            + self._format_value(system.get("cpu_percent"), " %"),
            "  RAM-Auslastung: "
            + self._format_value(system.get("memory_percent"), " %"),
            "  RAM verfügbar: "
            + self._format_value(system.get("memory_available_gb"), " GB"),
            "  Datenträger-Auslastung: "
            + self._format_value(system.get("disk_percent"), " %"),
            "  Datenträger frei: "
            + self._format_value(system.get("disk_free_gb"), " GB"),
            "  Temperatur: "
            + self._format_value(system.get("temperature_c"), " °C"),
        ]

    @staticmethod
    def _capability_label(capability_id):
        labels = {
            "fingerprint.register": "Fingerprint-Referenzen",
            "knowledge.search": "Wissensdatenbank",
            "media.basic_analysis": "Basis-Medienanalyse",
            "media.frame_analysis": "Frame- und Bildanalyse",
            "media.mkv_analysis": "MKV-Analyse",
            "media.mkv_editing": "MKV-Bearbeitung",
            "media.ocr": "Texterkennung im Video (OCR)",
            "quality.evaluate": "Qualitätsbewertung",
        }
        return labels.get(capability_id, capability_id)

    @staticmethod
    def _format_value(value, suffix=""):
        if value is None:
            return "-"
        return f"{value}{suffix}"

    def _format_ai_node_details(self, metadata):
        plugins = dict(metadata.get("plugins") or {})
        system = dict(metadata.get("system") or {})

        return [
            "",
            "AI-NODE-DETAILS",
            "===============",
            f"Adresse: {metadata.get('host') or '-'}",
            f"API-Port: {metadata.get('port') or '-'}",
            f"Version: {metadata.get('version') or '-'}",
            "Antwortzeit: "
            + self._format_value(metadata.get("latency_ms"), " ms"),
            f"API-Status: {metadata.get('status') or '-'}",
            "",
            "AI-Plugins:",
            f"  Erkannt: {plugins.get('detected', 0)}",
            f"  Aktiviert: {plugins.get('enabled', 0)}",
            f"  Geladen: {plugins.get('loaded', 0)}",
            f"  Fehler: {plugins.get('errors', 0)}",
            "",
            "System:",
            "  CPU: "
            + self._format_value(system.get("cpu_percent"), " %"),
            "  RAM-Auslastung: "
            + self._format_value(system.get("memory_percent"), " %"),
            "  RAM verfügbar: "
            + self._format_value(system.get("memory_available_gb"), " GB"),
            "  Datenträger-Auslastung: "
            + self._format_value(system.get("disk_percent"), " %"),
            "  Datenträger frei: "
            + self._format_value(system.get("disk_free_gb"), " GB"),
            "  Temperatur: "
            + self._format_value(system.get("temperature_c"), " °C"),
        ]

    @staticmethod
    def _capability_label(capability_id):
        labels = {
            "fingerprint.register": "Fingerprint-Referenzen",
            "knowledge.search": "Wissensdatenbank",
            "media.basic_analysis": "Basis-Medienanalyse",
            "media.frame_analysis": "Frame- und Bildanalyse",
            "media.mkv_analysis": "MKV-Analyse",
            "media.mkv_editing": "MKV-Bearbeitung",
            "media.ocr": "Texterkennung im Video (OCR)",
            "quality.evaluate": "Qualitätsbewertung",
        }
        return labels.get(capability_id, capability_id)

    @staticmethod
    def _format_value(value, suffix=""):
        if value is None:
            return "-"
        return f"{value}{suffix}"

    def _format_ai_node_details(self, metadata):
        plugins = dict(metadata.get("plugins") or {})
        system = dict(metadata.get("system") or {})

        return [
            "",
            "AI-NODE-DETAILS",
            "===============",
            f"Adresse: {metadata.get('host') or '-'}",
            f"API-Port: {metadata.get('port') or '-'}",
            f"Version: {metadata.get('version') or '-'}",
            "Antwortzeit: "
            + self._format_value(metadata.get("latency_ms"), " ms"),
            f"API-Status: {metadata.get('status') or '-'}",
            "",
            "AI-Plugins:",
            f"  Erkannt: {plugins.get('detected', 0)}",
            f"  Aktiviert: {plugins.get('enabled', 0)}",
            f"  Geladen: {plugins.get('loaded', 0)}",
            f"  Fehler: {plugins.get('errors', 0)}",
            "",
            "System:",
            "  CPU: "
            + self._format_value(system.get("cpu_percent"), " %"),
            "  RAM-Auslastung: "
            + self._format_value(system.get("memory_percent"), " %"),
            "  RAM verfügbar: "
            + self._format_value(system.get("memory_available_gb"), " GB"),
            "  Datenträger-Auslastung: "
            + self._format_value(system.get("disk_percent"), " %"),
            "  Datenträger frei: "
            + self._format_value(system.get("disk_free_gb"), " GB"),
            "  Temperatur: "
            + self._format_value(system.get("temperature_c"), " °C"),
        ]

    def _format_capability_status(self, status):
        lines = ["BACKENDS", "========"]
        ai_node_metadata = None

        backend_status = status.get("backends") or {}
        backends = backend_status.get("backends") or []

        if not backends:
            lines.append("Keine Backend-Informationen vorhanden.")
        else:
            for backend in backends:
                marker = "✔" if backend.get("available") else "✖"
                name = backend.get("name") or backend.get("id") or "-"
                lines.append(f"{marker} {name}")

                message = backend.get("message") or ""
                if message:
                    lines.append(f"    {message}")

                if backend.get("id") == "ai_node":
                    ai_node_metadata = dict(
                        backend.get("metadata") or {}
                    )

        if ai_node_metadata and ai_node_metadata.get("version"):
            lines.extend(
                self._format_ai_node_details(ai_node_metadata)
            )

        lines.extend(["", "FÄHIGKEITEN", "============"])
        capability_status = status.get("capabilities") or {}
        capabilities = capability_status.get("capabilities") or {}

        if not capabilities:
            lines.append("Keine Capability-Informationen vorhanden.")
        else:
            for capability_id, item in sorted(capabilities.items()):
                marker = "✔" if (item or {}).get("available") else "✖"
                lines.append(
                    f"{marker} {self._capability_label(capability_id)}"
                )

                missing = list((item or {}).get("missing_tools") or [])
                if missing:
                    lines.append(
                        "    Fehlende Werkzeuge: " + ", ".join(missing)
                    )

        summary = capability_status.get("summary") or {}
        if summary:
            lines.extend([
                "",
                "Zusammenfassung:",
                f"  Verfügbar: {summary.get('available', 0)}",
                f"  Nicht verfügbar: {summary.get('unavailable', 0)}",
            ])

        lines.extend(["", "WERKZEUGE", "========="])
        tools = capability_status.get("tools") or {}

        if not tools:
            lines.append("Keine Werkzeugdaten vorhanden.")
        else:
            for tool_id, item in sorted(tools.items()):
                lines.append(self._tool_line(tool_id, item))

        required_missing = list(
            capability_status.get("required_missing") or []
        )
        optional_missing = list(
            capability_status.get("optional_missing") or []
        )

        if required_missing:
            lines.extend([
                "",
                "Fehlende Pflichtwerkzeuge:",
                *[f"  - {tool_id}" for tool_id in required_missing],
            ])

        if optional_missing:
            lines.extend([
                "",
                "Fehlende optionale Werkzeuge:",
                *[f"  - {tool_id}" for tool_id in optional_missing],
            ])

        lines.extend(["", "TASKS", "====="])
        tasks = status.get("tasks") or {}
        lines.append(f"Gesamt: {tasks.get('total', 0)}")
        lines.append(f"Laufend: {tasks.get('running', 0)}")
        lines.append(f"Erfolgreich: {tasks.get('completed', 0)}")
        lines.append(f"Fehlgeschlagen: {tasks.get('failed', 0)}")

        history = list(tasks.get("history") or [])
        if history:
            latest = history[0]
            lines.extend([
                "",
                "Letzter Auftrag:",
                f"  Typ: {latest.get('task_type') or '-'}",
                f"  Status: {latest.get('state') or '-'}",
                f"  Backend: {latest.get('selected_backend') or '-'}",
                f"  Task-ID: {latest.get('id') or '-'}",
            ])

        return "\n".join(lines)

    def refresh_status(self):
        status = self.plugin.get_status()
        self.status_text.setPlainText(
            json.dumps(status, ensure_ascii=False, indent=2)
        )
        if hasattr(self, "capability_status_text"):
            self.capability_status_text.setPlainText(
                self._format_capability_status(status)
            )


Plugin = MediaHubAIAssistantPlugin
