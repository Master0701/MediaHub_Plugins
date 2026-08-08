from pathlib import Path
import json

from services.review_priority import ReviewPriorityService


def test_conflict_gets_critical_priority():
    result=ReviewPriorityService().classify({
        "status":"conflict","relation_type":"split_episode","confidence":0.8,"review_required":True
    })
    assert result["level"]=="critical"
    assert result["score"]>=70


def test_safe_high_confidence_is_low_priority():
    result=ReviewPriorityService().classify({
        "relation_type":"single","confidence":0.97,"review_required":False
    })
    assert result["level"]=="low"


def test_low_confidence_increases_priority():
    low=ReviewPriorityService().classify({"relation_type":"single","confidence":0.5})
    high=ReviewPriorityService().classify({"relation_type":"single","confidence":0.95})
    assert low["score"]>high["score"]


def test_split_movie_is_prioritized():
    result=ReviewPriorityService().classify({
        "relation_type":"split_movie","confidence":0.9,"review_required":True
    })
    assert result["score"]>=45


def test_rows_sorted_highest_priority_first():
    rows=ReviewPriorityService().enrich_rows([
        {"original_name":"safe.mkv","relation_type":"single","confidence":0.99},
        {"original_name":"problem.mkv","status":"conflict","relation_type":"split_episode","confidence":0.5,"review_required":True},
    ])
    assert rows[0]["original_name"]=="problem.mkv"
    assert rows[0]["priority_score"]>rows[1]["priority_score"]


def test_priority_never_grants_execution():
    result=ReviewPriorityService().classify({"status":"conflict","confidence":0.1})
    assert "execution_allowed" not in result


def test_web_and_desktop_priority_controls_present():
    root=Path(__file__).resolve().parents[1]
    plugin=(root/"plugin.py").read_text(encoding="utf-8")
    html=(root/"index.html").read_text(encoding="utf-8")
    js=(root/"assets/js/interactive_preview.js").read_text(encoding="utf-8")
    assert '"Priorität"' in plugin
    assert 'id="mh-priority-filter"' in html
    assert 'id="mh-priority-sort"' in html
    assert "priority_score" in js


def test_version_0516():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/"plugin.json").read_text(encoding="utf-8"))
    assert data["version"]=="0.5.16"
