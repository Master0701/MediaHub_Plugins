from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Capability:
    """Eine vom Plugin-Manifest gemeldete Fähigkeit."""

    name: str

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValueError("Capability-Name darf nicht leer sein.")
        object.__setattr__(self, "name", normalized)
