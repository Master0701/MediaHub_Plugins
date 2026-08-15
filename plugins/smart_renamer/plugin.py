from __future__ import annotations

import json
from pathlib import Path
from mediahub_smart_renamer_runtime.services.naming_profiles import NamingProfileService
from mediahub_smart_renamer_runtime.services.relation_preview_service import RelationPreviewService
from mediahub_smart_renamer_runtime.services.interactive_preview_service import InteractivePreviewService
from mediahub_smart_renamer_runtime.services.preview_decisions import PreviewDecisionStore
from mediahub_smart_renamer_runtime.services.gui_preview_session import GUIPreviewSession
from mediahub_smart_renamer_runtime.services.optional_preview_integrations import OptionalPreviewIntegrations
from mediahub_smart_renamer_runtime.services.review_service import ReviewService
from mediahub_smart_renamer_runtime.services.ai_review_bridge import AIReviewBridge
from mediahub_smart_renamer_runtime.services.batch_ai_review_bridge import BatchAIReviewBridge
from mediahub_smart_renamer_runtime.services.metadata_capability_bridge import MetadataCapabilityBridge
from mediahub_smart_renamer_runtime.services.decision_fusion import DecisionFusionService
from mediahub_smart_renamer_runtime.services.decision_evidence import DecisionEvidenceService
from mediahub_smart_renamer_runtime.services.review_priority import ReviewPriorityService
from mediahub_smart_renamer_runtime.services.preview_presentation import PreviewPresentationService
from mediahub_smart_renamer_runtime.services.candidate_review_context import CandidateReviewContextService
from mediahub_smart_renamer_runtime.services.ai_review_recommendation import AIReviewRecommendationService
from mediahub_smart_renamer_runtime.services.ai_review_comparison import AIReviewComparisonService
from mediahub_smart_renamer_runtime.services.web_picker_service import WindowsWebPathPicker
from typing import Any

from mediahub_smart_renamer_runtime.services.backend_registry import RenamerBackendRegistry
from mediahub_smart_renamer_runtime.services.preview_service import RenamePreviewService
from mediahub_smart_renamer_runtime.services.profile_service import ProfileService
from mediahub_smart_renamer_runtime.services.learning_store import LearningStore
from mediahub_smart_renamer_runtime.services.optional_integrations import OptionalIntegrationManager
from mediahub_smart_renamer_runtime.services.rename_plan import RenamePlanService
from mediahub_smart_renamer_runtime.services.transaction_service import RenameTransactionService
from mediahub_smart_renamer_runtime.services.rule_stack_merge import merge_profile_rules


