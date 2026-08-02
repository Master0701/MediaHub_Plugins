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
from services.knowledge_learning import KnowledgeLearningService
from services.knowledge_engine.proposal_store import GraphProposalStore
from services.knowledge_engine.order_proposals import KnowledgeGraphOrderProposalService
from services.knowledge_engine.completeness import KnowledgeGraphCompletenessService
from services.knowledge_engine.missing_media_queue import MissingMediaQueue
from services.knowledge_engine.missing_media_export import MissingMediaExportService
from services.knowledge_engine.missing_media_handoff import MissingMediaHandoffService
from services.knowledge_engine.identity_cleanup import IdentityCleanupService
from services.knowledge_engine.semantic_graph_reasoner import SemanticGraphReasoner
from services.knowledge_engine.reasoner_learning import ReasonerLearningStore
from services.source_manager_v2 import SourceManagerV2
from services.source_scanner import ControlledSourceScanner
from services.source_conflict_resolver import SourceConflictResolver
from services.parser_manager import ParserManager
from services.knowledge_extractor import KnowledgeExtractor
from services.semantic_knowledge_engine import SemanticKnowledgeEngine
from services.reasoning_context import ReasoningContext, ReasoningContextStore
from services.semantic_field_classifier import SemanticFieldClassifier
from services.knowledge_graph_builder import KnowledgeGraphBuilder
from services.persistent_knowledge_graph import PersistentKnowledgeGraphStore
from services.relationship_builder import RelationshipBuilder
from services.character_cast_resolver import CharacterCastResolver
from services.character_intelligence import CharacterIntelligence
from services.relationship_intelligence import RelationshipIntelligence
from services.character_relationship_engine import CharacterRelationshipEngine
from services.relationship_identity_map_builder import RelationshipIdentityMapBuilder
from services.character_alias_identity_fusion import CharacterAliasIdentityFusion
from services.franchise_collection_intelligence import FranchiseCollectionIntelligence
from services.franchise_relation_intelligence import FranchiseRelationIntelligence
from services.timeline_order_intelligence import TimelineOrderIntelligence
from services.franchise_connection_intelligence import FranchiseConnectionIntelligence
from services.universe_intelligence import UniverseIntelligence
from services.character_role_intelligence import CharacterRoleIntelligence
from services.character_relationship_intelligence import CharacterRelationshipIntelligence
from services.entity_intelligence import EntityIntelligence
from services.reasoning_intelligence import ReasoningIntelligence
from services.multi_source_fusion import MultiSourceFusion
from services.pipeline_debug_monitor import PipelineDebugMonitor
from services.semantic_reasoning_engine import SemanticReasoningEngine
from services.knowledge_engine.knowledge_graph_merge_validator import KnowledgeGraphMergeValidator
from services.event_intelligence import EventIntelligence
from services.knowledge_graph_builder import KnowledgeGraphBuilder
from services.universe_franchise_builder import UniverseFranchiseBuilder
from services.learning_status import LearningStatusService
from services.media_analyzer import MediaAnalyzer
from services.mediahub_reader import MediaHubDatabaseReader
from services.paths import resolve_database_paths
from services.tool_resolver import ToolResolver

