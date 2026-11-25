"""Local-only compatibility API for the original MediaHub KI chat page.

Run as a separate foreground process; does not change Compute Node or plugin runtime.
Requires an existing Compute Node API token via environment or CLI argument.
"""
import argparse
import base64
import hmac
import json
import os
import sqlite3
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Load beside this installed bridge: the service uses spec_from_file_location
# after the plugin loader has removed its temporary sys.path entry.
import importlib.util
_protocol_spec = importlib.util.spec_from_file_location(
    "mediahub_interaktions_ki_tool_protocol", Path(__file__).with_name("tool_protocol.py"))
tool_protocol = importlib.util.module_from_spec(_protocol_spec)
_protocol_spec.loader.exec_module(tool_protocol)

MAX_BODY = 128 * 1024

class Bridge:
    def __init__(self, page, db, node_url, token):
        self.page = Path(page).read_bytes()
        self.db = sqlite3.connect(str(db), check_same_thread=False)
        self.lock = threading.RLock()
        self.node_url = node_url.rstrip("/")
        self.token = token
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS chats(id TEXT PRIMARY KEY,title TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY,chat_id TEXT NOT NULL,
                    role TEXT NOT NULL,content TEXT NOT NULL);
            """)
            self.db.commit()

    def node(self, path, method="GET", data=None):
        headers = {"Authorization": "Bearer " + self.token}
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(self.node_url + path,
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.load(resp)

    def handler(self, lan_host=None, lan_password=None, lan_credentials=None, api_key=None):
        bridge = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                print("%s - %s" % (self.address_string(), fmt % args))
            def reply(self, code, value):
                raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            def do_GET(self): self.route("GET")
            def do_POST(self): self.route("POST")
            def do_PATCH(self): self.route("PATCH")
            def do_DELETE(self): self.route("DELETE")
            def route(self, method):
                host = self.headers.get("Host", "")
                valid_hosts = ("127.0.0.1:%d" % self.server.server_port,
                               "localhost:%d" % self.server.server_port)
                if lan_host:
                    valid_hosts = ("%s:%d" % (lan_host, self.server.server_port),)
                if host not in valid_hosts:
                    return self.reply(403, {"error": "Ungueltiger Host"})
                origin = self.headers.get("Origin")
                valid_origins = ("http://127.0.0.1:%d" % self.server.server_port,
                                 "http://localhost:%d" % self.server.server_port)
                if lan_host:
                    valid_origins = ("https://%s:%d" % (lan_host, self.server.server_port),)
                if origin and origin not in valid_origins:
                    return self.reply(403, {"error": "Ungueltiger Origin"})
                api_path = urllib.parse.urlsplit(self.path).path.startswith("/v1/")
                if api_path:
                    # API endpoints are LAN/HTTPS only; never expose on loopback HTTP.
                    if not lan_host:
                        return self.reply(404, {"error": "API nicht verfuegbar"})
                    if api_key is None or not api_key.enabled():
                        return self.reply(503, {"error": "Externe API deaktiviert"})
                    auth = self.headers.get("Authorization", "")
                    if not (auth.startswith("Bearer ") and api_key.verify(auth[7:])):
                        return self.reply(401, {"error": "Ungueltiger API-Schluessel"})
                elif lan_password is not None or lan_credentials is not None:
                    auth = self.headers.get("Authorization", "")
                    authorized = False
                    if auth.startswith("Basic "):
                        try:
                            decoded = base64.b64decode(auth[6:], validate=True).decode("utf-8")
                            username, separator, password = decoded.partition(":")
                            if separator:
                                if lan_credentials is not None:
                                    authorized = lan_credentials.verify(username, password)
                                elif lan_password is not None:
                                    authorized = hmac.compare_digest(username, "mediahub") and hmac.compare_digest(password, lan_password)
                        except (ValueError, UnicodeError):
                            authorized = False
                    if not authorized:
                        self.send_response(401)
                        self.send_header("WWW-Authenticate", 'Basic realm="MediaHub Interaktions-KI", charset="UTF-8"')
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return
                if method != "GET" and self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    return self.reply(415, {"error": "JSON erforderlich"})
                if self.path == "/" and method == "GET":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(bridge.page)))
                    self.end_headers()
                    return self.wfile.write(bridge.page)
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length < 0 or length > MAX_BODY:
                        return self.reply(413, {"error": "Nachricht zu gross"})
                    body = json.loads(self.rfile.read(length)) if length else {}
                    if not isinstance(body, dict):
                        return self.reply(400, {"error": "JSON-Objekt erforderlich"})
                    return self.dispatch(method, urllib.parse.urlsplit(self.path).path, body)
                except (ValueError, KeyError, sqlite3.Error) as e:
                    return self.reply(400, {"error": str(e)})
                except (urllib.error.URLError, TimeoutError, OSError) as e:
                    return self.reply(502, {"error": "Compute Node nicht erreichbar: " + str(e)})
            def dispatch(self, method, path, body):
                parts = [urllib.parse.unquote(x) for x in path.strip("/").split("/")]
                if path == "/v1/models" and method == "GET":
                    return self.reply(200, {"object": "list", "data": [{
                        "id": "mediahub-interaktions-ki", "object": "model", "created": 0,
                        "owned_by": "mediahub"}]})
                if path == "/v1/chat/completions" and method == "POST":
                    messages = body.get("messages")
                    if not isinstance(messages, list) or not messages or len(messages) > 40:
                        return self.reply(400, {"error": {"message": "messages muss 1 bis 40 Eintraege enthalten", "type": "invalid_request_error"}})
                    if body.get("model") != "mediahub-interaktions-ki":
                        return self.reply(400, {"error": {"message": "Unbekanntes Modell", "type": "invalid_request_error"}})
                    if body.get("stream", False) is not False:
                        return self.reply(400, {"error": {"message": "Streaming noch nicht unterstuetzt", "type": "invalid_request_error"}})
                    try:
                        mode, tools, definitions, choice, forced = tool_protocol.options(body)
                        clean = tool_protocol.messages(messages)
                    except ValueError as exc:
                        return self.reply(400, {"error": {"message": str(exc), "type": "invalid_request_error"}})
                    if mode == "json_compat":
                        # Explicit legacy protocol only; never retry native failures here.
                        converted = []
                        pending = {}
                        for item in clean:
                            if item.get("tool_calls"):
                                for call in item["tool_calls"]:
                                    fn = call["function"]
                                    pending[call["id"]] = fn["name"]
                                    converted.append({"role": "assistant", "content":
                                        "Tool-Aufruf: " + fn["name"] + " " + fn["arguments"]})
                            elif item["role"] == "tool":
                                converted.append({"role": "user", "content": "Ergebnis des Tools "
                                    + pending.pop(item["tool_call_id"]) + ": " + item["content"]})
                            else:
                                converted.append(item)
                        clean = converted
                    using_tools = bool(definitions) and choice != "none"
                    if using_tools and mode == "json_compat":
                        catalog = [{"name": name, "description": fn.get("description", ""),
                                    "parameters": fn.get("parameters", {"type": "object"})}
                                   for name, fn in definitions.items()]
                        instructions = (
                            "Du bist ein Assistent mit optionalen Werkzeugen. Entscheide anhand der "
                            "Benutzerfrage, ob ein Werkzeug wirklich gebraucht wird. Antworte mit GENAU "
                            "einem JSON-Objekt, ohne Markdown. Fuer einen Werkzeugaufruf: "
                            '{"action":"tool","name":"EXAKTER_NAME","arguments":{...}}. '
                            'Fuer eine direkte Antwort: {"action":"answer","content":"Antworttext"}. '
                            "Erfinde keine Werkzeuge oder Argumente. Fuehre niemals selbst Aktionen aus. "
                            "Werkzeugliste: " + json.dumps(catalog, ensure_ascii=False)
                        )
                        if forced:
                            instructions += " Du MUSST das Werkzeug " + json.dumps(forced) + " waehlen."
                        elif choice == "required":
                            instructions += " Du MUSST eines der angebotenen Werkzeuge waehlen."
                        if clean[0]["role"] == "system":
                            clean[0]["content"] = instructions + "\n\n" + clean[0]["content"]
                        else:
                            clean.insert(0, {"role": "system", "content": instructions})
                    if len(clean) > 40:
                        return self.reply(400, {"error": {"message": "Zu viele Nachrichten nach JSON-Kompatibilitaetsumwandlung", "type": "invalid_request_error"}})
                    payload = {"messages": clean, "tool_calling_mode": mode}
                    if mode == "native":
                        payload.update(tools=tools, tool_choice=choice, parallel_tool_calls=False)
                    for field in ("max_tokens", "temperature"):
                        if field in body:
                            payload[field] = body[field]
                    created = bridge.node("/jobs", "POST", {"job_type": "chat", "payload": payload, "execution": {}})
                    job_id = created.get("id") or created.get("job_id")
                    if not job_id:
                        return self.reply(502, {"error": {"message": "Compute Node lieferte keine Job-ID", "type": "server_error"}})
                    finished = bridge.node("/jobs/" + urllib.parse.quote(str(job_id), safe="") + "/execute", "POST", {})
                    if finished.get("status") != "completed":
                        return self.reply(502, {"error": {"message": "KI-Auftrag fehlgeschlagen", "type": "server_error"}})
                    result = finished.get("result") or {}
                    if result.get("worker_id") != "mediahub.interaktions_ki.worker":
                        return self.reply(502, {"error": {"message": "Falscher KI-Worker", "type": "server_error"}})
                    output = result.get("output") or {}
                    if mode == "native":
                        try:
                            finish_reason = output.get("finish_reason")
                            message = tool_protocol.response(output.get("message"), finish_reason,
                                                             definitions, choice, forced)
                        except ValueError as exc:
                            return self.reply(502, {"error": {"message": str(exc), "type": "server_error"}})
                    else:
                        answer = output.get("text")
                        if not isinstance(answer, str) or not answer.strip():
                            return self.reply(502, {"error": {"message": "Keine KI-Antwort", "type": "server_error"}})
                        message = {"role": "assistant", "content": answer}
                        finish_reason = output.get("finish_reason", "stop")
                        if using_tools:
                            import re
                            candidate = answer.strip()
                            if candidate.startswith("```"):
                                candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate).strip()
                            try:
                                decision = tool_protocol.loads(candidate)
                            except (ValueError, TypeError):
                                decision = None
                            if isinstance(decision, dict) and decision.get("action") == "tool":
                                name = decision.get("name")
                                args = decision.get("arguments")
                                if not isinstance(name, str) or name not in definitions or not isinstance(args, dict) or (forced and name != forced):
                                    return self.reply(502, {"error": {"message": "KI lieferte ungueltigen Tool-Aufruf", "type": "server_error"}})
                                try:
                                    if finish_reason != "stop":
                                        raise ValueError("Unvollstaendige JSON-Werkzeugentscheidung")
                                    tool_protocol.validate(args, definitions[name].get("parameters", {"type": "object"}))
                                except ValueError as exc:
                                    return self.reply(502, {"error": {"message": str(exc), "type": "server_error"}})
                                message = {"role": "assistant", "content": None, "tool_calls": [{
                                    "id": "call_" + uuid.uuid4().hex, "type": "function",
                                    "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}
                                }]}
                                finish_reason = "tool_calls"
                            elif (forced or choice == "required"):
                                return self.reply(502, {"error": {"message": "KI hat keinen gueltigen verpflichtenden Tool-Aufruf erzeugt", "type": "server_error"}})
                            elif isinstance(decision, dict) and decision.get("action") == "answer" and isinstance(decision.get("content"), str):
                                message["content"] = decision["content"]
                            elif forced or choice == "required":
                                return self.reply(502, {"error": {"message": "KI hat keinen gueltigen verpflichtenden Tool-Aufruf erzeugt", "type": "server_error"}})
                            # For auto, a plain text answer is a valid direct response.
                    import time
                    return self.reply(200, {"id": "chatcmpl-" + uuid.uuid4().hex,
                        "object": "chat.completion", "created": int(time.time()),
                        "model": "mediahub-interaktions-ki",
                        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
                        "usage": output.get("usage") if isinstance(output.get("usage"), dict) else {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
                if path == "/api/external-api" and lan_host and api_key is not None:
                    if method == "GET":
                        return self.reply(200, {"model": "mediahub-interaktions-ki",
                            "base_url": "https://%s:%d/v1" % (lan_host, self.server.server_port),
                            "enabled": api_key.enabled()})
                    if method == "POST" and body.get("action") == "reveal":
                        return self.reply(200, {"api_key": api_key.get()})
                    if method == "POST" and body.get("action") == "rotate":
                        return self.reply(200, {"api_key": api_key.rotate(),
                            "message": "Alter API-Schluessel sofort ungueltig"})
                    if method == "POST" and body.get("action") == "enable" and type(body.get("enabled")) is bool:
                        return self.reply(200, {"enabled": api_key.set_enabled(body["enabled"])})
                    return self.reply(400, {"error": "Ungueltige Verwaltungsaktion"})
                if path == "/api/status" and method == "GET":
                    try:
                        health = bridge.node("/health")
                        return self.reply(200, {"llama_server_reachable": health.get("status") == "ok",
                            "node_status": health.get("status")})
                    except Exception:
                        return self.reply(200, {"llama_server_reachable": False})
                if parts == ["api", "chats"]:
                    if method == "GET":
                        with bridge.lock:
                            rows = bridge.db.execute("SELECT id,title FROM chats ORDER BY rowid DESC").fetchall()
                        return self.reply(200, {"chats": [{"id": a, "title": b} for a,b in rows]})
                    if method == "POST":
                        cid = uuid.uuid4().hex
                        title = str(body.get("title", "Neuer Chat"))[:100]
                        with bridge.lock:
                            bridge.db.execute("INSERT INTO chats VALUES(?,?)", (cid,title))
                            bridge.db.commit()
                        return self.reply(201, {"id":cid,"title":title})
                if len(parts) >= 3 and parts[:2] == ["api", "chats"]:
                    cid = parts[2]
                    with bridge.lock:
                        exists = bridge.db.execute("SELECT 1 FROM chats WHERE id=?", (cid,)).fetchone()
                    if not exists:
                        return self.reply(404, {"error":"Chat nicht gefunden"})
                    if len(parts) == 3:
                        if method == "PATCH":
                            title = str(body.get("title","")).strip()[:100]
                            if not title: return self.reply(400, {"error":"Titel fehlt"})
                            with bridge.lock:
                                bridge.db.execute("UPDATE chats SET title=? WHERE id=?", (title,cid))
                                bridge.db.commit()
                            return self.reply(200, {"id":cid,"title":title})
                        if method == "DELETE":
                            with bridge.lock:
                                bridge.db.execute("DELETE FROM messages WHERE chat_id=?", (cid,))
                                bridge.db.execute("DELETE FROM chats WHERE id=?", (cid,))
                                bridge.db.commit()
                            return self.reply(200, {"deleted":True})
                    if len(parts) == 4 and parts[3] == "attachments":
                        if method == "GET": return self.reply(200, {"attachments":[]})
                        return self.reply(501, {"error":"Dateianhaenge in dieser Stufe noch nicht angebunden"})
                    if len(parts) == 4 and parts[3] == "messages":
                        if method == "GET":
                            with bridge.lock:
                                rows = bridge.db.execute(
                                    "SELECT id,role,content FROM messages WHERE chat_id=? ORDER BY rowid", (cid,)).fetchall()
                            return self.reply(200, {"messages":[{"id":a,"role":b,"content":c,"attachments":[]} for a,b,c in rows]})
                        if method == "POST":
                            content = str(body.get("content","")).strip()
                            if not content or len(content)>50000:
                                return self.reply(400, {"error":"Nachricht fehlt oder ist zu lang"})
                            if body.get("attachment_ids"):
                                return self.reply(501, {"error":"Dateianhaenge noch nicht unterstuetzt"})
                            with bridge.lock:
                                history = bridge.db.execute(
                                    "SELECT role,content FROM messages WHERE chat_id=? ORDER BY rowid DESC LIMIT 39", (cid,)).fetchall()
                                bridge.db.execute("INSERT INTO messages VALUES(?,?,?,?)",
                                    (uuid.uuid4().hex,cid,"user",content))
                                bridge.db.commit()
                            generated = False
                            if body.get("generate", True):
                                messages = [{"role":r,"content":c} for r,c in reversed(history)]
                                messages.append({"role":"user","content":content})
                                created = bridge.node("/jobs","POST",{
                                    "job_type":"chat","payload":{"messages":messages},"execution":{}})
                                job_id = created.get("id") or created.get("job_id")
                                if not job_id: raise ValueError("Compute Node lieferte keine Job-ID")
                                finished = bridge.node("/jobs/"+urllib.parse.quote(str(job_id),safe="")+"/execute","POST",{})
                                if finished.get("status") != "completed":
                                    raise ValueError("KI-Auftrag fehlgeschlagen: "+str(finished.get("error")))
                                result = finished.get("result") or {}
                                output = result.get("output") or {}
                                if result.get("worker_id") != "mediahub.interaktions_ki.worker":
                                    raise ValueError("Falscher Worker: "+str(result.get("worker_id")))
                                answer = output.get("text")
                                if not isinstance(answer,str) or not answer.strip():
                                    raise ValueError("Keine KI-Antwort erhalten")
                                with bridge.lock:
                                    bridge.db.execute("INSERT INTO messages VALUES(?,?,?,?)",
                                        (uuid.uuid4().hex,cid,"assistant",answer))
                                    bridge.db.commit()
                                generated = True
                            return self.reply(200, {"generated":generated})
                return self.reply(404, {"error":"API-Endpunkt nicht vorhanden"})
        return Handler

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--web",required=True)
    p.add_argument("--node-url",default="http://127.0.0.1:8766")
    p.add_argument("--port",type=int,default=8768)
    p.add_argument("--db",default=str(Path.home()/".mediahub"/"interaktions_ki_chats.sqlite3"))
    args=p.parse_args()
    parsed=urllib.parse.urlsplit(args.node_url)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1","localhost") or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path:
        p.error("--node-url muss eine lokale HTTP-Adresse ohne Pfad sein")
    token=os.environ.get("MEDIAHUB_NODE_API_TOKEN","")
    if not token: p.error("MEDIAHUB_NODE_API_TOKEN fehlt; Token niemals in Webseite oder Skript speichern")
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    bridge=Bridge(args.web,args.db,args.node_url,token)
    server=ThreadingHTTPServer(("127.0.0.1",args.port),bridge.handler())
    print("Lokale Weboberflaeche: http://127.0.0.1:%d/" % args.port,flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=="__main__": main()
