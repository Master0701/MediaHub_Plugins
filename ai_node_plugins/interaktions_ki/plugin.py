"""MediaHub Offline LLM worker, phase 1: attach to an explicitly configured local llama-server."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

# Der Compute-Node stellt den Plugin-Pfad nur waehrend des Ladens bereit.
# Daher Hilfsmodule jetzt laden, nicht erst beim ersten Chat-Auftrag.
from auto_server import ensure_running, backend_evidence, stop_owned
import tool_protocol


class OfflineLLMError(RuntimeError):
    pass


def _endpoint() -> str:
    import ipaddress
    from urllib.parse import urlsplit

    value = os.environ.get(
        "MEDIAHUB_LLAMA_SERVER_URL",
        "http://127.0.0.1:8767",
    ).rstrip("/")

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise OfflineLLMError("Ungueltige KI-Server-Adresse") from exc

    if (
        parsed.scheme != "http"
        or not hostname
        or not port
        or parsed.username
        or parsed.password
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise OfflineLLMError("Ungueltige lokale KI-Server-Adresse")

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        allowed = (
            hostname.lower() == "localhost"
            or hostname.lower().endswith(".local")
            or hostname.lower().endswith(".lan")
            or (
                "." not in hostname
                and hostname.replace("-", "").isalnum()
            )
        )
    else:
        allowed = address.is_private or address.is_loopback

    if not allowed:
        raise OfflineLLMError(
            "Nur lokale oder private Heimnetz-Adressen erlaubt"
        )

    return value


def _messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages = payload.get("messages")
    if messages is None:
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("payload.prompt oder payload.messages erforderlich")
        messages = [{"role": "user", "content": prompt}]
    return tool_protocol.messages(messages)


def create_handler(context: dict[str, Any]):
    def handler(request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise ValueError("Job muss ein Objekt sein")
        payload = request.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError("payload muss ein Objekt sein")
        mode, tools, definitions, choice, forced = tool_protocol.options(payload)
        messages = _messages(payload)
        tool_context = bool(tools) or any(m.get("tool_calls") or m["role"] == "tool" for m in messages)
        native_tools = mode == "native" and (tool_context or "tool_choice" in payload)

        if not any(item["role"] == "system" for item in messages):
            messages.insert(0, {
                "role": "system",
                "content": (
                    "Du bist der lokale MediaHub-KI-Assistent. "
                    "Antworte standardmaessig auf Deutsch, "
                    "freundlich, klar und direkt. "
                    "MediaHub ist ein selbst entwickeltes "
                    "Medienverwaltungsprogramm. "
                    "Erfinde keine Informationen. "
                    "Wenn du etwas nicht weisst, sage es."
                ),
            })

        thinking = payload.get("thinking", False)
        if not isinstance(thinking, bool):
            raise ValueError("payload.thinking muss boolesch sein")

        if not thinking and not (mode == "native" and tool_context):
            for item in reversed(messages):
                if item["role"] == "user":
                    if "/no_think" not in item["content"]:
                        item["content"] += "\n/no_think"
                    break
        max_tokens = int(payload.get("max_tokens", 256))
        if not 1 <= max_tokens <= 2048:
            raise ValueError("max_tokens muss zwischen 1 und 2048 liegen")
        temperature = float(payload.get("temperature", 0.7))
        if not 0 <= temperature <= 2:
            raise ValueError("temperature muss zwischen 0 und 2 liegen")
        body = {"messages": messages, "max_tokens": max_tokens, "temperature": temperature,
                "stream": False, "chat_template_kwargs": {"enable_thinking": thinking}}
        if native_tools:
            # b12125 accepts string choices; constrain a named choice to one tool.
            body.update(tools=[t for t in tools if not forced or t["function"]["name"] == forced],
                        tool_choice="required" if forced else choice, parallel_tool_calls=False)
        data = json.dumps(body, allow_nan=False).encode("utf-8")
        endpoint = _endpoint()
        try:
            # plugin_path is <runtime>/plugins/<plugin-id>; no global env required.
            plugin_path = context.get("plugin_path")
            runtime_root = plugin_path.resolve().parent.parent if plugin_path else None
            ensure_running(endpoint, runtime_root=runtime_root)
        except Exception as exc:
            raise OfflineLLMError(f"Automatischer llama-server-Start fehlgeschlagen: {exc}") from exc
        req = urllib.request.Request(endpoint + "/v1/chat/completions", data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                if response.status != 200:
                    raise OfflineLLMError(f"llama-server HTTP {response.status}")
                result = json.loads(response.read(4 * 1024 * 1024).decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OfflineLLMError(f"Lokaler llama-server nicht erreichbar: {exc}") from exc
        try:
            first = result["choices"][0]
            finish_reason = first.get("finish_reason", "stop")
            message = tool_protocol.response(first["message"], finish_reason,
                                             definitions if native_tools else {},
                                             choice if native_tools else "none", forced if native_tools else None)
            message.setdefault("role", "assistant")
            answer = message.get("content") or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise OfflineLLMError("Ungueltige llama-server-Antwort: " + str(exc)) from exc
        evidence = backend_evidence(endpoint)
        return {"status": "completed", "engine": "llama.cpp", "text": answer,
                "message": message, "tool_calls": message.get("tool_calls", []),
                "finish_reason": finish_reason,
                "usage": result.get("usage", {}), "provider": "local_llama_server",
                **evidence}
    return handler


def register(context: dict[str, Any]) -> None:
    context["workers"].register(
        worker_id="mediahub.interaktions_ki.worker",
        name="MediaHub Interaktions-KI Worker",
        job_types=["chat", "text_generation"],
        handler=create_handler(context),
        metadata={"plugin_id": context["plugin_id"], "plugin_version": context["plugin_version"], "engine": "llama.cpp", "phase": "external_local_server", "installation_managed": True},
    )


class MediaHubInteraktionsKIPlugin:
    def register(self, context: dict[str, Any]) -> None:
        register(context)

    def sleep(self) -> None:
        """Release only a llama process started by this plugin."""
        stop_owned()

    def shutdown(self) -> None:
        """Stop only this plugin's owned llama process."""
        stop_owned()
