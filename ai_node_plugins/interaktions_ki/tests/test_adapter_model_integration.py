import hashlib
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "ik_adapter_model", ROOT / "node_install_adapter.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def snapshot(runtime: pathlib.Path, model: pathlib.Path | None) -> dict:
    packages = {
        "runtime": {
            "path": str(runtime),
            "sha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
        },
    }
    if model is not None:
        packages["model"] = {
            "path": str(model),
            "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
        }
    return {"profile_selected": "cpu", "packages": packages}


class ModelIntegrationTests(unittest.TestCase):
    def test_model_required_before_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            runtime = base / "runtime.zip"
            with zipfile.ZipFile(runtime, "w") as z:
                z.writestr("llama-server.exe", b"fake-exe")
            with patch.dict(
                "os.environ", {"MEDIAHUB_COMPUTE_RUNTIME": str(base)}, clear=True
            ):
                with self.assertRaisesRegex(
                    module.InteraktionsKIInstallError,
                    "Runtime-/Modell-Snapshot unvollstaendig",
                ):
                    module.prepare_runtime(
                        {"id": "mediahub.interaktions_ki"},
                        ROOT,
                        approved=True,
                        pinned_tools=snapshot(runtime, None),
                    )
            self.assertFalse((base / "plugin_runtimes").exists())

    def test_both_packages_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            runtime, model = base / "runtime.zip", base / "model.zip"
            with zipfile.ZipFile(runtime, "w") as z:
                z.writestr("llama-server.exe", b"fake-exe")
            with zipfile.ZipFile(model, "w") as z:
                z.writestr("qwen.gguf", b"GGUF" + b"0" * 32)
            pinned = snapshot(runtime, model)
            with patch.dict(
                "os.environ", {"MEDIAHUB_COMPUTE_RUNTIME": str(base)}, clear=True
            ):
                result = module.prepare_runtime(
                    {"id": "mediahub.interaktions_ki"},
                    ROOT,
                    approved=True,
                    pinned_tools=pinned,
                )
                reused = module.prepare_runtime(
                    {"id": "mediahub.interaktions_ki"},
                    ROOT,
                    approved=True,
                    pinned_tools=pinned,
                )
            self.assertTrue(pathlib.Path(result["server"]).is_file())
            self.assertTrue(pathlib.Path(result["model"]).is_file())
            self.assertFalse(result["model_load_verified"])
            self.assertTrue(reused["reused"])
            self.assertTrue(reused["model_status"]["reused"])

    def test_model_checksum_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            runtime, model = base / "runtime.zip", base / "model.zip"
            with zipfile.ZipFile(runtime, "w") as z:
                z.writestr("llama-server.exe", b"exe")
            with zipfile.ZipFile(model, "w") as z:
                z.writestr("qwen.gguf", b"GGUF" + b"0" * 32)
            pinned = snapshot(runtime, model)
            pinned["packages"]["model"]["sha256"] = "0" * 64
            with patch.dict(
                "os.environ", {"MEDIAHUB_COMPUTE_RUNTIME": str(base)}, clear=True
            ):
                with self.assertRaisesRegex(
                    module.InteraktionsKIInstallError, "SHA-256"
                ):
                    module.prepare_runtime(
                        {"id": "mediahub.interaktions_ki"},
                        ROOT,
                        approved=True,
                        pinned_tools=pinned,
                    )
            self.assertFalse((base / "plugin_runtimes").exists())


if __name__ == "__main__":
    unittest.main()
