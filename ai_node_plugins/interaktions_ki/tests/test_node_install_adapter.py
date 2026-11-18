import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("offline_adapter", ROOT / "node_install_adapter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AdapterTests(unittest.TestCase):
    def test_requires_approval(self):
        with self.assertRaises(module.InteraktionsKIInstallError):
            module.prepare_runtime({"id":"mediahub.interaktions_ki"}, ROOT, approved=False)
    def test_requires_configuration(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(module.InteraktionsKIInstallError):
                module.prepare_runtime({"id":"mediahub.interaktions_ki"}, ROOT, approved=True)
    def test_no_wrong_id(self):
        with self.assertRaises(module.InteraktionsKIInstallError):
            module.prepare_runtime({"id":"other"}, ROOT, approved=True)

if __name__ == "__main__": unittest.main()
