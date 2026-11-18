import hashlib
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class DualPreflightTests(unittest.TestCase):
    def test_valid_archives(self):
        m = load('safe_preflight', 'safe_install.py')
        with tempfile.TemporaryDirectory() as tmp:
            for model, member, data in ((False, 'bin/llama-server.exe', b'PE'), (True, 'qwen.gguf', b'GGUF'+b'0'*32)):
                p = Path(tmp) / ('model.zip' if model else 'runtime.zip')
                with zipfile.ZipFile(p, 'w') as z: z.writestr(member, data)
                sha = hashlib.sha256(p.read_bytes()).hexdigest()
                self.assertTrue(m.preflight_local_archive(archive_path=str(p), expected_sha256=sha, model=model)['valid'])
    def test_bad_runtime_prevents_model_install(self):
        adapter = load('adapter_preflight', 'node_install_adapter.py')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = root / 'runtime.zip'
            model = root / 'model.zip'
            with zipfile.ZipFile(runtime, 'w') as z: z.writestr('wrong.exe', b'bad')
            with zipfile.ZipFile(model, 'w') as z: z.writestr('model.gguf', b'GGUF'+b'0'*32)
            config = {'ARCHIVE': str(runtime), 'SHA256': hashlib.sha256(runtime.read_bytes()).hexdigest(),
                      'TARGET': str(root / 'runtime_installed'), 'MODEL_ARCHIVE': str(model),
                      'MODEL_SHA256': hashlib.sha256(model.read_bytes()).hexdigest(),
                      'MODEL_TARGET': str(root / 'model_installed')}
            original = {k: os.environ.get('MEDIAHUB_INTERAKTIONS_KI_'+k) for k in config}
            try:
                os.environ.update({'MEDIAHUB_INTERAKTIONS_KI_'+k:v for k,v in config.items()})
                with self.assertRaises(Exception):
                    adapter.prepare_runtime({'id':'mediahub.interaktions_ki'}, ROOT, approved=True)
                self.assertFalse((root/'model_installed').exists())
                self.assertFalse((root/'runtime_installed').exists())
            finally:
                for k,v in original.items():
                    key='MEDIAHUB_INTERAKTIONS_KI_'+k
                    if v is None: os.environ.pop(key,None)
                    else: os.environ[key]=v
