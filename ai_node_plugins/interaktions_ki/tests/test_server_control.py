import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import Mock

MODULE = pathlib.Path(__file__).resolve().parents[1] / "server_control.py"
sys.path.insert(0, str(MODULE.parent))
spec = importlib.util.spec_from_file_location("offline_llm_server_control", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ServerControlTests(unittest.TestCase):
    def setUp(self):
        self.plan = {"command": ["llama-server.exe", "--port", "8080"],
                     "requires_manual_confirmation": True, "approved": False}
    def test_no_start_without_confirmation(self):
        popen = Mock()
        with self.assertRaises(PermissionError):
            mod.launch_foreground(self.plan, popen=popen)
        popen.assert_not_called()
    def test_refuses_existing_server(self):
        popen = Mock()
        with self.assertRaises(RuntimeError):
            mod.launch_foreground(self.plan, confirmed=True, popen=popen,
                                  health=lambda port: {"reachable": True})
        popen.assert_not_called()
    def test_start_when_confirmed(self):
        process = Mock(pid=1234)
        process.poll.return_value = None
        popen = Mock(return_value=process)
        result = mod.launch_foreground(self.plan, confirmed=True, popen=popen,
                                       health=lambda port: {"reachable": False} if not popen.called else {"reachable": True})
        self.assertTrue(result["started"])
        self.assertEqual(result["pid"], 1234)
    def test_stop_process(self):
        proc = Mock()
        proc.poll.return_value = None
        mod.stop_process(proc)
        proc.terminate.assert_called_once()
    def test_invalid_plan(self):
        with self.assertRaises(ValueError):
            mod.launch_foreground({"requires_manual_confirmation": True}, confirmed=True)

if __name__ == "__main__": unittest.main()
