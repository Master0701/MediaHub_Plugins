"""Safe, non-executing llama.cpp installation plan for Windows Compute Node.

No downloads, file writes, installation or process launch. Caller must verify
SHA-256 of an explicitly selected release artifact before installation.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import urlsplit

class InstallPlanError(ValueError):
    pass

def plan_install(*, archive_path: str, sha256: str, target_dir: str, backend: str = "cpu", confirmed: bool = False) -> dict:
    if backend not in {"cpu", "cuda"}:
        raise InstallPlanError("Backend muss cpu oder cuda sein")
    archive = Path(archive_path)
    if archive.suffix.lower() != ".zip" or not archive.is_file():
        raise InstallPlanError("Lokales llama.cpp ZIP fehlt")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", sha256):
        raise InstallPlanError("Gueltige SHA-256-Pruefsumme erforderlich")
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest.lower() != sha256.lower():
        raise InstallPlanError("SHA-256-Pruefsumme stimmt nicht")
    target = Path(target_dir)
    if not target.is_absolute() or not target.name or str(target) == target.anchor:
        raise InstallPlanError("Absolutes Zielverzeichnis erforderlich")
    return {"backend": backend, "archive": str(archive.resolve()), "sha256": digest, "target": str(target), "confirmed": bool(confirmed), "installation_performed": False, "requires_existing_node_installer_integration": True, "actions": ["ZIP-Inhalt und enthaltene Pfade vor Entpacken pruefen", "Lizenzen und CUDA-Abhaengigkeiten pruefen", "Ueber vorhandenen bestaetigten Installer installieren", "llama-server.exe und Backend nach Installation testen"]}

def plan_model(*, model_path: str, sha256: str | None = None) -> dict:
    path = Path(model_path)
    if not path.is_file() or path.suffix.lower() != ".gguf":
        raise InstallPlanError("Lokales GGUF-Modell fehlt")
    digest = None
    if sha256 is not None:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", sha256):
            raise InstallPlanError("Ungueltige Modell-Pruefsumme")
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        if digest.lower() != sha256.lower():
            raise InstallPlanError("GGUF-Pruefsumme stimmt nicht")
    return {"model": str(path.resolve()), "sha256_verified": digest is not None, "model_downloaded": False}
