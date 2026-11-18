import importlib.util
from pathlib import Path
from unittest.mock import patch
import json
import io
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("offline_llm_under_test", ROOT / "plugin.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Registry:
    def register(self, **kwargs):
        self.worker = kwargs

class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return json.dumps({"choices": [{"message": {"content": "Testantwort"}}], "usage": {"total_tokens": 4}}).encode()

class Tests(unittest.TestCase):
    def setUp(self):
        self.registry = Registry()
        mod.register({"workers": self.registry, "plugin_id": "mediahub.interaktions_ki", "plugin_version": "0.1.0"})
    def test_registration(self):
        self.assertEqual(self.registry.worker["job_types"], ["chat", "text_generation"])
    def test_no_prompt(self):
        with self.assertRaises(ValueError): self.registry.worker["handler"]({"payload": {}})
    def test_response(self):
        with patch.object(mod.urllib.request, "urlopen", return_value=FakeResponse()):
            result = self.registry.worker["handler"]({"payload": {"prompt": "Hallo"}})
        self.assertEqual(result["text"], "Testantwort")
    def test_thinking_flag_forwarded(self):
        for thinking in (False, True):
            with self.subTest(thinking=thinking):
                with patch.object(mod.urllib.request, "urlopen", return_value=FakeResponse()) as mocked:
                    self.registry.worker["handler"]({"payload": {"prompt": "Hallo", "thinking": thinking}})
                body = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
                self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": thinking})
                user_text = body["messages"][-1]["content"]
                self.assertEqual("/no_think" in user_text, not thinking)

    def test_empty_answer_rejected(self):
        class ThinkingOnlyResponse(FakeResponse):
            def read(self, limit):
                return json.dumps({"choices": [{"message": {"content": "", "reasoning_content": "thinking"}}]}).encode()
        with patch.object(mod.urllib.request, "urlopen", return_value=ThinkingOnlyResponse()):
            with self.assertRaisesRegex(mod.OfflineLLMError, "keinen Antworttext"):
                self.registry.worker["handler"]({"payload": {"prompt": "Hallo"}})

    def test_invalid_thinking_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.worker["handler"]({"payload": {"prompt": "Hallo", "thinking": "false"}})

    def test_remote_server_rejected(self):
        with patch.dict(mod.os.environ, {"MEDIAHUB_LLAMA_SERVER_URL": "http://192.168.1.1:8080"}):
            with self.assertRaises(mod.OfflineLLMError):
                self.registry.worker["handler"]({"payload": {"prompt": "Hallo"}})

if __name__ == "__main__": unittest.main()
