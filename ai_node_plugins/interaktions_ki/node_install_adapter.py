"""Approved local-only installation of llama.cpp runtime and GGUF model.

Both archives must be explicitly supplied and independently checksum-pinned.
No downloads, catalog assumptions, or implicit consent.
"""
from __future__ import annotations
import hashlib
import importlib.util
import os
from pathlib import Path
import re

class InteraktionsKIInstallError(RuntimeError):
    pass

_PREFIX = "MEDIAHUB_INTERAKTIONS_KI_"
_FIELDS = ("ARCHIVE", "SHA256", "TARGET", "MODEL_ARCHIVE", "MODEL_SHA256", "MODEL_TARGET")

def _validate_input(name: str, value: str) -> None:
    if name.endswith("SHA256") and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise InteraktionsKIInstallError(f"Ungueltige Pruefsumme: {name}")
    if name.endswith("TARGET"):
        target = Path(value)
        if not target.is_absolute() or target == Path(target.anchor):
            raise InteraktionsKIInstallError(f"Installationsziel ungueltig: {name}")
    if name.endswith("ARCHIVE"):
        archive = Path(value)
        if not archive.is_file() or archive.suffix.lower() != ".zip":
            raise InteraktionsKIInstallError(f"Lokales ZIP fehlt: {name}")

def _digest(path: str) -> str:
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def _resolve_local_catalog() -> dict[str, str]:
    """Resolve pinned local packages; never download or install here."""
    import json
    import shutil
    tools_root = os.environ.get("MEDIAHUB_TOOLS_ROOT", "").strip()
    if not tools_root:
        raise InteraktionsKIInstallError(
            "MEDIAHUB_TOOLS_ROOT fehlt (Pfad zum MediaHub-Tools-Repository)"
        )
    root = Path(tools_root).resolve()
    manifest_path = root / "packages" / "interaktions-ki" / "current" / "manifest.json"
    if not manifest_path.is_file():
        raise InteraktionsKIInstallError("MediaHub-Tools-Manifest fehlt: " + str(manifest_path))
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if data.get("tool") != "interaktions-ki" or data.get("installation") != "local-only-explicit-approval":
        raise InteraktionsKIInstallError("Unbekanntes oder nicht freigegebenes Tool-Manifest")
    profile = os.environ.get(_PREFIX + "PROFILE", "auto").strip().lower()
    if profile not in {"auto", "cpu", "cuda"}:
        raise InteraktionsKIInstallError("Ungueltiges Installationsprofil")
    if profile == "auto":
        profile = "cpu"
        # CUDA only when NVIDIA tooling actually reports a usable device.
        if shutil.which("nvidia-smi"):
            import subprocess
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=8, check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    profile = "cuda"
            except (OSError, subprocess.TimeoutExpired):
                pass
    runtime = data.get("runtime") or {}
    packages = runtime.get("packages") or {}
    chosen = packages.get(profile)
    model = data.get("model")
    if not isinstance(chosen, dict) or not isinstance(model, dict):
        raise InteraktionsKIInstallError("Runtime- oder Modellpaket fehlt im Manifest")
    archive_root = root / "tools" / "interaktions-ki"
    def archive(item: dict) -> str:
        filename = item.get("package")
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.zip", filename):
            raise InteraktionsKIInstallError("Ungueltiger Paketname im Manifest")
        return str(archive_root / filename)
    target_root = Path(os.environ.get("MEDIAHUB_COMPUTE_RUNTIME") or
                       (Path.home() / ".mediahub" / "compute_node"))
    return {
        "ARCHIVE": archive(chosen), "SHA256": str(chosen.get("sha256") or ""),
        "MODEL_ARCHIVE": archive(model), "MODEL_SHA256": str(model.get("sha256") or ""),
        "TARGET": str(target_root / "plugin_runtimes" / "interaktions_ki" / ("llama_" + profile)),
        "MODEL_TARGET": str(target_root / "plugin_runtimes" / "interaktions_ki" / "models" / "qwen3_1_7b_q8_0"),
    }

