from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.backend_registry import RenamerBackendRegistry
from services.preview_service import RenamePreviewService
from services.profile_service import ProfileService
from services.learning_store import LearningStore
from services.optional_integrations import OptionalIntegrationManager


class MediaHubSmartRenamerPlugin:
    """Windows-Smart-Renamer mit Desktop- und lokaler Weboberfläche.

    Version 0.4.8 bleibt strikt im Vorschau-Modus. Es werden weder Dateien
    noch Ordner umbenannt. Das spätere Raspberry-Pi-Backend gehört in ein
    separates MediaHub-AI-Node-Plugin und ist hier bewusst nicht enthalten.
    """

    VERSION = "0.4.8"

    def __init__(
        self,
        plugin_path: Path | str | None = None,
        mediahub_api=None,
        api=None,
    ):
        self.plugin_path = Path(plugin_path or Path(__file__).resolve().parent)
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
        self.preview_service = RenamePreviewService(
            backend_registry=self.backend_registry
        )
        self.profile_service = ProfileService(self.plugin_path)
        self.learning_store = LearningStore(self.base_dir)
        self.integrations = OptionalIntegrationManager(self.mediahub_api)
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
            "/smart-renamer/assets/mediahub.css": self._stylesheet,
        }.items():
            self.server.add_route(path, handler, owner=self)

        self.server.add_post_route(
            "/smart-renamer/api/preview",
            self._web_preview,
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
            "automatic_install": True,
            "automatic_rename": False,
            "desktop_ui": True,
            "web_ui": self.server is not None,
            "mobile_responsive_ui": self.server is not None,
            "capability_status": capability_status,
            "message": (
                "Smart Renamer v0.4.8 nutzt eine konservative Decision Engine und läuft eigenständig und aktiviert optionale Plugin-Integrationen nur bei tatsächlich verfügbarer Capability."
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

    def preview_rename(self, items, rules=None, preferred_backend=None):
        enriched_items, metadata_status = self.integrations.enrich_items(
            list(items or [])
        )
        result = self.preview_service.create_preview(
            items=enriched_items,
            rules=list(rules or []),
            preferred_backend=preferred_backend,
        )
        return {
            **result,
            "optional_integrations": {
                "metadata_editor": metadata_status.to_dict(),
            },
        }

    def get_optional_integrations(self):
        return {
            "metadata_editor": self.integrations.metadata_status().to_dict(),
        }

    def attach_optional_provider(self, capability: str, provider):
        """Öffentlicher, optionaler Hook für MediaHub/andere Plugins."""
        self.integrations.attach_provider(capability, provider)
        return self.get_optional_integrations()

    def detach_optional_provider(self, capability: str):
        self.integrations.detach_provider(capability)
        return self.get_optional_integrations()

    def execute_rename(self, *args, **kwargs):
        raise RuntimeError(
            "Ausführung ist in Smart Renamer v0.4.8 noch gesperrt. "
            "Es sind ausschließlich Vorschauen erlaubt."
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
            "automatic_application": False,
        })

    def _web_integrations(self, request=None):
        return self._json({
            "ok": True,
            "items": self.get_optional_integrations(),
            "all_optional": True,
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
                    "Sicherer Vorschau-Modus: v0.4.0 verändert keine Dateien. "
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

                # Center: preview table
                center = QWidget(); center_layout=QVBoxLayout(center); center_layout.setContentsMargins(0,0,0,0)
                center_layout.addWidget(QLabel("Vorschau"))
                self.table = QTableWidget(0, 6)
                self.table.setHorizontalHeaderLabels(["Status", "Original", "Vorschlag", "Quelle", "Hinweise", "Zielpfad"])
                self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
                self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
                header=self.table.horizontalHeader(); header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents); header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
                center_layout.addWidget(self.table,1)

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
                outer.setStretchFactor(0,2); outer.setStretchFactor(1,6); outer.setStretchFactor(2,3)
                root.addWidget(outer,1)

                self.status = QLabel("Bereit")
                self.status.setWordWrap(True)
                root.addWidget(self.status)

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
                    values=[status,item.get("original_name",""),item.get("proposed_name",""),source,issue_text,item.get("target_path","")]
                    for c,value in enumerate(values): self.table.setItem(r,c,QTableWidgetItem(str(value)))
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
