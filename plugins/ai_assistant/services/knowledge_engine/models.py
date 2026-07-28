from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any
from uuid import uuid4


class RelationType(StrEnum):
    FRANCHISE = "franchise"
    UNIVERSE = "universe"
    SPIN_OFF = "spin_off"
    PREQUEL = "prequel"
    SEQUEL = "sequel"
    CROSSOVER = "crossover"
    REMAKE = "remake"
    REBOOT = "reboot"
    ALTERNATE_TIMELINE = "alternate_timeline"
    CONTINUES_IN = "continues_in"
    STARTS_IN = "starts_in"


class OrderType(StrEnum):
    CHRONOLOGICAL = "chronological"
    RELEASE = "release"
    WATCH = "watch"
    CUSTOM = "custom"


@dataclass(slots=True)
class KnowledgeEntity:
    title: str
    media_type: str
    year: int | None = None
    external_ids: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeRelation:
    source_id: str
    target_id: str
    relation_type: RelationType
    label: str = ""
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["relation_type"] = self.relation_type.value
        return data


@dataclass(slots=True)
class OrderEntry:
    entity_id: str
    position: int
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class KnowledgeOrder:
    name: str
    order_type: OrderType
    entries: list[OrderEntry] = field(default_factory=list)
    description: str = ""
    source: str = "local"
    id: str = field(default_factory=lambda: uuid4().hex)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "order_type": self.order_type.value,
            "description": self.description,
            "source": self.source,
            "entries": [entry.as_dict() for entry in self.entries],
        }
