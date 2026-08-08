from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VALID_STATES = {"accepted", "ignored", "manual", "review", "conflict", "pending"}

@dataclass(slots=True)
class PreviewDecision:
    item_id: str
    state: str = "pending"
    manual_name: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"Ungültiger Preview-Status: {self.state}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class PreviewDecisionStore:
    """Nur Vorschauzustand. Führt keinerlei Dateisystemaktion aus."""

    def __init__(self) -> None:
        self._values: dict[str, PreviewDecision] = {}

    def set(self, item_id: str, *, state: str, manual_name: str = "", note: str = "") -> dict[str, Any]:
        value = PreviewDecision(item_id=item_id, state=state, manual_name=manual_name, note=note)
        self._values[item_id] = value
        return value.to_dict()

    def get(self, item_id: str) -> dict[str, Any]:
        return (self._values.get(item_id) or PreviewDecision(item_id=item_id)).to_dict()

    def all(self) -> list[dict[str, Any]]:
        return [self._values[key].to_dict() for key in sorted(self._values)]

    def clear(self) -> None:
        self._values.clear()
