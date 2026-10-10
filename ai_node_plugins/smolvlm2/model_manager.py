"""Central SmolVLM2 model package management.

The model is distributed separately through MediaHub_Tools and is not
bundled inside the .mhaiplugin package.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

MEDIAHUB_TOOLS_REPOSITORY = "Master0701/MediaHub_Tools"
MEDIAHUB_TOOLS_RELEASE = "mediahub-tools"

MODEL_TOOL_ID = "smolvlm2-model"
MODEL_PACKAGE_VERSION = "0.1.0"
MODEL_MANIFEST_ASSET = "smolvlm2-model-manifest.json"

MODEL_DIRECTORY_NAME = "SmolVLM2-500M-Video-Instruct"


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
            "MediaHub-Tools-Asset wurde nicht geladen: "
            f"{asset_name}"
        )

    return destination


def load_model_manifest(
    download_root: Path,
) -> dict[str, Any]:
    manifest_path = (
        download_root / MODEL_MANIFEST_ASSET
    )

    _download_release_asset(
        MODEL_MANIFEST_ASSET,
        manifest_path,
    )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8-sig"
        )
    )

    if manifest.get("tool") != MODEL_TOOL_ID:
        raise RuntimeError(
            "Ungueltiges SmolVLM2-Modellmanifest."
        )

    if str(manifest.get("version")) != MODEL_PACKAGE_VERSION:
        raise RuntimeError(
            "SmolVLM2-Modellversion stimmt nicht: "
            f"erwartet {MODEL_PACKAGE_VERSION}, "
            f"erhalten {manifest.get('version')!r}."
        )

    if manifest.get("multipart"):
        raise RuntimeError(
            "SmolVLM2 v0.1.0 wird als Single-ZIP erwartet."
        )

    package = manifest.get("package")

    if not isinstance(package, str) or not package:
        raise RuntimeError(
            "SmolVLM2-Manifest enthaelt keinen Paketnamen."
        )

    sha256 = manifest.get("sha256")

    if not isinstance(sha256, str) or not sha256:
        raise RuntimeError(
            "SmolVLM2-Manifest enthaelt keinen SHA256."
        )

    size = manifest.get("size")

    if not isinstance(size, int) or size <= 0:
        raise RuntimeError(
            "SmolVLM2-Manifest enthaelt keine gueltige Paketgroesse."
        )

    return manifest


def verify_model_archive(
    archive_path: Path,
    *,
    expected_sha256: str,
    expected_size: int,
) -> None:
    actual_size = archive_path.stat().st_size

    if actual_size != expected_size:
        raise RuntimeError(
            "SmolVLM2-Paketgroesse stimmt nicht. "
            f"Erwartet: {expected_size}; "
            f"erhalten: {actual_size}."
        )

    actual_sha256 = _sha256_file(
        archive_path
    )

    if (
        actual_sha256.lower()
        != expected_sha256.lower()
    ):
        raise RuntimeError(
            "SHA256-Pruefung des SmolVLM2-Modells "
            "ist fehlgeschlagen. "
            f"Erwartet: {expected_sha256}; "
            f"erhalten: {actual_sha256}."
        )


def inspect_model_directory(
    model_path: Path,
) -> dict[str, Any]:
    required_files = (
        "added_tokens.json",
        "chat_template.json",
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "processor_config.json",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
    )

    missing = [
        name
        for name in required_files
        if not (model_path / name).is_file()
    ]

    return {
        "model_path": str(model_path),
        "exists": model_path.is_dir(),
        "required_files": list(required_files),
        "missing_files": missing,
        "ready": (
            model_path.is_dir()
            and not missing
        ),
    }


def install_model(
    models_root: str | Path,
) -> dict[str, Any]:
    """Install the MediaHub_Tools model package atomically."""

    models_root = Path(models_root)

    models_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    active = (
        models_root / MODEL_DIRECTORY_NAME
    )

    staging = (
        models_root
        / f"{MODEL_DIRECTORY_NAME}.staging"
    )

    backup = (
        models_root
        / f"{MODEL_DIRECTORY_NAME}.backup"
    )

    if staging.exists():
        shutil.rmtree(staging)

    staging.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with tempfile.TemporaryDirectory(
            prefix="mediahub-smolvlm2-"
        ) as temporary:
            download_root = Path(temporary)

            manifest = load_model_manifest(
                download_root
            )

            package_name = str(
                manifest["package"]
            )

            archive_path = (
                download_root / package_name
            )

            _download_release_asset(
                package_name,
                archive_path,
            )

            verify_model_archive(
                archive_path,
                expected_sha256=str(
                    manifest["sha256"]
                ),
                expected_size=int(
                    manifest["size"]
                ),
            )

            with zipfile.ZipFile(
                archive_path,
                "r",
            ) as archive:
                seen = set()
                for entry in archive.infolist():
                    normalized = entry.filename.replace("\\", "/")
                    parts = normalized.rstrip("/").split("/")

                    if (
                        normalized.startswith("/")
                        or not parts[0]
                        or any(part in ("", ".", "..") for part in parts)
                        or ":" in parts[0]
                        or parts[0] != MODEL_DIRECTORY_NAME
                        or normalized.rstrip("/") in seen
                    ):
                        raise RuntimeError(
                            f"Unsicherer oder doppelter ZIP-Pfad: {entry.filename!r}"
                        )

                    seen.add(normalized.rstrip("/"))
                    target = staging.joinpath(*parts)

                    if entry.is_dir() or normalized.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                        continue

                    target.parent.mkdir(parents=True, exist_ok=True)

                    with (
                        archive.open(entry) as source,
                        target.open("wb") as destination,
                    ):
                        shutil.copyfileobj(source, destination)

        extracted_package = (
            staging / MODEL_DIRECTORY_NAME
        )

        extracted_model = (
            extracted_package / "model"
        )

        if not extracted_package.is_dir():
            raise RuntimeError(
                "Das SmolVLM2-Paket enthaelt nicht "
                "den erwarteten Hauptordner "
                f"{MODEL_DIRECTORY_NAME!r}."
            )

        status = inspect_model_directory(
            extracted_model
        )

        if not status["ready"]:
            raise RuntimeError(
                "Das entpackte SmolVLM2-Modell "
                "ist unvollstaendig. "
                f"Fehlend: {status['missing_files']}"
            )

        package_staging = (
            models_root
            / f"{MODEL_DIRECTORY_NAME}.package-staging"
        )

        if package_staging.exists():
            shutil.rmtree(package_staging)

        extracted_package.replace(
            package_staging
        )

        shutil.rmtree(staging)

        package_staging.replace(
            staging
        )

        if backup.exists():
            shutil.rmtree(backup)

        active_was_present = (
            active.exists()
        )

        if active_was_present:
            active.replace(
                backup
            )

        try:
            staging.replace(
                active
            )

            active_status = (
                inspect_model_directory(
                    active / "model"
                )
            )

            if not active_status["ready"]:
                raise RuntimeError(
                    "Das aktivierte SmolVLM2-Modell "
                    "ist nicht bereit."
                )

        except Exception:
            if active.exists():
                shutil.rmtree(active)

            if backup.exists():
                backup.replace(
                    active
                )

            raise

        if backup.exists():
            shutil.rmtree(backup)

        return {
            **active_status,
            "installed": True,
            "source": "mediahub-tools",
            "repository": MEDIAHUB_TOOLS_REPOSITORY,
            "release": MEDIAHUB_TOOLS_RELEASE,
            "tool_id": MODEL_TOOL_ID,
            "package_version": MODEL_PACKAGE_VERSION,
            "package": manifest["package"],
            "sha256": manifest["sha256"],
        }

    except Exception:
        if staging.exists():
            shutil.rmtree(staging)

        raise


def resolve_model_path(
    models_root: str | Path,
) -> Path:
    """Return the validated installed model path."""

    package_path = (
        Path(models_root)
        / MODEL_DIRECTORY_NAME
    )

    path = package_path / "model"

    status = inspect_model_directory(
        path
    )

    if not status["ready"]:
        raise RuntimeError(
            "SmolVLM2-Modell ist nicht installiert "
            "oder unvollstaendig. "
            f"Fehlend: {status['missing_files']}"
        )

    return path

