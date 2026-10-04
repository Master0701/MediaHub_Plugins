"""Model metadata and local cache handling for SmolVLM2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MODEL_ID = (
    "HuggingFaceTB/"
    "SmolVLM2-500M-Video-Instruct"
)

MODEL_FAMILY = "SmolVLM2"
MODEL_VARIANT = "500M-Video-Instruct"
MODEL_TOOL_ID = "smolvlm2-model"
MODEL_PACKAGE_VERSION = "0.1.0"


def model_metadata() -> dict[str, Any]:
    return {
        "family": MODEL_FAMILY,
        "variant": MODEL_VARIANT,
        "model_id": MODEL_ID,
        "distribution": "mediahub_tools",
        "bundled": False,
    }


def model_status(
    models_root: str | Path,
) -> dict[str, Any]:
    root = Path(models_root)

    local = (
        root
        / "SmolVLM2-500M-Video-Instruct"
    )

    return {
        **model_metadata(),
        "root": str(local),
        "local_exists": local.is_dir(),
    }

