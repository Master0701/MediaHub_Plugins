"""Opt-in real inference against an existing Node; only a simulated tool.

No installation, device access, process management, or credential logging.
Run while the isolated CPU/CUDA Node is still running, before its cleanup.
"""
import argparse
import getpass
import json
import ipaddress
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request

TOOL = {"type": "function", "function": {
    "name": "get_test_temperature",
    "description": "Liest nur eine simulierte Testtemperatur, keine echten Geraete.",
    "parameters": {"type": "object", "properties": {
        "room": {"type": "string", "enum": ["Testzimmer"]}},
        "required": ["room"], "additionalProperties": False}}}


STATE = {"transport": "Testskript", "phase": "Konfiguration", "iteration": 0}


def diagnostic(event, **fields):
    # Callers supply only fixed labels, booleans, counters and allowlisted enums.
    print("DIAG " + json.dumps(dict(STATE, event=event, **fields), ensure_ascii=True), flush=True)


def safe_enum(value, allowed):
    return value if isinstance(value, str) and value in allowed else "unbekannt/redigiert"


def job_diagnostic(job):
    status = safe_enum(job.get("status"), ("queued", "running", "completed", "failed", "cancelled"))
    error = job.get("error")
    # Never echo the exception: it can contain URLs, headers or model text.
    error = error if isinstance(error, str) else ""
    category = "nicht_nachweisbar"
    for needle, label in (
        ("KI hat keinen gueltigen verpflichtenden Tool-Aufruf erzeugt", "Plugin_verwirft_fehlenden_Pflichtaufruf"),
        ("Ungueltige llama-server-Antwort", "Plugin_verwirft_Modellantwort"),
        ("Lokaler llama-server nicht erreichbar", "Plugin_zu_llama_Transportfehler"),
        ("Automatischer llama-server-Start fehlgeschlagen", "Plugin_llama_Startfehler"),
        ("Kein installierter, aktivierter und gesunder Worker", "Node_Worker_nicht_verfuegbar"),
        ("Nicht unterstuetztes Werkzeug-Schema", "Plugin_Schema_abgelehnt")):
        if needle in error:
            category = label
            break
    diagnostic("job", status=status, cause=category,
               finish_reason="nicht_verfuegbar" if status != "completed" else "siehe_Antwort",
               tool_calls="nicht_verfuegbar" if status != "completed" else "siehe_Antwort")


def inspect_response(result):
    msg = result.get("message") if isinstance(result, dict) else None
    msg = msg if isinstance(msg, dict) else {}
    calls = msg.get("tool_calls", [])
    names, schemas = [], []
    if isinstance(calls, list):
        for call in calls[:16]:
            fn = call.get("function", {}) if isinstance(call, dict) else {}
            fn = fn if isinstance(fn, dict) else {}
            names.append(safe_enum(fn.get("name"), ("get_test_temperature",)))
            try:
                valid = json.loads(fn.get("arguments")) == {"room": "Testzimmer"}
            except (ValueError, TypeError):
                valid = False
            schemas.append(valid)
    diagnostic("response", finish_reason=safe_enum(result.get("finish_reason"),
               ("stop", "length", "tool_calls", "content_filter", "function_call")),
               tool_calls_count=len(calls) if isinstance(calls, list) else "ungueltig",
               tool_names=names, argument_schema=schemas or "nicht_anwendbar")
    return result


def check(condition, message):
    if not condition:
        diagnostic("assertion_failed", reason=message)
        raise RuntimeError(message)


def exercise(complete):
    original_complete = complete
    def complete(payload):
        return inspect_response(original_complete(payload))
    messages = [{"role": "user", "content":
        "Wie warm ist es im Testzimmer? Benutze das angebotene Testwerkzeug."}]
    base = {"messages": messages, "tools": [TOOL], "temperature": 0,
            "max_tokens": 512, "parallel_tool_calls": False}
    for choice in ("required", {"type": "function", "function": {"name": "get_test_temperature"}}):
        STATE["phase"] = "Named" if isinstance(choice, dict) else "Required"
        result = complete(dict(base, tool_choice=choice))
        msg = result["message"]
        calls = msg.get("tool_calls") or []
        check(result["finish_reason"] == "tool_calls" and len(calls) == 1,
              "Kein einzelner verpflichtender Werkzeugaufruf")
        call = calls[0]
        check(call.get("type") == "function" and isinstance(call.get("id"), str) and bool(call["id"]),
              "Tool-ID oder Typ ungueltig")
        check(call["function"]["name"] == "get_test_temperature", "Falsches Werkzeug")
        check(json.loads(call["function"]["arguments"]) == {"room": "Testzimmer"}, "Falsche Argumente")
        # The ONLY tool result is this local fixture. No ioBroker request exists.
        followup = messages + [msg, {"role": "tool", "tool_call_id": call["id"],
            "content": json.dumps({"room": "Testzimmer", "temperature_celsius": 21.5})}]
        STATE["phase"] += "/Tool-Ergebnis"
        diagnostic("fixture_prepared", temperature_celsius=21.5,
                   matching_call_id=followup[-1]["tool_call_id"] == call["id"],
                   delivery="vor_HTTP_Anfrage; Empfang_im_Modell_noch_nicht_bewiesen")
        answer = complete({"messages": followup, "tool_choice": "none", "temperature": 0,
                           "max_tokens": 512, "parallel_tool_calls": False})
        text = answer["message"].get("content") or ""
        diagnostic("fixture_answer", contains_expected_temperature=("21.5" in text or "21,5" in text))
        check(answer["finish_reason"] == "stop" and not answer["message"].get("tool_calls"),
              "Folgeantwort unvollstaendig oder unerlaubter Aufruf")
        check("21.5" in text or "21,5" in text, "Simulierter Messwert fehlt in Antwort")
    for choice in ("none", "auto"):
        STATE["phase"] = choice.title()
        result = complete(dict(base, messages=[{"role": "user", "content":
            "Antworte nur mit Hallo. Kein Werkzeug ist dafuer erforderlich."}], tool_choice=choice))
        check(result["finish_reason"] == "stop" and not result["message"].get("tool_calls")
              and bool(result["message"].get("content")), "Normaler Chat mit " + choice + " fehlgeschlagen")
    STATE["phase"] = "Chat-ohne-Tools"
    plain = complete({"messages": [{"role": "user", "content": "Sage Hallo."}],
                      "temperature": 0, "max_tokens": 128})
    check(plain["finish_reason"] == "stop" and bool(plain["message"].get("content")), "Chat ohne Tools fehlgeschlagen")


