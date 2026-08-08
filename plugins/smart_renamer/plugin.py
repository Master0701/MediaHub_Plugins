from __future__ import annotations

import json
from pathlib import Path
from services.naming_profiles import NamingProfileService
from services.relation_preview_service import RelationPreviewService
from services.interactive_preview_service import InteractivePreviewService
from services.preview_decisions import PreviewDecisionStore
from services.gui_preview_session import GUIPreviewSession
from services.optional_preview_integrations import OptionalPreviewIntegrations
from services.review_service import ReviewService
from services.ai_review_bridge import AIReviewBridge
from services.decision_fusion import DecisionFusionService
from services.preview_presentation import PreviewPresentationService
from services.web_picker_service import WindowsWebPathPicker
from typing import Any

from services.backend_registry import RenamerBackendRegistry
from services.preview_service import RenamePreviewService
from services.profile_service import ProfileService
from services.learning_store import LearningStore
from services.optional_integrations import OptionalIntegrationManager
from services.rename_plan import RenamePlanService
from services.transaction_service import RenameTransactionService


class MediaHubSmartRenamerPlugin:
    """Windows-Smart-Renamer mit Desktop- und lokaler Weboberfläche.

    Version 0.5.11 bleibt strikt im Vorschau-Modus. Es werden weder Dateien
    noch Ordner umbenannt. Das spätere Raspberry-Pi-Backend gehört in ein
    separates MediaHub-AI-Node-Plugin und ist hier bewusst nicht enthalten.
    """

    VERSION = "0.5.14"

    def __init__(
        self,
        plugin_path: Path | str | None = None,
        mediahub_api=None,
        api=None,
    ):
        self.plugin_path = Path(plugin_path or Path(__file__).resolve().parent)
        self.naming_profile_service = NamingProfileService(
            self.plugin_path / "data" / "naming_profiles.json"
        )
        self.relation_preview_service = RelationPreviewService(
            self.naming_profile_service
        )
        self.preview_decision_store = PreviewDecisionStore()
        self.interactive_preview_service = InteractivePreviewService(
            self.relation_preview_service
        )
        self.gui_preview_session = GUIPreviewSession(
            self.preview_decision_store
        )
        self.optional_preview_integrations = OptionalPreviewIntegrations()
        self.review_service = ReviewService()
        self.preview_presentation = PreviewPresentationService()
        self.web_path_picker = WindowsWebPathPicker(
            self.plugin_path / "tools" / "web_path_picker.ps1"
        )
        self.mediahub_api = mediahub_api or api
        self.api = self.mediahub_api
        self.base_dir = Path(
            getattr(self.mediahub_api, "base_dir", self.plugin_path)
        )
        self.started = False
        self.server = None
        self._web_runtime_settings = None

        self.backend_registry = RenamerBackendRegistry(
            base_dir=self.base_dir,
        )
        self.learning_store = LearningStore(self.base_dir)
        self.preview_service = RenamePreviewService(
            backend_registry=self.backend_registry,
            decision_hint_provider=self.learning_store.decision_hints_for,
        )
        self.profile_service = ProfileService(self.plugin_path)
        self.integrations = OptionalIntegrationManager(self.mediahub_api)
        self.ai_review_bridge = AIReviewBridge(self.integrations)
        self.decision_fusion_service = DecisionFusionService()
        self.rename_plan_service = RenamePlanService()
        self.transaction_service = RenameTransactionService(self.base_dir)
        self._prepare_web_runtime()
        self._register_routes()

    def _prepare_web_runtime(self) -> None:
        try:
            from mediahub_web_core.server import acquire_shared_server
            from mediahub_web_core.settings import WebRuntimeSettingsStore

            store = WebRuntimeSettingsStore(self.base_dir)
            self._web_runtime_settings = store.load()
            self.server = acquire_shared_server(
                str(self.base_dir),
                self._web_runtime_settings.host,
                self._web_runtime_settings.port,
            )
        except Exception:
            # Desktop-Betrieb muss auch ohne geladenen WebRuntime-Pfad starten.
            self.server = None
            self._web_runtime_settings = None

    def _register_routes(self) -> None:
        if self.server is None:
            return

        for path, handler in {
            "/smart-renamer": self._index,
            "/smart-renamer/": self._index,
            "/smart-renamer/api/status": self._web_status,
            "/smart-renamer/api/backends": self._web_backends,
            "/smart-renamer/api/profiles": self._web_profiles,
            "/smart-renamer/api/learning": self._web_learning,
            "/smart-renamer/api/integrations": self._web_integrations,
            "/smart-renamer/api/ai-review/status": self._web_ai_review_status,
            "/smart-renamer/api/decision-fusion/status": self._web_decision_fusion_status,
            "/smart-renamer/api/learning/decisions": self._web_learning_decisions,
            "/smart-renamer/api/transactions/status": self._web_transaction_status,
            "/smart-renamer/assets/mediahub.css": self._stylesheet,
            "/smart-renamer/assets/interactive_preview.js": self._interactive_preview_js,
            "/smart-renamer/assets/gui_wiring.js": self._gui_wiring_js,
            "/smart-renamer/api/picker/files": self._web_picker_files,
            "/smart-renamer/api/picker/folder": self._web_picker_folder,
        }.items():
            self.server.add_route(path, handler, owner=self)

        self.server.add_post_route(
            "/smart-renamer/api/preview",
            self._web_preview,
            owner=self,
        )
        self.server.add_post_route(
            "/smart-renamer/api/ai-review/analyze",
            self._web_ai_review_analyze,
            owner=self,
        )
        self.server.add_post_route(
            "/smart-renamer/api/decision-fusion",
            self._web_decision_fusion,
            owner=self,
        )
        self.server.add_post_route(
            "/smart-renamer/api/learning/decision",
            self._web_record_learning_decision,
            owner=self,
        )
        self.server.add_post_route(
            "/smart-renamer/api/plan",
            self._web_plan,
            owner=self,
        )
        self.server.add_post_route(
            "/smart-renamer/api/transaction/prepare",
            self._web_prepare_transaction,
            owner=self,
        )

    def start(self):
        self.started = True
        self.backend_registry.refresh()
        if self.server is not None:
            self.server.start()
        return True

    def stop(self):
        if self.server is not None:
            try:
                from mediahub_web_core.server import release_shared_server

                release_shared_server(str(self.base_dir), owner=self)
            except Exception:
                pass
        self.started = False
        return True

    def get_status(self):
        capability_status = self.backend_registry.get_capability_status()
        return {
            "ready": self.started,
            "planned": False,
            "version": self.VERSION,
            "safe_mode": True,
            "preview_only": True,
            "transaction_planning": True,
            "automatic_install": True,
            "automatic_rename": False,
            "execution_enabled": True,
            "execution_requires_confirmation": True,
            "web_execution_enabled": False,
            "desktop_ui": True,
            "web_ui": self.server is not None,
            "mobile_responsive_ui": self.server is not None,
            "capability_status": capability_status,
            "message": (
                "Smart Renamer v0.5.5 gruppiert Untertitel, Metadaten, Bilder und Prüfsummen unter dem zugehörigen Medienobjekt und läuft eigenständig und aktiviert optionale Plugin-Integrationen nur bei tatsächlich verfügbarer Capability."
            ),
        }

    def get_plugin_settings(self):
        route = "/smart-renamer"
        active_url = ""
        if self._web_runtime_settings is not None:
            try:
                from mediahub_web_core.settings import connection_info

                info = connection_info(self._web_runtime_settings)
                active_url = str(info.get("active_url") or "").rstrip("/")
            except Exception:
                pass
        return {
            "version": self.VERSION,
            "url": f"{active_url}{route}" if active_url else route,
            "safe_mode": True,
            "preview_only": True,
        }

    def refresh_backends(self):
        return self.backend_registry.refresh()

    def list_backends(self):
        return self.backend_registry.describe_backends()

    def get_capability_status(self):
        return self.backend_registry.get_capability_status()

    def list_profiles(self):
        return self.profile_service.list_profiles()

    def get_learning_suggestions(self):
        return self.learning_store.suggestions()

    def record_manual_correction(self, original: str, corrected: str):
        return self.learning_store.record(original, corrected)

    def record_detection_decision(
        self,
        original_path: str,
        *,
        candidate_id: str = "",
        media_type: str = "",
        title: str = "",
        year: str = "",
        season: str = "",
        episode: str = "",
        edition: str = "",
    ):
        return self.learning_store.record_decision(
            original_path,
            candidate_id=candidate_id,
            media_type=media_type,
            title=title,
            year=year,
            season=season,
            episode=episode,
            edition=edition,
            source="user",
        )

    def get_learned_decisions(self):
        return self.learning_store.list_decisions()

    def delete_learned_decision(self, original_path: str):
        return {
            "deleted": self.learning_store.delete_decision(original_path),
            "original_path": original_path,
        }

    def preview_rename(self, items, rules=None, preferred_backend=None):
        enriched_items, metadata_status = self.integrations.enrich_items(
            list(items or [])
        )
        result = self.preview_service.create_preview(
            items=enriched_items,
            rules=list(rules or []),
            preferred_backend=preferred_backend,
        )
        result = self.preview_presentation.enrich(result)
        return {
            **result,
            "optional_integrations": {
                "metadata_editor": metadata_status.to_dict(),
            },
        }

    def create_rename_plan(
        self,
        items,
        rules=None,
        preferred_backend=None,
    ):
        preview = self.preview_rename(
            items,
            rules=rules,
            preferred_backend=preferred_backend,
        )
        plan = self.rename_plan_service.create_from_preview(preview)
        return {
            "ok": True,
            "plan": plan.to_dict(),
            "execution_performed": False,
        }

    def prepare_rename_transaction(
        self,
        items,
        rules=None,
        preferred_backend=None,
    ):
        preview = self.preview_rename(
            items,
            rules=rules,
            preferred_backend=preferred_backend,
        )
        plan = self.rename_plan_service.create_from_preview(preview)
        paths = self.transaction_service.save_prepared_transaction(plan)
        return {
            "ok": True,
            "plan": plan.to_dict(),
            "transaction": paths,
            "execution_performed": False,
        }

    def confirm_rename_plan(
        self,
        plan,
        *,
        user_confirmed: bool,
    ):
        receipt = self.transaction_service.confirm(
            plan,
            user_confirmed=user_confirmed,
        )
        return {
            "ok": True,
            "confirmation": receipt.to_dict(),
            "execution_performed": False,
            "_receipt": receipt,
        }

    def execute_confirmed_rename(
        self,
        plan,
        *,
        confirmation_token: str,
    ):
        result = self.transaction_service.execute(
            plan,
            confirmation_token=confirmation_token,
        )
        return {
            "ok": result.ok,
            "execution": result.to_dict(),
            "execution_performed": (
                result.status in {
                    "completed",
                    "rolled_back",
                    "rollback_failed",
                }
            ),
        }

    def rollback_rename_transaction(self, plan):
        result = self.transaction_service.rollback_transaction(plan)
        return {
            "ok": result.ok,
            "rollback": result.to_dict(),
        }

    def get_optional_integrations(self):
        return {
            "metadata_editor": self.integrations.metadata_status().to_dict(),
            "ai_review": self.ai_review_bridge.status(),
        }

    def attach_optional_provider(self, capability: str, provider):
        """Öffentlicher, optionaler Hook für MediaHub/andere Plugins."""
        self.integrations.attach_provider(capability, provider)
        return self.get_optional_integrations()

    def detach_optional_provider(self, capability: str):
        self.integrations.detach_provider(capability)
        return self.get_optional_integrations()

    def execute_rename(
        self,
        plan=None,
        *,
        confirmation_token: str = "",
    ):
        if plan is None or not confirmation_token:
            raise PermissionError(
                "Echte Umbenennung erfordert einen unveränderten Rename-Plan "
                "und eine ausdrücklich erzeugte Bestätigung."
            )
        return self.execute_confirmed_rename(
            plan,
            confirmation_token=confirmation_token,
        )

    def create_widget(self, parent=None):
        return NativeSmartRenamerWidget(self, parent=parent)

    def _index(self, request=None):
        html = (
            self.plugin_path / "index.html"
        ).read_text(encoding="utf-8")
        profiles_json = json.dumps(
            self.list_profiles(),
            ensure_ascii=False,
        ).replace("</", "<\\/")
        bootstrap = (
            "<script>"
            "window.__SMART_RENAMER_PROFILES__="
            f"{profiles_json};"
            "</script>"
        )
        html = html.replace("<script>", bootstrap + "<script>", 1)
        return (
            200,
            "text/html; charset=utf-8",
            html.encode("utf-8"),
        )

    def _stylesheet(self, request=None):
        return (
            200,
            "text/css; charset=utf-8",
            (
                self.plugin_path
                / "assets"
                / "css"
                / "mediahub.css"
            ).read_bytes(),
        )

    def _interactive_preview_js(self, request=None):
        return (
            200,
            "application/javascript; charset=utf-8",
            (
                self.plugin_path
                / "assets"
                / "js"
                / "interactive_preview.js"
            ).read_bytes(),
        )

    def _gui_wiring_js(self, request=None):
        return (
            200,
            "application/javascript; charset=utf-8",
            (
                self.plugin_path
                / "assets"
                / "js"
                / "gui_wiring.js"
            ).read_bytes(),
        )

    def _web_picker_files(self, request=None):
        paths = self.web_path_picker.pick_files()
        return self._json({
            "ok": True,
            "kind": "files",
            "paths": paths,
            "cancelled": not bool(paths),
            "read_only_selection": True,
        })

    def _web_picker_folder(self, request=None):
        paths = self.web_path_picker.pick_folder()
        return self._json({
            "ok": True,
            "kind": "folder",
            "paths": paths,
            "cancelled": not bool(paths),
            "read_only_selection": True,
        })

    @staticmethod
    def _json(data: Any, status: int = 200):
        return (
            status,
            "application/json; charset=utf-8",
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
        )

    def _web_status(self, request=None):
        return self._json(self.get_status())

    def _web_backends(self, request=None):
        return self._json({
            "ok": True,
            "items": self.list_backends(),
            "capabilities": self.get_capability_status(),
        })

    def _web_profiles(self, request=None):
        return self._json({
            "ok": True,
            "items": self.list_profiles(),
        })

    def _web_learning(self, request=None):
        return self._json({
            "ok": True,
            "suggestions": self.get_learning_suggestions(),
            "decisions": self.get_learned_decisions(),
            "automatic_application": False,
        })

    def _web_learning_decisions(self, request=None):
        return self._json({
            "ok": True,
            "items": self.get_learned_decisions(),
            "automatic_application": False,
        })

    def _web_record_learning_decision(self, payload, request=None):
        source = dict(payload or {})
        original_path = str(source.get("original_path") or "")
        if not original_path:
            return self._json({
                "ok": False,
                "error": "original_path fehlt.",
            }, 400)

        result = self.record_detection_decision(
            original_path,
            candidate_id=str(source.get("candidate_id") or ""),
            media_type=str(source.get("media_type") or ""),
            title=str(source.get("title") or ""),
            year=str(source.get("year") or ""),
            season=str(source.get("season") or ""),
            episode=str(source.get("episode") or ""),
            edition=str(source.get("edition") or ""),
        )
        return self._json({
            "ok": True,
            "decision": result,
            "automatic_application": False,
        })

    def _web_transaction_status(self, request=None):
        return self._json({
            "ok": True,
            "transaction_planning": True,
            "confirmation_required": True,
            "rollback_preparation": True,
            "execution_enabled": False,
            "automatic_execution": False,
        })

    def _web_plan(self, payload, request=None):
        source = dict(payload or {})
        result = self.create_rename_plan(
            list(source.get("items") or []),
            rules=list(source.get("rules") or []),
            preferred_backend=source.get("preferred_backend"),
        )
        return self._json(result)

    def _web_prepare_transaction(self, payload, request=None):
        source = dict(payload or {})
        result = self.prepare_rename_transaction(
            list(source.get("items") or []),
            rules=list(source.get("rules") or []),
            preferred_backend=source.get("preferred_backend"),
        )
        return self._json(result)

    def _web_integrations(self, request=None):
        return self._json({
            "ok": True,
            "items": self.get_optional_integrations(),
            "all_optional": True,
        })

    def _web_ai_review_status(self, request=None):
        return self._json({
            "ok": True,
            **self.ai_review_status(),
        })

    def _web_ai_review_analyze(self, payload, request=None):
        source = dict(payload or {})
        if not source:
            return self._json({
                "ok": False,
                "error": "Review-Payload fehlt.",
                "execution_allowed": False,
                "human_confirmation_required": True,
            }, 400)
        return self._json({
            "ok": True,
            **self.analyze_review_with_ai(source),
        })

    def _web_decision_fusion_status(self, request=None):
        return self._json({
            "ok": True,
            "enabled": True,
            "ai_optional": True,
            "safe_threshold": self.decision_fusion_service.SAFE_THRESHOLD,
            "review_threshold": self.decision_fusion_service.REVIEW_THRESHOLD,
            "execution_allowed": False,
            "human_confirmation_required": True,
        })

    def _web_decision_fusion(self, payload, request=None):
        source = dict(payload or {})
        if not source:
            return self._json({
                "ok": False,
                "error": "Decision-Fusion-Payload fehlt.",
                "execution_allowed": False,
                "human_confirmation_required": True,
            }, 400)
        return self._json({
            "ok": True,
            **self.analyze_and_fuse_review(source),
        })

    def _web_preview(self, payload, request=None):
        source = dict(payload or {})
        result = self.preview_rename(
            source.get("items") or [],
            source.get("rules") or [],
            source.get("preferred_backend"),
        )
        return self._json(
            result,
            200 if result.get("status") != "capability_unavailable" else 409,
        )


