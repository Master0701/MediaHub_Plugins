import importlib.util
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('llm_runtime_manager',Path(__file__).resolve().parents[1]/'runtime_manager.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class RuntimePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.binary=root/'llama-server.exe'
        self.model=root/'model.gguf'
        self.binary.write_bytes(b'test')
        self.model.write_bytes(b'GGUFtest')
    def plan(self,**kw):
        return mod.plan_launch(binary_path=str(self.binary),model_path=str(self.model),**kw)
    def test_cpu(self):
        result=self.plan(mode='cpu')
        self.assertFalse(result['approved'])
        self.assertEqual(result['command'][0],str(self.binary))
    def test_two_gpu(self):
        result=self.plan(mode='gpu',gpu_layers=32,devices=['CUDA0','CUDA1'],tensor_split=[1,2])
        self.assertEqual(result['gpu_count'],2)
        self.assertIn('--tensor-split',result['command'])
    def test_cpu_rejects_gpu(self):
        with self.assertRaises(mod.RuntimeConfigurationError):self.plan(mode='cpu',gpu_layers=10)
    def test_missing_model(self):
        self.model.unlink()
        with self.assertRaises(mod.RuntimeConfigurationError):self.plan()
    def test_invalid_device(self):
        with self.assertRaises(mod.RuntimeConfigurationError):self.plan(mode='gpu',gpu_layers=5,devices=['CUDA0; rm -rf'])
    def test_invalid_port(self):
        with self.assertRaises(mod.RuntimeConfigurationError):self.plan(port=80)

if __name__=='__main__':unittest.main()