class MediaHubSmartRenamerPlugin:
    """Windows-Smart-Renamer mit Desktop- und lokaler Weboberfläche.

    Version 0.5.11 bleibt strikt im Vorschau-Modus. Es werden weder Dateien
    noch Ordner umbenannt. Das spätere Raspberry-Pi-Backend gehört in ein
    separates MediaHub-AI-Node-Plugin und ist hier bewusst nicht enthalten.
    """

    VERSION = "0.5.16"

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
        self.candidate_review_context = CandidateReviewContextService()
        self.ai_review_recommendation = AIReviewRecommendationService()
        self.ai_review_comparison = AIReviewComparisonService()
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
        self.batch_ai_review_bridge = BatchAIReviewBridge(self.integrations)
        self.metadata_capability_bridge = MetadataCapabilityBridge(self.integrations)
        self.decision_fusion_service = DecisionFusionService()
        self.decision_evidence_service = DecisionEvidenceService()
        self.review_priority_service = ReviewPriorityService()
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
            "/smart-renamer/api/decision-evidence/status": self._web_decision_evidence_status,
            "/smart-renamer/api/review-priority/status": self._web_review_priority_status,
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
            "/smart-renamer/api/decision-evidence",
            self._web_decision_evidence,
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
        rows_key = "preview_rows" if "preview_rows" in result else "changes"
        if rows_key in result:
            enriched_rows = self.review_priority_service.enrich_rows(
                list(result.get(rows_key) or [])
            )
            result[rows_key] = enriched_rows
            result["priority_summary"] = self.review_priority_service.summary(
                enriched_rows
            )
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

    def _web_decision_evidence_status(self, request=None):
        return self._json({
            "ok": True,
            "enabled": True,
            "execution_allowed": False,
            "human_confirmation_required": True,
        })

    def _web_review_priority_status(self, request=None):
        return self._json({
            "ok": True,
            "enabled": True,
            "levels": ["critical", "high", "medium", "low"],
            "execution_allowed": False,
            "human_confirmation_required": True,
        })

    def _web_decision_evidence(self, payload, request=None):
        source = dict(payload or {})
        if not source:
            return self._json({
                "ok": False,
                "error": "Decision-Evidence-Payload fehlt.",
                "execution_allowed": False,
                "human_confirmation_required": True,
            }, 400)
        combined = self.analyze_and_fuse_review(source)
        return self._json({
            "ok": True,
            **combined,
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

    def set_preview_decision(
        self,
        item_id: str,
        *,
        state: str,
        manual_name: str = "",
        note: str = "",
    ):
        return self.preview_decision_store.set(
            item_id,
            state=state,
            manual_name=manual_name,
            note=note,
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

    def gui_manual_name(
        self,
        item_id: str,
        manual_name: str,
        note: str = "",
    ):
        return self.gui_preview_session.apply_manual_name(
            item_id,
            manual_name,
            note,
        )

    def optional_integration_status(self):
        return self.optional_preview_integrations.status()

    def classify_preview_review(self, row):
        return self.review_service.classify(dict(row or {}))

    def batch_ai_review_status(self):
        status=self.batch_ai_review_bridge.status()
        status["metadata"] = self.metadata_capability_bridge.status()
        return status

    def analyze_batch_with_ai(self, items, *, reference=None, schema=None):
        enriched=[]
        metadata_status=self.metadata_capability_bridge.status()
        for raw in list(items or []):
            item=dict(raw or {})
            path=str(item.get("source_path") or item.get("path") or "")
            detected={
                "media_type":str(item.get("media_type") or ""),
                "title":str(item.get("title") or ""),
                "year":str(item.get("year") or ""),
                "season":str(item.get("season") or ""),
                "episode":str(item.get("episode") or ""),
                "series":str(item.get("series") or ""),
            }
            if metadata_status.get("read"):
                item["metadata_read"] = self.metadata_capability_bridge.read({"path":path,"item":item})
            if metadata_status.get("review"):
                item["metadata_review"] = self.metadata_capability_bridge.review({"path":path,"item":item,"detected":detected})
            try:
                item["local_review"] = self.analyze_review_with_ai(item)
            except Exception:
                item["local_review"] = {}
            enriched.append(item)
        result=self.batch_ai_review_bridge.analyze({
            "items":enriched,
            "reference":dict(reference or {}),
            "schema":dict(schema or {}),
            "metadata_status":metadata_status,
        })
        result["metadata_status"]=metadata_status
        result["execution_allowed"]=False
        result["automatic_apply_allowed"]=False
        result["metadata_write_allowed"]=False
        result["human_confirmation_required"]=True
        return result

    def ai_review_status(self):
        return self.ai_review_bridge.status()

    def analyze_review_with_ai(self, payload):
        review_context = self.candidate_review_context.build(
            dict(payload or {})
        )
        result = self.ai_review_bridge.analyze(review_context)
        structured = self.ai_review_recommendation.normalize(
            result,
            review_context,
        )
        result["structured_recommendation"] = structured
        result["recommended_candidate_id"] = str(
            structured.get("candidate_id") or ""
        )
        result["recommended_fields"] = dict(
            structured.get("fields") or {}
        )
        result["candidate_count"] = int(
            review_context.get("candidate_count") or 0
        )
        result["selected_candidate_id"] = str(
            review_context.get("selected_candidate_id") or ""
        )
        result["review_context_enriched"] = True
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["requires_human_confirmation"] = True
        result["human_confirmation_required"] = True
        return result

    def compare_review_recommendation(self, payload, ai_result=None):
        source = dict(payload or {})
        ai = dict(ai_result or {})
        if not ai:
            ai = self.analyze_review_with_ai(source)
        result = self.ai_review_comparison.compare(source, ai)
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["automatic_apply_allowed"] = False
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

    def build_decision_evidence(
        self,
        renamer_payload,
        ai_result=None,
        fusion_result=None,
    ):
        result = self.decision_evidence_service.build(
            dict(renamer_payload or {}),
            dict(ai_result or {}),
            dict(fusion_result or {}),
        )
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["human_confirmation_required"] = True
        return result

    def analyze_and_fuse_review(self, payload):
        source = dict(payload or {})
        ai_result = self.analyze_review_with_ai(source)
        fusion = self.fuse_review_decision(source, ai_result)
        evidence = self.build_decision_evidence(
            source,
            ai_result,
            fusion,
        )
        return {
            "ai": ai_result,
            "structured_recommendation": dict(
                ai_result.get("structured_recommendation") or {}
            ),
            "fusion": fusion,
            "evidence": evidence,
            "automatic_apply_allowed": False,
            "execution_locked": True,
            "execution_allowed": False,
            "human_confirmation_required": True,
        }


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
            QStackedWidget,
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
                ("replace_advanced", "Erweitert suchen/ersetzen", "Benutzer"),
                ("regex_replace", "RegEx ersetzen", "Benutzer"),
                ("remove_range", "Zeichenbereich entfernen", "Benutzer"),
                ("remove_start", "Zeichen am Anfang entfernen", "Benutzer"),
                ("remove_end", "Zeichen am Ende entfernen", "Benutzer"),
                ("insert_at", "Text an Position einfügen", "Benutzer"),
                ("remove_relative", "Vor/Nach Fundstelle entfernen (alles)", "Benutzer"),
                ("remove_before_extension", "Text direkt vor Dateiendung entfernen", "Benutzer"),
                ("remove_count_before_marker", "Zeichen direkt vor Fundstelle entfernen", "Benutzer"),
                ("normalize_separators", "Trennzeichen normalisieren", "Benutzer"),
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

                # Review/KI state must exist BEFORE _build().
                # During widget construction Qt can emit selection signals.
                self.last_ai_review = None
                self.last_batch_ai_review = None
                self.ai_reference_meta = None
                self.last_ai_comparison = None
                self.last_fusion_result = None
                self.last_evidence_result = None

                self.preview_timer = QTimer(self)
                self.preview_timer.setSingleShot(True)
                self.preview_timer.setInterval(35)
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
                self.live_check.stateChanged.connect(lambda state: self._live_preview_toggled(bool(state)))
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
                left_layout.addWidget(QLabel("Regelstapel – aktive Regelmodule"))
                self.rule_list = QListWidget()
                self.rule_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
                self.rule_list.model().rowsMoved.connect(self._rules_reordered)
                self.rule_list.currentRowChanged.connect(self._rule_selected)
                left_layout.addWidget(self.rule_list, 1)
                rule_buttons = QHBoxLayout()
                for label, handler in (("Regel +", self._add_rule),("Entfernen", self._delete_rule),("↑", lambda:self._move_rule(-1)),("↓", lambda:self._move_rule(1)),("Kopieren", self._copy_rule)):
                    b=QPushButton(label); b.clicked.connect(handler); rule_buttons.addWidget(b)
                left_layout.addLayout(rule_buttons)

                # Center: preview table + Web-parity controls
                center = QWidget(); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0)

                preview_head = QHBoxLayout()
                preview_head.addWidget(QLabel("Vorschau"))

                self.ai_review_status_label = QLabel("KI: wird geprüft …")
                self.ai_review_status_label.setMinimumWidth(180)
                self.ai_review_status_label.setToolTip(
                    "Aktuell verfügbarer KI-Review-Provider für den Smart Renamer."
                )
                preview_head.addWidget(self.ai_review_status_label)

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
                self.preview_status_filter.addItem("Sofort prüfen", "critical")
                self.preview_status_filter.addItem("Hohe Priorität", "high")
                self.preview_status_filter.currentIndexChanged.connect(self._apply_preview_filters)
                preview_head.addWidget(self.preview_status_filter)

                self.preview_sort = QComboBox()
                self.preview_sort.addItem("Name", 1)
                self.preview_sort.addItem("Vorschlag", 2)
                self.preview_sort.addItem("Relation", 3)
                self.preview_sort.addItem("Confidence", 4)
                self.preview_sort.addItem("Priorität", 6)
                self.preview_sort.currentIndexChanged.connect(self._sort_preview)
                preview_head.addWidget(self.preview_sort)
                center_layout.addLayout(preview_head)

                self.preview_summary = QLabel("0 Einträge · 0 Review · 0 Konflikte")
                center_layout.addWidget(self.preview_summary)

                preview_actions_top = QHBoxLayout()
                preview_actions_top.setSpacing(10)

                self.accept_button = QPushButton("Auswahl übernehmen")
                self.accept_button.clicked.connect(
                    lambda checked=False: self._set_selected_preview_state("accepted")
                )
                self.accept_button.setMinimumWidth(130)
                preview_actions_top.addWidget(self.accept_button)

                self.ignore_button = QPushButton("Auswahl ignorieren")
                self.ignore_button.clicked.connect(
                    lambda checked=False: self._set_selected_preview_state("ignored")
                )
                self.ignore_button.setMinimumWidth(125)
                preview_actions_top.addWidget(self.ignore_button)

                self.review_button = QPushButton("Auswahl prüfen")
                self.review_button.clicked.connect(
                    lambda checked=False: self._set_selected_preview_state("review")
                )
                self.review_button.setMinimumWidth(115)
                preview_actions_top.addWidget(self.review_button)

                self.ai_review_button = QPushButton("KI prüfen")
                self.ai_review_button.setMinimumWidth(95)
                self.ai_review_button.setToolTip(
                    "Ausgewählte Vorschauzeile mit dem verfügbaren KI-Provider prüfen."
                )
                self.ai_review_button.clicked.connect(self._run_ai_review_for_selection)
                preview_actions_top.addWidget(self.ai_review_button)

                self.ai_reference_button = QPushButton("Als Referenz")
                self.ai_reference_button.setMinimumWidth(110)
                self.ai_reference_button.clicked.connect(self._set_ai_reference_from_selection)
                preview_actions_top.addWidget(self.ai_reference_button)

                preview_actions_top.addStretch(1)
                center_layout.addLayout(preview_actions_top)

                preview_actions_bottom = QHBoxLayout()
                preview_actions_bottom.setSpacing(10)

                self.ai_batch_button = QPushButton("KI auf Auswahl")
                self.ai_batch_button.setMinimumWidth(125)
                self.ai_batch_button.setToolTip(
                    "Ausgewählte Einträge gemeinsam mit der gesetzten Referenz prüfen."
                )
                self.ai_batch_button.clicked.connect(self._run_ai_batch_for_selection)
                preview_actions_bottom.addWidget(self.ai_batch_button)

                self.fusion_button = QPushButton("Entscheidung vergleichen")
                self.fusion_button.setMinimumWidth(175)
                self.fusion_button.clicked.connect(self._run_decision_fusion_for_selection)
                preview_actions_bottom.addWidget(self.fusion_button)

                self.evidence_button = QPushButton("Belege anzeigen")
                self.evidence_button.setMinimumWidth(120)
                self.evidence_button.clicked.connect(self._run_decision_evidence_for_selection)
                preview_actions_bottom.addWidget(self.evidence_button)

                self.preview_selected_count = QLabel("0 ausgewählt")
                self.preview_selected_count.setMinimumWidth(85)
                preview_actions_bottom.addWidget(self.preview_selected_count)

                preview_actions_bottom.addStretch(1)
                center_layout.addLayout(preview_actions_bottom)

                self.table = QTableWidget(0, 10)
                self.table.setHorizontalHeaderLabels(["Status", "Original", "Vorschlag", "Relation", "Confidence", "Review", "Priorität", "Quelle", "Hinweise", "Zielpfad"])
                self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
                self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                self.table.setWordWrap(False)
                self.table.setMinimumWidth(650)
                self.table.itemSelectionChanged.connect(self._preview_selection_changed)
                header=self.table.horizontalHeader()
                header.setMinimumSectionSize(55)
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                header.setStretchLastSection(False)
                header.setToolTip("Spaltengrenzen ziehen, um jede Spalte frei zu verbreitern oder zu verkleinern.")
                self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
                self.table.setWordWrap(False)
                for column,width in {0:70,1:300,2:340,3:125,4:105,5:85,6:145,7:130,8:260,9:340}.items():
                    if column < self.table.columnCount():
                        self.table.setColumnWidth(column,width)
                center_layout.addWidget(self.table,1)

                center_layout.addWidget(QLabel("Ausgewählter Eintrag"))
                self.preview_details = QPlainTextEdit()
                self.preview_details.setReadOnly(True)
                self.preview_details.setMaximumHeight(280)
                self.preview_details.setPlaceholderText("Zeile auswählen, um vollständige Namen und Details zu sehen.")
                center_layout.addWidget(self.preview_details)

                # Right: rule editor - modular
                right=QWidget(); right_layout=QVBoxLayout(right); right_layout.setContentsMargins(0,0,0,0)
                right_layout.addWidget(QLabel("Regel-Eigenschaften"))
                self.enabled=QCheckBox("Regel aktiv"); self.enabled.stateChanged.connect(self._form_changed); right_layout.addWidget(self.enabled)

                common=QFormLayout()
                self.rule_type=QComboBox()
                for kind,label,_ in self.RULE_TYPES: self.rule_type.addItem(label,kind)
                self.rule_type.currentIndexChanged.connect(self._type_changed)
                self.rule_source=QComboBox(); self.rule_source.addItems(["Benutzer","Profil","KI","ReNamer","Plugin"])
                common.addRow("Regeltyp",self.rule_type); common.addRow("Quelle",self.rule_source)
                right_layout.addLayout(common)
                rule_action_row=QHBoxLayout()
                self.apply_rule_button=QPushButton("Regel übernehmen")
                self.apply_rule_button.setToolTip("Aktuelle Regel in den Regelstapel übernehmen und Vorschau aktualisieren.")
                self.apply_rule_button.clicked.connect(self._apply_current_rule)
                rule_action_row.addWidget(self.apply_rule_button)
                self.new_rule_button=QPushButton("Neue Regel")
                self.new_rule_button.setToolTip("Eine weitere Benutzerregel anlegen.")
                self.new_rule_button.clicked.connect(self._add_rule)
                rule_action_row.addWidget(self.new_rule_button)
                right_layout.addLayout(rule_action_row)
                rule_source_hint=QLabel("Profilregel = grün. Beim ersten Bearbeiten wird genau eine blaue Benutzerregel angelegt und automatisch ausgewählt.")
                rule_source_hint.setWordWrap(True)
                right_layout.addWidget(rule_source_hint)

                self.search=QLineEdit(); self.replacement=QLineEdit(); self.value=QLineEdit()
                self.case_mode=QComboBox(); self.case_mode.addItem("Unverändert",""); self.case_mode.addItem("klein","lower"); self.case_mode.addItem("GROSS","upper"); self.case_mode.addItem("Titel","title"); self.case_mode.addItem("Satz","sentence")
                self.start_number=QSpinBox(); self.start_number.setRange(0,999999); self.start_number.setValue(1)
                self.padding=QSpinBox(); self.padding.setRange(1,12); self.padding.setValue(2)
                self.schema=QLineEdit(); self.schema.setPlaceholderText("[titel] ([jahr])")
                self.position=QSpinBox(); self.position.setRange(1,9999); self.position.setValue(1); self.position.setToolTip("1 = erstes Zeichen, 2 = zweites Zeichen usw.")
                self.length=QSpinBox(); self.length.setRange(-1,9999); self.length.setValue(1)
                self.count_chars=QSpinBox(); self.count_chars.setRange(0,9999)
                self.needle=QLineEdit(); self.regex_pattern=QLineEdit(); self.regex_replacement=QLineEdit()
                self.case_sensitive=QCheckBox("Groß-/Kleinschreibung beachten")
                self.replace_all=QCheckBox("Alle Vorkommen"); self.replace_all.setChecked(True)
                self.whole_word=QCheckBox("Nur ganzes Wort")
                self.include_match=QCheckBox("Fundstelle mit entfernen")
                self.relative_mode=QComboBox(); self.relative_mode.addItem("Vor Fundstelle entfernen","before"); self.relative_mode.addItem("Nach Fundstelle entfernen","after")
                self.separators=QLineEdit("._")

                self.rule_stack=QStackedWidget(); self.rule_pages={}
                def add_page(key, rows):
                    page=QWidget(); form=QFormLayout(page); form.setContentsMargins(0,0,0,0)
                    for label,widget in rows: form.addRow(label,widget)
                    self.rule_pages[key]=page; self.rule_stack.addWidget(page)
                    return form

                add_page("basic",[("Suchen",self.search),("Ersetzen",self.replacement),("Wert",self.value)])
                add_page("case",[("Schreibweise",self.case_mode)])
                add_page("numbering",[("Startnummer",self.start_number),("Stellen",self.padding)])
                schema_form=add_page("schema",[("Schema",self.schema)])
                add_page("position",[("Position (1 = erstes Zeichen)",self.position),("Länge",self.length),("Anzahl Zeichen",self.count_chars)])
                add_page("relative",[("Fundstelle",self.needle),("Vor/Nach",self.relative_mode),("Anzahl Zeichen",self.count_chars),("",self.include_match),("",self.case_sensitive)])
                add_page("regex",[("RegEx-Muster",self.regex_pattern),("RegEx-Ersetzen",self.regex_replacement),("",self.case_sensitive),("",self.replace_all)])
                add_page("replace_adv",[("Suchen",self.search),("Ersetzen",self.replacement),("",self.case_sensitive),("",self.replace_all),("",self.whole_word)])
                add_page("separator",[("Trennzeichen",self.separators)])

                schema_form.addRow(QLabel("Beschriftungs-Reihenfolge"))
                self.schema_part_combo=QComboBox()
                for label,token in (
                    ("Titel","[titel]"),("Jahr","[jahr]"),("Staffel + Episode (SxxExx)","S[staffel]E[episode]"),
                    ("Staffel","S[staffel]"),("Episode","E[episode]"),("Episodentitel","[episodentitel]"),
                    ("Edition/Fassung","[edition]"),("Teil","[teil]"),("Nummer","[nummer]"),("Originalname","[original]"),("Endung","[endung]")
                ): self.schema_part_combo.addItem(label,token)
                schema_add=QWidget(); schema_add_l=QHBoxLayout(schema_add); schema_add_l.setContentsMargins(0,0,0,0); schema_add_l.addWidget(self.schema_part_combo,1)
                b=QPushButton("Hinzufügen"); b.clicked.connect(self._add_schema_part); schema_add_l.addWidget(b); schema_form.addRow(schema_add)
                self.schema_parts=QListWidget(); self.schema_parts.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove); self.schema_parts.setMaximumHeight(150); schema_form.addRow(self.schema_parts)
                schema_btn=QWidget(); schema_btn_l=QHBoxLayout(schema_btn); schema_btn_l.setContentsMargins(0,0,0,0)
                for label,handler in (("↑",lambda:self._move_schema_part(-1)),("↓",lambda:self._move_schema_part(1)),("Entfernen",self._remove_schema_part),("Schema übernehmen",self._apply_schema_order)):
                    bb=QPushButton(label); bb.clicked.connect(handler); schema_btn_l.addWidget(bb)
                schema_form.addRow(schema_btn)
                hint=QLabel("Nur im Namensschema-Modul: Reihenfolge frei wählen oder Schema direkt bearbeiten."); hint.setWordWrap(True); schema_form.addRow(hint)

                right_layout.addWidget(self.rule_stack,1)
                placeholders=QLabel("Platzhalter: [titel] [jahr] [staffel] [episode] [episodentitel] [nummer] [original] [endung]")
                placeholders.setWordWrap(True); right_layout.addWidget(placeholders)

                # Jede editierbare Regel-Eigenschaft aktualisiert den Regelstapel und
                # stößt eine debouncte Live-Vorschau an. Keine Felder dürfen hier fehlen.
                for widget in (
                    self.rule_source,self.search,self.replacement,self.value,self.case_mode,
                    self.start_number,self.padding,self.schema,self.position,self.length,self.count_chars,
                    self.needle,self.regex_pattern,self.regex_replacement,self.relative_mode,self.separators,
                    self.case_sensitive,self.replace_all,self.whole_word,self.include_match
                ):
                    if hasattr(widget, "textChanged"):
                        widget.textChanged.connect(self._form_changed)
                    elif hasattr(widget, "valueChanged"):
                        widget.valueChanged.connect(self._form_changed)
                    elif hasattr(widget, "currentIndexChanged"):
                        widget.currentIndexChanged.connect(self._form_changed)
                    elif hasattr(widget, "stateChanged"):
                        widget.stateChanged.connect(self._form_changed)


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
                    + self._format_batch_ai_detail(meta)
                    + self._format_ai_review_detail()
                )

            def _format_batch_ai_detail(self, meta):
                result=dict((meta or {}).get("batch_ai_review") or {})
                if not result:
                    return ""
                metadata=dict(result.get("metadata_review") or {})
                lines=[
                    "\n\nKI-Massenprüfung:",
                    "Vorschlag: " + str(result.get("suggested_name") or "—"),
                    "Medientyp: " + str(result.get("media_type") or "unknown"),
                    "Confidence: " + f"{float(result.get('confidence') or 0)*100:.0f}%",
                ]
                if result.get("rationale"):
                    lines.append("Begründung: " + str(result.get("rationale")))
                if metadata.get("available"):
                    lines.append("Metadaten-Prüfung: " + str(metadata.get("change_count") or 0) + " vorgeschlagene Änderung(en)")
                if result.get("warnings"):
                    lines.append("Hinweise: " + "; ".join(str(x) for x in result.get("warnings") or []))
                diagnostics=dict(result.get("metadata_diagnostics") or {})
                if diagnostics:
                    lines.append("")
                    lines.append("Metadaten-Quellen:")
                    lines.append(
                        "metadata.read: "
                        + ("ja" if diagnostics.get("metadata_read_present") else "nein")
                    )
                    lines.append(
                        "metadata.review: "
                        + ("ja" if diagnostics.get("metadata_review_present") else "nein")
                    )
                    lines.append(
                        "NFO: "
                        + ("gefunden" if diagnostics.get("nfo_present") else "nicht gefunden")
                    )
                    values=[]
                    values.extend(diagnostics.get("episode_title_values_review") or [])
                    values.extend(diagnostics.get("episode_title_values_read") or [])
                    if values:
                        lines.append("Episodentitel-Felder: " + " | ".join(str(x) for x in values))
                    else:
                        lines.append("Episodentitel-Felder: keine gefunden")
                lines.append("Nur Vorschau · keine automatische Übernahme.")
                formatted = "\\n".join(lines)
                return str(formatted).replace("\\n", "\n")

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
                    + self._format_ai_comparison_detail()
                    + self._format_fusion_detail()
                )

            def _format_ai_comparison_detail(self):
                result = self.last_ai_comparison
                if not result:
                    return ""
                return "\n" + self.plugin.ai_review_comparison.format_text(result)

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
                    + self._format_evidence_detail()
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
                self.last_ai_comparison = self.plugin.compare_review_recommendation(
                    meta,
                    ai_result,
                )
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

            def _format_evidence_detail(self):
                result = self.last_evidence_result
                if not result:
                    return ""
                items = result.get("items") or []
                lines = ["\n\nEntscheidungsbelege:"]
                for item in items:
                    confidence = float(item.get("confidence") or 0)
                    support = item.get("supports_decision")
                    suffix = ""
                    if support is True:
                        suffix = " · unterstützt"
                    elif support is False:
                        suffix = " · widerspricht"
                    lines.append(
                        "- "
                        + str(item.get("label") or item.get("source") or "Quelle")
                        + ": "
                        + str(item.get("value") or "—")
                        + f" · {confidence*100:.0f}%"
                        + suffix
                    )
                    if item.get("detail"):
                        lines.append("  " + str(item.get("detail")))
                lines.append(
                    "\nKonflikte: " + str(result.get("conflict_count") or 0)
                )
                lines.append("Keine automatische Ausführung.")
                return "\n".join(lines)

            def _run_decision_evidence_for_selection(self):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                if len(rows) != 1:
                    self.status.setText(
                        "Für Entscheidungsbelege bitte genau einen Vorschau-Eintrag auswählen."
                    )
                    return

                meta = self._row_meta(rows[0])
                ai_result = self.last_ai_review or self.plugin.analyze_review_with_ai(meta)
                fusion_result = self.last_fusion_result or self.plugin.fuse_review_decision(
                    meta, ai_result
                )
                self.last_ai_review = ai_result
                self.last_fusion_result = fusion_result
                self.last_evidence_result = self.plugin.build_decision_evidence(
                    meta, ai_result, fusion_result
                )
                self._preview_selection_changed()
                self.status.setText(
                    "Entscheidungsbelege angezeigt. Keine Datei wurde verändert."
                )

            def _refresh_ai_review_status(self):
                status = self.plugin.ai_review_status()
                if status.get("available"):
                    self.ai_review_status_label.setText(
                        "KI: " + str(status.get("provider") or "verfügbar")
                    )
                    self.ai_review_button.setEnabled(True)
                    batch_status = self.plugin.batch_ai_review_status()
                    self.ai_batch_button.setEnabled(bool(batch_status.get("available")))
                else:
                    self.ai_review_status_label.setText("KI: nicht verfügbar")
                    self.ai_review_button.setEnabled(False)
                    self.ai_batch_button.setEnabled(False)

            def _set_ai_reference_from_selection(self):
                rows=sorted({index.row() for index in self.table.selectedIndexes()})
                if len(rows)!=1:
                    self.status.setText("Für eine KI-Referenz bitte genau einen Vorschau-Eintrag auswählen.")
                    return
                self.ai_reference_meta=dict(self._row_meta(rows[0]) or {})
                self.status.setText("KI-Referenz gesetzt: " + str(self.ai_reference_meta.get("proposed_name") or self.ai_reference_meta.get("original_name") or "Eintrag"))

            def _active_schema_context(self):
                for rule in self.rules:
                    if bool(rule.get("enabled",True)) and str(rule.get("type") or "")=="schema":
                        return {"template":str(rule.get("template") or ""),"source":str(rule.get("source") or "")}
                return {}

            def _run_ai_batch_for_selection(self):
                rows=sorted({index.row() for index in self.table.selectedIndexes()})
                if not rows:
                    self.status.setText("Für KI-Massenprüfung bitte mindestens einen Vorschau-Eintrag auswählen.")
                    return
                items=[dict(self._row_meta(row) or {}) for row in rows]
                self.last_batch_ai_review=self.plugin.analyze_batch_with_ai(
                    items,
                    reference=dict(self.ai_reference_meta or {}),
                    schema=self._active_schema_context(),
                )
                by_path={str(x.get("source_path") or ""):x for x in (self.last_batch_ai_review.get("items") or [])}
                for row in rows:
                    meta=dict(self._row_meta(row) or {})
                    result=by_path.get(str(meta.get("source_path") or ""))
                    if result:
                        meta["batch_ai_review"]=dict(result)

                        # KI-Massenprüfung darf den sichtbaren Vorschlag in der
                        # Preview aktualisieren, aber niemals die Datei selbst.
                        ai_suggested=str(result.get("suggested_name") or "").strip()
                        if ai_suggested:
                            meta["proposed_name"]=ai_suggested
                            proposal_item=self.table.item(row,2)
                            if proposal_item is not None:
                                proposal_item.setText(ai_suggested)
                                proposal_item.setToolTip(
                                    "KI-Massenprüfung · nur Vorschau, noch nicht ausgeführt"
                                )

                        item=self.table.item(row,0)
                        if item is not None:
                            item.setData(Qt.ItemDataRole.UserRole,meta)
                self._preview_selection_changed()
                metadata=self.last_batch_ai_review.get("metadata_status") or {}
                self.status.setText(
                    f"KI-Massenprüfung: {len(rows)} Einträge geprüft · "
                    f"Metadata Editor: {'lesen/review' if metadata.get('read') or metadata.get('review') else 'nicht verfügbar'} · "
                    "keine Datei und keine Metadaten wurden verändert."
                )

            def _run_ai_review_for_selection(self):
                rows = sorted({index.row() for index in self.table.selectedIndexes()})
                if len(rows) != 1:
                    self.status.setText(
                        "Für KI-Review bitte genau einen Vorschau-Eintrag auswählen."
                    )
                    return
                meta = self._row_meta(rows[0])
                self.last_ai_review = self.plugin.analyze_review_with_ai(meta)
                self.last_ai_comparison = self.plugin.compare_review_recommendation(
                    meta,
                    self.last_ai_review,
                )
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
                        wanted == "all"
                        or meta.get("status") == wanted
                        or meta.get("priority_level") == wanted
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
                critical = 0
                high = 0
                for row in range(self.table.rowCount()):
                    level = self._row_meta(row).get("priority_level")
                    critical += int(level == "critical")
                    high += int(level == "high")
                self.preview_summary.setText(
                    f"{self.table.rowCount()} Einträge · {review} Review · {conflict} Konflikte · "
                    f"{critical} sofort · {high} hoch"
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
                # A profile switch may replace profile-owned rules only.
                # User/AI/ReNamer/Plugin rules must survive the switch.
                self.rules = merge_profile_rules(
                    self.rules,
                    profile.get("rules", []),
                )
                self._render_rules()
                self._schedule_preview()

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

            def _schema_label_for_token(self, token):
                return {
                    "[titel]":"Titel","[jahr]":"Jahr","S[staffel]E[episode]":"Staffel + Episode (SxxExx)",
                    "S[staffel]":"Staffel","E[episode]":"Episode","[episodentitel]":"Episodentitel",
                    "[edition]":"Edition/Fassung","[teil]":"Teil","[nummer]":"Nummer",
                    "[original]":"Originalname","[endung]":"Endung",
                }.get(str(token),str(token))

            def _load_schema_parts(self, rule):
                self.schema_parts.clear()
                order=list(rule.get("schema_order") or [])
                for token in order:
                    item=QListWidgetItem(self._schema_label_for_token(token))
                    item.setData(Qt.ItemDataRole.UserRole,token)
                    self.schema_parts.addItem(item)

            def _add_schema_part(self):
                token=self.schema_part_combo.currentData()
                item=QListWidgetItem(self._schema_label_for_token(token)); item.setData(Qt.ItemDataRole.UserRole,token)
                self.schema_parts.addItem(item); self.schema_parts.setCurrentRow(self.schema_parts.count()-1)
                self._form_changed()

            def _remove_schema_part(self):
                row=self.schema_parts.currentRow()
                if row>=0:
                    self.schema_parts.takeItem(row)
                    self._form_changed()

            def _move_schema_part(self, delta):
                row=self.schema_parts.currentRow(); target=row+delta
                if row<0 or target<0 or target>=self.schema_parts.count(): return
                item=self.schema_parts.takeItem(row); self.schema_parts.insertItem(target,item); self.schema_parts.setCurrentRow(target)
                self._form_changed()

            def _apply_schema_order(self):
                tokens=[self.schema_parts.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.schema_parts.count())]
                self.schema.setText(" - ".join(str(x) for x in tokens if x)); self._form_changed()

            def _rule_page_key(self, kind):
                return {
                    "replace":"basic","remove":"basic","prefix":"basic","suffix":"basic","trim":"basic",
                    "case":"case","numbering":"numbering","schema":"schema",
                    "remove_range":"position","remove_start":"position","remove_end":"position","insert_at":"position",
                    "remove_relative":"relative","remove_before_extension":"basic","remove_count_before_marker":"relative","regex_replace":"regex","replace_advanced":"replace_adv",
                    "normalize_separators":"separator",
                }.get(str(kind or ""),"basic")

            def _show_rule_page(self, kind):
                page=self.rule_pages.get(self._rule_page_key(kind))
                if page is not None: self.rule_stack.setCurrentWidget(page)

            def _apply_current_rule(self):
                """Editorwerte übernehmen, Regelstapel aktualisieren und Vorschau sofort neu planen."""
                row=self.rule_list.currentRow()
                if not (0 <= row < len(self.rules)):
                    self._add_rule()
                    row=self.rule_list.currentRow()
                self._form_changed()
                self._render_rules(row)
                self._schedule_preview()

            def _rule_selected(self,row):
                if not (0 <= row < len(self.rules)): return
                rule=self.rules[row]; self._updating_form=True
                self.enabled.setChecked(bool(rule.get("enabled",True)))
                idx=self.rule_type.findData(rule.get("type")); self.rule_type.setCurrentIndex(max(0,idx)); self._show_rule_page(rule.get("type"))
                self.rule_source.setCurrentText(str(rule.get("source") or "Benutzer"))
                self.search.setText(str(rule.get("old") or "")); self.replacement.setText(str(rule.get("new") or "")); self.value.setText(str(rule.get("value") or ""))
                idx=self.case_mode.findData(rule.get("mode") or ""); self.case_mode.setCurrentIndex(max(0,idx))
                self.start_number.setValue(int(rule.get("start",1))); self.padding.setValue(int(rule.get("padding",2))); self.schema.setText(str(rule.get("template") or ""))
                self.position.setValue(max(1,int(rule.get("position") or 1))); self.length.setValue(int(rule.get("length") if rule.get("length") not in (None,"") else 1))
                self.count_chars.setValue(int(rule.get("count") or 0)); self.needle.setText(str(rule.get("needle") or ""))
                self.regex_pattern.setText(str(rule.get("pattern") or "")); self.regex_replacement.setText(str(rule.get("replacement") or ""))
                self.case_sensitive.setChecked(bool(rule.get("case_sensitive"))); self.replace_all.setChecked(bool(rule.get("replace_all",True)))
                self.whole_word.setChecked(bool(rule.get("whole_word"))); self.include_match.setChecked(bool(rule.get("include_match")))
                idx=self.relative_mode.findData(str(rule.get("relative_mode") or "before")); self.relative_mode.setCurrentIndex(max(0,idx))
                self.separators.setText(str(rule.get("separators") or "._"))
                self._load_schema_parts(rule)
                self._updating_form=False

            def _type_changed(self,*_):
                self._show_rule_page(self.rule_type.currentData())
                self._form_changed()

            def _form_changed(self,*_):
                if self._updating_form: return
                row=self.rule_list.currentRow()
                if not (0 <= row < len(self.rules)): return

                original_rule=self.rules[row]
                original_source=str(original_rule.get("source") or "").strip().casefold()
                if original_source in ("profil","profile"):
                    clone=dict(original_rule)
                    clone["source"]="Benutzer"
                    clone["label"]=str(clone.get("label") or clone.get("type") or "Regel") + " (Benutzer)"
                    self.rules.append(clone)
                    row=len(self.rules)-1

                    # Wichtig: Die neue blaue Benutzerregel sofort sichtbar
                    # machen UND auswählen. Sonst würde die nächste
                    # Feldänderung erneut die grüne Profilregel kopieren.
                    self._updating_form=True
                    try:
                        self._render_rules(row)
                        self.rule_list.setCurrentRow(row)
                        self.rule_source.blockSignals(True)
                        self.rule_source.setCurrentText("Benutzer")
                        self.rule_source.blockSignals(False)
                    finally:
                        self._updating_form=False

                kind=self.rule_type.currentData(); rule=self.rules[row]
                rule.update({"type":kind,"enabled":self.enabled.isChecked(),"source":self.rule_source.currentText(),
                    "old":self.search.text(),"new":self.replacement.text(),"value":self.value.text(),"mode":self.case_mode.currentData(),
                    "start":self.start_number.value(),"padding":self.padding.value(),"template":self.schema.text(),
                    "schema_order":[self.schema_parts.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.schema_parts.count())],
                    "position":self.position.value(),"length":self.length.value(),"count":self.count_chars.value(),"needle":self.needle.text(),
                    "pattern":self.regex_pattern.text(),"replacement":self.regex_replacement.text(),
                    "case_sensitive":self.case_sensitive.isChecked(),"replace_all":self.replace_all.isChecked(),"whole_word":self.whole_word.isChecked(),
                    "include_match":self.include_match.isChecked(),"relative_mode":self.relative_mode.currentData(),"separators":self.separators.text()})
                labels=dict((k,l) for k,l,_ in self.RULE_TYPES); rule["label"]=labels.get(kind,kind)
                self._render_rules(row); self._schedule_preview()

            def _schedule_preview(self):
                if not self.live_check.isChecked():
                    return
                if not self.paths:
                    return
                self.status.setText("Live-Vorschau wird aktualisiert …")
                self.preview_timer.start()

            def _live_preview_toggled(self, checked):
                if checked:
                    self._schedule_preview()

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
                        str(item.get("priority_label") or "Niedrige Priorität"),
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
                        "priority_level": str(item.get("priority_level") or "low"),
                        "priority_score": int(item.get("priority_score") or 0),
                        "priority_label": str(item.get("priority_label") or "Niedrige Priorität"),
                        "issues": issue_text,
                        "target_path": str(item.get("target_path") or ""),
                    }
                    for c,value in enumerate(values):
                        cell=QTableWidgetItem(str(value))
                        if c in {1,2,6,8,9}:
                            cell.setToolTip(str(value))
                        if c == 0:
                            cell.setData(Qt.ItemDataRole.UserRole, row_meta)
                        if c == 6:
                            cell.setData(
                                Qt.ItemDataRole.UserRole + 1,
                                int(item.get("priority_score") or 0),
                            )
                            cell.setToolTip(
                                str((item.get("review_priority") or {}).get("reason") or "")
                            )
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

    def build_decision_evidence(self, renamer_payload, ai_result=None, fusion_result=None):
        result = self.decision_evidence_service.build(
            dict(renamer_payload or {}),
            dict(ai_result or {}),
            dict(fusion_result or {}),
        )
        result["execution_locked"] = True
        result["execution_allowed"] = False
        result["human_confirmation_required"] = True
        return result

    def analyze_and_fuse_review(self, payload):
        source = dict(payload or {})
        ai_result = self.analyze_review_with_ai(source)
        fusion = self.fuse_review_decision(source, ai_result)
        evidence = self.build_decision_evidence(source, ai_result, fusion)
        return {
            "ai": ai_result,
            "fusion": fusion,
            "evidence": evidence,
            "execution_locked": True,
            "execution_allowed": False,
            "human_confirmation_required": True,
        }


