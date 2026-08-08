from pathlib import Path

from services.interactive_preview_service import InteractivePreviewService
from services.media_scanner import MediaScanner
from services.preview_decisions import PreviewDecisionStore
from services.relation_preview_service import RelationPreviewService

def test_preview_payload_and_lock(tmp_path: Path):
    root=tmp_path/"Serie"; root.mkdir()
    (root/"Show - S01E01.mkv").write_text("1",encoding="utf-8")
    (root/"Show - S01E02-E03.mkv").write_text("2",encoding="utf-8")
    items,_=MediaScanner().scan([{"path":str(root)}])
    payload=InteractivePreviewService(RelationPreviewService()).build(items,profile_id="plex")
    assert payload["summary"]["total"]==2
    assert payload["execution_locked"] is True
    assert any(r["relation_type"]=="multi_episode" for r in payload["rows"])

def test_group_by_season(tmp_path: Path):
    root=tmp_path/"Serie"; root.mkdir()
    (root/"Show - S02E01.mkv").write_text("1",encoding="utf-8")
    items,_=MediaScanner().scan([{"path":str(root)}])
    payload=InteractivePreviewService(RelationPreviewService()).build(items)
    assert payload["groups"][0]["key"]=="series:season:02"

def test_decision_store_memory_only():
    store=PreviewDecisionStore()
    store.set("abc",state="accepted")
    assert store.get("abc")["state"]=="accepted"
    store.clear()
    assert store.all()==[]

def test_manual_decision():
    value=PreviewDecisionStore().set("abc",state="manual",manual_name="Neu.mkv")
    assert value["manual_name"]=="Neu.mkv"

def test_invalid_decision_rejected():
    store=PreviewDecisionStore()
    try:
        store.set("abc",state="execute-now")
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError erwartet")

def test_ui_panel_present():
    html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
    assert 'id="relation-preview-v058"' in html
    assert 'id="mh-profile-select"' in html
    assert "Rename/Merge/Split" in html
