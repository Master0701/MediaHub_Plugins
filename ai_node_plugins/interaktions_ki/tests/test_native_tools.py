import copy
import base64
import gzip
import importlib.util
import io
import json
from pathlib import Path
import sys
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tool_protocol as protocol
import plugin as worker
import web_bridge

TOOL = {"type": "function", "function": {"name": "get_test_temperature",
    "description": "Nur simulierte Testtemperatur, keine Geraete.",
    "parameters": {"type": "object", "properties": {
        "room": {"type": "string", "enum": ["Testzimmer"]}},
        "required": ["room"], "additionalProperties": False}}}
CALL = {"id": "call_test", "type": "function", "function": {
    "name": "get_test_temperature", "arguments": '{"room":"Testzimmer"}'}}
MESSAGE = {"role": "assistant", "content": None, "tool_calls": [CALL]}
BODY = {"model": "mediahub-interaktions-ki", "messages": [{"role": "user",
    "content": "Wie warm ist es im Testzimmer? Nutze das Testwerkzeug."}],
    "tools": [TOOL], "tool_choice": "required", "temperature": 0}


class ProtocolTests(unittest.TestCase):
    def test_valid(self):
        _, _, defs, choice, forced = protocol.options(BODY)
        self.assertEqual(protocol.response(MESSAGE, "tool_calls", defs, choice, forced), MESSAGE)

    def test_invalid_arguments(self):
        for args in ({}, {"room": 1}, {"room": "Bad"}, {"room": "Testzimmer", "extra": 1}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                protocol.validate(args, TOOL["function"]["parameters"])

    def test_nested_types(self):
        schema = {"type": "array", "items": {"type": "object", "properties": {
            "n": {"type": "integer", "enum": [1, 2]}}, "required": ["n"]}}
        protocol.check_schema(schema)
        protocol.validate([{"n": 1}], schema)
        for value in ([{"n": True}], [{"n": 1.5}], [{"n": 3}]):
            with self.assertRaises(ValueError):
                protocol.validate(value, schema)

    def test_unsupported_schema_rejected(self):
        for schema in ({"$ref": "#/x"}, {"type": "string", "pattern": "a"}, {"type": 5}):
            with self.assertRaises(ValueError):
                protocol.check_schema(schema)

    def test_history_roundtrip_and_order(self):
        history = BODY["messages"] + [MESSAGE, {"role": "tool", "tool_call_id": "call_test", "content": "21.5"}]
        self.assertEqual(protocol.messages(history), history)
        for invalid in (history[:-1], history + [history[-1]], history[:2] + BODY["messages"] + history[2:]):
            with self.assertRaises(ValueError):
                protocol.messages(invalid)

    def test_non_json_numbers_and_duplicate_keys(self):
        for value in ('{"x":NaN}', '{"x":1e999}', '{"x":1,"x":2}'):
            with self.assertRaises(ValueError):
                protocol.loads(value)


class BridgeTests(unittest.TestCase):
    def test_auth_host_and_origin_guards(self):
        class Key:
            def enabled(self): return True
            def verify(self, value): return value == "test-only"
        handler_type = web_bridge.Bridge.handler(object(), lan_host="127.0.0.1", api_key=Key())
        from types import SimpleNamespace
        for headers, status in (({"Host": "wrong:8769"}, 403),
                ({"Host": "127.0.0.1:8769"}, 401),
                ({"Host": "127.0.0.1:8769", "Authorization": "Bearer wrong"}, 401),
                ({"Host": "127.0.0.1:8769", "Origin": "https://wrong", "Authorization": "Bearer test-only"}, 403),
                ({"Host": "127.0.0.1:8769", "Authorization": "Bearer test-only"}, 200)):
            handler = object.__new__(handler_type)
            handler.path = "/v1/models"
            handler.server = SimpleNamespace(server_port=8769)
            handler.headers = headers
            handler.reply = lambda code, body: code
            self.assertEqual(handler.route("GET"), status)

    def dispatch(self, body, output=None, failed=False):
        class Bridge:
            def __init__(self):
                self.jobs = []
            def node(self, path, method, data):
                if path == "/jobs":
                    self.jobs.append(data)
                    return {"id": "test"}
                return {"status": "failed" if failed else "completed", "result": {
                    "worker_id": "mediahub.interaktions_ki.worker", "output": output or {
                        "message": MESSAGE, "finish_reason": "tool_calls", "text": ""}}}
        bridge = Bridge()
        handler_type = web_bridge.Bridge.handler(bridge, lan_host="127.0.0.1")
        handler = object.__new__(handler_type)
        handler.reply = lambda status, value: (status, value)
        result = handler.dispatch("POST", "/v1/chat/completions", body)
        return result, bridge.jobs

    def test_native_passthrough(self):
        (status, result), jobs = self.dispatch(BODY)
        self.assertEqual(status, 200)
        self.assertEqual(result["choices"][0]["message"], MESSAGE)
        self.assertEqual(jobs[0]["payload"]["tools"], [TOOL])
        self.assertEqual(jobs[0]["payload"]["messages"], BODY["messages"])
        self.assertIs(jobs[0]["payload"]["parallel_tool_calls"], False)

    def test_no_fallback(self):
        for output in ({"text": '{"action":"tool","name":"get_test_temperature","arguments":{"room":"Testzimmer"}}'},
                       {"message": {"role": "assistant", "content": "22 Grad"}, "finish_reason": "stop"}):
            (status, _), jobs = self.dispatch(BODY, output)
            self.assertEqual(status, 502)
            self.assertEqual(len(jobs), 1)
        self.assertEqual(self.dispatch(BODY, failed=True)[0][0], 502)

    def test_explicit_json_compat(self):
        (status, result), jobs = self.dispatch(dict(BODY, tool_calling_mode="json_compat"), {
            "text": '{"action":"tool","name":"get_test_temperature","arguments":{"room":"Testzimmer"}}', "finish_reason": "stop"})
        self.assertEqual(status, 200)
        self.assertEqual(result["choices"][0]["finish_reason"], "tool_calls")
        self.assertNotIn("tools", jobs[0]["payload"])
        self.assertIn('"action":"tool"', jobs[0]["payload"]["messages"][0]["content"])

    def test_history_preserved(self):
        history = BODY["messages"] + [MESSAGE, {"role": "tool", "tool_call_id": "call_test", "content": "21.5"}]
        (status, _), jobs = self.dispatch(dict(BODY, messages=history, tools=[], tool_choice="none"), {
            "message": {"role": "assistant", "content": "21,5 Grad"}, "finish_reason": "stop"})
        self.assertEqual(status, 200)
        self.assertEqual(jobs[0]["payload"]["messages"], history)

    def test_invalid_requests_do_not_create_job(self):
        for change in ({"parallel_tool_calls": True}, {"tool_choice": "required", "tools": []},
                       {"tool_calling_mode": "fallback"}, {"tool_choice": {"type": "function", "function": {"name": "missing"}}}):
            (status, _), jobs = self.dispatch(dict(BODY, **change))
            self.assertEqual(status, 400)
            self.assertEqual(jobs, [])

    def test_invalid_backend_arguments(self):
        for args in ({"room": 3}, {"room": "Bad"}, {}):
            msg = copy.deepcopy(MESSAGE)
            msg["tool_calls"][0]["function"]["arguments"] = json.dumps(args)
            self.assertEqual(self.dispatch(BODY, {"message": msg, "finish_reason": "tool_calls"})[0][0], 502)

    def test_auto_answers_and_none_rejects_calls(self):
        answer = {"message": {"role": "assistant", "content": "Hallo"}, "finish_reason": "length"}
        (status, result), _ = self.dispatch(dict(BODY, tool_choice="auto"), answer)
        self.assertEqual(status, 200)
        self.assertEqual(result["choices"][0]["finish_reason"], "length")
        self.assertEqual(self.dispatch(dict(BODY, tool_choice="none"))[0][0], 502)

    def test_legacy_validates_enum_and_required(self):
        for text in ('{"action":"answer","content":"22 Grad"}',
                     '{"action":"tool","name":"get_test_temperature","arguments":{"room":"Bad"}}'):
            self.assertEqual(self.dispatch(dict(BODY, tool_calling_mode="json_compat"), {"text": text})[0][0], 502)


class WorkerTests(unittest.TestCase):
    def run_worker(self, payload, message=MESSAGE, reason="tool_calls"):
        raw = json.dumps({"choices": [{"message": message, "finish_reason": reason}]}).encode()
        captured = []
        class Response(io.BytesIO):
            status = 200
        def request(req, **kwargs):
            captured.append(json.loads(req.data))
            return Response(raw)
        with patch.object(worker, "ensure_running"), patch.object(worker, "backend_evidence", return_value={"backend_verified": True}), patch.object(worker.urllib.request, "urlopen", side_effect=request):
            result = worker.create_handler({})({"payload": payload})
        return result, captured[0]

    def test_native_forwarding_and_null_content(self):
        original = copy.deepcopy(BODY)
        result, sent = self.run_worker(BODY)
        self.assertEqual(BODY, original)
        self.assertEqual(sent["tools"], [TOOL])
        self.assertEqual(sent["tool_choice"], "required")
        self.assertIs(sent["parallel_tool_calls"], False)
        self.assertEqual(sent["messages"][-1], BODY["messages"][0])
        self.assertEqual(result["message"], MESSAGE)
        self.assertEqual(result["finish_reason"], "tool_calls")
        self.assertEqual(result["text"], "")
        self.assertTrue(result["backend_verified"])

    def test_named_choice(self):
        other = copy.deepcopy(TOOL)
        other["function"]["name"] = "other"
        body = dict(BODY, tools=[TOOL, other], tool_choice={"type": "function", "function": {"name": "get_test_temperature"}})
        _, sent = self.run_worker(body)
        self.assertEqual(sent["tools"], [TOOL])
        self.assertEqual(sent["tool_choice"], "required")

    def test_history_without_current_tools(self):
        history = BODY["messages"] + [MESSAGE, {"role": "tool", "tool_call_id": "call_test", "content": "21.5"}]
        result, sent = self.run_worker({"messages": history, "tool_choice": "none"}, {"role": "assistant", "content": "21,5 Grad"}, "stop")
        self.assertEqual(sent["messages"][1:], history)
        self.assertEqual(result["text"], "21,5 Grad")

    def test_required_and_none_guards(self):
        with self.assertRaises(worker.OfflineLLMError):
            self.run_worker(BODY, {"role": "assistant", "content": "22 Grad"}, "stop")
        with self.assertRaises(worker.OfflineLLMError):
            self.run_worker(dict(BODY, tool_choice="none"))
        with self.assertRaises(worker.OfflineLLMError):
            self.run_worker(BODY, reason="length")

    def test_normal_chat_and_length(self):
        result, sent = self.run_worker({"prompt": "Hallo"}, {"content": "Hallo"}, "length")
        self.assertEqual(result["finish_reason"], "length")
        self.assertEqual(result["text"], "Hallo")
        self.assertNotIn("tools", sent)
        self.assertIn("/no_think", sent["messages"][-1]["content"])


class ProbeTests(unittest.TestCase):
    def test_common_nulltest_embeds_current_probe_before_cleanup(self):
        folder = ROOT.parents[1] / "tools/dev/plugin_nulltest"
        text = (folder / "MediaHub_Gemeinsamer_Nulltest_v1.0.25_BOM_DiagnoseAlle.ps1").read_text(encoding="utf-8-sig")
        def embedded(name):
            line = next(l for l in text.splitlines() if "Write-Embedded" in l and name in l)
            return gzip.decompress(base64.b64decode(re.findall(r"'([^']*)'", line)[-1]))
        self.assertEqual(embedded("native_tool_calling_probe.py"), (folder / "native_tool_calling_probe.py").read_bytes())
        script = embedded("Interaktions_KI_CPU_CUDA.ps1").decode("utf-8-sig")
        self.assertLess(script.index("& python -B $toolProbe"), script.index("try { Stop-OwnNode }"))
        self.assertIn('Contains("ECHTES NATIVES TOOL-CALLING BESTANDEN:', text)

    def test_probe_checks_simulated_result(self):
        path = ROOT.parents[1] / "tools/dev/plugin_nulltest/native_tool_calling_probe.py"
        spec = importlib.util.spec_from_file_location("native_probe_test", path)
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        seen = []
        def complete(payload):
            seen.append(payload)
            if payload.get("tool_choice") == "required" or isinstance(payload.get("tool_choice"), dict):
                return {"message": MESSAGE, "finish_reason": "tool_calls"}
            return {"message": {"role": "assistant", "content": "21,5 Grad"}, "finish_reason": "stop"}
        probe.exercise(complete)
        self.assertEqual(len(seen), 7)
        self.assertEqual(json.loads(seen[1]["messages"][-1]["content"])["temperature_celsius"], 21.5)
        with self.assertRaises(RuntimeError):
            probe.exercise(lambda _: {"message": {"content": "22 Grad"}, "finish_reason": "stop"})


if __name__ == "__main__":
    unittest.main()
