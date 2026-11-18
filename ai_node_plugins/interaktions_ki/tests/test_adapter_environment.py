import os
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util

spec = importlib.util.spec_from_file_location("ik_adapter_env", Path(__file__).resolve().parents[1] / "node_install_adapter.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AdapterEnvironmentTests(unittest.TestCase):
    def test_requires_new_environment_variables(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(module.InteraktionsKIInstallError):
                module.prepare_runtime({"id": "mediahub.interaktions_ki"}, Path(__file__).resolve().parents[1], approved=True)
    def test_rejects_old_environment_variables(self):
        with patch.dict(os.environ, {"MEDIAHUB_OFFLINE_LLM_ARCHIVE":"a.zip", "MEDIAHUB_OFFLINE_LLM_SHA256":"0"*64, "MEDIAHUB_OFFLINE_LLM_TARGET":"C:/runtime"}, clear=True):
            with self.assertRaises(module.InteraktionsKIInstallError):
                module.prepare_runtime({"id": "mediahub.interaktions_ki"}, Path(__file__).resolve().parents[1], approved=True)
    def test_requires_approval(self):
        with self.assertRaises(module.InteraktionsKIInstallError):
            module.prepare_runtime({"id":"mediahub.interaktions_ki"}, Path(__file__).resolve().parents[1], approved=False)