def request(url, token, payload=None, context=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=context, timeout=180) as response:
            diagnostic("http", status=response.status)
            try:
                return json.load(response)
            except json.JSONDecodeError as exc:
                diagnostic("http_json_invalid", status=response.status,
                           line=exc.lineno, column=exc.colno, position=exc.pos)
                raise RuntimeError("API-Antwort enthaelt ungueltiges JSON") from None
    except urllib.error.HTTPError as exc:
        diagnostic("http_failed", status=exc.code,
                   cause="HTTP_Endpunkt; tiefere_Ursache_nicht_nachweisbar",
                   finish_reason="nicht_verfuegbar", tool_calls="nicht_verfuegbar")
        # Never print error bodies, request headers, tokens, or generated content.
        raise RuntimeError("Testanfrage fehlgeschlagen: HTTP " + str(exc.code)) from None
    except (OSError, urllib.error.URLError):
        diagnostic("transport_failed", status="keine_HTTP_Antwort")
        raise RuntimeError("Testendpunkt nicht erreichbar") from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-url", default="http://127.0.0.1:8766")
    parser.add_argument("--backend", choices=("cpu", "cuda"), required=True)
    parser.add_argument("--api-url", help="Optional: HTTPS-Basis inklusive /v1 fuer zusaetzlichen API-Test")
    parser.add_argument("--ca-file", help="Vertrauenswuerdiges Zertifikat fuer HTTPS")
    parser.add_argument("--node-no-auth", action="store_true",
                        help="Nur fuer den isolierten gemeinsamen Nulltest mit explizit deaktivierter Node-Authentifizierung")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--nulltest-config-stdin", action="store_true",
                        help="Interner gemeinsamer Nulltest: API-Key und isolierte HTTPS-Adresse ueber stdin")
    parser.add_argument("--direct-llama", action="store_true",
                        help="Nur Diagnose gegen bereits laufenden llama-server auf 127.0.0.1:8767; kein Backend-Nachweis")
    args = parser.parse_args()
    if args.direct_llama:
        check(not args.api_url and not args.nulltest_config_stdin,
              "Direkte llama-Diagnose separat von Node/HTTPS ausfuehren")
        check(1 <= args.repetitions <= 20, "Wiederholungen muessen 1..20 sein")
        STATE.update(transport="llama-direkt", phase="Diagnose")
        def llama_complete(payload):
            body = dict(payload, stream=False, chat_template_kwargs={"enable_thinking": False})
            choice = body.get("tool_choice")
            if isinstance(choice, dict):
                body["tools"] = [t for t in body.get("tools", [])
                                 if t["function"]["name"] == choice["function"]["name"]]
                body["tool_choice"] = "required"
            diagnostic("llama_request", tool_definition_count=len(body.get("tools", [])),
                       native_tool_choice=safe_enum(body.get("tool_choice"), ("required", "none", "auto")))
            return request("http://127.0.0.1:8767/v1/chat/completions", "", body)["choices"][0]
        for iteration in range(args.repetitions):
            STATE["iteration"] = iteration + 1
            exercise(llama_complete)
        print("DIAGNOSE bestanden: llama direkt; Plugin/Web-Bridge umgangen, Backend NICHT verifiziert.")
        return 0
    isolated = None
    if args.nulltest_config_stdin:
        check(args.node_no_auth and not args.api_url and not args.ca_file,
              "Isolierte Konfiguration darf nicht mit manueller HTTPS-Konfiguration kombiniert werden")
        # Never log stdin content: it contains the isolated API key.
        raw_config = sys.stdin.buffer.read().decode("utf-8-sig")
        diagnostic("config_stdin", has_input=bool(raw_config.strip()),
                   input_chars=len(raw_config))
        try:
            isolated = json.loads(raw_config)
        except json.JSONDecodeError as exc:
            diagnostic("config_json_invalid", line=exc.lineno, column=exc.colno,
                       position=exc.pos, reason="ungueltiges_JSON_auf_stdin")
            raise RuntimeError("Isolierte JSON-Konfiguration auf stdin ungueltig") from None
        check(isinstance(isolated, dict), "Isolierte Konfiguration muss ein JSON-Objekt sein")
        check(isinstance(isolated.get("api_url"), str), "API-URL in Konfiguration fehlt")
        check(isinstance(isolated.get("api_key"), str), "API-Schluessel in Konfiguration fehlt")
        diagnostic("config_json_valid", has_api_url=bool(isolated["api_url"]),
                   has_api_key=bool(isolated["api_key"]))
        args.api_url = isolated["api_url"]
        endpoint = urllib.parse.urlsplit(args.api_url)
        address = ipaddress.ip_address(endpoint.hostname)
        check(address.version == 4 and address.is_private and not address.is_loopback
              and endpoint.port == 8769 and endpoint.path == "/v1",
              "Isolierter HTTPS-Test erfordert private LAN-IPv4:8769/v1")
    node = urllib.parse.urlsplit(args.node_url)
    check(node.scheme == "http" and node.hostname in ("127.0.0.1", "localhost", "::1")
          and not node.username and not node.password and not node.query and not node.fragment
          and node.path in ("", "/"), "Node muss eine lokale HTTP-Adresse sein")
    check(1 <= args.repetitions <= 20, "Wiederholungen muessen 1..20 sein")
    token = "" if args.node_no_auth else getpass.getpass("Compute-Node-Token (verborgen): ").strip()
    check(args.node_no_auth or bool(token), "Node-Token fehlt")
    def node_complete(payload):
        created = request(args.node_url.rstrip("/") + "/jobs", token,
                          {"job_type": "chat", "payload": payload, "execution": {}})
        job_id = created.get("id") or created.get("job_id")
        check(bool(job_id), "Job-ID fehlt")
        final = request(args.node_url.rstrip("/") + "/jobs/" + urllib.parse.quote(str(job_id), safe="") + "/execute", token, {})
        job_diagnostic(final)
        check(final.get("status") == "completed", "KI-Job fehlgeschlagen")
        result = final.get("result") or {}
        check(result.get("worker_id") == "mediahub.interaktions_ki.worker", "Falscher Worker")
        output = result.get("output") or {}
        check(output.get("backend_verified") is True and output.get("backend_used") == args.backend,
              "Angefordertes Backend nicht technisch bestaetigt")
        check(bool(output.get("evidence")), "Technischer Backend-Nachweis fehlt")
        return {"message": output["message"], "finish_reason": output["finish_reason"]}
    STATE["transport"] = "Node-direkt"
    for iteration in range(args.repetitions):
        STATE["iteration"] = iteration + 1
        exercise(node_complete)
    print("PASS: Node-Werkzeugrunde, Required/Named/None/Auto, Chat und Backend " + args.backend)
    if args.api_url:
        STATE.update(transport="HTTPS", phase="Konfiguration")
        api = urllib.parse.urlsplit(args.api_url)
        check(api.scheme == "https" and api.hostname and not api.username and not api.password
              and not api.query and not api.fragment, "API muss HTTPS ohne Zugangsdaten in URL sein")
        # Preserve v1.0.25's isolated self-signed TLS policy, scoped to this context.
        # Manual HTTPS probes continue to verify the certificate.
        context = ssl._create_unverified_context() if isolated else ssl.create_default_context(cafile=args.ca_file)
        key = isolated["api_key"] if isolated else getpass.getpass("Externer API-Schluessel (verborgen): ").strip()
        check(bool(key), "API-Schluessel fehlt")
        def api_complete(payload):
            body = dict(payload, model="mediahub-interaktions-ki", stream=False)
            return request(args.api_url.rstrip("/") + "/chat/completions", key, body, context)["choices"][0]
        for iteration in range(args.repetitions):
            STATE["iteration"] = iteration + 1
            exercise(api_complete)
        # Confirm the owned backend again after the HTTPS round.
        STATE.update(transport="Node-direkt", phase="Backend-nach-HTTPS")
        node_complete({"prompt": "Sage Hallo.", "max_tokens": 128})
        print("PASS: HTTPS-Werkzeugrunde und anschliessender Backend-Nachweis")
    else:
        print("OFFEN: HTTPS-Test (erneut mit --api-url und gegebenenfalls --ca-file ausfuehren)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, TypeError, IndexError, OSError) as exc:
        diagnostic("failed", exception_type=type(exc).__name__, cause="siehe_letzte_DIAG; bei_Strukturfehler_Testskript_oder_API_Vertrag")
        print("FAIL: Werkzeugtest nicht bestanden. Keine Zugangsdaten oder Antwortinhalte protokolliert.")
        raise SystemExit(1)
