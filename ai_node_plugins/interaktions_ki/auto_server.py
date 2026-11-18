"""Opt-in, local-only llama-server lifecycle for the Windows Compute Node."""
from __future__ import annotations

import atexit
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlsplit

try:
    from .runtime_manager import plan_launch
    from .server_control import server_health, launch_foreground, stop_process
except ImportError:
    from runtime_manager import plan_launch
    from server_control import server_health, launch_foreground, stop_process

_lock = threading.Lock()
_owned_process = None
_owned_mode = None
_owned_log = None


def _installed_runtime() -> Path:
    # .../runtime/plugins/mediahub.interaktions_ki/auto_server.py
    return Path(__file__).resolve().parents[2]


def _paths(mode: str) -> tuple[Path, Path]:
    root = Path(os.environ.get('MEDIAHUB_COMPUTE_RUNTIME') or _installed_runtime())
    base = root / 'plugin_runtimes' / 'interaktions_ki'
    binary = base / ('llama_cuda' if mode == 'cuda' else 'llama_cpu') / 'llama-server.exe'
    model = base / 'models' / 'qwen3_1_7b_q8_0' / 'Qwen3-1.7B-Q8_0.gguf'
    return binary, model


def ensure_running(endpoint: str) -> None:
    """Only start with explicit opt-in; never start for LAN/remote endpoints."""
    if os.environ.get('MEDIAHUB_LLAMA_AUTOSTART') != '1':
        return
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1') or not parsed.port:
        raise RuntimeError('Autostart ist ausschliesslich fuer lokalen Loopback erlaubt')
    global _owned_process, _owned_mode, _owned_log
    with _lock:
        if server_health(parsed.port).get('reachable'):
            return
        if _owned_process is not None and _owned_process.poll() is None:
            raise RuntimeError('Eigener llama-server laeuft, antwortet aber nicht')
        mode = os.environ.get('MEDIAHUB_LLAMA_MODE', 'cuda').lower()
        if mode not in ('cpu', 'cuda'):
            raise ValueError('MEDIAHUB_LLAMA_MODE muss cpu oder cuda sein')
        binary, model = _paths(mode)
        plan = plan_launch(binary_path=str(binary), model_path=str(model),
                           mode='gpu' if mode == 'cuda' else 'cpu',
                           gpu_layers=99 if mode == 'cuda' else 0,
                           cpu_threads=4, port=parsed.port)
        # Neuere llama.cpp-Builds zeigen GPU-Offload nicht immer mit Log-Level 3.
        # Debug-Log-Level nur fuer CUDA aktivieren, um echte Offload-Meldungen zu erhalten.
        if mode == 'cuda':
            plan['command'] = [*plan['command'], '-lv', '4']
        log_path = str(_installed_runtime() / 'logs' / ('llama-' + mode + '.log'))
        result = launch_foreground(plan, confirmed=True, startup_seconds=120, log_path=log_path)
        _owned_process = result['process']
        _owned_mode = mode
        _owned_log = log_path


def backend_evidence(endpoint: str) -> dict:
    """Report only verified execution; never infer CUDA from the request."""
    parsed = urlsplit(endpoint)
    with _lock:
        if (_owned_process is None or _owned_process.poll() is not None
                or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')):
            return {'backend_used': None, 'backend_verified': False,
                    'reason': 'external_or_unowned_server'}
        mode, path, pid = _owned_mode, _owned_log, _owned_process.pid
    if mode == 'cpu':
        return {'backend_used': 'cpu', 'backend_verified': True,
                'evidence': 'owned_llama_process_cpu_mode_gpu_layers_0'}
    if mode != 'cuda' or not path:
        return {'backend_used': None, 'backend_verified': False,
                'reason': 'unknown_launch_mode'}
    try:
        with Path(path).open('rb') as log_file:
            head = log_file.read(262144)
            log_file.seek(0, 2)
            end = log_file.tell()
            log_file.seek(max(0, end - 131072))
            tail = log_file.read(131072)
        content = (head + b'\n' + tail).decode('utf-8', errors='replace')
    except OSError:
        content = ''
    # Nur tatsaechlich ausgelagerte GPU-Schichten zaehlen, niemals die
    # angeforderte Einstellung --n-gpu-layers 99 oder die Chat-Geschwindigkeit.
    patterns = (
        r'offloaded\s+(\d+)\s*/\s*(\d+)\s+layers\s+to\s+GPU',
        r'offloaded\s+(\d+)\s+layers\s+to\s+GPU',
        r'offloading\s+(\d+)\s+repeating\s+layers\s+to\s+GPU',
    )
    for pattern in patterns:
        match = re.search(pattern, content, re.I)
        if match and int(match.group(1)) > 0:
            return {'backend_used': 'cuda', 'backend_verified': True,
                    'gpu_layers_offloaded': int(match.group(1)),
                    'evidence': 'llama_cpp_startup_log_offloaded_layers'}

    # Fallback: nvidia-smi belegt die Nutzung nur, wenn GENAU der von diesem
    # Worker gestartete PID als CUDA-Compute-Prozess mit >0 MiB erscheint.
    # Bei WDDM/N/A oder fehlendem nvidia-smi bewusst NICHT als PASS werten.
    executable = shutil.which('nvidia-smi')
    if executable:
        try:
            completed = subprocess.run(
                [executable, '--query-compute-apps=pid,used_gpu_memory',
                 '--format=csv,noheader,nounits'],
                capture_output=True, text=True, timeout=8, check=False,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            if completed.returncode == 0:
                for line in completed.stdout.splitlines():
                    fields = [field.strip() for field in line.split(',')]
                    if len(fields) < 2 or fields[0] != str(pid):
                        continue
                    memory = re.search(r'^\d+', fields[1])
                    if memory and int(memory.group()) > 0:
                        return {'backend_used': 'cuda', 'backend_verified': True,
                                'gpu_memory_mib': int(memory.group()),
                                'evidence': 'nvidia_smi_owned_process_gpu_memory'}
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {'backend_used': None, 'backend_verified': False,
            'reason': 'cuda_offload_not_confirmed_in_llama_log_or_nvidia_smi'}


def stop_owned() -> None:
    global _owned_process, _owned_mode, _owned_log
    with _lock:
        if _owned_process is not None:
            stop_process(_owned_process)
            _owned_process = None
            _owned_mode = None
            _owned_log = None


atexit.register(stop_owned)
