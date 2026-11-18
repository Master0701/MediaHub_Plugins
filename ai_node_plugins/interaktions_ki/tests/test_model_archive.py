import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ik_safe_model", ROOT / "safe_install.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ModelArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "model.zip"
        self.target = self.root / "model"
        self.make_archive({"model.gguf": b"GGUF" + bytes(64)})

    def make_archive(self, entries):
        with zipfile.ZipFile(self.archive, "w") as z:
            for name, data in entries.items():
                z.writestr(name, data)
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def install(self, **kw):
        return mod.install_local_model_archive(archive_path=str(self.archive),
            expected_sha256=self.sha, target_dir=str(self.target), **kw)

    def test_requires_confirmation(self):
        with self.assertRaises(mod.SafeInstallError): self.install()
        self.assertFalse(self.target.exists())

    def test_valid_model_archive(self):
        result = self.install(confirmed=True)
        self.assertTrue(Path(result["model"]).is_file())
        self.assertFalse(result["model_load_verified"])

    def test_no_overwrite(self):
        self.target.mkdir()
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)

    def test_checksum_rejected(self):
        with self.assertRaises(mod.SafeInstallError):
            mod.install_local_model_archive(archive_path=str(self.archive),
                expected_sha256="0"*64, target_dir=str(self.target), confirmed=True)
        self.assertFalse(self.target.exists())

    def test_zip_slip_rejected(self):
        self.make_archive({"model.gguf": b"GGUF"+bytes(64), "../escape.txt": b"bad"})
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_wrong_magic_rejected(self):
        self.make_archive({"model.gguf": b"NOT!"+bytes(64)})
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)

    def test_two_models_rejected(self):
        self.make_archive({"a.gguf": b"GGUF"+bytes(64), "b.gguf": b"GGUF"+bytes(64)})
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)

if __name__ == "__main__": unittest.main()