def prepare_runtime(manifest: dict, package_root: Path, *, approved: bool,
                    pinned_tools: dict | None = None) -> dict:
    if manifest.get("id") != "mediahub.interaktions_ki" or approved is not True:
        raise InteraktionsKIInstallError("Plugin-ID oder Installationsfreigabe ungueltig")
    if not isinstance(pinned_tools, dict) or pinned_tools.get("profile_selected") not in {"cpu", "cuda"}:
        raise InteraktionsKIInstallError("Bestaetigter Tool-Snapshot fehlt; direkte Installation gesperrt.")
    items = pinned_tools.get("packages") or {}
    if not isinstance(items, dict) or not all(isinstance(items.get(k), dict) for k in ("runtime", "model")):
        raise InteraktionsKIInstallError("Bestaetigter Runtime-/Modell-Snapshot unvollstaendig.")
    target_root = Path(os.environ.get("MEDIAHUB_COMPUTE_RUNTIME") or
                       (Path.home() / ".mediahub" / "compute_node"))
    profile = pinned_tools["profile_selected"]
    config = {
        "ARCHIVE": str(items["runtime"].get("path") or ""),
        "SHA256": str(items["runtime"].get("sha256") or ""),
        "MODEL_ARCHIVE": str(items["model"].get("path") or ""),
        "MODEL_SHA256": str(items["model"].get("sha256") or ""),
        "TARGET": str(target_root / "plugin_runtimes" / "interaktions_ki" / ("llama_" + profile)),
        "MODEL_TARGET": str(target_root / "plugin_runtimes" / "interaktions_ki" / "models" / "qwen3_1_7b_q8_0"),
    }
    missing = [field for field, value in config.items() if not value]
    if missing:
        raise InteraktionsKIInstallError("Runtime UND Modell muessen konfiguriert sein: " + ", ".join(missing))
    for field, value in config.items():
        _validate_input(field, value)
    if Path(config["TARGET"]).resolve() == Path(config["MODEL_TARGET"]).resolve():
        raise InteraktionsKIInstallError("Runtime- und Modellziel duerfen nicht identisch sein")
    if Path(config["TARGET"]).resolve().is_relative_to(Path(config["MODEL_TARGET"]).resolve()) or Path(config["MODEL_TARGET"]).resolve().is_relative_to(Path(config["TARGET"]).resolve()):
        raise InteraktionsKIInstallError("Installationsziele duerfen nicht ineinander liegen")
    # Check BOTH independently pinned archives before any filesystem mutation.
    for archive_field, sha_field in (("ARCHIVE", "SHA256"), ("MODEL_ARCHIVE", "MODEL_SHA256")):
        if _digest(config[archive_field]).lower() != config[sha_field].lower():
            raise InteraktionsKIInstallError("SHA-256-Pruefung fehlgeschlagen: " + archive_field)
    manager_file = Path(package_root) / "safe_install.py"
    if not manager_file.is_file():
        raise InteraktionsKIInstallError("Installationsmodul fehlt")
    spec = importlib.util.spec_from_file_location("mediahub_interaktions_ki_safe_install", manager_file)
    if spec is None or spec.loader is None:
        raise InteraktionsKIInstallError("Installationsmodul nicht ladbar")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Validate both archive structures BEFORE modifying either target.
    module.preflight_local_archive(
        archive_path=config["ARCHIVE"], expected_sha256=config["SHA256"], model=False)
    module.preflight_local_archive(
        archive_path=config["MODEL_ARCHIVE"], expected_sha256=config["MODEL_SHA256"], model=True)
    # Compare installed files with the independently SHA-pinned ZIPs before
    # reusing either target. A pre-existing directory is never trusted by name.
    runtime_existing = module.inspect_installed_archive(
        archive_path=config["ARCHIVE"], expected_sha256=config["SHA256"],
        target_dir=config["TARGET"], model=False)
    model_existing = module.inspect_installed_archive(
        archive_path=config["MODEL_ARCHIVE"], expected_sha256=config["MODEL_SHA256"],
        target_dir=config["MODEL_TARGET"], model=True)
    for label, state in (("Runtime", runtime_existing), ("Modell", model_existing)):
        if state["exists"] and not state["ready"]:
            raise InteraktionsKIInstallError(
                label + "-Ziel ist vorhanden, aber nicht identisch mit dem "
                "bestaetigten Paket; keine Ueberschreibung: " + state["root"]
                + " (" + state["error"] + ")")
    # Check both existing targets BEFORE installing anything. Existing verified
    # files remain untouched, even on partial/repeated installations.
    for field in ("TARGET", "MODEL_TARGET"):
        Path(config[field]).parent.mkdir(parents=True, exist_ok=True)
    if model_existing["ready"]:
        model_status = model_existing
    else:
        model_status = module.install_local_model_archive(
            archive_path=config["MODEL_ARCHIVE"], expected_sha256=config["MODEL_SHA256"],
            target_dir=config["MODEL_TARGET"], confirmed=True)
    if runtime_existing["ready"]:
        runtime_status = runtime_existing
    else:
        try:
            runtime_status = module.install_local_archive(
                archive_path=config["ARCHIVE"], expected_sha256=config["SHA256"],
                target_dir=config["TARGET"], confirmed=True)
        except Exception as exc:
            raise InteraktionsKIInstallError(
                "Runtime-Installation fehlgeschlagen; Modell vorhanden unter "
                + str(model_status["root"]) + "; keine automatische Loeschung. Ursache: "
                + str(exc)) from exc
    return {**runtime_status, "model_status": model_status,
            "model": model_status["model"], "model_load_verified": False,
            "requires_runtime_health_check": True}
