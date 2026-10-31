"""Opt-in download of the pinned MediaHub Tools CPython release asset."""
from __future__ import annotations

import json
import tempfile
import urllib.request
from pathlib import Path

REPO = 'Master0701/MediaHub_Tools'
MANIFEST_URL = f'https://raw.githubusercontent.com/{REPO}/main/packages/python/current/manifest.json'
EXPECTED_VERSION = '3.12.10'
EXPECTED_PACKAGE = 'MediaHub-Python-3.12.10-x64.zip'
EXPECTED_SHA256 = 'e1f891ef60245148ab41593d7600a5430b6549a450d67329702bd700926902f8'
EXPECTED_SIZE = 43260658
RELEASE_TAG = 'mediahub-tools'
MAX_BYTES = 100 * 1024 * 1024


def _fetch(url: str, max_bytes: int) -> bytes:
    request = urllib.request.Request(url, headers={'User-Agent': 'MediaHub-PythonRuntime/0.1.3'})
    with urllib.request.urlopen(request, timeout=60) as response:
        if response.geturl().split('/')[0] not in ('https:',):
            raise ValueError('Download muss HTTPS verwenden.')
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError('Download ueberschreitet die erlaubte Groesse.')
    return data


def download_and_install(*, confirmed: bool = False, target: Path | None = None) -> dict:
    """Download and install only with explicit consent; never replace an existing runtime."""
    if not confirmed:
        raise PermissionError('Download und Installation erfordern ausdrueckliche Bestaetigung.')

    import importlib.util
    plugin_path = Path(__file__).with_name('plugin.py')
    spec = importlib.util.spec_from_file_location('mediahub_python_runtime_for_download', plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Plugin-Modul fehlt.')
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)
    destination = Path(target) if target is not None else plugin.runtime_root()
    if destination.exists() or destination.is_symlink():
        existing = plugin.inspect_runtime(destination)
        if existing.get('ready'):
            return {'already_installed': True, **existing}
        raise FileExistsError(f'Ziel ist vorhanden, aber nicht bereit: {destination}')

    manifest = json.loads(_fetch(MANIFEST_URL, 64 * 1024).decode('utf-8-sig'))
    required = {
        'tool': 'python-runtime', 'python_version': EXPECTED_VERSION,
        'package': EXPECTED_PACKAGE, 'sha256': EXPECTED_SHA256,
        'size': EXPECTED_SIZE, 'release_tag': RELEASE_TAG,
        'platform': 'windows', 'architecture': 'x64',
    }
    for key, expected in required.items():
        value = manifest.get(key)
        if key == 'sha256':
            value = str(value).lower()
        if value != expected:
            raise ValueError(f'Tools-Manifest unerwartet: {key}={value!r}')
    if 'windows_compute' not in manifest.get('targets', []):
        raise ValueError('Tools-Paket ist nicht fuer Windows Compute freigegeben.')

    url = f'https://github.com/{REPO}/releases/download/{RELEASE_TAG}/{EXPECTED_PACKAGE}'
    data = _fetch(url, MAX_BYTES)
    if len(data) != EXPECTED_SIZE:
        raise ValueError('Python-Archivgroesse stimmt nicht mit Manifest ueberein.')
    # Temporary archive is never written into the plugin or existing runtime.
    with tempfile.TemporaryDirectory(prefix='mediahub-python-download-') as folder:
        archive = Path(folder) / EXPECTED_PACKAGE
        archive.write_bytes(data)
        result = plugin.install_local_archive(
            archive, EXPECTED_SHA256, confirmed=True, target=destination
        )
    return {'source': url, 'manifest': MANIFEST_URL, **result}