try:
    from PySide6.QtCore import QObject, Qt, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QScrollArea,
        QSpinBox,
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
    VERSION = "5.3.0"

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
        self.tool_resolver = ToolResolver(self.base_dir, self.plugin_path)
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
        self.knowledge_learning = KnowledgeLearningService(self.knowledge_db_path)
        self.graph_proposals = GraphProposalStore(self.knowledge_db_path)
        self.graph_order_proposals = KnowledgeGraphOrderProposalService(self.knowledge_engine)
        self.graph_completeness = KnowledgeGraphCompletenessService(self.knowledge_engine)
        self.missing_media_queue = MissingMediaQueue(self.knowledge_db_path)
        self.missing_media_export = MissingMediaExportService(self.missing_media_queue)
        self.missing_media_handoff = MissingMediaHandoffService(self.missing_media_queue, self.knowledge_db_path)
        self.identity_cleanup = IdentityCleanupService(self.knowledge_db_path, self.knowledge_engine.store)
        self.semantic_graph_reasoner = SemanticGraphReasoner(self.knowledge_engine)
        self.reasoner_learning = ReasonerLearningStore(self.knowledge_db_path)
        self.source_manager_v2 = SourceManagerV2(self.knowledge_db_path)
        self.controlled_source_scanner = ControlledSourceScanner(self.source_manager_v2.cache_path)
        self.source_conflict_resolver = SourceConflictResolver(self.knowledge_db_path)
        self.parser_manager = ParserManager()
        self.knowledge_extractor = KnowledgeExtractor()
        self.semantic_knowledge_engine = SemanticKnowledgeEngine()
        self.reasoning_context_store = ReasoningContextStore(self.knowledge_db_path)
        self.semantic_field_classifier = SemanticFieldClassifier()
        self.knowledge_graph_builder = KnowledgeGraphBuilder()
        self.persistent_graph_store = PersistentKnowledgeGraphStore(self.knowledge_db_path)
        self.relationship_builder = RelationshipBuilder()
        self.character_cast_resolver = CharacterCastResolver()
        self.character_intelligence = CharacterIntelligence()
        self.relationship_intelligence = RelationshipIntelligence()
        self.character_relationship_engine = CharacterRelationshipEngine()
        self.event_intelligence = EventIntelligence()
        self.knowledge_graph_builder = KnowledgeGraphBuilder()
        self.universe_franchise_builder = UniverseFranchiseBuilder()
        self.timeline_order_intelligence = TimelineOrderIntelligence()
        self.franchise_connection_intelligence = FranchiseConnectionIntelligence()
        self.universe_intelligence = UniverseIntelligence()
        self.character_role_intelligence = CharacterRoleIntelligence()
        self.character_relationship_intelligence = CharacterRelationshipIntelligence()
        self.entity_intelligence = EntityIntelligence()
        self.reasoning_intelligence = ReasoningIntelligence()
        self.multi_source_fusion = MultiSourceFusion()
        self.pipeline_debug_monitor = PipelineDebugMonitor()
        self.semantic_reasoning_engine = SemanticReasoningEngine()
        self.last_pipeline_debug_snapshot = None
        self.learning_status = LearningStatusService(self.knowledge_db_path)

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
            "learning": self.learning_status.status(),
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
        """Formatiert die Analyse mit bestätigter Identität als oberster Wahrheit."""
        identification = result.get("identification") or {}
        semantic = result.get("semantic_identity") or {}
        semantic_identity = semantic.get("identity") or {}
        fingerprint_agent = (
            ((result.get("in_video") or {}).get("agents") or {})
            .get("fingerprint_agent")
            or {}
        )
        matched_identity = fingerprint_agent.get("matched_identity") or {}

        preferred_source = "Dateiname"
        if semantic_identity.get("title"):
            preferred_identity = semantic_identity
            preferred_source = "Semantic Identity"
        elif matched_identity.get("title"):
            preferred_identity = matched_identity
            preferred_source = "Bestätigter Fingerprint"
        else:
            preferred_identity = {
                "media_type": identification.get("media_type"),
                "title": identification.get("title_candidate"),
                "year": identification.get("year"),
                "season": identification.get("season"),
                "episode": identification.get("episode"),
                "edition": identification.get("edition_candidate"),
            }

        media_type = preferred_identity.get("media_type") or "unknown"
        title = preferred_identity.get("title") or "-"
        year = preferred_identity.get("year")
        season = preferred_identity.get("season")
        episode = preferred_identity.get("episode")
        edition = preferred_identity.get("edition")

        summary = result.get("summary") or {}
        cache = result.get("cache") or {}
        warnings = result.get("warnings") or []
        decision = result.get("decision") or {}
        quality = result.get("quality") or {}
        in_video = result.get("in_video") or {}
        agents = in_video.get("agents") or {}

        duration = summary.get("duration_seconds")
        duration_text = "-"
        if duration is not None:
            total = round(float(duration))
            duration_text = f"{total // 60:02d}:{total % 60:02d} Minuten"

        semantic_status = semantic.get("final_status")
        semantic_confidence = semantic.get("confidence_percent")
        status = semantic_status or decision.get("status") or "-"
        confidence = (
            semantic_confidence
            if semantic_confidence is not None
            else decision.get("confidence_percent")
        )

        lines = [
            "ERKENNUNGSVORSCHLAG",
            "-------------------",
            f"Typ: {media_type}",
            f"Titel: {title}",
            f"Staffel: {season if season is not None else '-'}",
            f"Folge(n): {episode if episode is not None else '-'}",
            f"Jahr: {year if year is not None else '-'}",
            f"Fassung(en): {edition if edition else '-'}",
            f"Primäre Quelle: {preferred_source}",
            "",
            "KI-ENTSCHEIDUNG",
            "---------------",
            f"Status: {status}",
            f"Gesamtsicherheit: {confidence if confidence is not None else '-'} %",
        ]

        if semantic.get("reason"):
            lines.append(f"Warum: {semantic.get('reason')}")
        else:
            explanation = decision.get("explanation") or {}
            conclusion = explanation.get("conclusion")
            if conclusion:
                lines.append(f"Warum: {conclusion}")

        best = semantic.get("best_candidate") or {}
        explainable = best.get("explainable_decision") or {}
        if explainable.get("recommendation"):
            lines.append(
                f"Empfehlung: {explainable.get('recommendation')}"
            )
        elif decision.get("recommendation"):
            lines.append(
                f"Empfehlung: {decision.get('recommendation')}"
            )

        lines.extend(["", "KI-BEWEISE", "-----------"])
        if preferred_source == "Semantic Identity":
            label = f"✔ Semantic Identity: {title}"
            if year:
                label += f" ({year})"
            lines.append(label)
        elif preferred_source == "Bestätigter Fingerprint":
            label = f"✔ Bestätigter Fingerprint: {title}"
            if year:
                label += f" ({year})"
            lines.append(label)

        evidence_items = best.get("evidence") or []
        if evidence_items:
            for item in evidence_items:
                source = item.get("source") or "Beleg"
                value = item.get("value") or "-"
                strength = item.get("weighted_strength")
                marker = "✔" if item.get("used_for_group_score") else "○"
                if strength is None:
                    lines.append(f"{marker} {source}: {value}")
                else:
                    lines.append(
                        f"{marker} {source}: {value} "
                        f"({round(float(strength) * 100, 1)} %)"
                    )
        else:
            for item in decision.get("evidence") or []:
                marker = "✔" if item.get("supports") else "○"
                lines.append(
                    f"{marker} {item.get('label')}: "
                    f"{item.get('value')}"
                )

        lines.extend(
            [
                "",
                "TECHNISCHE DATEN",
                "-----------------",
                f"Laufzeit: {duration_text}",
                f"Container: {summary.get('container') or '-'}",
                f"Video: {summary.get('video_codec') or '-'}",
                f"Auflösung: "
                f"{summary.get('width') or '-'} × "
                f"{summary.get('height') or '-'}",
                f"HDR/Dolby Vision: {summary.get('hdr_format') or '-'}",
                f"Tonspuren: {summary.get('audio_tracks') or 0}",
                f"Untertitel: {summary.get('subtitle_tracks') or 0}",
                f"Kapitel: {summary.get('chapters') or 0}",
                "",
                "QUALITÄTSBEWERTUNG",
                "-------------------",
                f"Gesamt: {quality.get('overall_score') or '-'}",
                f"Status: {quality.get('status') or quality.get('label') or '-'}",
                "",
                "IN-VIDEO-ANALYSE",
                "-----------------",
                f"Status: {in_video.get('state') or '-'}",
                f"Ausgeführte Agenten: {in_video.get('completed_agents') or 0}",
            ]
        )

        for agent_name, agent_result in agents.items():
            lines.append(
                f"{agent_name}: {(agent_result or {}).get('state') or '-'}"
            )

        lines.extend(
            [
                "",
                "ANALYSEWEG",
                "-----------",
                "Cache: " + ("verwendet" if cache.get("hit") else "neu analysiert"),
            ]
        )

        if warnings:
            lines.extend(["", "WARNUNGEN", "---------"])
            lines.extend(str(warning) for warning in warnings if warning)

        return "\n".join(lines)

    def register_fingerprint_reference(self, analysis):
        """Speichert einen vom Benutzer bestätigten Fingerprint als lokale Referenz."""
        return self.media_analyzer.register_fingerprint_reference(analysis)

    def confirm_and_learn_identity(self, analysis, corrected_identity=None):
        """Speichert bestätigte Identität und übernimmt sie in den Knowledge Graph."""
        result = self.knowledge_learning.confirm(
            analysis,
            corrected_identity,
        )
        identity = dict(corrected_identity or {})
        identity.update(
            {
                "identity_id": result.get("identity_id"),
                "aliases": result.get("aliases") or [],
                "confidence": result.get("confidence") or 1.0,
            }
        )
        result["knowledge_graph"] = self.knowledge_engine.upsert_identity(
            identity,
            source="user_confirmation",
            confirmed_by_user=True,
        )
        result["missing_media_reconciliation"] = (
            self.missing_media_queue.reconcile_entity(
                (result.get("knowledge_graph") or {}).get("entity") or {}
            )
        )
        return result

    def get_knowledge_graph_status(self):
        return self.knowledge_engine.status()

    def get_pipeline_debug_snapshot(self):
        return dict(self.last_pipeline_debug_snapshot or {})

    def get_pipeline_debug_text(self):
        return self.pipeline_debug_monitor.format_text(
            self.last_pipeline_debug_snapshot
        )

    def create_knowledge_graph_entity(self, identity):
        result = self.knowledge_engine.upsert_identity(
            dict(identity or {}),
            source="desktop_gui_manual",
            confirmed_by_user=True,
        )
        result["missing_media_reconciliation"] = (
            self.missing_media_queue.reconcile_entity(
                result.get("entity") or {}
            )
        )
        return result

    def delete_knowledge_graph_relation(self, relation_id):
        return self.knowledge_engine.delete_relation(str(relation_id))

    def delete_knowledge_graph_order(self, order_id):
        return self.knowledge_engine.delete_order(str(order_id))

    def migrate_learned_identities_to_graph(self):
        snapshot = self.knowledge_learning.export_snapshot()
        results = []
        for learned in snapshot.get("identities") or []:
            aliases = [
                item.get("alias")
                for item in snapshot.get("aliases") or []
                if item.get("identity_id") == learned.get("id")
                and item.get("alias")
            ]
            results.append(
                self.knowledge_engine.upsert_identity(
                    {
                        "title": learned.get("canonical_title"),
                        "media_type": learned.get("media_type") or "other",
                        "year": learned.get("release_year"),
                        "season": learned.get("season"),
                        "episode": learned.get("episode"),
                        "edition": learned.get("edition"),
                        "external_ids": learned.get("external_ids") or {},
                        "aliases": aliases,
                        "identity_id": learned.get("id"),
                        "confidence": learned.get("confidence") or 1.0,
                    },
                    source="learning_database_migration",
                    confirmed_by_user=bool(
                        learned.get("confirmed_by_user")
                    ),
                )
            )
        return {
            "schema_version": 1,
            "learned_identity_count": len(
                snapshot.get("identities") or []
            ),
            "processed_count": len(results),
            "created_count": sum(
                bool(item.get("created")) for item in results
            ),
            "results": results,
        }

    def get_knowledge_graph_snapshot(self):
        migration = self.migrate_learned_identities_to_graph()
        reconciliation = self.missing_media_queue.reconcile_entities(
            self.knowledge_engine.all_items()
        )
        return {
            "status": self.knowledge_engine.status(),
            "migration": migration,
            "missing_media_reconciliation": reconciliation,
            "entities": self.knowledge_engine.all_items(),
            "relations": self.knowledge_engine.store.all_relations(),
            "orders": self.knowledge_engine.store.all_orders(),
        }

    def propose_knowledge_graph_relationships(self, identities):
        result = self.knowledge_engine.propose_relationships(identities)
        result["queue"] = self.graph_proposals.add_many(
            result.get("proposals") or []
        )
        return result

    def get_knowledge_graph_proposals(self, status=None):
        return self.graph_proposals.list(status)

    def analyze_knowledge_graph_completeness(self):
        result = self.graph_completeness.analyze()
        result["queue"] = self.missing_media_queue.add_from_completeness(
            result
        )
        return result

    def get_missing_media_items(self, status=None):
        return self.missing_media_queue.list(status)

    def update_missing_media_item(self, item_id, status, note=None):
        return self.missing_media_queue.set_status(
            item_id,
            status,
            note,
        )

    def get_missing_media_status(self):
        return self.missing_media_queue.status()

    def build_missing_media_export(self, statuses=None):
        return self.missing_media_export.build_payload(
            statuses=statuses
        )

    def export_missing_media(
        self,
        destination,
        format_name,
        statuses=None,
    ):
        return self.missing_media_export.write_file(
            destination,
            format_name=format_name,
            statuses=statuses,
        )

    def create_missing_media_handoff(
        self,
        target_plugin,
        statuses=None,
    ):
        return self.missing_media_handoff.create_handoff(
            target_plugin=target_plugin,
            statuses=statuses,
        )

    def apply_missing_media_handoff_result(self, result):
        return self.missing_media_handoff.apply_result(
            dict(result or {})
        )

    def get_source_manager_status(self):
        return self.source_manager_v2.status()

    def get_sources(self):
        return self.source_manager_v2.list_sources()

    def get_source(self, source_id):
        source = self.source_manager_v2.get_source(source_id)
        return dict(source) if source is not None else None

    def add_custom_source(self, **source):
        return self.source_manager_v2.add_custom_source(**source)

    def update_source(self, source_id, **changes):
        return self.source_manager_v2.update_source(
            source_id,
            **changes,
        )

    def remove_source(self, source_id):
        return self.source_manager_v2.remove_source(source_id)

    def create_source_scan_preview(
        self,
        source_id,
        requested_url=None,
        context=None,
    ):
        return self.source_manager_v2.create_scan_preview(
            source_id,
            requested_url=requested_url,
            context=context,
        )

    def compare_source_results(self, source_results):
        return self.source_conflict_resolver.compare(
            list(source_results or [])
        )

    def confirm_source_fields(
        self,
        comparison_id,
        selected_fields,
        target_entity_id=None,
        note=None,
    ):
        decision = self.source_conflict_resolver.confirm_fields(
            comparison_id,
            dict(selected_fields or {}),
            target_entity_id=target_entity_id,
            note=note,
        )
        if target_entity_id:
            entity = self.knowledge_engine.store.get_entity(
                str(target_entity_id)
            )
            if entity is None:
                raise KeyError(
                    f"Knowledge-Graph-Entität nicht gefunden: "
                    f"{target_entity_id}"
                )
            metadata = dict(entity.get("metadata") or {})
            for field, value in dict(selected_fields or {}).items():
                if field in {"title", "year", "media_type", "aliases"}:
                    entity[field] = value
                else:
                    metadata[field] = value
            entity["metadata"] = metadata
            self.knowledge_engine.store.save()
        return decision

    def get_source_conflict_status(self):
        return self.source_conflict_resolver.status()

    def get_universe_franchise_builder_status(self):
        return {
            "strategy": "universe_franchise_builder_v330",
            "supported_nodes": [
                "universe", "franchise", "team",
                "location", "organization", "character"
            ],
            "supported_edges": [
                "belongs_to", "part_of", "member_of",
                "replaced_by", "located_in", "enemy_of", "ally_of"
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_knowledge_graph_status(self):
        return {
            "strategy": "knowledge_graph_builder_v402",
            "phase": 1,
            "features": [
                "canonical_nodes",
                "deduplicated_edges",
                "placeholder_nodes",
                "stable_node_ids",
                "stable_edge_ids",
                "graph_statistics",
                "legacy_base_graph_integration",
                "knowledge_result_integration",
                "main_node_preservation",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_event_intelligence_status(self):
        return {
            "strategy": "event_intelligence_v386",
            "supported_event_types": [
                "battle",
                "victory",
                "rescue",
                "kidnapping",
                "discovery",
                "creation",
            ],
            "supported_edges": [
                "participates_in",
                "participant",
                "occurs_at",
                "uses",
                "winner",
                "loser",
                "destination",
                "object",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_character_relationship_status(self):
        return {
            "strategy": "character_relationship_engine_v413",
            "phase": 1,
            "supported_edges": [
                "spouse_of",
                "parent_of",
                "child_of",
                "half_sibling_of",
                "sibling_of",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_relationship_intelligence_status(self):
        return {
            "strategy": "relationship_intelligence_v360",
            "supported_nodes": [
                "character",
                "character_alias",
                "artifact",
            ],
            "supported_edges": [
                "works_with",
                "rescues",
                "rescued_by",
                "fights_with",
                "kidnaps",
                "kidnapped_by",
                "protects",
                "created_by",
                "creates",
                "alias_of",
                "sibling_of",
                "finds",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_character_intelligence_status(self):
        return {
            "strategy": "character_intelligence_v350",
            "supported_nodes": ["character", "location"],
            "supported_edges": [
                "married_to",
                "parent_of",
                "child_of",
                "sibling_of",
                "enemy_of",
                "ally_of",
                "ruler_of",
                "lives_in",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_character_cast_resolver_status(self):
        return {
            "strategy": "character_cast_intelligence_v340",
            "supported_nodes": ["person", "character", "character_alias"],
            "supported_edges": [
                "has_cast", "portrays", "portrayed_by",
                "appears_in", "alias_of", "voices"
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_relationship_builder_status(self):
        return {
            "strategy": "relationship_builder_v310",
            "supported_edges": [
                "sequel_of", "prequel_of", "spin_off_of",
                "appears_in", "portrayed_by"
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_persistent_graph_status(self):
        return self.persistent_graph_store.stats()

    def preview_persistent_graph_merge(self, graph_proposal):
        return self.persistent_graph_store.preview_merge(
            dict(graph_proposal or {})
        )

    def confirm_persistent_graph_merge(
        self,
        graph_proposal,
        confirmation_note="",
    ):
        return self.persistent_graph_store.confirm_merge(
            dict(graph_proposal or {}),
            str(confirmation_note or ""),
        )

    def resolve_persistent_graph_node(
        self,
        title,
        node_type=None,
        year=None,
    ):
        return self.persistent_graph_store.resolve_node(
            str(title or ""),
            node_type,
            year,
        )

    def get_knowledge_graph_builder_status(self):
        return {
            "strategy": "knowledge_graph_builder_v290",
            "supported_nodes": ["movie", "series", "character", "person", "universe", "event"],
            "supported_edges": [
                "sequel_of", "belongs_to", "directed_by",
                "music_by", "cinematography_by", "ends_with"
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_semantic_field_classifier_status(self):
        return {
            "strategy": "semantic_field_classifier_v280",
            "supported_fields": [
                "release_year",
                "planned_release_year",
                "production_year",
                "predecessor",
                "universe",
                "universe_transition_year",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }

    def get_reasoning_context_status(self):
        contexts = self.reasoning_context_store.list_contexts()
        return {
            "context_count": len(contexts),
            "latest_contexts": contexts[:20],
            "directory": str(self.reasoning_context_store.directory.resolve()),
        }

    def get_parser_manager_status(self):
        return {
            "parser_count": len(self.parser_manager.descriptors()),
            "parsers": self.parser_manager.descriptors(),
        }

    def extract_source_knowledge(
        self,
        source_id,
        parser_result,
        scan_result=None,
    ):
        source = self.source_manager_v2.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")
        result = self.knowledge_extractor.extract(
            source=dict(source),
            parser_result=dict(parser_result or {}),
            scan_result=dict(scan_result or {}),
        )
        preview = self.source_manager_v2.register_import_preview(
            job_id=str(source_id),
            extracted=result,
            conflicts=[],
        )
        return {
            "knowledge": result,
            "import_preview": preview,
        }

    def parse_source_scan_result(
        self,
        source_id,
        scan_result,
    ):
        source = self.source_manager_v2.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")
        parsed = self.parser_manager.parse(
            source=dict(source),
            scan_result=dict(scan_result or {}),
        )
        preview = self.source_manager_v2.register_import_preview(
            job_id=str(source_id),
            extracted=parsed,
            conflicts=[],
        )
        return {
            "parsed": parsed,
            "import_preview": preview,
        }

    def diagnose_source_policy(
        self,
        source_id,
        requested_url=None,
    ):
        source = self.source_manager_v2.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")
        url = requested_url or source.get("url")
        if not url:
            raise ValueError("Für diese Quelle ist keine URL hinterlegt.")
        return self.controlled_source_scanner.check_policy(url)

    def execute_source_scan(
        self,
        source_id,
        requested_url=None,
        allow_unknown_policy=False,
    ):
        source = self.source_manager_v2.get_source(source_id)
        if source is None:
            raise KeyError(f"Quelle nicht gefunden: {source_id}")
        url = requested_url or source.get("url")
        if not url:
            raise ValueError("Für diese Quelle ist keine URL hinterlegt.")

        scan = self.controlled_source_scanner.scan(
            url,
            allow_unknown_policy=bool(allow_unknown_policy),
            use_cache=True,
        )
        structured = (
            self.controlled_source_scanner.extract_structured_preview(scan)
        )
        parsed = self.parser_manager.parse(
            source=dict(source),
            scan_result=scan,
        )
        semantic = self.semantic_knowledge_engine.analyze(
            title=str((parsed.get("result") or {}).get("fields", {}).get("title") or scan.get("title") or ""),
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )
        knowledge = self.knowledge_extractor.extract(
            source=dict(source),
            parser_result=parsed,
            scan_result=scan,
            semantic_result=semantic,
        )

        classified_fields = self.semantic_field_classifier.classify(
            title=str((parsed.get("result") or {}).get("fields", {}).get("title") or scan.get("title") or ""),
            text=str(scan.get("text_preview") or ""),
            semantic_result=semantic,
            parser_result=parsed,
        )

        graph_proposal = self.knowledge_graph_builder.build(
            source=dict(source),
            parser_result=parsed,
            semantic_result=semantic,
            knowledge_result=knowledge,
            classified_fields=classified_fields,
            scan_result=scan,
        )

        main_graph_node = next(
            (
                node for node in graph_proposal.get("nodes") or []
                if node.get("key") == graph_proposal.get("main_node_key")
            ),
            None,
        ) or {
            "node_type": semantic.get("primary_entity_type") or "media",
            "title": (parsed.get("result") or {}).get("fields", {}).get("title") or scan.get("title") or "",
            "year": (classified_fields.get("primary_values") or {}).get("release_year"),
            "confidence": semantic.get("primary_entity_confidence", 0.8),
            "metadata": {},
        }

        relationship_proposal = self.relationship_builder.build(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )

        cast_resolution = self.character_cast_resolver.resolve(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )

        character_intelligence = self.character_intelligence.analyze(
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )

        relationship_intelligence = (
            self.relationship_intelligence.analyze(
                text=str(scan.get("text_preview") or ""),
                source=dict(source),
            )
        )

        event_intelligence = self.event_intelligence.analyze(
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )

        relationship_identity_map = (
            RelationshipIdentityMapBuilder.build(
                event_intelligence=event_intelligence,
                cast_resolution=cast_resolution,
            )
        )

        character_relationships = (
            self.character_relationship_engine.analyze(
                text=str(scan.get("text_preview") or ""),
                source=dict(source),
                identity_map=relationship_identity_map,
            )
        )

        character_identity_fusion = (
            CharacterAliasIdentityFusion.build(
                identity_map=relationship_identity_map,
                cast_resolution=cast_resolution,
                source=dict(source),
            )
        )

        universe_franchise_proposal = self.universe_franchise_builder.build(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
        )

        franchise_collection = (
            FranchiseCollectionIntelligence.analyze(
                main_node=main_graph_node,
                classified_fields=classified_fields,
                relationship_proposal=relationship_proposal,
                universe_proposal=universe_franchise_proposal,
                source=dict(source),
            )
        )


        franchise_relations = FranchiseRelationIntelligence.analyze(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
            relationship_proposal=relationship_proposal,
            franchise_collection=franchise_collection,
        )

        timeline_order_intelligence = (
            self.timeline_order_intelligence.analyze(
                main_node=main_graph_node,
                text=str(scan.get("text_preview") or ""),
                source=dict(source),
                franchise_collection=franchise_collection,
                franchise_relations=franchise_relations,
            )
        )

        franchise_connection_intelligence = (
            self.franchise_connection_intelligence.analyze(
                main_node=main_graph_node,
                text=str(scan.get("text_preview") or ""),
                source=dict(source),
                franchise_relations=franchise_relations,
                timeline_order_intelligence=timeline_order_intelligence,
            )
        )

        universe_intelligence = self.universe_intelligence.analyze(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
            universe_proposal=universe_franchise_proposal,
            franchise_connections=franchise_connection_intelligence,
        )

        character_role_intelligence = self.character_role_intelligence.analyze(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
            cast_resolution=cast_resolution,
        )

        character_relationship_intelligence = self.character_relationship_intelligence.analyze(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
            character_roles=character_role_intelligence,
        )
        entity_intelligence = self.entity_intelligence.analyze(
            main_node=main_graph_node,
            text=str(scan.get("text_preview") or ""),
            source=dict(source),
            character_roles=character_role_intelligence,
        )


        graph_validation_groups = [
            group
            for group in (
                graph_proposal,
                relationship_proposal,
                cast_resolution,
                character_intelligence,
                relationship_intelligence,
                event_intelligence,
                character_relationships,
                character_identity_fusion,
                universe_franchise_proposal,
                franchise_collection,
                franchise_relations,
                timeline_order_intelligence,
                franchise_connection_intelligence,
                universe_intelligence,
                character_role_intelligence,
                character_relationship_intelligence,
                entity_intelligence,
            )
            if isinstance(group, dict)
        ]

        graph_validation = KnowledgeGraphMergeValidator.merge(
            graph_groups=graph_validation_groups,
        )

        node_keys = {item.get("key") for item in graph_proposal.get("nodes") or []}
        for item in relationship_proposal.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        edge_keys = {
            (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            for item in graph_proposal.get("edges") or []
        }
        for item in relationship_proposal.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in cast_resolution.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in cast_resolution.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in character_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in character_intelligence.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in relationship_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in relationship_intelligence.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in character_relationships.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in character_relationships.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in character_identity_fusion.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in character_identity_fusion.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in event_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in event_intelligence.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in universe_franchise_proposal.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in universe_franchise_proposal.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in franchise_collection.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in franchise_collection.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in franchise_relations.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in franchise_relations.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in timeline_order_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in timeline_order_intelligence.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in franchise_connection_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in franchise_connection_intelligence.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in universe_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in universe_intelligence.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in character_role_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in character_role_intelligence.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        for item in character_relationship_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in character_relationship_intelligence.get("edges") or []:
            key = (item.get("edge_type"), item.get("source_node_key"), item.get("target_node_key"))
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)


        for item in entity_intelligence.get("nodes") or []:
            if item.get("key") not in node_keys:
                graph_proposal.setdefault("nodes", []).append(item)
                node_keys.add(item.get("key"))

        for item in entity_intelligence.get("edges") or []:
            key = (
                item.get("edge_type"),
                item.get("source_node_key"),
                item.get("target_node_key"),
            )
            if key not in edge_keys:
                graph_proposal.setdefault("edges", []).append(item)
                edge_keys.add(key)

        knowledge_graph = self.knowledge_graph_builder.build(
            node_groups=[
                list(graph_proposal.get("nodes") or []),
                list(
                    relationship_intelligence.get("nodes")
                    or []
                ),
                list(
                    character_relationships.get("nodes")
                    or []
                ),
                list(
                    character_identity_fusion.get("nodes")
                    or []
                ),
                list(
                    event_intelligence.get("nodes")
                    or []
                ),
                list(
                    universe_franchise_proposal.get("nodes")
                    or []
                ),
                list(
                    franchise_collection.get("nodes")
                    or []
                ),
                list(
                    franchise_relations.get("nodes")
                    or []
                ),
                list(
                    timeline_order_intelligence.get("nodes")
                    or []
                ),
                list(franchise_connection_intelligence.get("nodes") or []),
                list(universe_intelligence.get("nodes") or []),
                list(character_role_intelligence.get("nodes") or []),
                list(character_relationship_intelligence.get("nodes") or []),
                list(entity_intelligence.get("nodes") or []),
            ],
            edge_groups=[
                list(graph_proposal.get("edges") or []),
                list(
                    relationship_intelligence.get("edges")
                    or []
                ),
                list(
                    character_relationships.get("edges")
                    or []
                ),
                list(
                    character_identity_fusion.get("edges")
                    or []
                ),
                list(
                    event_intelligence.get("edges")
                    or []
                ),
                list(
                    universe_franchise_proposal.get("edges")
                    or []
                ),
                list(
                    franchise_collection.get("edges")
                    or []
                ),
                list(
                    franchise_relations.get("edges")
                    or []
                ),
                list(
                    timeline_order_intelligence.get("edges")
                    or []
                ),
                list(franchise_connection_intelligence.get("edges") or []),
                list(universe_intelligence.get("edges") or []),
                list(character_role_intelligence.get("edges") or []),
                list(character_relationship_intelligence.get("edges") or []),
                list(entity_intelligence.get("edges") or []),
            ],
            source=dict(source),
            knowledge_result=knowledge,
            parser_result=parsed,
            semantic_result=semantic,
            classified_fields=classified_fields,
            scan_result=scan,
        )

        graph_merge_preview = self.persistent_graph_store.preview_merge(
            graph_proposal
        )

        reasoning_intelligence = self.reasoning_intelligence.analyze(
            main_node=main_graph_node,
            groups={
                "relationship_intelligence": relationship_intelligence,
                "event_intelligence": event_intelligence,
                "character_relationships": character_relationships,
                "universe_franchise": universe_franchise_proposal,
                "franchise_relations": franchise_relations,
                "timeline_order": timeline_order_intelligence,
                "franchise_connections": franchise_connection_intelligence,
                "universe_intelligence": universe_intelligence,
                "character_roles": character_role_intelligence,
                "character_relationship_intelligence": character_relationship_intelligence,
                "entity_intelligence": entity_intelligence,
            },
            source=dict(source),
            graph_validation=graph_validation,
        )
        multi_source_fusion = self.multi_source_fusion.fuse(
            sources={
                "semantic_engine": dict(semantic),
                "knowledge_extractor": dict(knowledge),
                "relationship_intelligence": dict(relationship_intelligence),
                "event_intelligence": dict(event_intelligence),
                "universe_intelligence": dict(universe_intelligence),
                "character_role_intelligence": dict(character_role_intelligence),
                "character_relationship_intelligence": dict(character_relationship_intelligence),
                "entity_intelligence": dict(entity_intelligence),
                "reasoning_intelligence": dict(reasoning_intelligence),
            },
        )

        semantic_reasoning = self.semantic_reasoning_engine.analyze(
            fusion_result=multi_source_fusion,
            source=dict(source),
        )

        pipeline_debug = self.pipeline_debug_monitor.build(
            modules={
                "scan": scan,
                "structured_preview": structured,
                "parser_result": parsed,
                "semantic_result": semantic,
                "classified_fields": classified_fields,
                "graph_proposal": graph_proposal,
                "graph_merge_preview": graph_merge_preview,
                "relationship_proposal": relationship_proposal,
                "cast_resolution": cast_resolution,
                "character_intelligence": character_intelligence,
                "relationship_intelligence": relationship_intelligence,
                "character_relationships": character_relationships,
                "character_identity_fusion": character_identity_fusion,
                "event_intelligence": event_intelligence,
                "knowledge_graph": knowledge_graph,
                "universe_franchise_proposal": universe_franchise_proposal,
                "franchise_collection": franchise_collection,
                "franchise_relations": franchise_relations,
                "timeline_order_intelligence": timeline_order_intelligence,
                "franchise_connection_intelligence": franchise_connection_intelligence,
                "universe_intelligence": universe_intelligence,
                "character_role_intelligence": character_role_intelligence,
                "character_relationship_intelligence": character_relationship_intelligence,
                "entity_intelligence": entity_intelligence,
                "reasoning_intelligence": reasoning_intelligence,
                "multi_source_fusion": multi_source_fusion,
                "semantic_reasoning": semantic_reasoning,
                "graph_validation": graph_validation,
            },
            source=dict(source),
        )
        self.last_pipeline_debug_snapshot = pipeline_debug

        context = ReasoningContext.create(dict(source))
        context.document = {
            "url": scan.get("url"),
            "title": scan.get("title"),
            "headings": list(scan.get("headings") or []),
            "content_type": scan.get("content_type"),
            "byte_count": scan.get("byte_count"),
            "cache_hit": scan.get("cache_hit"),
        }
        context.parser_result = dict(parsed)
        context.semantic_result = dict(semantic)
        context.knowledge_result = dict(knowledge)
        context.document["classified_fields"] = classified_fields
        context.document["graph_proposal"] = graph_proposal
        context.document["graph_merge_preview"] = graph_merge_preview
        context.document["relationship_proposal"] = relationship_proposal
        context.document["cast_resolution"] = cast_resolution
        context.document["character_intelligence"] = character_intelligence
        context.document["relationship_intelligence"] = relationship_intelligence
        context.document["character_relationships"] = character_relationships
        context.document["relationship_identity_map"] = relationship_identity_map
        context.document["character_identity_fusion"] = character_identity_fusion
        context.document["event_intelligence"] = event_intelligence
        context.document["knowledge_graph"] = knowledge_graph
        context.document["universe_franchise_proposal"] = universe_franchise_proposal
        context.document["franchise_collection"] = franchise_collection
        context.document["franchise_relations"] = franchise_relations
        context.document["timeline_order_intelligence"] = timeline_order_intelligence
        context.document["franchise_connection_intelligence"] = franchise_connection_intelligence
        context.document["universe_intelligence"] = universe_intelligence
        context.document["character_role_intelligence"] = character_role_intelligence
        context.document["character_relationship_intelligence"] = character_relationship_intelligence
        context.document["entity_intelligence"] = entity_intelligence
        context.document["reasoning_intelligence"] = reasoning_intelligence
        context.document["multi_source_fusion"] = multi_source_fusion
        context.document["semantic_reasoning"] = semantic_reasoning
        context.document["pipeline_debug"] = pipeline_debug
        context.document["graph_validation"] = graph_validation
        context.entities = list(knowledge.get("entity_proposals") or [])
        context.relations = list(knowledge.get("relation_proposals") or [])

        context.add_trace("scanner", "Dokument geladen und Policy geprüft.", details={
            "url": scan.get("url"),
            "policy_status": (scan.get("policy") or {}).get("status"),
            "cache_hit": scan.get("cache_hit"),
        })
        context.add_trace("parser", "Quellenparser ausgeführt.", details={
            "selected_parser": parsed.get("selected_parser"),
        })
        context.add_trace("semantic_engine", "Semantikanalyse ausgeführt.", details={
            "primary_entity_type": semantic.get("primary_entity_type"),
            "entity_proposal_count": len(semantic.get("entity_proposals") or []),
        })
        context.add_trace("knowledge_extractor", "Wissensvorschläge erzeugt.", details={
            "entity_count": len(knowledge.get("entity_proposals") or []),
            "relation_count": len(knowledge.get("relation_proposals") or []),
        })

        for entity in semantic.get("entity_proposals") or []:
            sentence = str(entity.get("sentence") or "")
            evidence = context.add_evidence(
                sentence,
                "semantic_engine",
                "text_preview",
                {"entity_type": entity.get("entity_type"), "year": entity.get("year")},
            )
            candidate = context.add_candidate(
                "entity",
                {
                    "title": entity.get("title"),
                    "entity_type": entity.get("entity_type"),
                    "year": entity.get("year"),
                },
                float(entity.get("confidence") or 0.0),
                str(entity.get("reason") or ""),
                "semantic_engine",
                evidence.get("id"),
            )
            if any(marker in sentence.casefold() for marker in (
                "cosplay", "poster", "cover", "screenshot", "logo", "artwork", "bildunterschrift"
            )):
                context.reject(
                    candidate,
                    "Jahreszahl stammt vermutlich aus Bild-, Cover- oder Artwork-Kontext.",
                    "context_filter",
                )
            else:
                context.accept(
                    candidate,
                    "Entität wurde in normalem Textkontext mit Typbezug erkannt.",
                    "context_filter",
                )

        if any(
            item.get("media_type") == "character" and item.get("year") is not None
            for item in knowledge.get("entity_proposals") or []
        ):
            context.add_open_question(
                "Besitzt die Figur ein echtes Entstehungsjahr oder nur ein Jahr des ersten Auftritts?",
                90,
                "context_filter",
            )
            context.add_next_task(
                "resolve_character_first_appearance",
                {
                    "title": (parsed.get("result") or {}).get("fields", {}).get("title"),
                    "candidate_years": (parsed.get("result") or {}).get("fields", {}).get("year_candidates"),
                },
                90,
                "context_filter",
            )

        context_path = self.reasoning_context_store.save(context)
        payload = {
            "semantic_result": semantic,
            "knowledge_result": knowledge,
            "classified_fields": classified_fields,
            "graph_proposal": graph_proposal,
            "graph_merge_preview": graph_merge_preview,
            "relationship_proposal": relationship_proposal,
            "cast_resolution": cast_resolution,
            "character_intelligence": character_intelligence,
            "relationship_intelligence": relationship_intelligence,
            "character_relationships": character_relationships,
            "relationship_identity_map": relationship_identity_map,
            "character_identity_fusion": character_identity_fusion,
            "event_intelligence": event_intelligence,
            "knowledge_graph": knowledge_graph,
            "universe_franchise_proposal": universe_franchise_proposal,
            "franchise_collection": franchise_collection,
            "franchise_relations": franchise_relations,
            "timeline_order_intelligence": timeline_order_intelligence,
            "franchise_connection_intelligence": franchise_connection_intelligence,
            "universe_intelligence": universe_intelligence,
            "character_role_intelligence": character_role_intelligence,
            "character_relationship_intelligence": character_relationship_intelligence,
            "entity_intelligence": entity_intelligence,
            "reasoning_intelligence": reasoning_intelligence,
            "multi_source_fusion": multi_source_fusion,
            "semantic_reasoning": semantic_reasoning,
            "pipeline_debug": pipeline_debug,
            "graph_validation": graph_validation,
            "reasoning_context": context.to_dict(),
        }
        preview = self.source_manager_v2.register_import_preview(
            job_id=str(source_id),
            extracted=payload,
            conflicts=[],
        )
        return {
            "scan": scan,
            "structured_preview": structured,
            "parser_result": parsed,
            "semantic_result": semantic,
            "knowledge_result": knowledge,
            "classified_fields": classified_fields,
            "graph_proposal": graph_proposal,
            "graph_merge_preview": graph_merge_preview,
            "relationship_proposal": relationship_proposal,
            "cast_resolution": cast_resolution,
            "character_intelligence": character_intelligence,
            "relationship_intelligence": relationship_intelligence,
            "character_relationships": character_relationships,
            "relationship_identity_map": relationship_identity_map,
            "character_identity_fusion": character_identity_fusion,
            "event_intelligence": event_intelligence,
            "knowledge_graph": knowledge_graph,
            "universe_franchise_proposal": universe_franchise_proposal,
            "franchise_collection": franchise_collection,
            "franchise_relations": franchise_relations,
            "timeline_order_intelligence": timeline_order_intelligence,
            "franchise_connection_intelligence": franchise_connection_intelligence,
            "universe_intelligence": universe_intelligence,
            "character_role_intelligence": character_role_intelligence,
            "character_relationship_intelligence": character_relationship_intelligence,
            "entity_intelligence": entity_intelligence,
            "reasoning_intelligence": reasoning_intelligence,
            "multi_source_fusion": multi_source_fusion,
            "semantic_reasoning": semantic_reasoning,
            "pipeline_debug": pipeline_debug,
            "graph_validation": graph_validation,
            "reasoning_context": context.to_dict(),
            "reasoning_context_path": str(context_path),
            "import_preview": preview,
        }

    def get_missing_media_handoff_status(self):
        return self.missing_media_handoff.status()

    def preview_identity_cleanup(
        self,
        source_entity_id,
        target_entity_id=None,
    ):
        return self.identity_cleanup.preview(
            source_entity_id,
            target_entity_id,
        )

    def apply_identity_cleanup(
        self,
        source_entity_id,
        target_entity_id=None,
    ):
        return self.identity_cleanup.apply(
            source_entity_id,
            target_entity_id,
        )

    def import_missing_media_handoff_results(self, payload):
        if isinstance(payload, dict) and isinstance(
            payload.get("results"),
            list,
        ):
            results = payload.get("results") or []
        elif isinstance(payload, list):
            results = payload
        elif isinstance(payload, dict):
            results = [payload]
        else:
            raise ValueError(
                "Es wird ein Ergebnisobjekt oder eine Ergebnisliste erwartet."
            )

        imported = []
        errors = []
        for index, result in enumerate(results):
            try:
                imported.append(
                    self.apply_missing_media_handoff_result(result)
                )
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "error": str(exc),
                        "result": result,
                    }
                )

        return {
            "schema_version": 1,
            "processed_count": len(results),
            "imported_count": len(imported),
            "error_count": len(errors),
            "imported": imported,
            "errors": errors,
        }

    def generate_knowledge_graph_order_proposals(self):
        result = self.graph_order_proposals.propose()
        result["queue"] = self.graph_proposals.add_many(
            result.get("proposals") or []
        )
        return result

    def reason_about_knowledge_graph(self):
        result = self.semantic_graph_reasoner.reason()
        adjusted = self.reasoner_learning.adjust_many(
            result.get("proposals") or []
        )
        result["proposals"] = adjusted
        result["proposal_count"] = len(adjusted)
        result["learning_status"] = self.reasoner_learning.status()
        result["queue"] = self.graph_proposals.add_many(adjusted)
        return result

    def generate_knowledge_graph_proposals(self):
        identities = []
        for entity in self.knowledge_engine.all_items():
            metadata = dict(entity.get("metadata") or {})
            identity = {
                "id": entity.get("id"),
                "title": entity.get("title"),
                "media_type": entity.get("media_type"),
                "year": entity.get("year"),
                "aliases": entity.get("aliases") or [],
                "external_ids": entity.get("external_ids") or {},
                "metadata": metadata,
                "franchise": (
                    metadata.get("franchise")
                    or metadata.get("franchise_name")
                ),
                "universe": (
                    metadata.get("universe")
                    or metadata.get("universe_name")
                ),
                "relation_hints": metadata.get("relation_hints") or [],
            }
            identities.append(identity)

        result = self.knowledge_engine.propose_relationships(
            identities
        )
        result["queue"] = self.graph_proposals.add_many(
            result.get("proposals") or []
        )
        return result

    def update_knowledge_graph_proposal(
        self,
        proposal_id,
        status,
        note=None,
    ):
        return self.graph_proposals.set_status(
            proposal_id,
            status,
            note,
        )

    def accept_knowledge_graph_proposal(self, proposal_id):
        proposal = self.graph_proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Vorschlag nicht gefunden: {proposal_id}")

        kind = proposal.get("kind")
        if kind == "direct_relation":
            result = self.knowledge_engine.connect_confirmed(
                proposal.get("source_id"),
                proposal.get("target_id"),
                proposal.get("relation_type"),
                confidence=float(proposal.get("confidence") or 1.0),
                metadata={"proposal_id": proposal_id},
                sources=[
                    {
                        "source": "proposal_queue",
                        "confirmed_by_user": True,
                    }
                ],
                confirmed_by_user=True,
            )
        elif kind == "order":
            result = self.knowledge_engine.create_or_get_order(
                proposal.get("name"),
                proposal.get("order_type"),
                proposal.get("entity_ids") or [],
                description=str(proposal.get("reason") or ""),
                source="proposal_queue_user_confirmation",
            )
        elif kind == "group_membership":
            group_name = str(
                proposal.get("group_name") or ""
            ).strip()
            if not group_name:
                raise ValueError(
                    "Der Gruppenname des Vorschlags fehlt."
                )

            relation_type = str(
                proposal.get("relation_type") or "part_of"
            )
            group_media_type = (
                "universe"
                if relation_type == "universe"
                else "franchise"
                if relation_type == "franchise"
                else "collection"
            )
            group_result = self.knowledge_engine.upsert_identity(
                {
                    "title": group_name,
                    "media_type": group_media_type,
                    "confidence": float(
                        proposal.get("confidence") or 1.0
                    ),
                    "metadata": {
                        "generated_from_proposal": True,
                        "proposal_id": proposal_id,
                    },
                },
                source="proposal_queue",
                confirmed_by_user=True,
            )
            group_entity = group_result["entity"]
            result = self.knowledge_engine.connect_confirmed(
                proposal.get("entity_id"),
                group_entity.get("id"),
                relation_type,
                label=group_name,
                confidence=float(
                    proposal.get("confidence") or 1.0
                ),
                metadata={
                    "proposal_id": proposal_id,
                    "group_membership": True,
                },
                sources=[
                    {
                        "source": "proposal_queue",
                        "confirmed_by_user": True,
                    }
                ],
                confirmed_by_user=True,
            )
            result["group_entity"] = group_result
        else:
            raise ValueError(
                f"Unbekannter Vorschlagstyp: {kind}"
            )

        self.graph_proposals.set_status(
            proposal_id,
            "accepted",
            "Über Desktop-GUI bestätigt.",
        )
        self.reasoner_learning.record(
            proposal,
            "accepted",
            note="Über Desktop-GUI bestätigt.",
        )
        return result

    def confirm_knowledge_graph_relation(
        self,
        source_id,
        target_id,
        relation_type,
        **kwargs,
    ):
        return self.knowledge_engine.connect_confirmed(
            source_id,
            target_id,
            relation_type,
            confirmed_by_user=True,
            **kwargs,
        )

    def create_knowledge_graph_order(
        self,
        name,
        order_type,
        entity_ids,
        **kwargs,
    ):
        return self.knowledge_engine.create_or_get_order(
            name,
            order_type,
            entity_ids,
            **kwargs,
        )

    def get_learning_status(self):
        """Zeigt die tatsächlich verwendete Wissensdatenbank und deren Lernbestand."""
        return self.learning_status.status()

    def search_learned_knowledge(self, query):
        return self.knowledge_learning.lookup(query)

    def get_knowledge_conflicts(self):
        return self.knowledge_learning.conflicts()

    def export_learning_snapshot(self):
        return self.knowledge_learning.export_snapshot()

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
        self.last_analysis_result = None

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("MediaHub KI-Assistent")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        root.addWidget(title)

        subtitle = QLabel(
            "Lokale Medienanalyse, semantische Identitätserkennung und "
            "bestätigtes Lernen aus Fingerprint- und Bildmerkmalen."
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

        graph_page = QWidget()
        graph_page.setMinimumWidth(0)
        graph_layout = QVBoxLayout(graph_page)

        graph_hint = QLabel(
            "Verwalte gespeicherte Medienentitäten, bestätigte Beziehungen "
            "und Reihenfolgen. Vorschläge werden erst nach ausdrücklicher "
            "Bestätigung gespeichert."
        )
        graph_hint.setWordWrap(True)
        graph_layout.addWidget(graph_hint)

        graph_toolbar = QHBoxLayout()
        self.graph_search = QLineEdit()
        self.graph_search.setPlaceholderText(
            "Entitäten nach Titel, Alias oder Medientyp filtern"
        )
        self.graph_search.textChanged.connect(
            self.refresh_knowledge_graph
        )
        graph_toolbar.addWidget(self.graph_search, 1)

        graph_refresh = QPushButton("Graph aktualisieren")
        graph_refresh.clicked.connect(self.refresh_knowledge_graph)
        graph_toolbar.addWidget(graph_refresh)

        graph_status = QPushButton("Graph-Status")
        graph_status.clicked.connect(self.show_knowledge_graph_status)
        graph_toolbar.addWidget(graph_status)
        graph_layout.addLayout(graph_toolbar)

        self.graph_text = QPlainTextEdit()
        self.graph_text.setReadOnly(True)
        graph_layout.addWidget(self.graph_text, 1)

        entity_title = QLabel("Entität hinzufügen")
        entity_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        graph_layout.addWidget(entity_title)

        entity_form = QFormLayout()
        self.graph_entity_title = QLineEdit()
        self.graph_entity_title.setPlaceholderText("Titel")
        entity_form.addRow("Titel:", self.graph_entity_title)

        self.graph_entity_type = QComboBox()
        for label, value in (
            ("Film", "movie"),
            ("Serie", "series"),
            ("Episode", "episode"),
            ("Hörbuch", "audiobook"),
            ("Franchise", "franchise"),
            ("Universum", "universe"),
            ("Sammlung", "collection"),
            ("Sonstiges", "other"),
        ):
            self.graph_entity_type.addItem(label, value)
        entity_form.addRow("Medientyp:", self.graph_entity_type)

        self.graph_entity_year = QSpinBox()
        self.graph_entity_year.setRange(0, 3000)
        self.graph_entity_year.setSpecialValueText("-")
        entity_form.addRow("Jahr:", self.graph_entity_year)

        self.graph_entity_aliases = QLineEdit()
        self.graph_entity_aliases.setPlaceholderText(
            "Optionale Aliase, durch Kommas getrennt"
        )
        entity_form.addRow("Aliase:", self.graph_entity_aliases)

        self.graph_entity_franchise = QLineEdit()
        self.graph_entity_franchise.setPlaceholderText(
            "Optionales Franchise"
        )
        entity_form.addRow("Franchise:", self.graph_entity_franchise)

        self.graph_entity_universe = QLineEdit()
        self.graph_entity_universe.setPlaceholderText(
            "Optionales Universum"
        )
        entity_form.addRow("Universum:", self.graph_entity_universe)

        self.graph_entity_expected = QPlainTextEdit()
        self.graph_entity_expected.setMaximumHeight(70)
        self.graph_entity_expected.setPlaceholderText(
            "Optionale Soll-Liste: je Zeile ein erwarteter Titel"
        )
        entity_form.addRow("Erwartete Teile:", self.graph_entity_expected)
        graph_layout.addLayout(entity_form)

        add_entity = QPushButton("Entität speichern")
        add_entity.clicked.connect(self.create_graph_entity)
        graph_layout.addWidget(add_entity)

        cleanup_title = QLabel("Identitäten bereinigen")
        cleanup_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        graph_layout.addWidget(cleanup_title)

        cleanup_form = QFormLayout()
        self.cleanup_source = QComboBox()
        cleanup_form.addRow("Falscher Eintrag:", self.cleanup_source)

        self.cleanup_target = QComboBox()
        self.cleanup_target.addItem(
            "Nur löschen – nicht zusammenführen",
            None,
        )
        cleanup_form.addRow("Behalten/Ziel:", self.cleanup_target)
        graph_layout.addLayout(cleanup_form)

        cleanup_buttons = QHBoxLayout()
        preview_cleanup = QPushButton("Bereinigung prüfen")
        preview_cleanup.clicked.connect(
            self.preview_identity_cleanup
        )
        cleanup_buttons.addWidget(preview_cleanup)

        apply_cleanup = QPushButton("Bereinigung ausführen")
        apply_cleanup.clicked.connect(
            self.apply_identity_cleanup
        )
        cleanup_buttons.addWidget(apply_cleanup)
        cleanup_buttons.addStretch(1)
        graph_layout.addLayout(cleanup_buttons)

        relation_title = QLabel("Beziehung bestätigen")
        relation_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        graph_layout.addWidget(relation_title)

        relation_form = QFormLayout()
        self.graph_relation_source = QComboBox()
        relation_form.addRow("Quelle:", self.graph_relation_source)

        self.graph_relation_target = QComboBox()
        relation_form.addRow("Ziel:", self.graph_relation_target)

        self.graph_relation_type = QComboBox()
        for label, value in (
            ("Teil von", "part_of"),
            ("Franchise", "franchise"),
            ("Universum", "universe"),
            ("Prequel", "prequel"),
            ("Sequel", "sequel"),
            ("Spin-off", "spin_off"),
            ("Crossover", "crossover"),
            ("Remake", "remake"),
            ("Adaption", "adaptation"),
            ("Verwandt", "related"),
        ):
            self.graph_relation_type.addItem(label, value)
        relation_form.addRow("Beziehung:", self.graph_relation_type)

        self.graph_relation_label = QLineEdit()
        self.graph_relation_label.setPlaceholderText(
            "Optionale Beschreibung"
        )
        relation_form.addRow("Bezeichnung:", self.graph_relation_label)
        graph_layout.addLayout(relation_form)

        relation_buttons = QHBoxLayout()
        confirm_relation = QPushButton("Beziehung speichern")
        confirm_relation.clicked.connect(
            self.confirm_graph_relation
        )
        relation_buttons.addWidget(confirm_relation)

        self.graph_proposal_input = QPlainTextEdit()
        self.graph_proposal_input.setMaximumHeight(70)
        self.graph_proposal_input.setPlaceholderText(
            "Optional: JSON-Liste mit Identitäten und relation_hints "
            "für bestätigbare Vorschläge"
        )
        relation_buttons.addWidget(self.graph_proposal_input, 1)

        create_proposals = QPushButton("Vorschläge prüfen")
        create_proposals.clicked.connect(
            self.preview_graph_proposals
        )
        relation_buttons.addWidget(create_proposals)
        graph_layout.addLayout(relation_buttons)

        proposal_queue_title = QLabel("Vorschlagsliste")
        proposal_queue_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        graph_layout.addWidget(proposal_queue_title)

        proposal_queue_row = QHBoxLayout()
        self.graph_proposal_select = QComboBox()
        proposal_queue_row.addWidget(self.graph_proposal_select, 1)

        accept_proposal = QPushButton("Bestätigen")
        accept_proposal.clicked.connect(self.accept_graph_proposal)
        proposal_queue_row.addWidget(accept_proposal)

        reject_proposal = QPushButton("Ablehnen")
        reject_proposal.clicked.connect(self.reject_graph_proposal)
        proposal_queue_row.addWidget(reject_proposal)

        later_proposal = QPushButton("Später prüfen")
        later_proposal.clicked.connect(self.defer_graph_proposal)
        proposal_queue_row.addWidget(later_proposal)

        refresh_proposals = QPushButton("Liste aktualisieren")
        refresh_proposals.clicked.connect(self.refresh_graph_proposals)
        proposal_queue_row.addWidget(refresh_proposals)

        learning_status = QPushButton("Reasoner-Lernstatus")
        learning_status.clicked.connect(
            self.show_reasoner_learning_status
        )
        proposal_queue_row.addWidget(learning_status)

        generate_proposals = QPushButton("Automatisch vorschlagen")
        generate_proposals.clicked.connect(
            self.generate_graph_proposals
        )
        proposal_queue_row.addWidget(generate_proposals)

        reason_graph = QPushButton("Graph analysieren")
        reason_graph.clicked.connect(
            self.run_semantic_graph_reasoner
        )
        proposal_queue_row.addWidget(reason_graph)

        generate_orders = QPushButton("Reihenfolgen vorschlagen")
        generate_orders.clicked.connect(
            self.generate_graph_order_proposals
        )
        proposal_queue_row.addWidget(generate_orders)

        check_completeness = QPushButton("Vollständigkeit prüfen")
        check_completeness.clicked.connect(
            self.check_graph_completeness
        )
        proposal_queue_row.addWidget(check_completeness)

        missing_queue_button = QPushButton("Fehlende Medien")
        missing_queue_button.clicked.connect(
            self.show_missing_media_queue
        )
        proposal_queue_row.addWidget(missing_queue_button)

        export_missing_button = QPushButton("Fehlende Medien exportieren")
        export_missing_button.clicked.connect(
            self.export_missing_media_queue
        )
        proposal_queue_row.addWidget(export_missing_button)

        handoff_missing_button = QPushButton("An Plugin übergeben")
        handoff_missing_button.clicked.connect(
            self.create_missing_media_handoff
        )
        proposal_queue_row.addWidget(handoff_missing_button)

        import_handoff_button = QPushButton("Plugin-Rückmeldung importieren")
        import_handoff_button.clicked.connect(
            self.import_missing_media_handoff_results
        )
        proposal_queue_row.addWidget(import_handoff_button)

        missing_status_button = QPushButton("Fehlende-Medien-Status")
        missing_status_button.clicked.connect(
            self.show_missing_media_block_status
        )
        proposal_queue_row.addWidget(missing_status_button)
        graph_layout.addLayout(proposal_queue_row)

        missing_title = QLabel("Fehlende Medien")
        missing_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        graph_layout.addWidget(missing_title)

        missing_row = QHBoxLayout()
        self.missing_media_select = QComboBox()
        missing_row.addWidget(self.missing_media_select, 1)

        wanted_button = QPushButton("Als gesucht markieren")
        wanted_button.clicked.connect(
            self.mark_missing_media_wanted
        )
        missing_row.addWidget(wanted_button)

        reject_missing_button = QPushButton("Nicht benötigt")
        reject_missing_button.clicked.connect(
            self.reject_missing_media
        )
        missing_row.addWidget(reject_missing_button)

        later_missing_button = QPushButton("Später prüfen")
        later_missing_button.clicked.connect(
            self.defer_missing_media
        )
        missing_row.addWidget(later_missing_button)

        resolved_missing_button = QPushButton("Als vorhanden markieren")
        resolved_missing_button.clicked.connect(
            self.resolve_missing_media
        )
        missing_row.addWidget(resolved_missing_button)

        refresh_missing_button = QPushButton("Liste aktualisieren")
        refresh_missing_button.clicked.connect(
            self.refresh_missing_media_queue
        )
        missing_row.addWidget(refresh_missing_button)
        graph_layout.addLayout(missing_row)

        order_title = QLabel("Reihenfolge anlegen")
        order_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        graph_layout.addWidget(order_title)

        order_form = QFormLayout()
        self.graph_order_name = QLineEdit()
        self.graph_order_name.setPlaceholderText(
            "Zum Beispiel: Aquaman – Veröffentlichungsreihenfolge"
        )
        order_form.addRow("Name:", self.graph_order_name)

        self.graph_order_type = QComboBox()
        self.graph_order_type.addItem("Veröffentlichung", "release")
        self.graph_order_type.addItem("Chronologisch", "chronological")
        self.graph_order_type.addItem("Anschauen", "watch")
        self.graph_order_type.addItem("Benutzerdefiniert", "custom")
        order_form.addRow("Typ:", self.graph_order_type)

        self.graph_order_entities = QPlainTextEdit()
        self.graph_order_entities.setMaximumHeight(90)
        self.graph_order_entities.setPlaceholderText(
            "Je Zeile eine Entität – Titel oder ID. "
            "Die Reihenfolge der Zeilen wird übernommen."
        )
        order_form.addRow("Entitäten:", self.graph_order_entities)
        graph_layout.addLayout(order_form)

        order_buttons = QHBoxLayout()
        create_order = QPushButton("Reihenfolge speichern")
        create_order.clicked.connect(self.create_graph_order)
        order_buttons.addWidget(create_order)

        delete_relation = QPushButton("Beziehung über ID löschen")
        delete_relation.clicked.connect(self.delete_graph_relation)
        order_buttons.addWidget(delete_relation)

        delete_order = QPushButton("Reihenfolge über ID löschen")
        delete_order.clicked.connect(self.delete_graph_order)
        order_buttons.addWidget(delete_order)
        order_buttons.addStretch(1)
        graph_layout.addLayout(order_buttons)

        graph_scroll = QScrollArea()
        graph_scroll.setWidgetResizable(True)
        graph_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        graph_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        graph_scroll.setWidget(graph_page)
        tabs.addTab(graph_scroll, "Knowledge Graph")
        source_page = QWidget()
        source_page.setMinimumWidth(0)
        source_layout = QVBoxLayout(source_page)

        source_title = QLabel("Source Manager")
        source_title.setStyleSheet("font-size: 18px; font-weight: 700;")
        source_layout.addWidget(source_title)

        source_help = QLabel(
            "Quellen werden zentral verwaltet. Scans erzeugen zuerst "
            "nur eine Vorschau und importieren niemals automatisch."
        )
        source_help.setWordWrap(True)
        source_layout.addWidget(source_help)

        source_selection_form = QFormLayout()
        self.source_select = QComboBox()
        self.source_select.setMinimumWidth(500)
        self.source_select.currentIndexChanged.connect(
            self.load_selected_source_gui
        )
        source_selection_form.addRow(
            "Vorhandene Quelle auswählen:",
            self.source_select,
        )
        source_layout.addLayout(source_selection_form)

        source_form = QFormLayout()
        self.source_name = QLineEdit()
        source_form.addRow("Name:", self.source_name)

        self.source_url = QLineEdit()
        self.source_url.setPlaceholderText("https://...")
        source_form.addRow("URL:", self.source_url)

        self.source_category = QLineEdit()
        self.source_category.setPlaceholderText(
            "Franchise, Chronologie, Episoden, Hörbücher ..."
        )
        source_form.addRow("Kategorie:", self.source_category)

        self.source_trust = QSpinBox()
        self.source_trust.setRange(0, 100)
        self.source_trust.setValue(75)
        source_form.addRow("Vertrauen (%):", self.source_trust)

        self.source_priority = QSpinBox()
        self.source_priority.setRange(0, 1000)
        self.source_priority.setValue(50)
        source_form.addRow("Priorität:", self.source_priority)

        self.source_enabled = QCheckBox("Quelle ist aktiv")
        self.source_enabled.setChecked(True)
        source_form.addRow("Status:", self.source_enabled)

        self.source_type_display = QLineEdit()
        self.source_type_display.setReadOnly(True)
        source_form.addRow("Quellentyp:", self.source_type_display)
        source_layout.addLayout(source_form)

        manage_buttons = QHBoxLayout()

        new_source = QPushButton("Neue Quelle")
        new_source.clicked.connect(self.clear_source_form_gui)
        manage_buttons.addWidget(new_source)

        add_source = QPushButton("Als eigene Quelle speichern")
        add_source.clicked.connect(self.add_custom_source_gui)
        manage_buttons.addWidget(add_source)

        save_source = QPushButton("Änderungen speichern")
        save_source.clicked.connect(self.save_selected_source_gui)
        manage_buttons.addWidget(save_source)

        delete_source = QPushButton("Ausgewählte Quelle löschen")
        delete_source.clicked.connect(self.delete_selected_source_gui)
        manage_buttons.addWidget(delete_source)

        refresh_sources = QPushButton("Quellen aktualisieren")
        refresh_sources.clicked.connect(self.refresh_sources_gui)
        manage_buttons.addWidget(refresh_sources)
        manage_buttons.addStretch(1)
        source_layout.addLayout(manage_buttons)

        scan_buttons = QHBoxLayout()

        preview_source = QPushButton("Scan-Vorschau")
        preview_source.clicked.connect(self.preview_source_scan_gui)
        scan_buttons.addWidget(preview_source)

        execute_source = QPushButton("Quelle kontrolliert scannen")
        execute_source.clicked.connect(
            self.execute_source_scan_gui
        )
        scan_buttons.addWidget(execute_source)

        diagnose_policy = QPushButton("Policy-Diagnose")
        diagnose_policy.clicked.connect(
            self.diagnose_source_policy_gui
        )
        scan_buttons.addWidget(diagnose_policy)

        source_status = QPushButton("Source-Manager-Status")
        source_status.clicked.connect(self.show_source_manager_status)
        scan_buttons.addWidget(source_status)

        parser_status = QPushButton("Parser-Status")
        parser_status.clicked.connect(
            self.show_parser_manager_status
        )
        scan_buttons.addWidget(parser_status)

        extractor_status = QPushButton("Knowledge-Extractor-Status")
        extractor_status.clicked.connect(
            self.show_knowledge_extractor_status
        )
        scan_buttons.addWidget(extractor_status)

        semantic_status = QPushButton("Semantic-Engine-Status")
        semantic_status.clicked.connect(self.show_semantic_engine_status)
        scan_buttons.addWidget(semantic_status)

        universe_status = QPushButton("Universe-Franchise-Status")
        universe_status.clicked.connect(
            self.show_universe_franchise_builder_status
        )
        scan_buttons.addWidget(universe_status)

        event_status = QPushButton("Event-Intelligence-Status")
        event_status.clicked.connect(
            self.show_event_intelligence_status
        )
        scan_buttons.addWidget(event_status)

        relationship_intelligence_status = QPushButton(
            "Relationship-Intelligence-Status"
        )
        relationship_intelligence_status.clicked.connect(
            self.show_relationship_intelligence_status
        )
        scan_buttons.addWidget(relationship_intelligence_status)

        character_status = QPushButton("Character-Intelligence-Status")
        character_status.clicked.connect(
            self.show_character_intelligence_status
        )
        scan_buttons.addWidget(character_status)

        cast_status = QPushButton("Character-Cast-Resolver-Status")
        cast_status.clicked.connect(self.show_character_cast_resolver_status)
        scan_buttons.addWidget(cast_status)

        relationship_status = QPushButton("Relationship-Builder-Status")
        relationship_status.clicked.connect(
            self.show_relationship_builder_status
        )
        scan_buttons.addWidget(relationship_status)

        persistent_status = QPushButton("Persistenter Graph-Status")
        persistent_status.clicked.connect(
            self.show_persistent_graph_status
        )
        scan_buttons.addWidget(persistent_status)
        scan_buttons.addStretch(1)
        source_layout.addLayout(scan_buttons)

        source_summary_title = QLabel("Quellenübersicht")
        source_summary_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        source_layout.addWidget(source_summary_title)

        self.source_text = QPlainTextEdit()
        self.source_text.setReadOnly(True)
        self.source_text.setMaximumHeight(230)
        source_layout.addWidget(self.source_text)

        conflict_title = QLabel("Quellenkonflikte")
        conflict_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        source_layout.addWidget(conflict_title)

        self.source_conflict_json = QPlainTextEdit()
        self.source_conflict_json.setMaximumHeight(140)
        self.source_conflict_json.setPlaceholderText(
            "JSON-Liste mit Quellenergebnissen einfügen."
        )
        source_layout.addWidget(self.source_conflict_json)

        conflict_buttons = QHBoxLayout()
        compare_sources = QPushButton("Quellen vergleichen")
        compare_sources.clicked.connect(
            self.compare_source_results_gui
        )
        conflict_buttons.addWidget(compare_sources)

        conflict_status = QPushButton("Konfliktstatus")
        conflict_status.clicked.connect(
            self.show_source_conflict_status
        )
        conflict_buttons.addWidget(conflict_status)
        conflict_buttons.addStretch(1)
        source_layout.addLayout(conflict_buttons)

        selection_title = QLabel("Feldübernahme")
        selection_title.setStyleSheet(
            "font-size: 16px; font-weight: 700;"
        )
        source_layout.addWidget(selection_title)

        selection_form = QFormLayout()
        self.source_comparison_id = QLineEdit()
        self.source_comparison_id.setReadOnly(True)
        selection_form.addRow("Vergleich-ID:", self.source_comparison_id)

        self.source_target_entity = QComboBox()
        selection_form.addRow("Ziel-Entität:", self.source_target_entity)

        self.source_field_selection = QPlainTextEdit()
        self.source_field_selection.setMaximumHeight(140)
        self.source_field_selection.setPlaceholderText(
            "Bestätigte Felder als JSON-Objekt, z. B. "
            '{"title":"Aquaman","year":2018}'
        )
        selection_form.addRow("Ausgewählte Felder:", self.source_field_selection)
        source_layout.addLayout(selection_form)

        apply_buttons = QHBoxLayout()
        preview_field_import = QPushButton("Übernahme prüfen")
        preview_field_import.clicked.connect(
            self.preview_source_field_import
        )
        apply_buttons.addWidget(preview_field_import)

        apply_field_import = QPushButton("Felder übernehmen")
        apply_field_import.clicked.connect(
            self.apply_source_field_import
        )
        apply_buttons.addWidget(apply_field_import)
        apply_buttons.addStretch(1)
        source_layout.addLayout(apply_buttons)

        source_scroll = QScrollArea()
        source_scroll.setWidgetResizable(True)
        source_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        source_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        source_scroll.setWidget(source_page)
        tabs.addTab(source_scroll, "Quellen")


        analysis_page = QWidget()
        analysis_page.setMinimumWidth(0)
        analysis_layout = QVBoxLayout(analysis_page)
        analysis_hint = QLabel(
            "Wähle eine Mediendatei. Unsichere Ergebnisse können unten "
            "korrigiert und ausdrücklich bestätigt werden. Erst die "
            "Bestätigung speichert Fingerprint und visuelles Wissen."
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

        identity_title = QLabel("Identität korrigieren und lernen")
        identity_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        analysis_layout.addWidget(identity_title)

        identity_form = QFormLayout()
        self.identity_media_type = QComboBox()
        self.identity_media_type.addItem("Unbekannt", "unknown")
        self.identity_media_type.addItem("Film", "movie")
        self.identity_media_type.addItem("Serie", "series")
        self.identity_media_type.addItem("Episode", "episode")
        self.identity_media_type.addItem("Hörbuch", "audiobook")
        identity_form.addRow("Medientyp:", self.identity_media_type)

        self.identity_title = QLineEdit()
        self.identity_title.setPlaceholderText("Korrekter Titel")
        identity_form.addRow("Titel:", self.identity_title)

        self.identity_year = QSpinBox()
        self.identity_year.setRange(0, 3000)
        self.identity_year.setSpecialValueText("-")
        identity_form.addRow("Jahr:", self.identity_year)

        self.identity_season = QSpinBox()
        self.identity_season.setRange(0, 999)
        self.identity_season.setSpecialValueText("-")
        identity_form.addRow("Staffel:", self.identity_season)

        self.identity_episode = QSpinBox()
        self.identity_episode.setRange(0, 99999)
        self.identity_episode.setSpecialValueText("-")
        identity_form.addRow("Episode:", self.identity_episode)

        self.identity_edition = QLineEdit()
        self.identity_edition.setPlaceholderText(
            "Optional, z. B. Extended oder Director's Cut"
        )
        identity_form.addRow("Fassung:", self.identity_edition)
        analysis_layout.addLayout(identity_form)

        learning_buttons = QHBoxLayout()
        self.confirm_identity_button = QPushButton(
            "Identität bestätigen und lernen"
        )
        self.confirm_identity_button.setEnabled(False)
        self.confirm_identity_button.clicked.connect(
            self.confirm_and_learn_identity
        )
        learning_buttons.addWidget(self.confirm_identity_button)

        self.learning_status_button = QPushButton("Lernstatus anzeigen")
        self.learning_status_button.clicked.connect(
            self.show_learning_status
        )
        learning_buttons.addWidget(self.learning_status_button)

        self.reanalyze_button = QPushButton("Erneut analysieren")
        self.reanalyze_button.setEnabled(False)
        self.reanalyze_button.clicked.connect(
            self.reanalyze_current_file
        )
        learning_buttons.addWidget(self.reanalyze_button)
        learning_buttons.addStretch(1)
        analysis_layout.addLayout(learning_buttons)

        self.learning_status_label = QLabel(
            "Noch keine Identität bestätigt."
        )
        self.learning_status_label.setWordWrap(True)
        analysis_layout.addWidget(self.learning_status_label)

        self.analysis_text = QPlainTextEdit()
        self.analysis_text.setReadOnly(True)
        analysis_layout.addWidget(self.analysis_text, 1)
        analysis_scroll = QScrollArea()
        analysis_scroll.setWidgetResizable(True)
        analysis_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        analysis_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        analysis_scroll.setWidget(analysis_page)
        tabs.addTab(analysis_scroll, "Dateianalyse & Lernen")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        refresh = QPushButton("Status aktualisieren")
        refresh.clicked.connect(self.refresh_status)
        buttons.addWidget(refresh)
        root.addLayout(buttons)

        self.refresh_status()

        self.refresh_knowledge_graph()
        self.refresh_sources_gui()

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
            self.last_analysis_result = result
            self.open_file_button.setEnabled(True)
            self.confirm_identity_button.setEnabled(True)
            self.reanalyze_button.setEnabled(True)
            self._prefill_identity_fields(result)
        except Exception as exc:
            self.analysis_text.setPlainText(f"Analysefehler:\n{exc}")
            return
        text = self.plugin.format_analysis_summary(result)
        text += "\n\nROHDATEN\n--------\n"
        text += json.dumps(result, ensure_ascii=False, indent=2)
        self.analysis_text.setPlainText(text)

    def show_scrollable_text_dialog(
        self,
        title,
        content,
        *,
        width=820,
        height=620,
    ):
        """Zeigt lange Status- und JSON-Texte in einem begrenzten Fenster."""
        dialog = QDialog(self)
        dialog.setWindowTitle(str(title))
        dialog.resize(width, height)
        dialog.setMinimumSize(520, 360)

        layout = QVBoxLayout(dialog)
        text_view = QPlainTextEdit(dialog)
        text_view.setReadOnly(True)
        text_view.setPlainText(str(content))
        layout.addWidget(text_view, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=dialog,
        )
        buttons.rejected.connect(dialog.reject)
        buttons.clicked.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.exec()

    def _graph_snapshot(self):
        return self.plugin.get_knowledge_graph_snapshot()

    def refresh_knowledge_graph(self, *_args):
        try:
            snapshot = self._graph_snapshot()
        except Exception as exc:
            self.graph_text.setPlainText(
                f"Knowledge Graph konnte nicht geladen werden:\n{exc}"
            )
            return

        query = self.graph_search.text().strip().casefold()
        entities = list(snapshot.get("entities") or [])
        relations = list(snapshot.get("relations") or [])
        orders = list(snapshot.get("orders") or [])

        if query:
            entities = [
                item
                for item in entities
                if query in str(item.get("title") or "").casefold()
                or query in str(item.get("media_type") or "").casefold()
                or any(
                    query in str(alias).casefold()
                    for alias in item.get("aliases") or []
                )
            ]

        self.graph_entity_lookup = {}
        for item in snapshot.get("entities") or []:
            entity_id = str(item.get("id"))
            title_key = str(item.get("title") or "").strip().casefold()
            self.graph_entity_lookup[entity_id] = entity_id
            if title_key:
                self.graph_entity_lookup[title_key] = entity_id

        self.graph_relation_source.clear()
        self.graph_relation_target.clear()
        if hasattr(self, "source_target_entity"):
            self.source_target_entity.clear()
        self.cleanup_source.clear()
        self.cleanup_target.clear()
        self.cleanup_target.addItem(
            "Nur löschen – nicht zusammenführen",
            None,
        )
        for item in snapshot.get("entities") or []:
            label = (
                f"{item.get('id')} | {item.get('title')} "
                f"[{item.get('media_type')}]"
            )
            self.graph_relation_source.addItem(label, str(item.get("id")))
            self.graph_relation_target.addItem(label, str(item.get("id")))
            self.cleanup_source.addItem(label, str(item.get("id")))
            self.cleanup_target.addItem(label, str(item.get("id")))
            if hasattr(self, "source_target_entity"):
                self.source_target_entity.addItem(
                    label,
                    str(item.get("id")),
                )

        migration = snapshot.get("migration") or {}
        reconciliation = (
            snapshot.get("missing_media_reconciliation") or {}
        )
        lines = [
            "KNOWLEDGE GRAPH",
            "===============",
            f"Entitäten: {len(snapshot.get('entities') or [])}",
            f"Beziehungen: {len(relations)}",
            f"Reihenfolgen: {len(orders)}",
            f"Gelernte Identitäten geprüft: "
            f"{migration.get('processed_count', 0)}",
            f"Davon neu in den Graph übernommen: "
            f"{migration.get('created_count', 0)}",
            f"Fehlende Medien automatisch aufgelöst: "
            f"{reconciliation.get('resolved_count', 0)}",
            "",
            "ENTITÄTEN",
            "---------",
        ]
        if not entities:
            lines.append("Keine passenden Entitäten gefunden.")
        for item in entities:
            aliases = ", ".join(item.get("aliases") or []) or "-"
            lines.append(
                f"{item.get('id')} | {item.get('title')} "
                f"({item.get('year') or '-'}) | "
                f"{item.get('media_type')} | Aliase: {aliases}"
            )

        lines.extend(["", "BEZIEHUNGEN", "-----------"])
        if not relations:
            lines.append("Noch keine bestätigten Beziehungen.")
        entity_by_id = {
            str(item.get("id")): item
            for item in snapshot.get("entities") or []
        }

        for relation in relations:
            source = entity_by_id.get(
                str(relation.get("source_id"))
            ) or {}
            target = entity_by_id.get(
                str(relation.get("target_id"))
            ) or {}
            source_label = (
                f"{source.get('title') or relation.get('source_id')}"
                + (
                    f" ({source.get('year')})"
                    if source.get("year")
                    else ""
                )
            )
            target_label = (
                f"{target.get('title') or relation.get('target_id')}"
                + (
                    f" ({target.get('year')})"
                    if target.get("year")
                    else ""
                )
            )
            relation_label = str(
                relation.get("relation_type") or "related"
            ).replace("_", " ").title()
            lines.append(
                f"{source_label}"
                f" --{relation_label}--> "
                f"{target_label}"
            )

        lines.extend(["", "REIHENFOLGEN", "-------------"])
        if not orders:
            lines.append("Noch keine Reihenfolgen.")
        for order in orders:
            lines.append(
                f"{order.get('name')} "
                f"[{order.get('order_type')}]"
            )
            for position, entry in enumerate(
                sorted(
                    order.get("entries") or [],
                    key=lambda item: int(item.get("position") or 0),
                ),
                start=1,
            ):
                entity = entity_by_id.get(
                    str(entry.get("entity_id"))
                ) or {}
                label = (
                    str(entity.get("title") or entry.get("entity_id"))
                    + (
                        f" ({entity.get('year')})"
                        if entity.get("year")
                        else ""
                    )
                )
                lines.append(f"  {position}. {label}")

        self.graph_text.setPlainText("\n".join(lines))
        self.refresh_graph_proposals()
        self.refresh_missing_media_queue()

    def show_knowledge_graph_status(self):
        try:
            status = self.plugin.get_knowledge_graph_status()
        except Exception as exc:
            QMessageBox.warning(self, "Knowledge Graph", str(exc))
            return
        self.show_scrollable_text_dialog(
            "Knowledge-Graph-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def preview_identity_cleanup(self):
        source_id = self.cleanup_source.currentData()
        target_id = self.cleanup_target.currentData()
        if not source_id:
            QMessageBox.warning(
                self,
                "Identitäten bereinigen",
                "Bitte den falschen Eintrag auswählen.",
            )
            return
        if target_id and source_id == target_id:
            QMessageBox.warning(
                self,
                "Identitäten bereinigen",
                "Quelle und Ziel dürfen nicht identisch sein.",
            )
            return
        try:
            preview = self.plugin.preview_identity_cleanup(
                source_id,
                target_id,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Bereinigung prüfen",
                str(exc),
            )
            return
        self.show_scrollable_text_dialog(
            "Bereinigungsvorschau",
            json.dumps(preview, ensure_ascii=False, indent=2),
        )

    def apply_identity_cleanup(self):
        source_id = self.cleanup_source.currentData()
        target_id = self.cleanup_target.currentData()
        if not source_id:
            QMessageBox.warning(
                self,
                "Identitäten bereinigen",
                "Bitte den falschen Eintrag auswählen.",
            )
            return
        if target_id and source_id == target_id:
            QMessageBox.warning(
                self,
                "Identitäten bereinigen",
                "Quelle und Ziel dürfen nicht identisch sein.",
            )
            return

        try:
            preview = self.plugin.preview_identity_cleanup(
                source_id,
                target_id,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Identitäten bereinigen",
                str(exc),
            )
            return

        source = preview.get("source") or {}
        target = preview.get("target") or {}
        action = (
            f"mit {target.get('title')} zusammenführen"
            if target
            else "vollständig löschen"
        )
        answer = QMessageBox.question(
            self,
            "Bereinigung bestätigen",
            f"{source.get('title')} ({source.get('year') or '-'}) "
            f"wirklich {action}?\n\n"
            "Vor der Änderung wird automatisch ein Backup erstellt.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.plugin.apply_identity_cleanup(
                source_id,
                target_id,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Bereinigung fehlgeschlagen",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Bereinigung abgeschlossen",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_knowledge_graph()
        self.refresh_missing_media_queue()

    def create_graph_entity(self):
        title = self.graph_entity_title.text().strip()
        if not title:
            QMessageBox.warning(
                self,
                "Entität speichern",
                "Bitte einen Titel eingeben.",
            )
            return

        aliases = [
            item.strip()
            for item in self.graph_entity_aliases.text().split(",")
            if item.strip()
        ]
        metadata = {}
        franchise = self.graph_entity_franchise.text().strip()
        universe = self.graph_entity_universe.text().strip()
        if franchise:
            metadata["franchise"] = franchise
        if universe:
            metadata["universe"] = universe

        expected_entries = [
            line.strip()
            for line in self.graph_entity_expected.toPlainText().splitlines()
            if line.strip()
        ]
        if expected_entries:
            metadata["expected_entries"] = expected_entries

        identity = {
            "title": title,
            "media_type": self.graph_entity_type.currentData() or "other",
            "year": self.graph_entity_year.value() or None,
            "aliases": aliases,
            "metadata": metadata,
            "confidence": 1.0,
        }

        try:
            result = self.plugin.create_knowledge_graph_entity(identity)
        except Exception as exc:
            QMessageBox.critical(self, "Entität speichern", str(exc))
            return

        self.show_scrollable_text_dialog(
            "Entität gespeichert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.graph_entity_title.clear()
        self.graph_entity_year.setValue(0)
        self.graph_entity_aliases.clear()
        self.graph_entity_franchise.clear()
        self.graph_entity_universe.clear()
        self.graph_entity_expected.clear()
        self.refresh_knowledge_graph()

    def _resolve_graph_entity_ids(self, lines):
        lookup = getattr(self, "graph_entity_lookup", {})
        resolved = []
        missing = []
        for raw in lines:
            value = str(raw).strip()
            if not value:
                continue
            entity_id = lookup.get(value) or lookup.get(value.casefold())
            if entity_id is None:
                missing.append(value)
            else:
                resolved.append(entity_id)
        if missing:
            raise ValueError(
                "Folgende Entitäten wurden nicht gefunden: "
                + ", ".join(missing)
            )
        return resolved

    def _ask_simple_text(self, title, label):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(label))
        field = QLineEdit(dialog)
        layout.addWidget(field)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        return field.text().strip(), accepted

    def delete_graph_relation(self):
        relation_id, accepted = self._ask_simple_text(
            "Beziehung löschen",
            "Beziehungs-ID:",
        )
        if not accepted or not relation_id:
            return
        answer = QMessageBox.question(
            self,
            "Beziehung löschen",
            f"Beziehung {relation_id} wirklich dauerhaft löschen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.plugin.delete_knowledge_graph_relation(relation_id)
        except Exception as exc:
            QMessageBox.critical(self, "Beziehung löschen", str(exc))
            return
        QMessageBox.information(
            self,
            "Beziehung löschen",
            "Beziehung gelöscht."
            if result
            else "Keine passende Beziehung gefunden.",
        )
        self.refresh_knowledge_graph()

    def delete_graph_order(self):
        order_id, accepted = self._ask_simple_text(
            "Reihenfolge löschen",
            "Reihenfolge-ID:",
        )
        if not accepted or not order_id:
            return
        answer = QMessageBox.question(
            self,
            "Reihenfolge löschen",
            f"Reihenfolge {order_id} wirklich dauerhaft löschen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.plugin.delete_knowledge_graph_order(order_id)
        except Exception as exc:
            QMessageBox.critical(self, "Reihenfolge löschen", str(exc))
            return
        QMessageBox.information(
            self,
            "Reihenfolge löschen",
            "Reihenfolge gelöscht."
            if result
            else "Keine passende Reihenfolge gefunden.",
        )
        self.refresh_knowledge_graph()

    def confirm_graph_relation(self):
        source_id = self.graph_relation_source.currentData()
        target_id = self.graph_relation_target.currentData()
        relation_type = self.graph_relation_type.currentData()
        if not source_id or not target_id:
            QMessageBox.warning(
                self,
                "Beziehung speichern",
                "Bitte Quelle und Ziel auswählen.",
            )
            return
        if source_id == target_id:
            QMessageBox.warning(
                self,
                "Beziehung speichern",
                "Quelle und Ziel dürfen nicht identisch sein.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Beziehung bestätigen",
            "Diese Beziehung wird dauerhaft im Knowledge Graph gespeichert.\n\n"
            f"{source_id} --{relation_type}--> {target_id}\n\n"
            "Ist die Beziehung sicher korrekt?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.plugin.confirm_knowledge_graph_relation(
                source_id,
                target_id,
                relation_type,
                label=self.graph_relation_label.text().strip(),
                confidence=1.0,
                sources=[
                    {
                        "source": "desktop_gui",
                        "confirmed_by_user": True,
                    }
                ],
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Beziehung speichern",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Beziehung gespeichert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_knowledge_graph()

    def preview_graph_proposals(self):
        raw = self.graph_proposal_input.toPlainText().strip()
        if not raw:
            QMessageBox.information(
                self,
                "Beziehungsvorschläge",
                "Keine JSON-Identitäten eingegeben.",
            )
            return
        try:
            identities = json.loads(raw)
            if not isinstance(identities, list):
                raise ValueError("Es wird eine JSON-Liste erwartet.")
            result = self.plugin.propose_knowledge_graph_relationships(
                identities
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Beziehungsvorschläge",
                str(exc),
            )
            return

        self.graph_text.appendPlainText(
            "\n\nVORSCHLÄGE – NOCH NICHT GESPEICHERT\n"
            "-----------------------------------\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
        )
        QMessageBox.information(
            self,
            "Beziehungsvorschläge",
            f"{result.get('proposal_count', 0)} Vorschläge erzeugt.\n"
            "Es wurde keine Beziehung automatisch gespeichert.",
        )

    def check_graph_completeness(self):
        try:
            result = self.plugin.analyze_knowledge_graph_completeness()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Vollständigkeit prüfen",
                str(exc),
            )
            return

        lines = [
            "KNOWLEDGE-GRAPH-VOLLSTÄNDIGKEIT",
            "================================",
            f"Gruppen geprüft: {result.get('group_count', 0)}",
            f"Fehlende Einträge: {result.get('missing_count', 0)}",
            f"Neu in Warteschlange: "
            f"{(result.get('queue') or {}).get('created_count', 0)}",
            "",
        ]

        for group in result.get("groups") or []:
            lines.append(
                f"{group.get('group_name')} "
                f"[{group.get('group_type')}]"
            )
            lines.append(
                f"Vorhanden: {group.get('member_count', 0)} | "
                f"Erwartet: {group.get('expected_count', 0)} | "
                f"Fehlend: {group.get('missing_count', 0)}"
            )
            lines.append(
                "Status: "
                + (
                    "Vollständig"
                    if group.get("complete")
                    else "Unvollständig"
                )
            )
            for member in group.get("members") or []:
                title = member.get("title") or "-"
                year = member.get("year")
                lines.append(
                    f"  VORHANDEN: {title}"
                    + (f" ({year})" if year else "")
                )
            for missing in group.get("missing") or []:
                title = missing.get("title") or "-"
                year = missing.get("year")
                lines.append(
                    f"  FEHLT: {title}"
                    + (f" ({year})" if year else "")
                )
            for limitation in group.get("limitations") or []:
                lines.append(f"  Hinweis: {limitation}")
            lines.append("")

        self.show_scrollable_text_dialog(
            "Franchise- und Reihenfolgen-Vollständigkeit",
            "\n".join(lines),
        )

    def import_missing_media_handoff_results(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Plugin-Rückmeldung importieren",
            "",
            "JSON-Datei (*.json)",
        )
        if not path:
            return

        try:
            payload = json.loads(
                Path(path).read_text(encoding="utf-8-sig")
            )
            result = self.plugin.import_missing_media_handoff_results(
                payload
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Plugin-Rückmeldung importieren",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Plugin-Rückmeldung importiert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_missing_media_queue()
        self.refresh_knowledge_graph()

    def show_missing_media_block_status(self):
        try:
            queue_status = self.plugin.get_missing_media_status()
            handoff_status = (
                self.plugin.get_missing_media_handoff_status()
            )
            items = self.plugin.get_missing_media_items()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehlende-Medien-Status",
                str(exc),
            )
            return

        payload = {
            "queue": queue_status,
            "handoff": handoff_status,
            "open_items": [
                item
                for item in items
                if item.get("status") in {
                    "pending",
                    "wanted",
                    "later",
                }
            ],
            "safety": {
                "automatic_download": False,
                "automatic_search": False,
                "automatic_file_change": False,
            },
        }
        self.show_scrollable_text_dialog(
            "Fehlende-Medien-Status",
            json.dumps(payload, ensure_ascii=False, indent=2),
        )

    def create_missing_media_handoff(self):
        target_plugin, accepted = self._ask_simple_text(
            "Fehlende Medien übergeben",
            "Ziel-Plugin-ID:",
        )
        if not accepted or not target_plugin:
            return

        try:
            payload = self.plugin.create_missing_media_handoff(
                target_plugin,
                statuses=["pending", "wanted", "later"],
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehlende Medien übergeben",
                str(exc),
            )
            return

        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Plugin-Übergabe speichern",
            f"missing_media_handoff_{payload.get('handoff_id')}.json",
            "JSON-Datei (*.json)",
        )
        if not path:
            return
        if not str(path).lower().endswith(".json"):
            path += ".json"

        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8-sig",
        )
        self.show_scrollable_text_dialog(
            "Plugin-Übergabe erstellt",
            json.dumps(
                {
                    "path": str(Path(path).resolve()),
                    "handoff_id": payload.get("handoff_id"),
                    "target_plugin": payload.get("target_plugin"),
                    "item_count": len(payload.get("items") or []),
                    "safety": payload.get("safety"),
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

    def export_missing_media_queue(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Fehlende Medien exportieren",
            "fehlende_medien.json",
            "JSON-Datei (*.json);;CSV-Datei (*.csv)",
        )
        if not path:
            return

        format_name = (
            "csv"
            if selected_filter.startswith("CSV")
            or str(path).lower().endswith(".csv")
            else "json"
        )

        if format_name == "json" and not str(path).lower().endswith(".json"):
            path += ".json"
        if format_name == "csv" and not str(path).lower().endswith(".csv"):
            path += ".csv"

        try:
            result = self.plugin.export_missing_media(
                path,
                format_name,
                statuses=["pending", "wanted", "later"],
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehlende Medien exportieren",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Fehlende Medien exportiert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )

    def refresh_missing_media_queue(self):
        if not hasattr(self, "missing_media_select"):
            return
        try:
            items = self.plugin.get_missing_media_items()
        except Exception as exc:
            self.missing_media_select.clear()
            self.missing_media_select.addItem(
                f"Liste konnte nicht geladen werden: {exc}",
                None,
            )
            return

        self.missing_media_select.clear()
        active = [
            item
            for item in items
            if item.get("status") in {
                "pending",
                "wanted",
                "later",
            }
        ]
        if not active:
            self.missing_media_select.addItem(
                "Keine offenen fehlenden Medien",
                None,
            )
            return

        for item in active:
            label = (
                f"{item.get('title')}"
                + (
                    f" ({item.get('year')})"
                    if item.get("year")
                    else ""
                )
                + f" | {item.get('group_name')} "
                f"[{item.get('status')}]"
            )
            self.missing_media_select.addItem(
                label,
                str(item.get("id")),
            )

    def _selected_missing_media_id(self):
        item_id = self.missing_media_select.currentData()
        if not item_id:
            QMessageBox.information(
                self,
                "Fehlende Medien",
                "Kein offener Eintrag ausgewählt.",
            )
            return None
        return str(item_id)

    def _set_missing_media_status(self, status, note):
        item_id = self._selected_missing_media_id()
        if not item_id:
            return
        try:
            self.plugin.update_missing_media_item(
                item_id,
                status,
                note,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehlende Medien",
                str(exc),
            )
            return
        self.refresh_missing_media_queue()

    def mark_missing_media_wanted(self):
        self._set_missing_media_status(
            "wanted",
            "Vom Benutzer als gesucht markiert.",
        )

    def reject_missing_media(self):
        self._set_missing_media_status(
            "rejected",
            "Vom Benutzer als nicht benötigt markiert.",
        )

    def defer_missing_media(self):
        self._set_missing_media_status(
            "later",
            "Zur späteren Prüfung zurückgestellt.",
        )

    def resolve_missing_media(self):
        self._set_missing_media_status(
            "resolved",
            "Vom Benutzer als vorhanden markiert.",
        )

    def show_missing_media_queue(self):
        try:
            status = self.plugin.get_missing_media_status()
            items = self.plugin.get_missing_media_items()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehlende Medien",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Fehlende Medien",
            json.dumps(
                {
                    "status": status,
                    "items": items,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        self.refresh_missing_media_queue()

    def generate_graph_order_proposals(self):
        try:
            result = self.plugin.generate_knowledge_graph_order_proposals()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Reihenfolge-Vorschläge",
                str(exc),
            )
            return

        queue = result.get("queue") or {}
        self.show_scrollable_text_dialog(
            "Reihenfolge-Vorschläge",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        QMessageBox.information(
            self,
            "Reihenfolge-Vorschläge",
            f"Neu erzeugt: {queue.get('created_count', 0)}\n"
            f"Bereits vorhanden: {queue.get('existing_count', 0)}",
        )
        self.refresh_graph_proposals()

    def refresh_sources_gui(self):
        previous_id = (
            self.source_select.currentData()
            if hasattr(self, "source_select")
            else None
        )
        try:
            sources = self.plugin.get_sources()
        except Exception as exc:
            self.source_text.setPlainText(str(exc))
            return

        self._source_gui_items = {
            str(item.get("id")): dict(item)
            for item in sources
        }

        self.source_select.blockSignals(True)
        self.source_select.clear()
        selected_index = -1

        lines = [
            "SOURCE MANAGER",
            "==============",
            f"Quellen: {len(sources)}",
            "",
        ]

        for index, source in enumerate(sources):
            label = (
                f"{source.get('name')} | "
                f"{source.get('source_type')} | "
                f"Priorität {source.get('priority')} | "
                f"Vertrauen "
                f"{round(float(source.get('trust') or 0) * 100)} % | "
                + ("aktiv" if source.get("enabled") else "deaktiviert")
            )
            source_id = str(source.get("id"))
            self.source_select.addItem(label, source_id)
            if previous_id is not None and str(previous_id) == source_id:
                selected_index = index

            lines.append(label)
            if source.get("url"):
                lines.append(f"  URL: {source.get('url')}")
            if source.get("category"):
                lines.append(f"  Kategorie: {source.get('category')}")
            lines.append("")

        if selected_index >= 0:
            self.source_select.setCurrentIndex(selected_index)
        elif sources:
            self.source_select.setCurrentIndex(0)

        self.source_select.blockSignals(False)
        self.source_text.setPlainText("\n".join(lines))
        self.load_selected_source_gui()

    def load_selected_source_gui(self, _index=None):
        if not hasattr(self, "source_select"):
            return

        source_id = self.source_select.currentData()
        source = getattr(self, "_source_gui_items", {}).get(
            str(source_id)
        )
        if source is None and source_id:
            try:
                source = self.plugin.get_source(source_id)
            except Exception:
                source = None
        if not source:
            return

        self.source_name.setText(str(source.get("name") or ""))
        self.source_url.setText(str(source.get("url") or ""))
        self.source_category.setText(
            str(source.get("category") or "")
        )
        self.source_trust.setValue(
            round(float(source.get("trust") or 0.0) * 100)
        )
        self.source_priority.setValue(
            int(source.get("priority") or 0)
        )
        self.source_enabled.setChecked(
            bool(source.get("enabled"))
        )
        self.source_type_display.setText(
            str(source.get("source_type") or "")
        )

        is_custom = bool(source.get("user_defined"))
        self.source_name.setReadOnly(not is_custom)
        self.source_url.setReadOnly(not is_custom)
        self.source_category.setReadOnly(not is_custom)

    def clear_source_form_gui(self):
        self.source_select.setCurrentIndex(-1)
        self.source_name.setReadOnly(False)
        self.source_url.setReadOnly(False)
        self.source_category.setReadOnly(False)
        self.source_name.clear()
        self.source_url.clear()
        self.source_category.clear()
        self.source_trust.setValue(75)
        self.source_priority.setValue(50)
        self.source_enabled.setChecked(True)
        self.source_type_display.setText("custom_url")
        self.source_name.setFocus()

    def save_selected_source_gui(self):
        source_id = self.source_select.currentData()
        if not source_id:
            QMessageBox.information(
                self,
                "Quelle speichern",
                "Bitte zuerst eine vorhandene Quelle auswählen.",
            )
            return

        try:
            result = self.plugin.update_source(
                source_id,
                name=self.source_name.text().strip(),
                enabled=self.source_enabled.isChecked(),
                priority=self.source_priority.value(),
                trust=self.source_trust.value() / 100.0,
                category=self.source_category.text().strip() or None,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Quelle speichern",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Quelle aktualisiert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_sources_gui()

    def delete_selected_source_gui(self):
        source_id = self.source_select.currentData()
        if not source_id:
            QMessageBox.information(
                self,
                "Quelle löschen",
                "Bitte zuerst eine Quelle auswählen.",
            )
            return

        source = getattr(self, "_source_gui_items", {}).get(
            str(source_id),
            {},
        )
        if not source.get("user_defined"):
            QMessageBox.information(
                self,
                "Quelle löschen",
                "Vordefinierte Quellen können nicht gelöscht werden. "
                "Du kannst sie über „Quelle ist aktiv“ deaktivieren.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Quelle löschen",
            f"Die Quelle „{source.get('name')}“ wirklich löschen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.plugin.remove_source(source_id)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Quelle löschen",
                str(exc),
            )
            return

        self.refresh_sources_gui()

    def add_custom_source_gui(self):
        try:
            source = self.plugin.add_custom_source(
                name=self.source_name.text().strip(),
                url=self.source_url.text().strip(),
                category=self.source_category.text().strip() or "general",
                trust=self.source_trust.value() / 100.0,
                priority=self.source_priority.value(),
                language="de",
            )
            if not self.source_enabled.isChecked():
                source = self.plugin.update_source(
                    source.get("id"),
                    enabled=False,
                )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Eigene Quelle hinzufügen",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Quelle gespeichert",
            json.dumps(source, ensure_ascii=False, indent=2),
        )
        new_source_id = str(source.get("id") or "")
        self.refresh_sources_gui()
        index = self.source_select.findData(new_source_id)
        if index >= 0:
            self.source_select.setCurrentIndex(index)

    def preview_source_scan_gui(self):
        source_id = self.source_select.currentData()
        if not source_id:
            QMessageBox.information(
                self,
                "Scan-Vorschau",
                "Bitte zuerst eine Quelle auswählen.",
            )
            return

        requested_url = self.source_url.text().strip() or None
        try:
            preview = self.plugin.create_source_scan_preview(
                source_id,
                requested_url=requested_url,
                context={
                    "requested_by": "desktop_gui",
                    "purpose": "user_preview",
                },
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Scan-Vorschau",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Source-Scan-Vorschau",
            json.dumps(preview, ensure_ascii=False, indent=2),
        )

    def _source_field_import_payload(self):
        comparison_id = self.source_comparison_id.text().strip()
        if not comparison_id:
            raise ValueError(
                "Bitte zuerst einen Quellenvergleich durchführen."
            )

        entity_id = self.source_target_entity.currentData()
        if not entity_id:
            raise ValueError("Bitte eine Ziel-Entität auswählen.")

        raw_fields = self.source_field_selection.toPlainText().strip()
        if not raw_fields:
            raise ValueError("Bitte mindestens ein Feld auswählen.")

        selected_fields = json.loads(raw_fields)
        if not isinstance(selected_fields, dict):
            raise ValueError(
                "Die Feldauswahl muss ein JSON-Objekt sein."
            )
        if not selected_fields:
            raise ValueError("Die Feldauswahl ist leer.")

        return {
            "comparison_id": comparison_id,
            "entity_id": str(entity_id),
            "selected_fields": selected_fields,
        }

    def preview_source_field_import(self):
        try:
            payload = self._source_field_import_payload()
            entity = self.plugin.knowledge_engine.store.get_entity(
                payload["entity_id"]
            )
            if entity is None:
                raise KeyError("Ziel-Entität wurde nicht gefunden.")

            before = dict(entity)
            after = dict(entity)
            metadata = dict(after.get("metadata") or {})
            for field, value in payload["selected_fields"].items():
                if field in {"title", "year", "media_type", "aliases"}:
                    after[field] = value
                else:
                    metadata[field] = value
            after["metadata"] = metadata

            preview = {
                "comparison_id": payload["comparison_id"],
                "entity_id": payload["entity_id"],
                "before": before,
                "selected_fields": payload["selected_fields"],
                "after": after,
                "automatic_import": False,
                "requires_confirmation": True,
            }
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Übernahme prüfen",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Feldübernahme-Vorschau",
            json.dumps(preview, ensure_ascii=False, indent=2),
        )

    def apply_source_field_import(self):
        try:
            payload = self._source_field_import_payload()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Felder übernehmen",
                str(exc),
            )
            return

        answer = QMessageBox.question(
            self,
            "Felder übernehmen",
            "Die ausgewählten Felder wirklich in die Ziel-Entität "
            "übernehmen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.plugin.confirm_source_fields(
                payload["comparison_id"],
                payload["selected_fields"],
                target_entity_id=payload["entity_id"],
                note="Über Source-Manager-GUI bestätigt.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Felder übernehmen",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Felder übernommen",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_knowledge_graph()

    def compare_source_results_gui(self):
        raw = self.source_conflict_json.toPlainText().strip()
        if not raw:
            QMessageBox.information(
                self,
                "Quellen vergleichen",
                "Bitte zuerst Quellenergebnisse als JSON einfügen.",
            )
            return
        try:
            payload = json.loads(raw)
            if isinstance(payload, dict) and isinstance(
                payload.get("results"),
                list,
            ):
                payload = payload["results"]
            if not isinstance(payload, list):
                raise ValueError(
                    "Es wird eine JSON-Liste mit Quellenergebnissen erwartet."
                )
            result = self.plugin.compare_source_results(payload)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Quellen vergleichen",
                str(exc),
            )
            return

        self.source_comparison_id.setText(
            str(result.get("id") or "")
        )
        recommended = {
            str(item.get("field")): item.get("recommended_value")
            for item in result.get("fields") or []
            if item.get("recommended_value") is not None
        }
        self.source_field_selection.setPlainText(
            json.dumps(
                recommended,
                ensure_ascii=False,
                indent=2,
            )
        )
        self.show_scrollable_text_dialog(
            "Quellenvergleich",
            json.dumps(result, ensure_ascii=False, indent=2),
        )

    def show_source_conflict_status(self):
        try:
            status = self.plugin.get_source_conflict_status()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Konfliktstatus",
                str(exc),
            )
            return
        self.show_scrollable_text_dialog(
            "Source-Conflict-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def diagnose_source_policy_gui(self):
        source_id = self.source_select.currentData()
        if not source_id:
            QMessageBox.information(
                self,
                "Policy-Diagnose",
                "Bitte zuerst eine Quelle auswählen.",
            )
            return

        requested_url = self.source_url.text().strip() or None
        try:
            result = self.plugin.diagnose_source_policy(
                source_id,
                requested_url=requested_url,
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Policy-Diagnose",
                str(exc),
            )
            return

        lines = [
            "SOURCE POLICY DIAGNOSE",
            "======================",
            f"URL: {result.get('url')}",
            f"robots.txt: {result.get('robots_url')}",
            f"User-Agent: {result.get('user_agent')}",
            f"Status: {result.get('status')}",
            f"Erlaubt: {result.get('allowed')}",
            f"HTTP-Status: {result.get('http_status')}",
            f"Inhaltstyp: {result.get('content_type')}",
            f"robots.txt gefunden: {result.get('robots_found')}",
            f"Manuelle Entscheidung nötig: "
            f"{result.get('requires_manual_confirmation')}",
        ]
        if result.get("error_type") or result.get("error"):
            lines.extend(
                [
                    f"Fehlertyp: {result.get('error_type')}",
                    f"Fehler: {result.get('error')}",
                ]
            )
        preview = result.get("robots_text_preview")
        if preview:
            lines.extend(
                [
                    "",
                    "ROBOTS.TXT-AUSZUG",
                    "------------------",
                    str(preview),
                ]
            )

        self.show_scrollable_text_dialog(
            "Policy-Diagnose",
            "\n".join(lines),
        )

    def execute_source_scan_gui(self):
        source_id = self.source_select.currentData()
        if not source_id:
            QMessageBox.information(
                self,
                "Quelle scannen",
                "Bitte zuerst eine Quelle auswählen.",
            )
            return

        requested_url = self.source_url.text().strip() or None
        try:
            result = self.plugin.execute_source_scan(
                source_id,
                requested_url=requested_url,
                allow_unknown_policy=False,
            )
        except PermissionError as exc:
            try:
                diagnosis = self.plugin.diagnose_source_policy(
                    source_id,
                    requested_url=requested_url,
                )
                details = json.dumps(
                    diagnosis,
                    ensure_ascii=False,
                    indent=2,
                )
            except Exception:
                details = ""
            self.show_scrollable_text_dialog(
                "Quelle kann nicht gescannt werden",
                str(exc)
                + ("\n\n" + details if details else ""),
            )
            return
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Quelle scannen",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Strukturierte Quellen-Vorschau",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_sources_gui()

    def show_universe_franchise_builder_status(self):
        status = self.plugin.get_universe_franchise_builder_status()
        self.show_scrollable_text_dialog(
            "Universe-Franchise-Builder-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_event_intelligence_status(self):
        status = self.plugin.get_event_intelligence_status()
        self.show_scrollable_text_dialog(
            "Event-Intelligence-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_relationship_intelligence_status(self):
        status = self.plugin.get_relationship_intelligence_status()
        self.show_scrollable_text_dialog(
            "Relationship-Intelligence-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_character_intelligence_status(self):
        status = self.plugin.get_character_intelligence_status()
        self.show_scrollable_text_dialog(
            "Character-Intelligence-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_character_cast_resolver_status(self):
        status = self.plugin.get_character_cast_resolver_status()
        self.show_scrollable_text_dialog(
            "Character-Cast-Resolver-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_relationship_builder_status(self):
        status = self.plugin.get_relationship_builder_status()
        self.show_scrollable_text_dialog(
            "Relationship-Builder-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_persistent_graph_status(self):
        status = self.plugin.get_persistent_graph_status()
        self.show_scrollable_text_dialog(
            "Persistenter-Knowledge-Graph-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_knowledge_graph_builder_status(self):
        status = self.plugin.get_knowledge_graph_builder_status()
        self.show_scrollable_text_dialog(
            "Knowledge-Graph-Builder-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_semantic_field_classifier_status(self):
        status = self.plugin.get_semantic_field_classifier_status()
        self.show_scrollable_text_dialog(
            "Semantic-Field-Classifier-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_reasoning_context_status(self):
        try:
            status = self.plugin.get_reasoning_context_status()
        except Exception as exc:
            QMessageBox.warning(self, "Reasoning-Context-Status", str(exc))
            return
        self.show_scrollable_text_dialog(
            "Reasoning-Context-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_semantic_engine_status(self):
        status = {
            "strategy": "semantic_knowledge_engine_v271",
            "features": [
                "sentence_segmentation",
                "primary_entity_type_detection",
                "same_sentence_year_assignment",
                "multi_entity_proposals",
                "semantic_relation_detection",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }
        self.show_scrollable_text_dialog(
            "Semantic-Knowledge-Engine-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_knowledge_extractor_status(self):
        status = {
            "strategy": "semantic_knowledge_extractor_v272",
            "supported_outputs": [
                "field_candidates",
                "entity_proposals",
                "relation_proposals",
                "group_proposals",
            ],
            "automatic_import": False,
            "requires_confirmation": True,
        }
        self.show_scrollable_text_dialog(
            "Knowledge-Extractor-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_parser_manager_status(self):
        try:
            status = self.plugin.get_parser_manager_status()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Parser-Status",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Parser-Manager-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_source_manager_status(self):
        try:
            status = self.plugin.get_source_manager_status()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Source-Manager-Status",
                str(exc),
            )
            return
        self.show_scrollable_text_dialog(
            "Source-Manager-Status",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def show_reasoner_learning_status(self):
        try:
            status = self.plugin.reasoner_learning.status()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Reasoner-Lernstatus",
                str(exc),
            )
            return
        self.show_scrollable_text_dialog(
            "Reasoner-Lernstatus",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def run_semantic_graph_reasoner(self):
        try:
            result = self.plugin.reason_about_knowledge_graph()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Graph analysieren",
                str(exc),
            )
            return

        queue = result.get("queue") or {}
        lines = [
            "SEMANTIC GRAPH REASONER",
            "=======================",
            f"Entitäten geprüft: {result.get('entity_count', 0)}",
            f"Vorschläge: {result.get('proposal_count', 0)}",
            f"Bereits vorhandene Beziehungen übersprungen: "
            f"{result.get('skipped_existing_relation_count', 0)}",
            f"Neu in Warteschlange: {queue.get('created_count', 0)}",
            f"Schon vorhanden: {queue.get('existing_count', 0)}",
            "",
        ]

        for proposal in result.get("proposals") or []:
            confidence = round(
                float(proposal.get("confidence") or 0.0) * 100,
                1,
            )
            base_confidence = round(
                float(
                    proposal.get("base_confidence")
                    or proposal.get("confidence")
                    or 0.0
                )
                * 100,
                1,
            )
            learning_adjustment = round(
                float(proposal.get("learning_adjustment") or 0.0) * 100,
                1,
            )
            if proposal.get("kind") == "direct_relation":
                lines.append(
                    f"{proposal.get('source_title')} "
                    f"--{proposal.get('relation_type')}--> "
                    f"{proposal.get('target_title')} "
                    f"({confidence} %)"
                )
            else:
                lines.append(
                    f"{proposal.get('entity_title')} "
                    f"--{proposal.get('relation_type')}--> "
                    f"{proposal.get('group_name')} "
                    f"({confidence} %)"
                )
            lines.append(
                f"  Basis: {base_confidence} % | "
                f"Lernanpassung: {learning_adjustment:+.1f} %"
            )
            lines.append(f"  Warum: {proposal.get('reason')}")
            for evidence in proposal.get("evidence") or []:
                lines.append(
                    f"  Beleg: {evidence.get('type')} = "
                    f"{evidence.get('value')}"
                )
            lines.append("")

        if not result.get("proposals"):
            lines.append(
                "Keine neuen ausreichend sicheren Vorschläge gefunden."
            )

        self.show_scrollable_text_dialog(
            "Semantic Graph Reasoner",
            "\n".join(lines),
        )
        self.refresh_graph_proposals()

    def generate_graph_proposals(self):
        try:
            result = self.plugin.generate_knowledge_graph_proposals()
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Automatische Vorschläge",
                str(exc),
            )
            return

        queue = result.get("queue") or {}
        self.show_scrollable_text_dialog(
            "Automatische Knowledge-Graph-Vorschläge",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        QMessageBox.information(
            self,
            "Automatische Vorschläge",
            f"Neu erzeugt: {queue.get('created_count', 0)}\n"
            f"Bereits vorhanden: {queue.get('existing_count', 0)}",
        )
        self.refresh_graph_proposals()

    def refresh_graph_proposals(self):
        if not hasattr(self, "graph_proposal_select"):
            return
        try:
            proposals = self.plugin.get_knowledge_graph_proposals()
        except Exception as exc:
            self.graph_proposal_select.clear()
            self.graph_proposal_select.addItem(
                f"Vorschlagsliste konnte nicht geladen werden: {exc}",
                None,
            )
            return

        self.graph_proposal_select.clear()
        active = [
            item for item in proposals
            if item.get("status") in {"pending", "later"}
        ]
        if not active:
            self.graph_proposal_select.addItem(
                "Keine offenen Vorschläge",
                None,
            )
            return

        for item in active:
            if item.get("kind") == "direct_relation":
                label = (
                    f"{item.get('source_title')} "
                    f"--{item.get('relation_type')}--> "
                    f"{item.get('target_title')} "
                    f"[{item.get('status')}]"
                )
            elif item.get("kind") == "order":
                label = (
                    f"{item.get('name')} "
                    f"[{item.get('order_type')}; "
                    f"{item.get('status')}]"
                )
            else:
                label = (
                    f"{item.get('entity_title')} "
                    f"--{item.get('relation_type')}--> "
                    f"{item.get('group_name')} "
                    f"[{item.get('status')}]"
                )
            self.graph_proposal_select.addItem(
                label,
                str(item.get("id")),
            )

    def _selected_graph_proposal_id(self):
        proposal_id = self.graph_proposal_select.currentData()
        if not proposal_id:
            QMessageBox.information(
                self,
                "Vorschlagsliste",
                "Kein offener Vorschlag ausgewählt.",
            )
            return None
        return str(proposal_id)

    def accept_graph_proposal(self):
        proposal_id = self._selected_graph_proposal_id()
        if not proposal_id:
            return
        answer = QMessageBox.question(
            self,
            "Vorschlag bestätigen",
            "Diesen Beziehungsvorschlag dauerhaft übernehmen?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            result = self.plugin.accept_knowledge_graph_proposal(
                proposal_id
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Vorschlag bestätigen",
                str(exc),
            )
            return
        self.show_scrollable_text_dialog(
            "Vorschlag übernommen",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_knowledge_graph()

    def reject_graph_proposal(self):
        proposal_id = self._selected_graph_proposal_id()
        if not proposal_id:
            return
        try:
            proposal = next(
                (
                    item
                    for item in self.plugin.get_knowledge_graph_proposals()
                    if str(item.get("id")) == str(proposal_id)
                ),
                None,
            )
            self.plugin.update_knowledge_graph_proposal(
                proposal_id,
                "rejected",
                "Über Desktop-GUI abgelehnt.",
            )
            if proposal:
                self.plugin.reasoner_learning.record(
                    proposal,
                    "rejected",
                    note="Über Desktop-GUI abgelehnt.",
                )
        except Exception as exc:
            QMessageBox.warning(self, "Vorschlag ablehnen", str(exc))
            return
        self.refresh_graph_proposals()

    def defer_graph_proposal(self):
        proposal_id = self._selected_graph_proposal_id()
        if not proposal_id:
            return
        try:
            proposal = next(
                (
                    item
                    for item in self.plugin.get_knowledge_graph_proposals()
                    if str(item.get("id")) == str(proposal_id)
                ),
                None,
            )
            self.plugin.update_knowledge_graph_proposal(
                proposal_id,
                "later",
                "Zur späteren Prüfung zurückgestellt.",
            )
            if proposal:
                self.plugin.reasoner_learning.record(
                    proposal,
                    "later",
                    note="Zur späteren Prüfung zurückgestellt.",
                )
        except Exception as exc:
            QMessageBox.warning(self, "Später prüfen", str(exc))
            return
        self.refresh_graph_proposals()

    def create_graph_order(self):
        name = self.graph_order_name.text().strip()
        entries = [
            line.strip()
            for line in self.graph_order_entities.toPlainText().splitlines()
            if line.strip()
        ]
        try:
            entity_ids = self._resolve_graph_entity_ids(entries)
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Reihenfolge speichern",
                str(exc),
            )
            return
        if not name:
            QMessageBox.warning(
                self,
                "Reihenfolge speichern",
                "Bitte einen Namen eingeben.",
            )
            return
        if not entity_ids:
            QMessageBox.warning(
                self,
                "Reihenfolge speichern",
                "Bitte mindestens eine Entitäts-ID eingeben.",
            )
            return

        try:
            result = self.plugin.create_knowledge_graph_order(
                name,
                self.graph_order_type.currentData(),
                entity_ids,
                source="desktop_gui_user_confirmation",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Reihenfolge speichern",
                str(exc),
            )
            return

        self.show_scrollable_text_dialog(
            "Reihenfolge gespeichert",
            json.dumps(result, ensure_ascii=False, indent=2),
        )
        self.refresh_knowledge_graph()

    def _prefill_identity_fields(self, result):
        semantic = result.get("semantic_identity") or {}
        identity = semantic.get("identity") or {}
        identification = result.get("identification") or {}

        media_type = (
            identity.get("media_type")
            or identification.get("media_type")
            or "unknown"
        )
        index = self.identity_media_type.findData(media_type)
        self.identity_media_type.setCurrentIndex(
            index if index >= 0 else 0
        )

        self.identity_title.setText(
            str(
                identity.get("title")
                or identification.get("title_candidate")
                or ""
            )
        )
        self.identity_year.setValue(
            int(identity.get("year") or identification.get("year") or 0)
        )
        self.identity_season.setValue(
            int(identity.get("season") or identification.get("season") or 0)
        )
        episode = identity.get("episode")
        if episode is None:
            episode = identification.get("episode")
        self.identity_episode.setValue(int(episode or 0))
        self.identity_edition.setText(
            str(
                identity.get("edition")
                or identification.get("edition_candidate")
                or ""
            )
        )

        final_status = semantic.get("final_status") or "unknown"
        confidence = semantic.get("confidence_percent")
        self.learning_status_label.setText(
            f"Semantischer Status: {final_status}; "
            f"Vertrauen: {confidence if confidence is not None else '-'} %"
        )

    def _corrected_identity(self):
        title = self.identity_title.text().strip()
        if not title:
            raise ValueError("Bitte einen korrekten Titel eingeben.")

        return {
            "media_type": self.identity_media_type.currentData()
            or "unknown",
            "title": title,
            "year": self.identity_year.value() or None,
            "season": self.identity_season.value() or None,
            "episode": self.identity_episode.value() or None,
            "edition": self.identity_edition.text().strip() or None,
            "confidence": 1.0,
            "source": "user_confirmation",
        }

    def confirm_and_learn_identity(self):
        if not self.last_analysis_result:
            QMessageBox.warning(
                self,
                "Identität bestätigen",
                "Bitte zuerst eine Datei analysieren.",
            )
            return

        try:
            corrected = self._corrected_identity()
        except ValueError as exc:
            QMessageBox.warning(self, "Identität bestätigen", str(exc))
            return

        answer = QMessageBox.question(
            self,
            "Identität bestätigen und lernen",
            "Diese Zuordnung wird dauerhaft in der lokalen "
            "MediaHub-KI-Wissensdatenbank gespeichert.\n\n"
            f"Typ: {corrected['media_type']}\n"
            f"Titel: {corrected['title']}\n"
            f"Jahr: {corrected['year'] or '-'}\n\n"
            "Ist die Identität sicher korrekt?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.plugin.confirm_and_learn_identity(
                self.last_analysis_result,
                corrected,
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Lernen fehlgeschlagen",
                str(exc),
            )
            return

        fingerprint_saved = bool(result.get("fingerprint_detected"))
        visual_saved = bool(result.get("visual_knowledge_detected"))
        database_path = result.get("database_path") or "-"

        self.learning_status_label.setText(
            "Identität gespeichert: "
            f"{corrected['title']} | "
            f"Fingerprint: {'ja' if fingerprint_saved else 'nein'} | "
            f"Visual Knowledge: {'ja' if visual_saved else 'nein'}"
        )
        self.analysis_text.appendPlainText(
            "\n\nBESTÄTIGTES LERNEN\n"
            "-------------------\n"
            + json.dumps(result, ensure_ascii=False, indent=2)
        )
        QMessageBox.information(
            self,
            "Identität gelernt",
            "Die Identität wurde gespeichert.\n\n"
            f"Fingerprint gespeichert: "
            f"{'Ja' if fingerprint_saved else 'Nein'}\n"
            f"Visual Knowledge gespeichert: "
            f"{'Ja' if visual_saved else 'Nein'}\n"
            f"Wissensdatenbank:\n{database_path}",
        )

    def show_learning_status(self):
        try:
            status = self.plugin.get_learning_status()
        except Exception as exc:
            QMessageBox.warning(self, "Lernstatus", str(exc))
            return

        self.learning_status_label.setText(
            f"Gelernte Identitäten: "
            f"{status.get('learned_identity_count', 0)} | "
            f"Fingerprints: "
            f"{status.get('fingerprint_reference_count', 0)} | "
            f"Visual Knowledge: "
            f"{status.get('visual_knowledge_count', 0)}"
        )
        self.show_scrollable_text_dialog(
            "Lernstatus",
            json.dumps(status, ensure_ascii=False, indent=2),
        )

    def reanalyze_current_file(self):
        if not self.last_analyzed_path:
            return
        try:
            result = self.plugin.analyze_media_file(
                self.last_analyzed_path,
                force=True,
            )
            self.last_analysis_result = result
            self._prefill_identity_fields(result)
        except Exception as exc:
            self.analysis_text.setPlainText(
                f"Erneute Analyse fehlgeschlagen:\n{exc}"
            )
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

