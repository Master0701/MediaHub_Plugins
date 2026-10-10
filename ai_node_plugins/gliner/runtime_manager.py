"""Managed isolated runtime for the GLiNER plugin."""

from __future__ import annotations

import hashlib
import platform
import tempfile
import urllib.request
import zipfile
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

RUNTIME_NAME = "gliner"

REQUIRED_PACKAGES = {
    "gliner": "gliner",
}


def _load_python_runtime_provider():
    """Load the shared MediaHub Compute Python runtime provider."""
    try:
        from windows_compute_node.runtime_support import (
            python_runtime,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Gemeinsamer MediaHub Python-Runtime-Provider "
            "konnte nicht geladen werden."
        ) from exc

    return python_runtime

def runtime_base_python():
    """Find a compatible Python interpreter for GLiNER."""
    if os.name == "nt":
        provider = _load_python_runtime_provider()
        return Path(provider.require_python())

    import sys
    import struct

    candidates = [
        sys.executable,
        shutil.which("python3"),
        shutil.which("python"),
    ]

    for candidate in candidates:
        if not candidate:
            continue

        path = Path(candidate).resolve()

        try:
            result = subprocess.run(
                [
                    str(path),
                    "-c",
                    (
                        "import sys, struct;"
                        "print(sys.version_info.major,"
                        "sys.version_info.minor,"
                        "struct.calcsize('P') * 8)"
                    ),
                ],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )

            major, minor, bits = map(
                int, result.stdout.split()
            )

            if (
                major == 3
                and minor in (11, 12, 13)
                and bits == 64
            ):
                return path

        except (
            OSError,
            subprocess.SubprocessError,
            ValueError,
        ):
            continue

    raise RuntimeError(
        "Keine kompatible Python-Runtime fuer GLiNER "
        "gefunden (Python 3.11 bis 3.13, 64 Bit)."
    )


def default_runtime_root():
    override = os.environ.get(
        "MEDIAHUB_COMPUTE_RUNTIME"
    )

    if override:
        return (
            Path(override)
            / "plugin_runtimes"
            / RUNTIME_NAME
        )

    return (
        Path.home()
        / ".mediahub"
        / "compute_node"
        / "plugin_runtimes"
        / RUNTIME_NAME
    )


def runtime_paths(
    root: Path | None = None,
) -> dict[str, Path]:
    root = Path(
        root or default_runtime_root()
    )

    return {
        "root": root,
        "packages": root / "packages",
        "state": root / "state.json",
        "models": root / "models",
        "cache": root / "cache",
    }


def runtime_transaction_paths(
    root: Path | None = None,
) -> dict[str, Path]:
    """Return paths used for transactional runtime replacement."""

    paths = runtime_paths(root)

    packages = paths["packages"]

    return {
        "active": packages,
        "staging": packages.with_name(
            f"{packages.name}_staging"
        ),
        "backup": packages.with_name(
            f"{packages.name}_backup"
        ),
    }


def clear_runtime_directory(
    path: Path,
) -> None:
    """Remove a temporary runtime directory when it exists."""

    if path.exists():
        shutil.rmtree(path)


