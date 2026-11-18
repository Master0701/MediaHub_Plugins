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

    def handler(self, lan_host=None, lan_password=None, lan_credentials=None):
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
                if lan_password is not None or lan_credentials is not None:
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
