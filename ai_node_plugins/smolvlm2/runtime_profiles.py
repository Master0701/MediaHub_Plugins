"""Platform-specific runtime profiles for SmolVLM2."""

from __future__ import annotations

import os
import platform
from typing import Any

WINDOWS_CUDA_INDEX = (
    "https://download.pytorch.org/whl/cu126"
)

WINDOWS_CPU_INDEX = (
    "https://download.pytorch.org/whl/cpu"
)


COMMON_PACKAGES = (
    "transformers",
    "accelerate",
    "safetensors",
    "huggingface_hub",
    "Pillow",
    "num2words",
    "numpy",
)


WINDOWS_CUDA_PACKAGES = (
    "torch==2.14.0+cu126",
    "torchvision==0.29.0+cu126",
)


WINDOWS_CPU_PACKAGES = (
    "torch==2.14.0",
    "torchvision==0.29.0",
)


def platform_info() -> dict[str, Any]:
    return {
        "os": os.name,
        "system": platform.system(),
        "machine": platform.machine(),
        "python_architecture": platform.architecture()[0],
    }


def is_windows_x64() -> bool:
    machine = platform.machine().lower()

    return (
        os.name == "nt"
        and machine in {
            "amd64",
            "x86_64",
        }
    )


def is_linux_arm64() -> bool:
    machine = platform.machine().lower()

    return (
        os.name == "posix"
        and platform.system().lower() == "linux"
        and machine in {
            "aarch64",
            "arm64",
        }
    )


def runtime_profile(
    backend: str = "auto",
) -> dict[str, Any]:

    backend = str(
        backend or "auto"
    ).strip().lower()

    if backend not in {
        "auto",
        "cpu",
        "cuda",
    }:
        raise ValueError(
            f"Unbekanntes Backend: {backend}"
        )

    if is_windows_x64():
        return {
            "platform": "windows-x64",
            "requested_backend": backend,
            "cpu": {
                "supported": True,
                "index_url": WINDOWS_CPU_INDEX,
                "packages": list(
                    WINDOWS_CPU_PACKAGES
                ),
            },
            "cuda": {
                "supported": True,
                "cuda_runtime": "12.6",
                "index_url": WINDOWS_CUDA_INDEX,
                "packages": list(
                    WINDOWS_CUDA_PACKAGES
                ),
            },
            "common_packages": list(
                COMMON_PACKAGES
            ),
        }

    if is_linux_arm64():
        return {
            "platform": "linux-arm64",
            "requested_backend": backend,
            "cpu": {
                "supported": True,
                "index_url": None,
                "packages": [
                    "torch==2.14.1+cpu",
                    "torchvision==0.29.1+cpu",
                ],
            },
            "cuda": {
                "supported": False,
                "reason": (
                    "CUDA-Profil ist fuer "
                    "Raspberry-Pi/Linux-ARM64 "
                    "nicht vorgesehen."
                ),
            },
            "common_packages": list(
                COMMON_PACKAGES
            ),
        }

    return {
        "platform": "unsupported",
        "requested_backend": backend,
        "platform_info": platform_info(),
        "cpu": {
            "supported": False,
        },
        "cuda": {
            "supported": False,
        },
        "common_packages": list(
            COMMON_PACKAGES
        ),
    }
