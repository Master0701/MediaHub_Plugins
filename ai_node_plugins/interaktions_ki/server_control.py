"""Explicitly confirmed, foreground llama.cpp server controller.

No downloads, installs or persistent configuration changes. The child process
ends when the foreground controller is interrupted.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .runtime_manager import plan_launch
except ImportError:
    from runtime_manager import plan_launch


def server_health(port: int, timeout: float = 1.0) -> dict:
    """Read-only localhost health check; does not start or change anything."""
    request = urllib.request.Request(f"http://127.0.0.1:{port}/health")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(65536)
            return {"reachable": True, "http_status": response.status,
                    "body": data.decode("utf-8", errors="replace")}
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return {"reachable": False, "error": str(exc)}


def launch_foreground(plan: dict, *, confirmed: bool = False,
                      popen=subprocess.Popen, health=server_health,
                      startup_seconds: float = 30, log_path: str | None = None) -> dict:
    """Run only an approved local plan; never silently replace another server."""
    if not confirmed:
        raise PermissionError("Start abgelehnt: --confirm-start erforderlich")
    if not plan.get("requires_manual_confirmation") or plan.get("approved"):
        raise ValueError("Ungueltiger oder bereits modifizierter Startplan")
    args = plan.get("command")
    if not isinstance(args, list) or not args or not all(isinstance(x, str) for x in args):
        raise ValueError("Startplan enthaelt keine gueltigen Argumente")
    if "--port" not in args:
        raise ValueError("Port fehlt")
    port = int(args[args.index("--port") + 1])
    if health(port).get("reachable"):
        raise RuntimeError(f"Port {port} wird bereits von einem Server verwendet")
    log_handle = None
    if log_path:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_file.open("wb")
    try:
        proc = popen(args, stdin=subprocess.DEVNULL,
                     stdout=log_handle if log_handle else subprocess.DEVNULL,
                     stderr=subprocess.STDOUT if log_handle else subprocess.DEVNULL)
    finally:
        if log_handle is not None:
            log_handle.close()
    try:
        deadline = time.monotonic() + startup_seconds
        while time.monotonic() < deadline:
            code = proc.poll()
            if code is not None:
                raise RuntimeError(f"llama-server beendet (Exit-Code {code})")
            status = health(port)
            if status.get("reachable"):
                return {"started": True, "pid": proc.pid, "port": port,
                        "process": proc, "health": status}
            time.sleep(0.25)
        raise TimeoutError("llama-server innerhalb des Startlimits nicht erreichbar")
    except BaseException:
        stop_process(proc)
        raise


def stop_process(proc, *, timeout: float = 5.0) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MediaHub Offline-LLM llama.cpp Start")
    parser.add_argument("--binary", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--mode", choices=["auto", "cpu", "gpu"], default="cpu")
    parser.add_argument("--device", action="append", default=[])
    parser.add_argument("--tensor-split", default="")
    parser.add_argument("--gpu-layers", type=int, default=0)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--confirm-start", action="store_true")
    options = parser.parse_args(argv)
    split = [float(x) for x in options.tensor_split.split(",")] if options.tensor_split else None
    plan = plan_launch(binary_path=options.binary, model_path=options.model,
                       mode=options.mode, devices=options.device or None,
                       gpu_layers=options.gpu_layers, cpu_threads=options.threads,
                       port=options.port, tensor_split=split)
    print(json.dumps({k: v for k, v in plan.items() if k != "command"} | {"command": plan["command"]}, indent=2))
    if not options.confirm_start:
        print("NUR VORSCHAU. Zum Starten --confirm-start angeben.")
        return 0
    result = launch_foreground(plan, confirmed=True)
    proc = result["process"]
    print(f"llama-server PID {result['pid']} auf 127.0.0.1:{result['port']}. Ctrl+C zum Beenden.")
    try:
        return proc.wait()
    except KeyboardInterrupt:
        stop_process(proc)
        print("llama-server beendet")
        return 0


if __name__ == "__main__":
    sys.exit(main())
