import importlib.util
import sys
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

# Minimal PySide6 stubs for read-only capability tests.
qt=types.ModuleType("PySide6")
qtcore=types.ModuleType("PySide6.QtCore")
qtgui=types.ModuleType("PySide6.QtGui")
qtwidgets=types.ModuleType("PySide6.QtWidgets")
class QUrl:
    @staticmethod
    def fromLocalFile(value): return value
class QDesktopServices:
    @staticmethod
    def openUrl(value): return False
class QImageReader:
    def __init__(self,*a,**k): pass
class QListWidgetItem: pass
class QWidget: pass
qtcore.QUrl=QUrl
qtgui.QDesktopServices=QDesktopServices
qtgui.QImageReader=QImageReader
qtwidgets.QListWidgetItem=QListWidgetItem
qtwidgets.QWidget=QWidget
sys.modules.setdefault("PySide6",qt)
sys.modules["PySide6.QtCore"]=qtcore
sys.modules["PySide6.QtGui"]=qtgui
sys.modules["PySide6.QtWidgets"]=qtwidgets

# Avoid starting real Qt/web dependencies during import.
web=types.ModuleType("mediahub_web_core")
server=types.ModuleType("mediahub_web_core.server")
settings=types.ModuleType("mediahub_web_core.settings")
class DummyServer:
    def add_route(self,*a,**k): pass
    def add_post_route(self,*a,**k): pass
    def start(self): pass
server.acquire_shared_server=lambda *a,**k: DummyServer()
server.release_shared_server=lambda *a,**k: None
class Store:
    def __init__(self,*a,**k): pass
    def load(self): return types.SimpleNamespace(host="127.0.0.1",port=8765)
settings.WebRuntimeSettingsStore=Store
settings.connection_info=lambda s: {"active_url":"http://127.0.0.1:8765"}
sys.modules.setdefault("mediahub_web_core",web)
sys.modules["mediahub_web_core.server"]=server
sys.modules["mediahub_web_core.settings"]=settings

spec=importlib.util.spec_from_file_location("metadata_plugin_test",ROOT/"plugin.py")
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
Plugin=module.MediaHubMetadataEditorPlugin

def build(tmp_path):
    obj=Plugin.__new__(Plugin)
    obj.plugin_path=ROOT; obj.base_dir=tmp_path
    return obj

def test_read_and_review_capabilities_are_exposed(tmp_path):
    obj=build(tmp_path)
    caps=obj.get_runtime_capabilities()
    assert set(caps)=={"metadata.read","metadata.review"}
    assert "metadata.write" not in caps
    assert obj.get_capability_contracts()["metadata.write"]["available"] is False

def test_nfo_can_be_used_as_read_only_metadata_source(tmp_path):
    movie=tmp_path/"Movie.mkv"; movie.write_bytes(b"x")
    movie.with_suffix(".nfo").write_text("<movie><title>Movie</title><year>2024</year></movie>",encoding="utf-8")
    obj=build(tmp_path)
    result=obj.read_metadata({"path":str(movie)})
    assert result["metadata"]["title"]=="Movie"
    assert result["metadata"]["year"] == 2024
    assert result["execution_allowed"] is False

def test_review_only_proposes_metadata_changes(tmp_path):
    movie=tmp_path/"Old.mkv"; movie.write_bytes(b"x")
    obj=build(tmp_path)
    result=obj.review_metadata({"path":str(movie),"detected":{"title":"New","year":"2025"}})
    assert result["change_count"]>=1
    assert result["automatic_apply_allowed"] is False
