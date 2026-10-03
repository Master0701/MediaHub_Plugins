"""GLiNER semantic text analysis engine."""

from __future__ import annotations

import importlib.util
from typing import Any


class GLiNEREngineError(RuntimeError):
    pass


def gliner_available() -> bool:
    return (
        importlib.util.find_spec("gliner")
        is not None
    )


def engine_status() -> dict[str, Any]:
    return {
        "engine": "gliner",
        "available": gliner_available(),
    }


def analyze_text(
    *,
    text: str,
    execution: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = str(text or "").strip()

    if not text:
        raise GLiNEREngineError(
            "GLiNER benoetigt einen nicht leeren Text."
        )

    options = dict(options or {})

    if options.get("mock", False):
        return _mock_analyze(
            text=text,
            execution=execution,
            options=options,
        )

    if not gliner_available():
        raise GLiNEREngineError(
            "GLiNER ist fuer dieses Plugin noch "
            "nicht installiert."
        )

    return _gliner_analyze(
        text=text,
        execution=execution,
        options=options,
    )


def _mock_analyze(
    *,
    text: str,
    execution: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    entities = list(
        options.get("mock_entities") or []
    )

    return {
        "engine": "mock",
        "model": "mock",
        "text": text,
        "entities": entities,
        "execution": execution,
    }


def _gliner_analyze(
    *,
    text: str,
    execution: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    from gliner import GLiNER

    model_name = str(
        options.get(
            "model",
            "urchade/gliner_multi-v2.1",
        )
    )

    labels = list(
        options.get("labels")
        or [
            "title",
            "person",
            "organization",
            "location",
            "episode",
            "media franchise",
        ]
    )

    threshold = float(
        options.get(
            "threshold",
            0.35,
        )
    )

    backend = str(
        execution.get(
            "backend",
            "cpu",
        )
    ).strip().lower()

    if backend not in {
        "cpu",
        "cuda",
        "gpu",
    }:
        raise GLiNEREngineError(
            "Unbekanntes GLiNER-Backend: "
            f"{backend}"
        )

    device = (
        "cuda"
        if backend in {
            "cuda",
            "gpu",
        }
        else "cpu"
    )

    if device == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise GLiNEREngineError(
                "CUDA wurde fuer GLiNER angefordert, "
                "ist in dieser Runtime aber nicht "
                "verfuegbar."
            )

    model = GLiNER.from_pretrained(
        model_name
    )

    model = model.to(
        device
    )

    predictions = model.predict_entities(
        text,
        labels,
        threshold=threshold,
    )

    entities = []

    for item in predictions:
        entities.append(
            {
                "text": str(
                    item.get("text", "")
                ),
                "label": str(
                    item.get("label", "")
                ),
                "score": float(
                    item.get("score", 0.0)
                ),
                "start": item.get("start"),
                "end": item.get("end"),
            }
        )

    return {
        "engine": "gliner",
        "model": model_name,
        "text": text,
        "labels": labels,
        "threshold": threshold,
        "entities": entities,
        "execution": execution,
    }
