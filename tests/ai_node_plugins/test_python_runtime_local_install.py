import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest


PLUGIN = Path(__file__).resolve().parents[2] / "ai_node_plugins" / "python_runtime" / "plugin.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("test_runtime_plugin_local", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_install_requires_explicit_confirmation(tmp_path):
    module = load_plugin()
    with pytest.raises(PermissionError):
        module.install_local_archive(tmp_path / "missing.zip", "0" * 64)
    assert not (tmp_path / "python").exists()


def test_install_rejects_malformed_sha256(tmp_path):
    module = load_plugin()
    with pytest.raises(ValueError, match="SHA256"):
        module.install_local_archive(tmp_path / "missing.zip", "not-a-hash", confirmed=True)


def test_install_rejects_unsafe_zip_path(tmp_path):
    module = load_plugin()
    archive_path = tmp_path / "malicious.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("foo//bar", b"bad")
        archive.writestr("python.exe", b"test")
    sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="Unsicherer ZIP-Pfad"):
        module.install_local_archive(archive_path, sha256, confirmed=True, target=tmp_path / "python")
    assert not (tmp_path / "python").exists()
