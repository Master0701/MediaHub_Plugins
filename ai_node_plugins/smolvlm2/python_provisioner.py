"""Private CPython provisioning for SmolVLM2."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

PYTHON_VERSION = "3.12.10"

PYTHON_ARCH = "amd64"

PYTHON_FILENAME = (
    "python-3.12.10-amd64.exe"
)

PYTHON_URL = (
    "https://www.python.org/"
    "ftp/python/3.12.10/"
    "python-3.12.10-amd64.exe"
)

# Fuer den vollstaendigen Windows-Installer
# wird ausschliesslich SHA256 verifiziert.
PYTHON_MD5 = None

# Wird spaeter im Release-Prozess
# zusaetzlich mit einem von uns
# verifizierten SHA256 belegt.
PYTHON_SHA256: str | None = (
    "67b5635e80ea51072b87941312d00ec8"
    "927c4db9ba18938f7ad2d27b328b95fb"
)


class PythonProvisionError(
    RuntimeError
):
    pass


def default_private_root() -> Path:
    """Use persistent user data, not the Compute Node executable runtime."""
    override = os.environ.get("MEDIAHUB_COMPUTE_DATA_ROOT")
    base = Path(override).expanduser() if override else Path.home() / ".mediahub" / "compute_node"
    return base / "private_python" / f"cpython-{PYTHON_VERSION}-x64"

def python_executable(
    root: Path | None = None,
) -> Path:
    root = Path(
        root or default_private_root()
    )

    return root / "python.exe"


def package_metadata() -> dict[str, Any]:
    return {
        "version": PYTHON_VERSION,
        "architecture": "x64",
        "filename": PYTHON_FILENAME,
        "url": PYTHON_URL,
        "md5": PYTHON_MD5,
        "sha256": PYTHON_SHA256,
        "source": "python.org",
        "private": True,
        "changes_system_path": False,
        "changes_registry": True,
    }


def validate_official_source(
    url: str = PYTHON_URL,
) -> None:
    parsed = urllib.parse.urlparse(
        url
    )

    if parsed.scheme.lower() != "https":
        raise PythonProvisionError(
            "Python-Download muss HTTPS "
            "verwenden."
        )

    if (
        parsed.hostname
        != "www.python.org"
    ):
        raise PythonProvisionError(
            "Python darf nur von "
            "www.python.org geladen werden."
        )

    if not parsed.path.endswith(
        "/" + PYTHON_FILENAME
    ):
        raise PythonProvisionError(
            "Unerwarteter Python-Dateiname."
        )


def file_hash(
    path: str | Path,
    algorithm: str,
) -> str:
    path = Path(path)

    digest = hashlib.new(
        algorithm
    )

    with path.open("rb") as handle:
        while True:
            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def verify_package(
    package_path: str | Path,
) -> dict[str, Any]:
    path = Path(
        package_path
    )

    if not path.is_file():
        raise PythonProvisionError(
            "Python-Paket nicht gefunden."
        )

    sha256 = file_hash(
        path,
        "sha256",
    )
    md5 = file_hash(
        path,
        "md5",
    )

    if (
        PYTHON_SHA256 is not None
        and sha256.lower()
        != PYTHON_SHA256.lower()
    ):
        raise PythonProvisionError(
            "SHA256-Pruefung fehlgeschlagen."
        )


    return {
        "verified": True,
        "md5": md5,
        "sha256": sha256,
        "size": path.stat().st_size,
    }


def download_package(
    destination: str | Path,
    *,
    url: str = PYTHON_URL,
) -> Path:
    validate_official_source(
        url
    )

    destination = Path(
        destination
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = destination.with_suffix(
        destination.suffix + ".part"
    )

    if temp_path.exists():
        temp_path.unlink()

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "MediaHub-Compute-Node/"
                "SmolVLM2-Runtime"
            )
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:

            final_url = (
                response.geturl()
            )

            validate_official_source(
                final_url
            )

            with temp_path.open(
                "wb"
            ) as target:
                shutil.copyfileobj(
                    response,
                    target,
                )

    except Exception:
        if temp_path.exists():
            temp_path.unlink()

        raise

    verify_package(
        temp_path
    )

    temp_path.replace(
        destination
    )

    return destination


def _validate_zip_members(
    archive: zipfile.ZipFile,
) -> None:
    for info in archive.infolist():
        raw = info.filename.replace(
            "\\",
            "/",
        )

        member = Path(raw)

        if member.is_absolute():
            raise PythonProvisionError(
                "Absoluter ZIP-Pfad "
                "nicht erlaubt."
            )

        if ".." in member.parts:
            raise PythonProvisionError(
                "ZIP-Pfadnavigation "
                "nicht erlaubt."
            )

        if (
            len(raw) >= 2
            and raw[1] == ":"
        ):
            raise PythonProvisionError(
                "Windows-Laufwerkspfad "
                "im ZIP nicht erlaubt."
            )


def extract_package(
    package_path: str | Path,
    target_root: str | Path,
    *,
    verify: bool = True,
) -> Path:
    package_path = Path(
        package_path
    )

    target_root = Path(
        target_root
    )

    if verify:
        verify_package(
            package_path
        )

    if not zipfile.is_zipfile(
        package_path
    ):
        raise PythonProvisionError(
            "Ungueltiges Python-ZIP."
        )

    target_root.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix="mediahub_python_"
    ) as temp_name:

        stage = (
            Path(temp_name)
            / "python"
        )

        stage.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            package_path,
            "r",
        ) as archive:

            _validate_zip_members(
                archive
            )

            archive.extractall(
                stage
            )

        executable = (
            stage / "python.exe"
        )

        if not executable.is_file():
            raise PythonProvisionError(
                "python.exe fehlt im "
                "extrahierten Paket."
            )

        _enable_import_site(
            stage
        )

        if target_root.exists() or target_root.is_symlink():
            raise FileExistsError(
                f"Python-Zielordner existiert bereits: {target_root}"
            )

        shutil.move(
            str(stage),
            str(target_root),
        )

    return (
        target_root
        / "python.exe"
    )


def _enable_import_site(
    root: Path,
) -> None:
    files = sorted(
        root.glob(
            "python*._pth"
        )
    )

    if not files:
        raise PythonProvisionError(
            "Python _pth-Datei fehlt."
        )

    pth = files[0]

    text = pth.read_text(
        encoding="utf-8"
    )

    lines = []

    found = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped in {
            "#import site",
            "# import site",
            "import site",
        }:
            lines.append(
                "import site"
            )
            found = True
        else:
            lines.append(
                line
            )

    if not found:
        lines.append(
            "import site"
        )

    pth.write_text(
        "\n".join(lines)
        + "\n",
        encoding="utf-8",
    )


def _python_supports_venv(executable: Path) -> bool:
    """Check that managed Python supports isolated environments."""
    if not executable.is_file():
        return False

    try:
        result = subprocess.run(
            [
                str(executable),
                "-c",
                (
                    "import sys, venv, ensurepip; "
                    "assert sys.version_info[:2] == (3, 12)"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def inspect_private_python(
    root: Path | None = None,
) -> dict[str, Any]:
    root = Path(
        root or default_private_root()
    )

    executable = (
        root / "python.exe"
    )

    return {
        **package_metadata(),
        "root": str(root),
        "python": str(
            executable
        ),
        "installed": (
            executable.is_file()
            and _python_supports_venv(executable)
        ),
    }

def provision_private_python(root: Path | None = None) -> dict[str, Any]:
    """Never run the legacy python.org EXE installer automatically.

    Portable runtime installation is a separate confirmed operation.
    """
    target_root = Path(root) if root is not None else (
        default_private_root().parent / "cpython-3.12.10-x64-astral-20250409"
    )
    current = inspect_private_python(target_root)
    if current["installed"]:
        return current
    raise PythonProvisionError(
        "Keine funktionsfaehige portable Python-Runtime vorhanden. "
        "Bitte MediaHub Python Runtime separat mit bestaetigter "
        "Installation und SHA256-Pruefung einrichten. "
        "Der alte python.org-EXE-Installer wird nicht gestartet."
    )
