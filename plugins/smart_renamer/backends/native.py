from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backends.base import RenamerBackend
from services.rule_engine import RenameRuleEngine


class NativeRenamerBackend(RenamerBackend):
    backend_id = "mediahub_native"
    display_name = "MediaHub Native Renamer"
    platform_names = ("windows",)
    priority = 20
    tool_id = None
    homepage = ""
    license_name = "MediaHub-Projektlizenz"
    preview_bridge_ready = True
    execution_bridge_ready = False
    capabilities = (
        "preview_changes", "rename_files", "rename_folders",
        "custom_naming_schemes", "undo_plan",
    )

    def __init__(self):
        self.rule_engine = RenameRuleEngine()

    def probe(self) -> dict[str, Any]:
        return {
            "backend_id": self.backend_id, "display_name": self.display_name,
            "installed": True, "enabled": True, "reachable": True,
            "healthy": True, "platform_compatible": os.name == "nt",
            "capabilities": list(self.capabilities), "version": "0.3.0",
            "priority": self.priority, "tool_id": self.tool_id,
            "homepage": self.homepage, "license": self.license_name,
            "preview_bridge_ready": True, "execution_bridge_ready": False,
            "configuration_ready": True,
            "reason": "built_in_backend" if os.name == "nt" else "windows_plugin_not_supported",
        }

    def preview(self, items: list[dict[str, Any]], rules: list[dict[str, Any]]) -> dict[str, Any]:
        changes=[]; conflicts=[]; target_index={}; warning_count=0
        for index,item in enumerate(items):
            source=Path(str(item.get("path") or "")); original=source.name
            evaluated=self.rule_engine.apply(original,rules,item_index=index,metadata=dict(item.get("metadata") or {}))
            proposed=evaluated["proposed_name"]; target=source.with_name(proposed)
            warnings=list(evaluated["warnings"]); warning_count += len(warnings)
            record={
                "index":index,"source_path":str(source),"original_name":original,
                "proposed_name":proposed,"target_path":str(target),
                "changed":proposed!=original,"exists":source.exists(),
                "automatic_execution":False,"requires_confirmation":True,
                "applied_rules":evaluated["applied_rules"],
                "change_source":evaluated["change_source"],
                "warnings":warnings,"extension_protected":evaluated["extension_protected"],
                "item_type":"folder" if source.is_dir() else "file",
            }
            changes.append(record)
            key=os.path.normcase(os.path.abspath(str(target))); target_index.setdefault(key,[]).append(index)
        for target,indexes in target_index.items():
            if len(indexes)>1:
                conflicts.append({"type":"duplicate_target","target_path":target,"item_indexes":indexes})
        return {
            "backend_id":self.backend_id,"changes":changes,"conflicts":conflicts,
            "summary":{"item_count":len(changes),"changed_count":sum(1 for x in changes if x["changed"]),"conflict_count":len(conflicts),"warning_count":warning_count},
            "automatic_execution":False,"requires_confirmation":True,
        }
