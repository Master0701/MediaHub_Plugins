from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from mediahub_smart_renamer_runtime.services.preview_decisions import PreviewDecisionStore

@dataclass(slots=True)
class PreviewSelection:
    selected_ids: set[str] = field(default_factory=set)
    selected_group: str = ""
    status_filter: str = "all"
    sort_by: str = "current_name"
    sort_direction: str = "asc"
    search_text: str = ""

class GUIPreviewSession:
    VALID_STATUS = {"all", "safe", "review", "conflict"}
    VALID_SORT = {"current_name","suggested_name","relation_type","confidence","season","episode","status"}
    VALID_DIRECTION = {"asc","desc"}

    def __init__(self, decision_store: PreviewDecisionStore | None = None):
        self.decision_store = decision_store or PreviewDecisionStore()
        self.selection = PreviewSelection()

    def set_selection(self, item_ids: list[str]) -> dict[str, Any]:
        self.selection.selected_ids = {str(v) for v in item_ids}
        return self.snapshot()

    def toggle_selection(self, item_id: str) -> dict[str, Any]:
        item_id = str(item_id)
        if item_id in self.selection.selected_ids:
            self.selection.selected_ids.remove(item_id)
        else:
            self.selection.selected_ids.add(item_id)
        return self.snapshot()

    def clear_selection(self) -> dict[str, Any]:
        self.selection.selected_ids.clear()
        return self.snapshot()

    def set_group(self, group_key: str) -> dict[str, Any]:
        self.selection.selected_group = str(group_key or "")
        return self.snapshot()

    def set_status_filter(self, status: str) -> dict[str, Any]:
        status = str(status or "all").casefold()
        if status not in self.VALID_STATUS:
            raise ValueError(f"Ungültiger Statusfilter: {status}")
        self.selection.status_filter = status
        return self.snapshot()

    def set_sort(self, sort_by: str, direction: str = "asc") -> dict[str, Any]:
        sort_by = str(sort_by or "current_name")
        direction = str(direction or "asc").casefold()
        if sort_by not in self.VALID_SORT:
            raise ValueError(f"Ungültige Sortierung: {sort_by}")
        if direction not in self.VALID_DIRECTION:
            raise ValueError(f"Ungültige Sortierrichtung: {direction}")
        self.selection.sort_by = sort_by
        self.selection.sort_direction = direction
        return self.snapshot()

    def set_search(self, search_text: str) -> dict[str, Any]:
        self.selection.search_text = str(search_text or "")
        return self.snapshot()

    def bulk_decision(self, state: str) -> list[dict[str, Any]]:
        return [
            self.decision_store.set(item_id, state=state)
            for item_id in sorted(self.selection.selected_ids)
        ]

    def apply_manual_name(self, item_id: str, manual_name: str, note: str = "") -> dict[str, Any]:
        name = str(manual_name or "").strip()
        if not name:
            raise ValueError("Manueller Zielname darf nicht leer sein.")
        return self.decision_store.set(str(item_id), state="manual", manual_name=name, note=note)

    def snapshot(self) -> dict[str, Any]:
        return {
            "selected_ids": sorted(self.selection.selected_ids),
            "selected_group": self.selection.selected_group,
            "status_filter": self.selection.status_filter,
            "sort_by": self.selection.sort_by,
            "sort_direction": self.selection.sort_direction,
            "search_text": self.selection.search_text,
            "decisions": self.decision_store.all(),
            "execution_locked": True,
        }
