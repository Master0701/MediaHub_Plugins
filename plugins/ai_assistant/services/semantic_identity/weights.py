from __future__ import annotations

from typing import Final


SOURCE_WEIGHTS: Final[dict[str, float]] = {
    "fingerprint": 1.00,
    "learned_knowledge": 0.94,
    "visual_knowledge": 0.92,
    "online": 0.82,
    "visual_ocr": 0.76,
    "subtitle": 0.74,
    "audio": 0.68,
    "filename": 0.58,
    "technical": 0.34,
    "other": 0.40,
}

GROUP_WEIGHTS: Final[dict[str, float]] = {
    "fingerprint": 1.00,
    "knowledge": 0.94,
    "visual": 0.88,
    "visual_text": 0.78,
    "online": 0.82,
    "subtitle": 0.76,
    "audio": 0.70,
    "filename": 0.58,
    "technical": 0.34,
    "other": 0.40,
}


def source_weight(source: str | None) -> float:
    return SOURCE_WEIGHTS.get(str(source or "other").strip().lower(), 0.40)


def group_weight(group: str | None) -> float:
    return GROUP_WEIGHTS.get(str(group or "other").strip().lower(), 0.40)
