"""Runtime manifest for the SmolVLM2 Compute-Node plugin."""

from __future__ import annotations

from typing import Any

RUNTIME_SCHEMA_VERSION = 1
RUNTIME_VERSION = "0.1.0"

MODEL_ID = (
    "HuggingFaceTB/"
    "SmolVLM2-500M-Video-Instruct"
)

MODEL_FAMILY = "SmolVLM2"
MODEL_VARIANT = "500M-Video-Instruct"
MODEL_TOOL_ID = "smolvlm2-model"
MODEL_PACKAGE_VERSION = "0.1.0"


def runtime_manifest() -> dict[str, Any]:
    """Return the platform-neutral SmolVLM2 runtime manifest."""

    return {
        "schema_version": RUNTIME_SCHEMA_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "runtime_id": "smolvlm2",
        "name": "SmolVLM2 Runtime",
        "model": {
            "id": MODEL_ID,
            "family": MODEL_FAMILY,
            "variant": MODEL_VARIANT,
            "source": "huggingface",
            "bundled": False,
        },
        "execution": {
            "backends": [
                "cpu",
                "cuda",
            ],
            "default_backend": "auto",
        },
        "platforms": {
            "windows-x64": {
                "supported": True,
                "plugin_type": "windows_compute",
                "backends": [
                    "cpu",
                    "cuda",
                ],
            },
            "linux-arm64": {
                "supported": True,
                "plugin_type": "ai_node",
                "backends": [
                    "cpu",
                ],
            },
        },
        "distribution": {
            "repository": "MediaHub_Tools",
            "tool_id": MODEL_TOOL_ID,
            "package_version": MODEL_PACKAGE_VERSION,
            "runtime_bundled_in_plugin": False,
            "model_bundled_in_plugin": False,
        },
    }

