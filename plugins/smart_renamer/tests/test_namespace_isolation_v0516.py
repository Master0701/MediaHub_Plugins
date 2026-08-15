from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def _run(code):
    completed=subprocess.run(
        [sys.executable,"-c",code],
        cwd=ROOT,text=True,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,
    )
    assert completed.returncode==0,completed.stdout+completed.stderr
    return completed.stdout

def test_foreign_services_does_not_break_plugin_load():
    assert "OK" in _run(r"""
import importlib.util,sys,types
from pathlib import Path
root=Path.cwd()
foreign=types.ModuleType("services")
foreign.__path__=[]
foreign.owner="ai-assistant"
sys.modules["services"]=foreign
spec=importlib.util.spec_from_file_location("sr_plugin_test",root/"plugin.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert hasattr(module,"MediaHubSmartRenamerPlugin")
assert sys.modules["services"].owner=="ai-assistant"
from mediahub_smart_renamer_runtime.services.naming_profiles import NamingProfileService
assert NamingProfileService
print("OK")
""")

def test_backend_can_load_before_plugin():
    assert "OK" in _run(r"""
from mediahub_smart_renamer_runtime.backends.native import NativeRenamerBackend
assert NativeRenamerBackend
print("OK")
""")

def test_runtime_has_no_global_services_or_backends_imports():
    bad=[]
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        for n,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            s=line.strip()
            if (
                s.startswith("from services") or s.startswith("import services")
                or s.startswith("from backends") or s.startswith("import backends")
            ):
                bad.append((str(path.relative_to(ROOT)),n,s))
    assert bad==[]

def test_unique_namespace_resolves_core_modules():
    assert "OK" in _run(r"""
from mediahub_smart_renamer_runtime.services.naming_profiles import NamingProfileService
from mediahub_smart_renamer_runtime.services.rule_engine import RenameRuleEngine
from mediahub_smart_renamer_runtime.backends.native import NativeRenamerBackend
assert NamingProfileService and RenameRuleEngine and NativeRenamerBackend
print("OK")
""")
