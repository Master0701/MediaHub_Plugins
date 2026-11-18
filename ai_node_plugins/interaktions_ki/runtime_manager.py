"""Read-only llama.cpp runtime discovery and validated launch planning.

No download, installation, process launch or filesystem mutation is performed.
"""
from __future__ import annotations

import os
from pathlib import Path


class RuntimeConfigurationError(ValueError):
    pass


def inspect_runtime(binary_path: str | None = None, model_path: str | None = None) -> dict:
    binary = Path(binary_path or os.environ.get("MEDIAHUB_LLAMA_SERVER_EXE", "")) if (binary_path or os.environ.get("MEDIAHUB_LLAMA_SERVER_EXE")) else None
    model = Path(model_path or os.environ.get("MEDIAHUB_LLAMA_MODEL", "")) if (model_path or os.environ.get("MEDIAHUB_LLAMA_MODEL")) else None
    binary_ready = bool(binary and binary.is_file() and binary.name.lower() in {"llama-server.exe", "llama-server"})
    model_ready = bool(model and model.is_file() and model.suffix.lower() == ".gguf")
    return {"ready": binary_ready and model_ready, "binary_ready": binary_ready, "model_ready": model_ready, "binary": str(binary) if binary else None, "model": str(model) if model else None}


def plan_launch(*, binary_path: str, model_path: str, mode: str = "auto", devices: list[str] | None = None, gpu_layers: int = 0, cpu_threads: int = 4, port: int = 8080, tensor_split: list[float] | None = None) -> dict:
    status = inspect_runtime(binary_path, model_path)
    if not status["ready"]:
        raise RuntimeConfigurationError("llama-server oder GGUF-Modell fehlt bzw. ist ungueltig")
    if mode not in {"auto", "cpu", "gpu"}:
        raise RuntimeConfigurationError("Modus muss auto, cpu oder gpu sein")
    if isinstance(cpu_threads, bool) or not isinstance(cpu_threads, int) or not 1 <= cpu_threads <= 256:
        raise RuntimeConfigurationError("cpu_threads ausserhalb 1..256")
    if isinstance(gpu_layers, bool) or not isinstance(gpu_layers, int) or not 0 <= gpu_layers <= 999:
        raise RuntimeConfigurationError("gpu_layers ausserhalb 0..999")
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise RuntimeConfigurationError("Port ausserhalb 1024..65535")
    if mode == "cpu" and (gpu_layers or devices or tensor_split):
        raise RuntimeConfigurationError("CPU-Modus erlaubt keine GPU-Parameter")
    if mode == "gpu" and gpu_layers == 0:
        raise RuntimeConfigurationError("GPU-Modus benoetigt gpu_layers > 0")
    if devices is not None and (not isinstance(devices, list) or not devices or len(devices)>8 or any(not isinstance(d,str) or not d or len(d)>80 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-.' for c in d) for d in devices) or len(set(devices))!=len(devices)):
        raise RuntimeConfigurationError("Ungueltige GPU-Geraete")
    if tensor_split is not None and (not isinstance(tensor_split,list) or not 1 <= len(tensor_split) <= 8 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not 0 < v <= 100 for v in tensor_split) or (devices and len(tensor_split)!=len(devices))):
        raise RuntimeConfigurationError("Ungueltige tensor_split-Werte")
    if tensor_split and not devices:
        raise RuntimeConfigurationError("tensor_split erfordert explizite GPU-Geraete")
    args = [str(Path(binary_path)), "--model", str(Path(model_path)), "--host", "127.0.0.1", "--port", str(port), "--threads", str(cpu_threads), "--n-gpu-layers", str(gpu_layers)]
    if devices:
        args += ["--device", ",".join(devices)]
    if tensor_split:
        args += ["--split-mode", "layer", "--tensor-split", ",".join(str(x) for x in tensor_split)]
    return {"approved": False, "launches_process": False, "downloads": False, "command": args, "mode": mode, "gpu_count": len(devices or []), "requires_manual_confirmation": True}
