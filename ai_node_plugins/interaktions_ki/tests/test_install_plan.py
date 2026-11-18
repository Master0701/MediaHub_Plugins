import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "install_plan.py"
spec = importlib.util.spec_from_file_location("llm_install_plan", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InstallPlanTests(unittest.TestCase):
    def test_valid_cpu_and_cuda_plans_are_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "llama.zip"
            archive.write_bytes(b"test fixture")
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            for backend in ("cpu", "cuda"):
                plan = module.plan_install(archive_path=str(archive), sha256=digest, target_dir=str(Path(tmp) / "runtime"), backend=backend)
                self.assertFalse(plan["installation_performed"])
                self.assertFalse((Path(tmp) / "runtime").exists())
    def test_checksum_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "llama.zip"
            archive.write_bytes(b"test fixture")
            with self.assertRaises(module.InstallPlanError):
                module.plan_install(archive_path=str(archive), sha256="0" * 64, target_dir=str(Path(tmp) / "runtime"))
    def test_model_plan_does_not_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / "small.gguf"
            model.write_bytes(b"fixture")
            plan = module.plan_model(model_path=str(model))
            self.assertFalse(plan["model_downloaded"])
            self.assertFalse(plan["sha256_verified"])

if __name__ == "__main__":
    unittest.main()
