from pathlib import Path
import sys
import pytest

PLUGIN_ROOT=Path(__file__).resolve().parents[1]
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0,str(PLUGIN_ROOT))

@pytest.fixture(autouse=True)
def windows_native(monkeypatch):
    # Patch both import identities used by legacy tests and the isolated runtime.
    from backends.native import NativeRenamerBackend as LegacyNativeRenamerBackend
    from mediahub_smart_renamer_runtime.backends.native import (
        NativeRenamerBackend as RuntimeNativeRenamerBackend,
    )

    for backend_class in (LegacyNativeRenamerBackend, RuntimeNativeRenamerBackend):
        original=backend_class.probe

        def probe(self, _original=original):
            status=dict(_original(self))
            status["platform_compatible"]=True
            return status

        monkeypatch.setattr(backend_class,"probe",probe)
