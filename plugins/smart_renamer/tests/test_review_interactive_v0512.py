from pathlib import Path
from services.review_service import ReviewService
from services.ai_review_bridge import AIReviewBridge

def test_split_episode_reason():
    r=ReviewService().classify({"relation_type":"split_episode","confidence":0.8,"review_required":True})
    assert r[0]["code"]=="split_episode"

def test_multi_episode_requires_review():
    assert ReviewService().needs_human_review({"relation_type":"multi_episode","review_required":False}) is True

def test_safe_single_no_review():
    assert ReviewService().needs_human_review({"relation_type":"single","review_required":False}) is False

def test_low_confidence_reason():
    r=ReviewService().classify({"relation_type":"single","confidence":0.5,"review_required":True})
    assert any(x["code"]=="low_confidence" for x in r)

def test_ai_optional():
    r=AIReviewBridge().analyze({"x":1}); assert r["available"] is False and r["requires_human_confirmation"] is True

def test_ai_provider_never_autoconfirms():
    b=AIReviewBridge({"ai.rename_review":lambda p:{"provider":"mock","recommendation":"multi_episode","confidence":0.88,"rationale":"test"}})
    r=b.analyze({}); assert r["available"] and r["provider"]=="mock" and r["requires_human_confirmation"] is True

def test_ui_mentions_ai_review():
    html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
    assert "KI-Review" in html and "ai.rename_review" in html

def test_version_0512():
    import json
    data=json.loads((Path(__file__).resolve().parents[1]/"plugin.json").read_text(encoding="utf-8")); assert data["version"]=="0.5.12"
