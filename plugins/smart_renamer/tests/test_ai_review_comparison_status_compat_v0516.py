from services.ai_review_comparison import AIReviewComparisonService

def test_normal_differences_stay_different():
    r=AIReviewComparisonService().compare(
        {"media_type":"movie","title":"Batman","year":"1989","confidence":0.82},
        {"available":True,"confidence":0.91,"structured_recommendation":{
            "candidate_id":"movie-2022","candidate_valid":True,
            "fields":{"media_type":"movie","title":"The Batman","year":"2022"},
            "confidence":0.91,"rationale":"Andere Fassung erkannt."}}
    )
    assert r["status"]=="different"

def test_episode_name_mismatch_is_conflict():
    r=AIReviewComparisonService().compare(
        {"proposed_name":"12 Monkeys - S03E01.mkv"},
        {"available":True,"suggested_name":"12 Monkeys - S02E01.mkv",
         "structured_recommendation":{"fields":{},"suggested_name":"12 Monkeys - S02E01.mkv"}}
    )
    assert r["status"]=="conflict"
    assert "season" in r["conflict_fields"]
