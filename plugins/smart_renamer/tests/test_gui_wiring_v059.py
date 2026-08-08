from pathlib import Path
import pytest
from services.gui_preview_session import GUIPreviewSession
from services.optional_preview_integrations import OptionalPreviewIntegrations
from services.preview_decisions import PreviewDecisionStore

def test_multi_selection_and_clear():
    session=GUIPreviewSession()
    assert session.set_selection(["a","b"])["selected_ids"]==["a","b"]
    assert session.toggle_selection("a")["selected_ids"]==["b"]
    assert session.clear_selection()["selected_ids"]==[]

def test_bulk_preview_decision():
    store=PreviewDecisionStore();session=GUIPreviewSession(store)
    session.set_selection(["a","b"]);session.bulk_decision("accepted")
    assert {v["state"] for v in store.all()}=={"accepted"}

def test_manual_name_preview_only():
    session=GUIPreviewSession()
    value=session.apply_manual_name("abc","Neu.mkv")
    assert value["state"]=="manual"
    assert session.snapshot()["execution_locked"] is True

def test_empty_manual_name_rejected():
    with pytest.raises(ValueError):
        GUIPreviewSession().apply_manual_name("abc"," ")

def test_filter_sort_validation():
    session=GUIPreviewSession()
    assert session.set_status_filter("review")["status_filter"]=="review"
    assert session.set_sort("confidence","desc")["sort_direction"]=="desc"
    with pytest.raises(ValueError): session.set_status_filter("maybe")
    with pytest.raises(ValueError): session.set_sort("wrong")

def test_optional_integrations_absent_by_default():
    assert OptionalPreviewIntegrations().status()=={"metadata_editor":False,"ai_assistant":False}

def test_optional_integrations_when_available():
    bridge=OptionalPreviewIntegrations({
      "metadata.preview":lambda p:{"metadata":p["x"]},
      "ai.rename_suggestion":lambda p:{"suggestion":p["x"]},
    })
    assert bridge.status()=={"metadata_editor":True,"ai_assistant":True}
    assert bridge.metadata_preview({"x":1})=={"metadata":1}
    assert bridge.ai_suggestion({"x":2})=={"suggestion":2}

def test_gui_v059_controls_present_and_v058_compatibility_kept():
    root=Path(__file__).resolve().parents[1]
    html=(root/"index.html").read_text(encoding="utf-8")
    js=(root/"assets/js/gui_wiring.js").read_text(encoding="utf-8")
    assert 'id="relation-preview-v058"' in html
    assert 'data-ui-version="0.5.9"' in html
    assert 'id="mh-status-filter"' in html
    assert 'id="mh-sort-by"' in html
    assert 'id="mh-select-visible"' in html
    assert "selectedIds" in js
