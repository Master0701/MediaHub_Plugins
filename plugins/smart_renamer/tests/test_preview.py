from services.backend_registry import RenamerBackendRegistry
from services.preview_service import RenamePreviewService

def test_folder_expansion_and_preview(tmp_path):
 (tmp_path/"A.mkv").write_text("a")
 (tmp_path/"B.mkv").write_text("b")
 result=RenamePreviewService(RenamerBackendRegistry(tmp_path)).create_preview(items=[{"path":str(tmp_path)}],rules=[{"type":"prefix","value":"Neu - "}])
 assert result["status"]=="preview_ready"
 assert result["summary"]["item_count"]==2
 assert all(x["change_source"]=="prefix" for x in result["changes"])

def test_duplicate_targets(tmp_path):
 a=tmp_path/"A.mkv"; b=tmp_path/"B.mkv"; a.write_text("a"); b.write_text("b")
 rules=[{"type":"replace","old":"A","new":"Same"},{"type":"replace","old":"B","new":"Same"}]
 result=RenamePreviewService(RenamerBackendRegistry(tmp_path)).create_preview(items=[{"path":str(a)},{"path":str(b)}],rules=rules)
 assert result["status"]=="conflicts_found"

def test_missing_paths_are_skipped(tmp_path):
 result=RenamePreviewService(RenamerBackendRegistry(tmp_path)).create_preview(items=[{"path":str(tmp_path/"missing.mkv")}],rules=[])
 assert result["summary"]["skipped_count"]==1
