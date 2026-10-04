"""Execution backend selection for SmolVLM2."""

from __future__ import annotations

import os
from typing import Any


def cpu_thread_count() -> int:
    count = os.cpu_count() or 4
    return max(1, min(count, 8))


def select_execution(
    requested: str = "auto",
) -> dict[str, Any]:
    """Select requested execution backend.

    Actual CUDA availability is checked inside the isolated
    SmolVLM2 runtime where PyTorch is installed.
    """

    backend = str(requested or "auto").strip().lower()

    if backend not in {
        "auto",
        "cpu",
        "cuda",
    }:
        raise ValueError(
            "Unbekanntes SmolVLM2-Backend: "
            f"{backend}"
        )

    return {
        "requested_backend": backend,
        "backend": backend,
        "cpu_threads": cpu_thread_count(),
    }