class NativeSmartRenamerWidget:
    """Dreispaltige Desktop-Oberfläche mit Live-Vorschau."""

    def __new__(cls, plugin, parent=None):
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QCheckBox,
            QComboBox,
            QFileDialog,
            QFormLayout,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QLineEdit,
            QPlainTextEdit,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QSpinBox,
            QSplitter,
            QTableWidget,
            QTableWidgetItem,
            QVBoxLayout,
            QWidget,
        )

        class _Widget(QWidget):
            RULE_TYPES = [
                ("replace", "Suchen und Ersetzen", "Benutzer"),
                ("remove", "Text entfernen", "Benutzer"),
                ("prefix", "Präfix", "Benutzer"),
                ("suffix", "Suffix", "Benutzer"),
                ("trim", "Leerzeichen bereinigen", "Benutzer"),
                ("case", "Groß-/Kleinschreibung", "Benutzer"),
                ("numbering", "Nummerierung", "Benutzer"),
                ("schema", "Namensschema", "Benutzer"),
            ]

            def __init__(self):
                super().__init__(parent)
                self.plugin = plugin
                self.paths: list[str] = []
                self.rules: list[dict] = []
                self._profiles = []
                self._updating_form = False
                self.preview_timer = QTimer(self)
                self.preview_timer.setSingleShot(True)
                self.preview_timer.setInterval(250)
                self.preview_timer.timeout.connect(self._preview)
                self._build()
                self._load_profiles()
                self._refresh_ai_review_status()
                self._refresh_backends()

            def _build(self):
                root = QVBoxLayout(self)
                root.setContentsMargins(8, 8, 8, 8)
                root.setSpacing(8)

                top = QHBoxLayout()
                title = QLabel("MediaHub Smart Renamer")
                title.setStyleSheet("font-size: 19px; font-weight: 700;")
                top.addWidget(title)
                top.addStretch(1)
                top.addWidget(QLabel("Profil:"))
                self.profile_combo = QComboBox()
                self.profile_combo.setMinimumWidth(170)
                self.profile_combo.currentIndexChanged.connect(self._profile_changed)
                top.addWidget(self.profile_combo)
                root.addLayout(top)

                notice = QLabel(
                    "Sicherer Vorschau-Modus: v0.5.11 verändert keine Dateien. "
                    "Desktop, WebRemote und Mobile verwenden dieselbe Plugin-API."
                )
                notice.setWordWrap(True)
                root.addWidget(notice)

                toolbar = QHBoxLayout()
                for label, handler in (
                    ("Dateien hinzufügen", self._add_files),
                    ("Ordner hinzufügen", self._add_folder),
                    ("Auswahl entfernen", self._remove_paths),
                    ("Liste leeren", self._clear_paths),
                ):
                    button = QPushButton(label)
                    button.clicked.connect(handler)
                    toolbar.addWidget(button)
                toolbar.addStretch(1)
                self.live_check = QCheckBox("Live-Vorschau")
                self.live_check.setChecked(True)
                toolbar.addWidget(self.live_check)
                preview_button = QPushButton("Vorschau aktualisieren")
                preview_button.clicked.connect(self._preview)
                toolbar.addWidget(preview_button)
                root.addLayout(toolbar)

                outer = QSplitter(Qt.Orientation.Horizontal)

                # Left: files and rules
                left = QWidget(); left_layout = QVBoxLayout(left); left_layout.setContentsMargins(0,0,0,0)
                left_layout.addWidget(QLabel("Dateien und Ordner"))
                self.path_list = QListWidget()
                self.path_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
                left_layout.addWidget(self.path_list, 1)
                left_layout.addWidget(QLabel("Regelstapel"))
                self.rule_list = QListWidget()
                self.rule_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
                self.rule_list.model().rowsMoved.connect(self._rules_reordered)
                self.rule_list.currentRowChanged.connect(self._rule_selected)
                left_layout.addWidget(self.rule_list, 1)
                rule_buttons = QHBoxLayout()
                for label, handler in (("+", self._add_rule),("–", self._delete_rule),("↑", lambda:self._move_rule(-1)),("↓", lambda:self._move_rule(1)),("Kopieren", self._copy_rule)):
                    b=QPushButton(label); b.clicked.connect(handler); rule_buttons.addWidget(b)
                left_layout.addLayout(rule_buttons)

                # Center: preview table + Web-parity controls
                center = QWidget(); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0)

                preview_head = QHBoxLayout()
                preview_head.addWidget(QLabel("Vorschau"))
                preview_head.addStretch(1)
                preview_head.addWidget(QLabel("Suche:"))
                self.preview_search = QLineEdit()
                self.preview_search.setPlaceholderText("Original, Vorschlag, Relation …")
                self.preview_search.setMinimumWidth(190)
                self.preview_search.textChanged.connect(self._apply_preview_filters)
                preview_head.addWidget(self.preview_search)

                self.preview_status_filter = QComboBox()
                self.preview_status_filter.addItem("Alle Status", "all")
                self.preview_status_filter.addItem("Sicher", "safe")
                self.preview_status_filter.addItem("Review", "review")
                self.preview_status_filter.addItem("Konflikt", "conflict")
                self.preview_status_filter.currentIndexChanged.connect(self._apply_preview_filters)
                preview_head.addWidget(self.preview_status_filter)

                self.preview_sort = QComboBox()
                self.preview_sort.addItem("Name", 1)
                self.preview_sort.addItem("Vorschlag", 2)
                self.preview_sort.addItem("Relation", 3)
                self.preview_sort.addItem("Confidence", 4)
                self.preview_sort.currentIndexChanged.connect(self._sort_preview)
                preview_head.addWidget(self.preview_sort)
                center_layout.addLayout(preview_head)

                self.preview_summary = QLabel("0 Einträge · 0 Review · 0 Konflikte")
                center_layout.addWidget(self.preview_summary)

                preview_actions = QHBoxLayout()
                for label, state in (
                    ("Auswahl übernehmen", "accepted"),
                    ("Auswahl ignorieren", "ignored"),
                    ("Auswahl prüfen", "review"),
                ):
                    button = QPushButton(label)
                    button.clicked.connect(lambda checked=False, s=state: self._set_selected_preview_state(s))
                    preview_actions.addWidget(button)
                self.ai_review_button = QPushButton("KI prüfen")
                self.ai_review_button.setToolTip(
                    "Optionalen KI-Provider für genau einen ausgewählten Review-Fall fragen. "
                    "Keine Datei wird verändert."
                )
                self.ai_review_button.clicked.connect(self._run_ai_review_for_selection)
                preview_actions.addWidget(self.ai_review_button)

                self.ai_review_status_label = QLabel("KI: wird geprüft …")
                preview_actions.addWidget(self.ai_review_status_label)

                self.fusion_button = QPushButton("Entscheidung vergleichen")
                self.fusion_button.setToolTip(
                    "Renamer- und KI-Bewertung vergleichen. "
                    "Bei Widerspruch bleibt der Fall zwingend auf Bitte prüfen."
                )
                self.fusion_button.clicked.connect(self._run_decision_fusion_for_selection)
                preview_actions.addWidget(self.fusion_button)

                preview_actions.addStretch(1)
                self.preview_selected_count = QLabel("0 ausgewählt")
                preview_actions.addWidget(self.preview_selected_count)
                center_layout.addLayout(preview_actions)

                self.table = QTableWidget(0, 9)
                self.table.setHorizontalHeaderLabels(["Status", "Original", "Vorschlag", "Relation", "Confidence", "Review", "Quelle", "Hinweise", "Zielpfad"])
                self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
                self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                self.table.setWordWrap(False)
                self.table.setMinimumWidth(650)
                self.table.itemSelectionChanged.connect(self._preview_selection_changed)
                header=self.table.horizontalHeader(); header.setMinimumSectionSize(65); header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
                center_layout.addWidget(self.table,1)

                center_layout.addWidget(QLabel("Ausgewählter Eintrag"))
                self.preview_details = QPlainTextEdit()
                self.preview_details.setReadOnly(True)
                self.preview_details.setMaximumHeight(180)
                self.preview_details.setPlaceholderText("Zeile auswählen, um vollständige Namen und Details zu sehen.")
                center_layout.addWidget(self.preview_details)

                # Right: rule editor
                right=QWidget(); right_layout=QVBoxLayout(right); right_layout.setContentsMargins(0,0,0,0)
                right_layout.addWidget(QLabel("Regel-Eigenschaften"))
                self.enabled = QCheckBox("Regel aktiv")
                self.enabled.stateChanged.connect(self._form_changed)
                right_layout.addWidget(self.enabled)
                form=QFormLayout()
                self.rule_type=QComboBox()
                for kind,label,_ in self.RULE_TYPES: self.rule_type.addItem(label,kind)
                self.rule_type.currentIndexChanged.connect(self._type_changed)
                self.rule_source=QComboBox(); self.rule_source.addItems(["Benutzer", "Profil", "KI", "ReNamer", "Plugin"])
                self.search=QLineEdit(); self.replacement=QLineEdit(); self.value=QLineEdit()
                self.case_mode=QComboBox(); self.case_mode.addItem("Unverändert",""); self.case_mode.addItem("klein","lower"); self.case_mode.addItem("GROSS","upper"); self.case_mode.addItem("Titel","title"); self.case_mode.addItem("Satz","sentence")
                self.start_number=QSpinBox(); self.start_number.setRange(0,999999); self.start_number.setValue(1)
                self.padding=QSpinBox(); self.padding.setRange(1,12); self.padding.setValue(2)
                self.schema=QLineEdit(); self.schema.setPlaceholderText("[titel] ([jahr])")
                form.addRow("Regeltyp",self.rule_type); form.addRow("Quelle",self.rule_source); form.addRow("Suchen",self.search); form.addRow("Ersetzen",self.replacement); form.addRow("Wert",self.value); form.addRow("Schreibweise",self.case_mode); form.addRow("Startnummer",self.start_number); form.addRow("Stellen",self.padding); form.addRow("Schema",self.schema)
                right_layout.addLayout(form)
                placeholders=QLabel("Platzhalter: [titel] [jahr] [staffel] [episode] [episodentitel] [nummer] [original] [endung]")
                placeholders.setWordWrap(True); right_layout.addWidget(placeholders); right_layout.addStretch(1)
                for widget in (self.rule_source,self.search,self.replacement,self.value,self.case_mode,self.start_number,self.padding,self.schema):
                    signal = getattr(widget, 'textChanged', None) or getattr(widget, 'currentIndexChanged', None) or getattr(widget, 'valueChanged', None)
                    signal.connect(self._form_changed)

                outer.addWidget(left); outer.addWidget(center); outer.addWidget(right)
                left.setMinimumWidth(145)
                center.setMinimumWidth(650)
                right.setMinimumWidth(310)
                outer.setStretchFactor(0,1); outer.setStretchFactor(1,8); outer.setStretchFactor(2,3)
                outer.setSizes([160, 850, 360])
                root.addWidget(outer,1)

                self.status = QLabel("Bereit")
                self.status.setWordWrap(True)
                root.addWidget(self.status)

            def _row_meta(self, row):
                item = self.table.item(row, 0)
                if item is None:
                    return {}
                return item.data(Qt.ItemDataRole.UserRole) or {}

            def _preview_selection_changed(self):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                self.preview_selected_count.setText(f"{len(rows)} ausgewählt")
                if not rows:
                    self.preview_details.clear()
                    return
                meta = self._row_meta(rows[0])
                self.preview_details.setPlainText(
                    "Original:\n"
                    + str(meta.get("original_name") or "")
                    + "\n\nVorschlag:\n"
                    + str(meta.get("proposed_name") or "")
                    + "\n\nRelation: "
                    + str(meta.get("relation_type") or "single")
                    + "    Confidence: "
                    + f"{float(meta.get('confidence') or 0)*100:.0f}%"
                    + "    Review: "
                    + ("Ja" if meta.get("review_required") else "Nein")
                    + ("\n\nHinweise:\n" + str(meta.get("issues") or "") if meta.get("issues") else "")
                    + self._format_ai_review_detail()
                )

            def _format_ai_review_detail(self):
                result = self.last_ai_review
                if not result:
                    return ""
                if not result.get("available"):
                    return "\n\nKI-Review:\nKein KI-Provider verfügbar."
                warnings = result.get("warnings") or []
                return (
                    "\n\nKI-Review:"
                    "\nProvider: " + str(result.get("provider") or "unbekannt")
                    + "\nEmpfehlung: " + str(result.get("recommendation") or "—")
                    + ("\nNamensvorschlag: " + str(result.get("suggested_name")) if result.get("suggested_name") else "")
                    + "\nConfidence: " + f"{float(result.get('confidence') or 0)*100:.0f}%"
                    + "\nBegründung: " + str(result.get("rationale") or "—")
                    + ("\nWarnungen: " + "; ".join(str(x) for x in warnings) if warnings else "")
                    + "\n\nNur Vorschlag · Benutzerbestätigung erforderlich."
                    + self._format_fusion_detail()
                )

            def _format_fusion_detail(self):
                result = self.last_fusion_result
                if not result:
                    return ""
                return (
                    "\n\nDecision Fusion:"
                    "\nErgebnis: " + str(result.get("decision") or "review")
                    + "\nAgreement: " + str(result.get("agreement") or "—")
                    + "\nConfidence: " + f"{float(result.get('confidence') or 0)*100:.0f}%"
                    + "\nReview nötig: " + ("Ja" if result.get("review_required") else "Nein")
                    + "\nBegründung: " + str(result.get("reason") or "—")
                    + "\n\nKeine automatische Ausführung."
                )

            def _run_decision_fusion_for_selection(self):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                if len(rows) != 1:
                    self.status.setText(
                        "Für Decision Fusion bitte genau einen Vorschau-Eintrag auswählen."
                    )
                    return
                meta = self._row_meta(rows[0])
                ai_result = self.last_ai_review or self.plugin.analyze_review_with_ai(meta)
                self.last_ai_review = ai_result
                self.last_fusion_result = self.plugin.fuse_review_decision(meta, ai_result)
                self._preview_selection_changed()

                if self.last_fusion_result.get("agreement") == "conflict":
                    self.status.setText(
                        "Renamer und KI widersprechen sich: Bitte prüfen bleibt zwingend."
                    )
                elif self.last_fusion_result.get("agreement") == "agree":
                    self.status.setText(
                        "Renamer und KI stimmen überein. Keine Datei wurde verändert."
                    )
                else:
                    self.status.setText(
                        "Keine KI verfügbar. Renamer-Bewertung bleibt aktiv."
                    )

            def _refresh_ai_review_status(self):
                status = self.plugin.ai_review_status()
                if status.get("available"):
                    self.ai_review_status_label.setText(
                        "KI: " + str(status.get("provider") or "verfügbar")
                    )
                    self.ai_review_button.setEnabled(True)
                else:
                    self.ai_review_status_label.setText("KI: nicht verfügbar")
                    self.ai_review_button.setEnabled(False)

            def _run_ai_review_for_selection(self):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                if len(rows) != 1:
                    self.status.setText(
                        "Für KI-Review bitte genau einen Vorschau-Eintrag auswählen."
                    )
                    return
                meta = self._row_meta(rows[0])
                self.last_ai_review = self.plugin.analyze_review_with_ai(meta)
                self._preview_selection_changed()
                if self.last_ai_review.get("available"):
                    self.status.setText(
                        "KI-Vorschlag geladen. Keine Datei wurde verändert."
                    )
                else:
                    self.status.setText(
                        "Kein KI-Review-Provider verfügbar. Manueller Review bleibt aktiv."
                    )

            def _apply_preview_filters(self):
                if not hasattr(self, "preview_search"):
                    return
                term = self.preview_search.text().strip().casefold()
                wanted = self.preview_status_filter.currentData() or "all"
                for row in range(self.table.rowCount()):
                    meta = self._row_meta(row)
                    haystack = " ".join(
                        str(meta.get(key) or "")
                        for key in ("original_name", "proposed_name", "relation_type", "issues", "source_path")
                    ).casefold()
                    visible = (not term or term in haystack) and (
                        wanted == "all" or meta.get("status") == wanted
                    )
                    self.table.setRowHidden(row, not visible)

            def _sort_preview(self):
                column = int(self.preview_sort.currentData() or 1)
                self.table.sortItems(column, Qt.SortOrder.AscendingOrder)

            def _set_selected_preview_state(self, state):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                for row in rows:
                    meta = self._row_meta(row)
                    source_path = str(meta.get("source_path") or "")
                    item_id = self.plugin.interactive_preview_service.item_id(source_path)
                    self.plugin.set_preview_decision(item_id, state=state)
                    status_item = self.table.item(row, 0)
                    if status_item is not None:
                        status_item.setToolTip(f"Vorschauentscheidung: {state}")
                self.status.setText(
                    f"{len(rows)} Vorschau-Eintrag/Einträge auf '{state}' gesetzt. "
                    "Keine Datei wurde verändert."
                )

            def _update_preview_summary(self):
                review = 0
                conflict = 0
                for row in range(self.table.rowCount()):
                    status = self._row_meta(row).get("status")
                    review += int(status == "review")
                    conflict += int(status == "conflict")
                self.preview_summary.setText(
                    f"{self.table.rowCount()} Einträge · {review} Review · {conflict} Konflikte"
                )

            def _load_profiles(self):
                self._profiles = self.plugin.list_profiles()
                self.profile_combo.blockSignals(True); self.profile_combo.clear()
                for profile in self._profiles: self.profile_combo.addItem(profile.get("name",profile.get("id","Profil")),profile.get("id"))
                self.profile_combo.blockSignals(False)
                if self._profiles: self._apply_profile(self._profiles[0])

            def _profile_changed(self, index):
                if 0 <= index < len(self._profiles): self._apply_profile(self._profiles[index])

            def _apply_profile(self, profile):
                self.rules = [dict(rule) for rule in profile.get("rules",[])]
                for rule in self.rules:
                    rule.setdefault("enabled",True); rule.setdefault("source","Profil")
                self._render_rules(); self._schedule_preview()

            def _render_rules(self, current=0):
                self.rule_list.blockSignals(True); self.rule_list.clear()
                icons={"Benutzer":"🟦","Profil":"🟩","KI":"🟨","ReNamer":"🟪","Plugin":"⬜"}
                for rule in self.rules:
                    source=str(rule.get("source") or "Benutzer"); label=str(rule.get("label") or rule.get("type") or "Regel")
                    item=QListWidgetItem(f"{icons.get(source,'⬜')} {'☑' if rule.get('enabled',True) else '☐'} {label}")
                    self.rule_list.addItem(item)
                self.rule_list.blockSignals(False)
                if self.rules: self.rule_list.setCurrentRow(max(0,min(current,len(self.rules)-1)))

            def _add_rule(self):
                self.rules.append({"type":"trim","label":"Leerzeichen bereinigen","source":"Benutzer","enabled":True})
                self._render_rules(len(self.rules)-1); self._schedule_preview()

            def _delete_rule(self):
                row=self.rule_list.currentRow()
                if 0 <= row < len(self.rules): self.rules.pop(row); self._render_rules(max(0,row-1)); self._schedule_preview()

            def _copy_rule(self):
                row=self.rule_list.currentRow()
                if 0 <= row < len(self.rules):
                    clone=dict(self.rules[row]); clone["label"]=str(clone.get("label") or clone.get("type"))+" (Kopie)"; self.rules.insert(row+1,clone); self._render_rules(row+1); self._schedule_preview()

            def _move_rule(self, delta):
                row=self.rule_list.currentRow(); target=row+delta
                if 0 <= row < len(self.rules) and 0 <= target < len(self.rules):
                    self.rules[row],self.rules[target]=self.rules[target],self.rules[row]; self._render_rules(target); self._schedule_preview()

            def _rules_reordered(self,*_):
                ordered=[]
                # QListWidget text alone cannot preserve dictionaries; use visual move coordinates via selected row.
                # Keep safe deterministic behavior by rebuilding from current visible labels only when buttons are used.
                self._render_rules(self.rule_list.currentRow())

            def _rule_selected(self,row):
                if not (0 <= row < len(self.rules)): return
                rule=self.rules[row]; self._updating_form=True
                self.enabled.setChecked(bool(rule.get("enabled",True)))
                idx=self.rule_type.findData(rule.get("type")); self.rule_type.setCurrentIndex(max(0,idx))
                self.rule_source.setCurrentText(str(rule.get("source") or "Benutzer"))
                self.search.setText(str(rule.get("old") or "")); self.replacement.setText(str(rule.get("new") or "")); self.value.setText(str(rule.get("value") or ""))
                idx=self.case_mode.findData(rule.get("mode") or ""); self.case_mode.setCurrentIndex(max(0,idx))
                self.start_number.setValue(int(rule.get("start",1))); self.padding.setValue(int(rule.get("padding",2))); self.schema.setText(str(rule.get("template") or ""))
                self._updating_form=False

            def _type_changed(self,*_): self._form_changed()

            def _form_changed(self,*_):
                if self._updating_form: return
                row=self.rule_list.currentRow()
                if not (0 <= row < len(self.rules)): return
                kind=self.rule_type.currentData(); rule=self.rules[row]
                rule.update({"type":kind,"enabled":self.enabled.isChecked(),"source":self.rule_source.currentText(),"old":self.search.text(),"new":self.replacement.text(),"value":self.value.text(),"mode":self.case_mode.currentData(),"start":self.start_number.value(),"padding":self.padding.value(),"template":self.schema.text()})
                labels=dict((k,l) for k,l,_ in self.RULE_TYPES); rule["label"]=labels.get(kind,kind)
                self._render_rules(row); self._schedule_preview()

            def _schedule_preview(self):
                if self.live_check.isChecked(): self.preview_timer.start()

            def _add_files(self):
                paths,_=QFileDialog.getOpenFileNames(self,"Dateien hinzufügen")
                self._append_paths(paths)

            def _add_folder(self):
                path=QFileDialog.getExistingDirectory(self,"Ordner hinzufügen")
                if path: self._append_paths([path])

            def _append_paths(self,paths):
                for path in paths:
                    if path and path not in self.paths: self.paths.append(path); self.path_list.addItem(path)
                self._schedule_preview()

            def _remove_paths(self):
                rows=sorted({self.path_list.row(i) for i in self.path_list.selectedItems()},reverse=True)
                for row in rows: self.path_list.takeItem(row); self.paths.pop(row)
                self._schedule_preview()

            def _clear_paths(self): self.paths.clear(); self.path_list.clear(); self.table.setRowCount(0); self._update_status({})

            def _refresh_backends(self): self.plugin.refresh_backends(); self._update_status({})

            def _preview(self):
                if not self.paths: self.table.setRowCount(0); self.status.setText("Keine Dateien oder Ordner ausgewählt."); return
                result=self.plugin.preview_rename([{"path":p,"recursive":True} for p in self.paths],self.rules)
                rows=result.get("preview_rows") or result.get("changes") or []
                self.table.setRowCount(len(rows))
                for r,item in enumerate(rows):
                    severity=item.get("highest_severity") or ("blocking" if item.get("blocked") else "info")
                    status={"info":"✓","warning":"⚠","error":"!","blocking":"✖"}.get(severity,"✓")
                    issues=item.get("issues") or []
                    issue_text="; ".join(str(x.get("message") or x) for x in issues) or "; ".join(item.get("warnings") or [])
                    source=", ".join(item.get("rule_sources") or []) or item.get("change_source") or "unverändert"
                    relation=str(item.get("relation_type") or "single")
                    confidence=float(item.get("confidence") or 0)
                    review="Ja" if item.get("review_required") else "Nein"
                    values=[
                        status,
                        item.get("original_name",""),
                        item.get("proposed_name",""),
                        relation,
                        f"{confidence*100:.0f}%",
                        review,
                        source,
                        issue_text,
                        item.get("target_path",""),
                    ]
                    row_meta={
                        "status": "review" if item.get("review_required") else ("conflict" if status == "⛔" else "safe"),
                        "source_path": str(item.get("source_path") or ""),
                        "original_name": str(item.get("original_name") or ""),
                        "proposed_name": str(item.get("proposed_name") or ""),
                        "relation_type": relation,
                        "confidence": confidence,
                        "review_required": bool(item.get("review_required")),
                        "issues": issue_text,
                        "target_path": str(item.get("target_path") or ""),
                    }
                    for c,value in enumerate(values):
                        cell=QTableWidgetItem(str(value))
                        if c in {1,2,7,8}:
                            cell.setToolTip(str(value))
                        if c == 0:
                            cell.setData(Qt.ItemDataRole.UserRole, row_meta)
                        self.table.setItem(r,c,cell)
                self._update_preview_summary()
                self._apply_preview_filters()
                self._update_status(result)

            def _update_status(self,result):
                summary=result.get("summary") or {}; caps=self.plugin.get_capability_status()
                self.status.setText(
                    f"Dateien: {summary.get('item_count',summary.get('total_count',0))} · "
                    f"Änderungen: {summary.get('changed_count',0)} · "
                    f"Blockierend: {summary.get('blocking_count',0)} · "
                    f"Warnungen: {summary.get('warning_row_count',0)} · "
                    f"Backend: {result.get('selected_backend') or caps.get('active_preview_backend_id') or 'nicht verfügbar'} · "
                    "Ausführung: gesperrt"
                )

        return _Widget()

    def list_naming_profiles(self):
        return [
            profile.to_dict()
            for profile in self.naming_profile_service.list_profiles()
        ]

    def save_custom_naming_profile(
        self,
        *,
        profile_id: str,
        display_name: str,
        multi_episode_template: str,
        split_episode_template: str,
        split_movie_template: str,
        custom_fields=None,
    ):
        profile = self.naming_profile_service.save_custom_profile(
            profile_id=profile_id,
            display_name=display_name,
            multi_episode_template=multi_episode_template,
            split_episode_template=split_episode_template,
            split_movie_template=split_movie_template,
            custom_fields=custom_fields,
        )
        return profile.to_dict()

    def delete_custom_naming_profile(self, profile_id: str):
        return self.naming_profile_service.delete_custom_profile(profile_id)

    def build_relation_preview(self, items, *, profile_id: str = "plex"):
        return self.relation_preview_service.build_many(
            items,
            profile_id=profile_id,
        )

    def build_interactive_preview(self, items, *, profile_id: str = "plex"):
        return self.interactive_preview_service.build(items, profile_id=profile_id)

    def set_preview_decision(self, item_id: str, *, state: str, manual_name: str = "", note: str = ""):
        return self.preview_decision_store.set(
            item_id, state=state, manual_name=manual_name, note=note
        )

    def get_preview_decisions(self):
        return self.preview_decision_store.all()

    def clear_preview_decisions(self):
        self.preview_decision_store.clear()
        return {"ok": True}

    def gui_preview_state(self):
        return self.gui_preview_session.snapshot()

    def gui_set_selection(self, item_ids):
        return self.gui_preview_session.set_selection(item_ids)

    def gui_toggle_selection(self, item_id: str):
        return self.gui_preview_session.toggle_selection(item_id)

    def gui_clear_selection(self):
        return self.gui_preview_session.clear_selection()

    def gui_set_group(self, group_key: str):
        return self.gui_preview_session.set_group(group_key)

    def gui_set_status_filter(self, status: str):
        return self.gui_preview_session.set_status_filter(status)

    def gui_set_sort(self, sort_by: str, direction: str = "asc"):
        return self.gui_preview_session.set_sort(sort_by, direction)

    def gui_set_search(self, search_text: str):
        return self.gui_preview_session.set_search(search_text)

    def gui_bulk_decision(self, state: str):
        return self.gui_preview_session.bulk_decision(state)

    def gui_manual_name(self, item_id: str, manual_name: str, note: str = ""):
        return self.gui_preview_session.apply_manual_name(item_id, manual_name, note)

    def optional_integration_status(self):
        return self.optional_preview_integrations.status()

    def classify_preview_review(self, row):
        return self.review_service.classify(dict(row or {}))

    def ai_review_status(self):
        return self.ai_review_bridge.status()

    def analyze_review_with_ai(self, payload):
        result = self.ai_review_bridge.analyze(dict(payload or {}))
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["requires_human_confirmation"] = True
        result["human_confirmation_required"] = True
        return result

    def fuse_review_decision(self, renamer_payload, ai_result=None):
        result = self.decision_fusion_service.fuse(
            dict(renamer_payload or {}),
            dict(ai_result or {}),
        )
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["human_confirmation_required"] = True
        return result

    def analyze_and_fuse_review(self, payload):
        source = dict(payload or {})
        ai_result = self.analyze_review_with_ai(source)
        fusion = self.fuse_review_decision(source, ai_result)
        return {
            "ai": ai_result,
            "fusion": fusion,
            "execution_locked": True,
            "execution_allowed": False,
            "human_confirmation_required": True,
        }


