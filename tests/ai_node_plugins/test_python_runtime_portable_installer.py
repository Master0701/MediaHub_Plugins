import importlib.util
from pathlib import Path

import pytest


def test_existing_runtime_is_not_overwritten(tmp_path):
    installer_path = (
        Path(__file__).resolve().parents[2]
        / "ai_node_plugins"
        / "python_runtime"
        / "portable_installer.py"
    )

    spec = importlib.util.spec_from_file_location(
        "mediahub_portable_installer_test",
        installer_path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    target = tmp_path / "python_runtime"
    target.mkdir()

    marker = target / "existing.txt"
    marker.write_text("NICHT UEBERSCHREIBEN", encoding="utf-8")

    with pytest.raises(FileExistsError):
        module.install_verified_runtime(
            package=tmp_path / "nicht_vorhanden.zip",
            target=target,
            expected_sha256="0" * 64,
        )

    assert marker.read_text(encoding="utf-8") == "NICHT UEBERSCHREIBEN"

def test_archive_with_wrong_sha256_is_rejected(tmp_path):
    import hashlib
    import zipfile

    installer_path = (
        Path(__file__).resolve().parents[2]
        / "ai_node_plugins"
        / "python_runtime"
        / "portable_installer.py"
    )

    spec = importlib.util.spec_from_file_location(
        "mediahub_portable_installer_sha_test",
        installer_path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    package = tmp_path / "python.zip"

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("python.exe", b"test")

    actual_sha256 = hashlib.sha256(package.read_bytes()).hexdigest()
    wrong_sha256 = "0" * 64

    assert actual_sha256 != wrong_sha256

    target = tmp_path / "installed_python"

    with pytest.raises((ValueError, RuntimeError)):
        module.install_verified_runtime(
            package=package,
            target=target,
            expected_sha256=wrong_sha256,
        )

    assert not target.exists()

def test_archive_path_traversal_is_rejected(tmp_path):
    import hashlib
    import zipfile

    installer_path = (
        Path(__file__).resolve().parents[2]
        / "ai_node_plugins"
        / "python_runtime"
        / "portable_installer.py"
    )

    spec = importlib.util.spec_from_file_location(
        "mediahub_portable_installer_path_test",
        installer_path,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    package = tmp_path / "malicious.zip"

    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../outside.txt", "UNERLAUBT")
        archive.writestr("python.exe", "test")

    sha256 = hashlib.sha256(package.read_bytes()).hexdigest()
    target = tmp_path / "installed_python"

    with pytest.raises((ValueError, RuntimeError)):
        module.install_verified_runtime(
            package=package,
            target=target,
            expected_sha256=sha256,
        )

    assert not target.exists()
    assert not (tmp_path / "outside.txt").exists()