def _python_has_module(
    python_path: Path,
    module: str,
    *,
    packages: Path | None = None,
) -> bool:
    if not python_path.is_file():
        return False

    code = [
        "import importlib.util",
        "import sys",
    ]

    if packages is not None:
        code.append(
            f"sys.path.insert(0, {str(packages)!r})"
        )

    code.extend(
        [
            (
                "spec = importlib.util.find_spec("
                f"{module!r})"
            ),
            "sys.exit(0 if spec is not None else 1)",
        ]
    )

    result = subprocess.run(
        [
            str(python_path),
            "-c",
            ";".join(code),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0



def inspect_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    paths = runtime_paths(root)

    try:
        python_path = runtime_base_python()
        runtime_error = None
    except Exception as exc:  # noqa: BLE001
        python_path = Path()
        runtime_error = str(exc)

    packages = {}

    for package, module in REQUIRED_PACKAGES.items():
        packages[package] = _python_has_module(
            python_path,
            module,
            packages=paths["packages"],
        )

    return {
        "runtime": RUNTIME_NAME,
        "mode": "isolated_target",
        "root": str(paths["root"]),
        "python": str(python_path),
        "python_exists": python_path.is_file(),
        "packages_path": str(paths["packages"]),
        "models": str(paths["models"]),
        "cache": str(paths["cache"]),
        "packages": packages,
        "ready": (
            python_path.is_file()
            and all(packages.values())
        ),
        "error": runtime_error,
    }



def create_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    paths = runtime_paths(root)

    for key in (
        "root",
        "packages",
        "models",
        "cache",
    ):
        paths[key].mkdir(
            parents=True,
            exist_ok=True,
        )

    python_path = runtime_base_python()

    if not python_path.is_file():
        raise RuntimeError(
            "Kein kompatibles Runtime-Python vorhanden."
        )

    state = {
        "runtime": RUNTIME_NAME,
        "mode": "isolated_target",
        "python": str(python_path),
        "packages": str(paths["packages"]),
    }

    paths["state"].write_text(
        json.dumps(
            state,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return inspect_runtime(root)



MEDIAHUB_TOOLS_REPOSITORY = "Master0701/MediaHub_Tools"
MEDIAHUB_TOOLS_RELEASE = "mediahub-tools"
GLINER_MANIFEST_ASSET = "gliner-manifest.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _download_release_asset(
    asset_name: str,
    destination: Path,
) -> Path:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    url = (
        "https://github.com/"
        f"{MEDIAHUB_TOOLS_REPOSITORY}/releases/download/"
        f"{MEDIAHUB_TOOLS_RELEASE}/{asset_name}"
    )

    urllib.request.urlretrieve(
        url,
        destination,
    )

    if not destination.is_file():
        raise RuntimeError(
            f"Release-Asset wurde nicht geladen: {asset_name}"
        )

    return destination


def _load_tools_gliner_manifest(
    download_root: Path,
) -> dict[str, Any]:
    manifest_path = (
        download_root / GLINER_MANIFEST_ASSET
    )

    _download_release_asset(
        GLINER_MANIFEST_ASSET,
        manifest_path,
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8-sig"
        )
    )

    if manifest.get("tool") != "gliner-runtime":
        raise RuntimeError(
            "Ungueltiges GLiNER-Runtime-Manifest."
        )

    return manifest


def _verify_runtime_asset(
    path: Path,
    expected_sha256: str,
) -> None:
    actual = _sha256_file(path)

    if actual.lower() != expected_sha256.lower():
        raise RuntimeError(
            "SHA256-Pruefung fehlgeschlagen fuer "
            f"{path.name}. Erwartet: {expected_sha256}; "
            f"erhalten: {actual}"
        )


def _download_windows_runtime(
    *,
    profile: str,
    staging: Path,
) -> dict[str, Any]:
    selected = normalize_install_profile(profile)

    if selected not in {"cpu", "cuda"}:
        raise ValueError(
            "Windows-Runtime benoetigt CPU oder CUDA."
        )

    with tempfile.TemporaryDirectory(
        prefix="mediahub-gliner-"
    ) as temporary:
        download_root = Path(temporary)

        manifest = _load_tools_gliner_manifest(
            download_root
        )

        packages = manifest.get("packages", {})
        package = packages.get(selected)

        if not isinstance(package, dict):
            raise RuntimeError(
                "GLiNER-Manifest enthaelt kein Paket "
                f"fuer Profil {selected}."
            )

        archive_path = (
            download_root
            / "GLiNER-Runtime-Windows-x64.zip"
        )

        if selected == "cpu":
            asset_name = str(
                package["package"]
            )

            downloaded = _download_release_asset(
                asset_name,
                download_root / asset_name,
            )

            _verify_runtime_asset(
                downloaded,
                str(package["sha256"]),
            )

            archive_path = downloaded

        else:
            if not package.get("multipart"):
                raise RuntimeError(
                    "CUDA-Runtime ist nicht als "
                    "Multipart-Paket deklariert."
                )

            parts = package.get("parts")

            if not isinstance(parts, list) or not parts:
                raise RuntimeError(
                    "CUDA-Runtime enthaelt keine Teile."
                )

            with archive_path.open("wb") as output:
                for part in parts:
                    part_name = str(part["file"])

                    part_path = _download_release_asset(
                        part_name,
                        download_root / part_name,
                    )

                    expected_size = int(
                        part["size"]
                    )

                    actual_size = (
                        part_path.stat().st_size
                    )

                    if actual_size != expected_size:
                        raise RuntimeError(
                            "CUDA-Part hat falsche Groesse: "
                            f"{part_name}; erwartet "
                            f"{expected_size}, erhalten "
                            f"{actual_size}"
                        )

                    _verify_runtime_asset(
                        part_path,
                        str(part["sha256"]),
                    )

                    with part_path.open("rb") as source:
                        shutil.copyfileobj(
                            source,
                            output,
                            length=1024 * 1024,
                        )

            expected_size = int(
                package["size"]
            )

            actual_size = (
                archive_path.stat().st_size
            )

            if actual_size != expected_size:
                raise RuntimeError(
                    "Rekonstruierte CUDA-Runtime hat "
                    "eine falsche Groesse."
                )

            _verify_runtime_asset(
                archive_path,
                str(package["sha256"]),
            )

        with zipfile.ZipFile(
            archive_path,
            "r",
        ) as archive:
            archive.extractall(staging)

        return {
            "source": "mediahub-tools",
            "release": MEDIAHUB_TOOLS_RELEASE,
            "repository": MEDIAHUB_TOOLS_REPOSITORY,
            "runtime_version": manifest.get(
                "version"
            ),
            "profile": selected,
            "multipart": bool(
                package.get("multipart", False)
            ),
            "package": package.get("package"),
        }


def _use_linux_arm64_runtime() -> bool:
    """Use the published CPU runtime on Linux ARM64 nodes."""
    return (
        os.name == "posix"
        and platform.system().lower() == "linux"
        and platform.machine().lower() in {"aarch64", "arm64"}
    )


def _download_linux_arm64_runtime(
    *,
    profile: str,
    staging: Path,
) -> dict[str, Any]:
    """Download and validate the MediaHub Tools ARM64 CPU runtime."""
    selected = normalize_install_profile(profile)
    if selected != "cpu":
        raise ValueError(
            "GLiNER Linux ARM64 bietet nur das CPU-Runtime-Paket."
        )

    with tempfile.TemporaryDirectory(
        prefix="mediahub-gliner-arm64-"
    ) as temporary:
        download_root = Path(temporary)
        manifest = _load_tools_gliner_manifest(download_root)
        packages = manifest.get("packages")
        package = (
            packages.get("pi")
            if isinstance(packages, dict)
            else None
        )
        if not isinstance(package, dict):
            raise RuntimeError(
                "GLiNER-Manifest enthaelt kein Linux-ARM64-Paket "
                "(packages.pi)."
            )

        if (
            str(package.get("platform", "")).lower() != "linux"
            or str(package.get("architecture", "")).lower()
            not in {"arm64", "aarch64"}
            or str(package.get("acceleration", "")).lower() != "cpu"
            or package.get("multipart", False)
        ):
            raise RuntimeError(
                "GLiNER-Pi-Runtime hat ungueltige Plattform- "
                "oder Beschleunigungsangaben."
            )

        asset_name = package.get("package")
        expected_hash = package.get("sha256")
        if (
            not isinstance(asset_name, str)
            or not asset_name
            or Path(asset_name).name != asset_name
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in expected_hash)
        ):
            raise RuntimeError(
                "GLiNER-Pi-Manifest enthaelt ungueltige Asset-Daten."
            )

        archive_path = _download_release_asset(
            asset_name,
            download_root / asset_name,
        )
        expected_size = int(package["size"])
        if expected_size <= 0 or archive_path.stat().st_size != expected_size:
            raise RuntimeError(
                "GLiNER-Pi-Runtime hat eine falsche Dateigroesse."
            )
        _verify_runtime_asset(archive_path, expected_hash)

        with zipfile.ZipFile(archive_path, "r") as archive:
            # Never let a release archive write outside the staging root.
            destination = staging.resolve()
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if not target.is_relative_to(destination):
                    raise RuntimeError(
                        "Unsicherer Pfad im GLiNER-Pi-Runtime-ZIP."
                    )
                # ZIP Unix symlinks must not be extracted as regular files.
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise RuntimeError(
                        "Symbolischer Link im GLiNER-Pi-Runtime-ZIP."
                    )
            archive.extractall(staging)

        return {
            "source": "mediahub-tools",
            "release": MEDIAHUB_TOOLS_RELEASE,
            "repository": MEDIAHUB_TOOLS_REPOSITORY,
            "runtime_version": manifest.get("version"),
            "profile": selected,
            "platform": "linux",
            "architecture": "arm64",
            "multipart": False,
            "package": asset_name,
        }


def _use_mediahub_tools_runtime() -> bool:
    return (
        os.name == "nt"
        and platform.machine().lower()
        in {
            "amd64",
            "x86_64",
        }
    )

def install_dependencies(
    root: Path | None = None,
    *,
    profile: str = "auto",
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Install GLiNER with the selected CPU/CUDA runtime."""

    create_runtime(root)

    transaction = runtime_transaction_paths(root)
    python_path = runtime_base_python()

    selection = select_install_profile(
        requested=profile,
        capabilities=capabilities,
    )

    selected_profile = str(
        selection["selected"]
    )

    staging = transaction["staging"]

    clear_runtime_directory(
        staging
    )

    staging.mkdir(
        parents=True,
        exist_ok=True,
    )

    runtime_source: dict[str, Any]

    if _use_mediahub_tools_runtime():
        runtime_source = _download_windows_runtime(
            profile=selected_profile,
            staging=staging,
        )
    elif _use_linux_arm64_runtime():
        runtime_source = _download_linux_arm64_runtime(
            profile=selected_profile,
            staging=staging,
        )
    else:
        commands = dependency_install_commands(
            profile=selected_profile,
            python_path=python_path,
            packages_path=staging,
        )

        for command in commands:
            subprocess.run(
                command,
                check=True,
            )

        runtime_source = {
            "source": "pip",
            "profile": selected_profile,
        }
    staging_status = inspect_package_runtime(
        staging
    )

    if not staging_status["ready"]:
        raise RuntimeError(
            "GLiNER wurde im Staging installiert, "
            "die Staging-Runtime ist aber nicht "
            "bereit. "
            f"Status: {staging_status}"
        )

    if (
        selected_profile == "cuda"
        and not staging_status.get(
            "cuda_available",
            False,
        )
    ):
        raise RuntimeError(
            "GLiNER wurde mit CUDA-Profil im "
            "Staging installiert, aber CUDA ist "
            "dort nicht verfuegbar."
        )

    if (
        selected_profile == "cpu"
        and staging_status.get(
            "cuda_built",
            False,
        )
    ):
        raise RuntimeError(
            "GLiNER wurde mit CPU-Profil "
            "installiert, das Staging enthaelt "
            "aber einen CUDA-Torch-Build."
        )

    activation = activate_staged_runtime(
        root
    )

    status = inspect_runtime(root)

    if not status["ready"]:
        raise RuntimeError(
            "GLiNER wurde aktiviert, "
            "die aktive Runtime ist aber "
            "nicht bereit."
        )

    acceleration = inspect_acceleration(root)

    if (
        selected_profile == "cuda"
        and not acceleration.get(
            "cuda_available",
            False,
        )
    ):
        raise RuntimeError(
            "Die aktivierte GLiNER-Runtime "
            "verwendet trotz CUDA-Profil "
            "kein verfuegbares CUDA."
        )

    if (
        selected_profile == "cpu"
        and acceleration.get(
            "cuda_built",
            False,
        )
    ):
        raise RuntimeError(
            "Die aktivierte GLiNER-Runtime "
            "enthaelt trotz CPU-Profil "
            "einen CUDA-Torch-Build."
        )

    return {
        **status,
        "install_profile": selection,
        "runtime_source": runtime_source,
        "acceleration": acceleration,
        "staging_validated": True,
        "activation": activation,
    }


def activate_staged_runtime(
    root: Path | None = None,
) -> dict[str, Any]:
    """Atomically activate a validated staged GLiNER runtime."""

    transaction = runtime_transaction_paths(root)

    active = transaction["active"]
    staging = transaction["staging"]
    backup = transaction["backup"]

    staging_status = inspect_package_runtime(
        staging
    )

    if not staging_status["ready"]:
        raise RuntimeError(
            "GLiNER-Staging kann nicht aktiviert "
            "werden, weil es nicht bereit ist. "
            f"Status: {staging_status}"
        )

    clear_runtime_directory(
        backup
    )

    active_was_present = active.is_dir()

    try:
        if active_was_present:
            active.replace(
                backup
            )

        staging.replace(
            active
        )

        activated_status = inspect_package_runtime(
            active
        )

        if not activated_status["ready"]:
            raise RuntimeError(
                "Die aktivierte GLiNER-Runtime "
                "ist nach dem Umschalten nicht bereit. "
                f"Status: {activated_status}"
            )

    except Exception:
        if active.is_dir():
            clear_runtime_directory(
                active
            )

        if backup.is_dir():
            backup.replace(
                active
            )

        raise

    return {
        **activated_status,
        "activated": True,
        "rollback_required": active_was_present,
        "backup_path": str(backup),
    }


def finalize_runtime_activation(
    root: Path | None = None,
) -> dict[str, Any]:
    """Commit an activated GLiNER runtime and remove its backup."""

    transaction = runtime_transaction_paths(root)

    active = transaction["active"]
    backup = transaction["backup"]

    status = inspect_package_runtime(
        active
    )

    if not status["ready"]:
        raise RuntimeError(
            "Die aktive GLiNER-Runtime kann nicht "
            "finalisiert werden, weil sie nicht "
            "bereit ist. "
            f"Status: {status}"
        )

    backup_was_present = backup.is_dir()

    clear_runtime_directory(
        backup
    )

    return {
        **status,
        "finalized": True,
        "backup_removed": backup_was_present,
    }


def rollback_runtime_activation(
    root: Path | None = None,
) -> dict[str, Any]:
    """Restore the previous GLiNER runtime from backup."""

    transaction = runtime_transaction_paths(root)

    active = transaction["active"]
    backup = transaction["backup"]

    if not backup.is_dir():
        raise RuntimeError(
            "GLiNER-Rollback ist nicht moeglich, "
            "weil kein Runtime-Backup vorhanden ist."
        )

    clear_runtime_directory(
        active
    )

    backup.replace(
        active
    )

    status = inspect_package_runtime(
        active
    )

    if not status["ready"]:
        raise RuntimeError(
            "Das GLiNER-Backup wurde "
            "zurueckgespielt, ist aber nicht bereit. "
            f"Status: {status}"
        )

    return {
        **status,
        "rolled_back": True,
        "backup_restored": True,
    }


def inspect_package_runtime(
    packages_path: Path,
) -> dict[str, Any]:
    """Inspect GLiNER and Torch in a specific package directory."""

    python_path = runtime_base_python()

    result = {
        "packages_path": str(packages_path),
        "packages_exist": packages_path.is_dir(),
        "gliner_available": False,
        "torch_available": False,
        "torch_version": None,
        "cuda_built": False,
        "cuda_version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "devices": [],
        "ready": False,
        "error": None,
    }

    if not python_path.is_file():
        result["error"] = (
            "Private Python Runtime wurde nicht gefunden."
        )
        return result

    if not packages_path.is_dir():
        result["error"] = (
            "Paketverzeichnis wurde nicht gefunden."
        )
        return result

    code = r"""
import json
import sys

packages_path = sys.argv[1]

sys.path.insert(
    0,
    packages_path,
)

result = {
    "gliner_available": False,
    "torch_available": False,
    "torch_version": None,
    "cuda_built": False,
    "cuda_version": None,
    "cuda_available": False,
    "cuda_device_count": 0,
    "devices": [],
    "error": None,
}

try:
    import gliner

    result["gliner_available"] = True

    import torch

    result["torch_available"] = True
    result["torch_version"] = str(
        torch.__version__
    )

    cuda_version = getattr(
        torch.version,
        "cuda",
        None,
    )

    result["cuda_version"] = (
        str(cuda_version)
        if cuda_version is not None
        else None
    )

    result["cuda_built"] = (
        cuda_version is not None
    )

    result["cuda_available"] = bool(
        torch.cuda.is_available()
    )

    result["cuda_device_count"] = int(
        torch.cuda.device_count()
    )

    if result["cuda_available"]:
        for index in range(
            result["cuda_device_count"]
        ):
            result["devices"].append(
                {
                    "index": index,
                    "name": (
                        torch.cuda.get_device_name(
                            index
                        )
                    ),
                    "capability": list(
                        torch.cuda.get_device_capability(
                            index
                        )
                    ),
                }
            )

except Exception as exc:
    result["error"] = (
        type(exc).__name__
        + ": "
        + str(exc)
    )

print(
    json.dumps(
        result,
        ensure_ascii=False,
    )
)
"""

    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            code,
            str(packages_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    if completed.returncode != 0:
        result["error"] = (
            completed.stderr.strip()
            or (
                "Runtime-Pruefung ist mit "
                f"Code {completed.returncode} "
                "fehlgeschlagen."
            )
        )
        return result

    try:
        inspected = json.loads(
            completed.stdout.strip()
        )
    except Exception as exc:  # noqa: BLE001
        result["error"] = (
            "Runtime-Pruefung lieferte "
            "ungueltiges JSON: "
            + str(exc)
        )
        return result

    result.update(
        inspected
    )

    result["ready"] = bool(
        result["gliner_available"]
        and result["torch_available"]
        and not result["error"]
    )

    return result


def inspect_acceleration(
    root: Path | None = None,
) -> dict[str, Any]:
    """Inspect acceleration available inside the GLiNER runtime."""

    status = inspect_runtime(root)

    python_path = Path(
        status["python"]
    )

    packages_path = Path(
        status["packages_path"]
    )

    result = {
        "torch_available": False,
        "torch_version": None,
        "cuda_built": False,
        "cuda_version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "devices": [],
        "error": None,
    }

    if not python_path.is_file():
        result["error"] = (
            "Runtime-Python ist nicht vorhanden."
        )
        return result

    if not packages_path.is_dir():
        result["error"] = (
            "GLiNER-Paketverzeichnis ist nicht vorhanden."
        )
        return result

    code = r"""
import json
import sys

packages_path = sys.argv[1]
sys.path.insert(0, packages_path)

result = {
    "torch_available": False,
    "torch_version": None,
    "cuda_built": False,
    "cuda_version": None,
    "cuda_available": False,
    "cuda_device_count": 0,
    "devices": [],
    "error": None,
}

try:
    import torch

    result["torch_available"] = True
    result["torch_version"] = str(
        torch.__version__
    )

    cuda_version = getattr(
        torch.version,
        "cuda",
        None,
    )

    result["cuda_version"] = (
        str(cuda_version)
        if cuda_version is not None
        else None
    )

    result["cuda_built"] = (
        cuda_version is not None
    )

    result["cuda_available"] = bool(
        torch.cuda.is_available()
    )

    result["cuda_device_count"] = int(
        torch.cuda.device_count()
    )

    if result["cuda_available"]:
        for index in range(
            result["cuda_device_count"]
        ):
            result["devices"].append(
                {
                    "index": index,
                    "name": (
                        torch.cuda.get_device_name(
                            index
                        )
                    ),
                    "capability": list(
                        torch.cuda.get_device_capability(
                            index
                        )
                    ),
                }
            )

except Exception as exc:
    result["error"] = (
        type(exc).__name__
        + ": "
        + str(exc)
    )

print(
    json.dumps(
        result,
        ensure_ascii=False,
    )
)
"""

    completed = subprocess.run(
        [
            str(python_path),
            "-c",
            code,
            str(packages_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    stdout = (
        completed.stdout or ""
    ).strip()

    if completed.returncode != 0:
        result["error"] = (
            "Torch/CUDA-Pruefung fehlgeschlagen: "
            + (completed.stderr or "").strip()
        )
        return result

    try:
        detected = json.loads(stdout)
    except json.JSONDecodeError:
        result["error"] = (
            "Torch/CUDA-Pruefung lieferte "
            "keine gueltige JSON-Antwort."
        )
        return result

    if isinstance(detected, dict):
        result.update(detected)

    return result


def normalize_install_profile(
    profile: str | None,
) -> str:
    """Normalize the requested GLiNER runtime profile."""

    value = str(
        profile or "auto"
    ).strip().lower()

    aliases = {
        "gpu": "cuda",
        "nvidia": "cuda",
    }

    value = aliases.get(
        value,
        value,
    )

    if value not in {
        "auto",
        "cpu",
        "cuda",
    }:
        raise ValueError(
            "Unbekanntes GLiNER-Installationsprofil: "
            f"{profile!r}"
        )

    return value



def select_install_profile(
    *,
    requested: str | None = "auto",
    capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Select CPU or CUDA installation for GLiNER."""

    requested_profile = normalize_install_profile(
        requested
    )

    node_cuda_available = False
    cuda_devices = []

    capability_data = dict(
        capabilities or {}
    )

    accelerators = capability_data.get(
        "accelerators"
    )

    if isinstance(accelerators, list):
        for accelerator in accelerators:
            if not isinstance(
                accelerator,
                dict,
            ):
                continue

            families = accelerator.get(
                "backend_family"
            )

            if not isinstance(
                families,
                list,
            ):
                continue

            normalized_families = {
                str(family).strip().lower()
                for family in families
            }

            if "cuda" not in normalized_families:
                continue

            node_cuda_available = True

            cuda_devices.append(
                {
                    "name": accelerator.get(
                        "name"
                    ),
                    "vendor": accelerator.get(
                        "vendor"
                    ),
                    "backend_family": list(
                        families
                    ),
                }
            )

    if requested_profile == "cpu":
        selected_profile = "cpu"
        reason = "cpu_requested"

    elif requested_profile == "cuda":
        if not node_cuda_available:
            raise RuntimeError(
                "CUDA-Profil wurde angefordert, "
                "aber der Node meldet keine "
                "CUDA-faehige GPU."
            )

        selected_profile = "cuda"
        reason = "cuda_requested"

    elif node_cuda_available:
        selected_profile = "cuda"
        reason = "auto_cuda_available"

    else:
        selected_profile = "cpu"
        reason = "auto_cpu_fallback"

    return {
        "requested": requested_profile,
        "selected": selected_profile,
        "reason": reason,
        "node_cuda_available": (
            node_cuda_available
        ),
        "cuda_devices": cuda_devices,
    }



def package_install_plan(
    *,
    profile: str,
) -> dict[str, Any]:
    """Return the package plan without installing anything."""

    selected = normalize_install_profile(
        profile
    )

    if selected == "auto":
        raise ValueError(
            "package_install_plan benoetigt "
            "ein bereits ausgewaehltes Profil."
        )

    if selected == "cpu":
        return {
            "profile": "cpu",
            "packages": [
                "gliner",
            ],
            "torch_variant": "cpu",
            "torch_index_url": (
                "https://download.pytorch.org/whl/cpu"
            ),
            "extra_index_url": None,
        }

    return {
        "profile": "cuda",
        "packages": [
            "gliner",
        ],
        "torch_variant": "cu126",
        "torch_index_url": (
            "https://download.pytorch.org/whl/cu126"
        ),
        "extra_index_url": None,
    }


def dependency_install_commands(
    *,
    profile: str,
    python_path: str | Path,
    packages_path: str | Path,
) -> list[list[str]]:
    """Build one dependency-resolved GLiNER installation command."""

    plan = package_install_plan(profile=profile)

    command = [
        str(Path(python_path)),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--target",
        str(Path(packages_path)),
    ]

    if profile == "cpu":
        torch_package = "torch"

        if (
            os.name == "posix"
            and platform.machine().lower() in {"aarch64", "arm64"}
        ):
            torch_package = "torch==2.14.1+cpu"

        command.extend([
            "--extra-index-url",
            str(plan["torch_index_url"]),
            torch_package,
        ])
    else:
        command.extend([
            "--extra-index-url",
            str(plan["torch_index_url"]),
            "torch",
        ])

    command.extend([
        "gliner==0.2.29",
        "transformers>=4.51.3,<5.17.0",
        "tiktoken",
        "protobuf",
    ])

    return [command]

















