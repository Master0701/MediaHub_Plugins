"""Persistent, isolated SmolVLM2 worker with idle-time cleanup."""
from __future__ import annotations

import atexit
import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any


class SmolVLM2RuntimeBridgeError(RuntimeError):
    pass


_IDLE_SECONDS = 180
_LOCK = threading.RLock()
_PROCESS: subprocess.Popen | None = None
_PROCESS_KEY: tuple[str, str] | None = None
_RESPONSES: queue.Queue | None = None
_IDLE_TIMER: threading.Timer | None = None


def _stop_locked() -> None:
    global _PROCESS, _PROCESS_KEY, _RESPONSES, _IDLE_TIMER
    if _IDLE_TIMER is not None:
        _IDLE_TIMER.cancel()
        _IDLE_TIMER = None
    proc = _PROCESS
    _PROCESS = None
    _PROCESS_KEY = None
    _RESPONSES = None
    if proc is not None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        for stream in (proc.stdin, proc.stdout):
            if stream is not None:
                stream.close()


def _stop() -> None:
    with _LOCK:
        _stop_locked()


atexit.register(_stop)


def _read_responses(proc: subprocess.Popen, responses: queue.Queue) -> None:
    try:
        for line in proc.stdout:
            responses.put(line)
    finally:
        responses.put(None)


def _ensure_process(runtime_python: Path, runner_path: Path) -> tuple[subprocess.Popen, queue.Queue]:
    global _PROCESS, _PROCESS_KEY, _RESPONSES
    key = (str(runtime_python.resolve()), str(runner_path.resolve()))
    if _PROCESS is not None and (_PROCESS.poll() is not None or _PROCESS_KEY != key):
        _stop_locked()
    if _PROCESS is None:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(
            [str(runtime_python), str(runner_path), "--persistent"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
            bufsize=1, creationflags=flags,
        )
        responses = queue.Queue()
        threading.Thread(target=_read_responses, args=(proc, responses), daemon=True).start()
        _PROCESS, _PROCESS_KEY, _RESPONSES = proc, key, responses
    return _PROCESS, _RESPONSES


def _expire_idle(proc: subprocess.Popen) -> None:
    with _LOCK:
        if _PROCESS is proc:
            _stop_locked()


def run_analysis(
    *, runtime_python: str | Path, runner_path: str | Path,
    job_type: str, input_path: str | Path,
    execution: dict[str, Any], options: dict[str, Any] | None = None,
    timeout: int = 3600,
) -> dict[str, Any]:
    global _IDLE_TIMER
    runtime_python, runner_path = Path(runtime_python), Path(runner_path)
    if not runtime_python.is_file():
        raise SmolVLM2RuntimeBridgeError(f"Runtime-Python nicht gefunden: {runtime_python}")
    if not runner_path.is_file():
        raise SmolVLM2RuntimeBridgeError(f"Runtime-Runner nicht gefunden: {runner_path}")
    request = {
        "job_type": str(job_type), "input_path": str(input_path),
        "execution": dict(execution), "options": dict(options or {}),
    }
    with _LOCK:
        if _IDLE_TIMER is not None:
            _IDLE_TIMER.cancel()
            _IDLE_TIMER = None
        try:
            proc, responses = _ensure_process(runtime_python, runner_path)
            proc.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            proc.stdin.flush()
            try:
                line = responses.get(timeout=timeout)
            except queue.Empty as exc:
                raise SmolVLM2RuntimeBridgeError("SmolVLM2-Analyse: Zeitlimit ueberschritten.") from exc
            if line is None:
                raise SmolVLM2RuntimeBridgeError("SmolVLM2-Worker unerwartet beendet.")
            response = json.loads(line)
            if not isinstance(response, dict):
                raise ValueError("Runtime-Antwort ist kein Objekt")
            if not response.get("ok"):
                error = response.get("error") or {}
                raise SmolVLM2RuntimeBridgeError(
                    f"SmolVLM2-Runtime-Fehler: {error.get('type', 'Error')}: {error.get('message', '')}"
                )
            result = response.get("result")
            if not isinstance(result, dict):
                raise SmolVLM2RuntimeBridgeError("SmolVLM2-Runtime lieferte kein Ergebnisobjekt.")
            return result
        except SmolVLM2RuntimeBridgeError as exc:
            # A model-level error is a valid response; keep the worker in that case.
            if "Runtime-Fehler:" not in str(exc):
                _stop_locked()
            raise
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            _stop_locked()
            raise SmolVLM2RuntimeBridgeError(f"SmolVLM2-Worker-Kommunikation: {exc}") from exc
        finally:
            if _PROCESS is not None and _PROCESS.poll() is None:
                _IDLE_TIMER = threading.Timer(_IDLE_SECONDS, _expire_idle, args=(_PROCESS,))
                _IDLE_TIMER.daemon = True
                _IDLE_TIMER.start()
