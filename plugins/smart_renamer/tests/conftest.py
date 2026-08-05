from pathlib import Path
import sys
import pytest
PLUGIN_ROOT=Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path: sys.path.insert(0,str(PLUGIN_ROOT))
@pytest.fixture(autouse=True)
def windows_native(monkeypatch):
 from backends.native import NativeRenamerBackend
 original=NativeRenamerBackend.probe
 def probe(self):
  status=dict(original(self)); status["platform_compatible"]=True; return status
 monkeypatch.setattr(NativeRenamerBackend,"probe",probe)
