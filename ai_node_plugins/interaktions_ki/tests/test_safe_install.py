import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "safe_install.py"
spec = importlib.util.spec_from_file_location("llm_safe_install", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestSafeInstall(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "llama.zip"
        with zipfile.ZipFile(self.archive, "w") as z:
            z.writestr("bin/llama-server.exe", b"dummy executable")
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.target = self.root / "runtime"

    def install(self, **kwargs):
        return mod.install_local_archive(archive_path=str(self.archive), expected_sha256=self.sha,
                                         target_dir=str(self.target), **kwargs)

    def test_requires_confirmation(self):
        with self.assertRaises(mod.SafeInstallError): self.install()
        self.assertFalse(self.target.exists())

    def test_install_with_confirmation(self):
        result = self.install(confirmed=True)
        self.assertTrue(Path(result["server"]).is_file())
        self.assertFalse(result["backend_verified"])

    def test_no_overwrite(self):
        self.target.mkdir()
        (self.target / "important.txt").write_text("keep")
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)
        self.assertEqual((self.target / "important.txt").read_text(), "keep")

    def test_wrong_checksum(self):
        with self.assertRaises(mod.SafeInstallError):
            mod.install_local_archive(archive_path=str(self.archive), expected_sha256="0"*64,
                                      target_dir=str(self.target), confirmed=True)
        self.assertFalse(self.target.exists())

    def test_zip_slip_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as z:
            z.writestr("bin/llama-server.exe", b"dummy")
            z.writestr("../escape.txt", b"bad")
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)
        self.assertFalse((self.root / "escape.txt").exists())

    def test_missing_server_rejected(self):
        with zipfile.ZipFile(self.archive, "w") as z: z.writestr("readme.txt", b"hello")
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        with self.assertRaises(mod.SafeInstallError): self.install(confirmed=True)
